#!/usr/bin/env python3
"""Offline checks for the parts that past reports got wrong: python3 -m unittest test_adsense_facts (from scripts/)."""
import unittest

from adsense_facts import ad_state, canonical_of, main_html, parse_sitemap, robots_blocks_google, robots_disallows, word_count


class AdState(unittest.TestCase):
    def test_a_verification_tag_is_not_ad_code(self):
        state = ad_state('<head><meta name="google-adsense-account" content="ca-pub-1234567890"></head>')
        self.assertEqual(state["state"], "verification-only")
        self.assertFalse(state["ad_script"])

    def test_the_ad_script_is_ad_code(self):
        state = ad_state('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1234567890"></script>')
        self.assertEqual(state["state"], "ad-script")

    def test_no_ad_traces(self):
        self.assertEqual(ad_state("<html><body>hello</body></html>")["state"], "none")


class Sitemap(unittest.TestCase):
    def test_an_index_returns_its_children_not_pages(self):
        children, pages = parse_sitemap('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://a.test/core.xml</loc></sitemap><sitemap><loc>https://a.test/more.xml</loc></sitemap></sitemapindex>')
        self.assertEqual(children, ["https://a.test/core.xml", "https://a.test/more.xml"])
        self.assertEqual(pages, [])

    def test_a_urlset_returns_pages(self):
        children, pages = parse_sitemap('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://a.test/x</loc></url></urlset>')
        self.assertEqual((children, pages), ([], ["https://a.test/x"]))

    def test_broken_xml_is_empty(self):
        self.assertEqual(parse_sitemap("<html>not found</html"), ([], []))


class Robots(unittest.TestCase):
    def test_a_partial_disallow_does_not_block(self):
        self.assertEqual(robots_blocks_google("User-agent: *\nDisallow: /admin/\n"), [])

    def test_a_full_disallow_for_adsense_is_found(self):
        self.assertEqual(robots_blocks_google("User-agent: Mediapartners-Google\nDisallow: /\n"), ["mediapartners-google"])

    def test_grouped_agents_share_rules(self):
        self.assertEqual(robots_blocks_google("User-agent: GPTBot\nUser-agent: Googlebot\nDisallow: /\n"), ["googlebot"])


class QueryPages(unittest.TestCase):
    ROBOTS = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nDisallow: /studio?\nDisallow: /*?format=\nAllow: /studio?keep=\n"

    def test_a_prefix_rule_covers_the_query_url(self):
        self.assertTrue(robots_disallows(self.ROBOTS, "https://a.test/studio?base=x"))

    def test_a_wildcard_rule_matches(self):
        self.assertTrue(robots_disallows(self.ROBOTS, "https://a.test/sounds/x?format=wav"))

    def test_the_longer_allow_wins(self):
        self.assertFalse(robots_disallows(self.ROBOTS, "https://a.test/studio?keep=1"))

    def test_rules_for_another_bot_do_not_count(self):
        self.assertFalse(robots_disallows(self.ROBOTS, "https://a.test/sounds/x"))

    def test_canonical_resolves_against_the_page(self):
        self.assertEqual(canonical_of('<link rel="canonical" href="/x">', "https://a.test/x?y=1"), "https://a.test/x")


class Words(unittest.TestCase):
    def test_main_leaves_out_navigation(self):
        self.assertEqual(main_html("<nav>a b c</nav><main>real text</main><footer>d</footer>"), "<main>real text</main>")
        self.assertIsNone(main_html("<div>no main</div>"))

    def test_latin_and_cjk(self):
        self.assertEqual(word_count("free sound effects"), 3)
        self.assertEqual(word_count("免费音效"), 2)


if __name__ == "__main__":
    unittest.main()
