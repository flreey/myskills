from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "prepare_bundle.py"


class BundleFixture:
    def __init__(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "fixture@example.test")
        self.run_git("config", "user.name", "Fixture")

    def close(self) -> None:
        self.tempdir.cleanup()

    def run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            text=True,
            capture_output=True,
        )

    def write(self, relative_path: str, content: str | bytes) -> Path:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def commit_baseline(self) -> None:
        self.run_git("add", ".")
        self.run_git("commit", "-q", "-m", "fixture baseline")

    def bundle(
        self,
        output_name: str,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                "--output-dir",
                str(self.root / output_name),
                "--task-id",
                "fixture",
                *extra,
            ],
            check=False,
            text=True,
            capture_output=True,
        )


class PrepareBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = BundleFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_builds_deterministic_bundle_and_records_dirty_source(self) -> None:
        self.fixture.write("src/main.py", "def answer():\n    return 42\n")
        self.fixture.write(".gitignore", "node_modules/\n")
        self.fixture.commit_baseline()
        self.fixture.write("src/main.py", "def answer():\n    return 43\n")
        self.fixture.write("src/new.py", "VALUE = 'new'\n")
        self.fixture.write("node_modules/pkg/index.js", "ignored\n")
        self.fixture.write(".env", "API_KEY=real-looking-but-filename-excluded\n")
        self.fixture.write("state.sqlite", b"SQLite format 3\x00private")
        self.fixture.write(".codex/browser-state/session.json", "{}\n")

        first = self.fixture.bundle("out-a", "--include", ".")
        second = self.fixture.bundle("out-b", "--include", ".")

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        first_summary = json.loads(first.stdout)
        second_summary = json.loads(second.stdout)
        self.assertTrue(first_summary["source_dirty"])
        self.assertEqual(first_summary["archive_sha256"], second_summary["archive_sha256"])

        archive_path = Path(first_summary["archive"])
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            manifest = json.loads(archive.read("bundle-manifest.json"))

        self.assertIn("src/main.py", names)
        self.assertIn("src/new.py", names)
        self.assertNotIn(".env", names)
        self.assertNotIn("state.sqlite", names)
        self.assertNotIn(".codex/browser-state/session.json", names)
        self.assertNotIn("node_modules/pkg/index.js", names)
        excluded = {item["path"]: item["reason"] for item in manifest["selection"]["excluded"]}
        self.assertEqual(excluded[".env"], "sensitive-filename")
        self.assertEqual(excluded["state.sqlite"], "denied-file-type")
        self.assertEqual(
            excluded[".codex/browser-state/session.json"], "denied-directory"
        )

        expected_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        self.assertEqual(first_summary["archive_sha256"], expected_sha)
        sha_text = Path(first_summary["sha256_file"]).read_text(encoding="utf-8")
        self.assertTrue(sha_text.startswith(expected_sha))

    def test_content_secret_blocks_archive_and_redacts_value(self) -> None:
        secret = "ghp_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcd"
        self.fixture.write("src/config.py", f'TOKEN = "{secret}"\n')
        self.fixture.commit_baseline()

        result = self.fixture.bundle("blocked", "--include", "src")

        self.assertEqual(result.returncode, 3, result.stderr)
        summary = json.loads(result.stdout)
        report_path = Path(summary["report"])
        report_text = report_path.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["findings"][0]["path"], "src/config.py")
        self.assertNotIn(secret, report_text)
        self.assertEqual(list(report_path.parent.glob("*.zip")), [])

    def test_symlinks_and_binary_files_are_excluded(self) -> None:
        self.fixture.write("src/main.txt", "safe\n")
        internal = self.fixture.write("src/internal.txt", "internal\n")
        outside = self.fixture.root / "outside.txt"
        outside.write_text("outside secret\n", encoding="utf-8")
        (self.fixture.repo / "src/link.txt").symlink_to(outside)
        (self.fixture.repo / "src/internal-link.txt").symlink_to(internal)
        self.fixture.write("src/blob.bin", b"\x00\x01\x02")
        self.fixture.write("src/image.png", b"\x89PNG\r\n\x1a\n\x00secret")
        self.fixture.commit_baseline()

        result = self.fixture.bundle("out", "--include", "src")

        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        manifest = json.loads(Path(summary["manifest"]).read_text(encoding="utf-8"))
        excluded = {item["path"]: item["reason"] for item in manifest["selection"]["excluded"]}
        self.assertEqual(excluded["src/link.txt"], "symlink")
        self.assertEqual(excluded["src/internal-link.txt"], "symlink")
        self.assertEqual(excluded["src/blob.bin"], "unapproved-binary")
        self.assertEqual(excluded["src/image.png"], "unapproved-binary")

    def test_size_limit_blocks_archive(self) -> None:
        self.fixture.write("src/large.txt", "a" * 128)
        self.fixture.commit_baseline()

        result = self.fixture.bundle(
            "too-large",
            "--include",
            "src",
            "--max-bytes",
            "64",
        )

        self.assertEqual(result.returncode, 5, result.stderr)
        summary = json.loads(result.stdout)
        report = json.loads(Path(summary["report"]).read_text(encoding="utf-8"))
        self.assertEqual(report["reason"], "size-limit")
        self.assertEqual(list(Path(summary["report"]).parent.glob("*.zip")), [])

    def test_placeholder_assignment_does_not_trigger(self) -> None:
        self.fixture.write("config.example", 'api_key = "YOUR_API_KEY"\n')
        self.fixture.commit_baseline()

        result = self.fixture.bundle("out", "--include", "config.example")

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
