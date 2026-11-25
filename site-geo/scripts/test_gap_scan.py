import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gap_scan as g


def answer(queries, retrieved=(), cited=(), md=''):
    return {'tasks': [{'result': [{'fan_out_queries': list(queries), 'model': 'gpt-6', 'markdown': md,
                                   'search_results': [{'url': u} for u in retrieved],
                                   'sources': [{'url': u} for u in cited]}]}]}


class SplitId(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(g.split_id('church-bell--kw'), ('church-bell', 'kw'))
        self.assertEqual(g.split_id('unblur-video--tool--2'), ('unblur-video', 'tool'))
        self.assertEqual(g.split_id('low-light--r2'), ('low-light', ''))
        self.assertEqual(g.split_id('phone--notification--n1'), ('phone', 'notification'))
        self.assertEqual(g.split_id('cartoon'), ('cartoon', ''))


class Judge(unittest.TestCase):
    def j(self, **kw):
        return g.judge(g.load_answer_dict(answer(**kw)), 'example.com', 'example')

    def test_verdicts(self):
        self.assertEqual(self.j(queries=[])[0], 'no-search')
        self.assertEqual(self.j(queries=[], md='Example does it')[0], 'wins')
        self.assertEqual(self.j(queries=['q'], cited=['https://www.example.com/a'])[0], 'wins')
        v, seen = self.j(queries=['q'], retrieved=['https://example.com/tools/x/?utm=1'], cited=['https://other.io/'])
        self.assertEqual((v, seen), ('retrieved-not-named', ['/tools/x']))
        self.assertEqual(self.j(queries=['q'], cited=['https://other.io/'])[0], 'gap')


class Classify(unittest.TestCase):
    def test_need_takes_best_run_and_styles(self):
        with tempfile.TemporaryDirectory() as d:
            for name, body in {'bee--dl--1': answer(['q'], cited=['https://p.com/']),
                               'bee--dl--2': answer(['q'], cited=['https://example.com/sounds/bee']),
                               'bee--kw--1': answer([])}.items():
                json.dump(body, open(os.path.join(d, name + '.json'), 'w'))
            rows, styles, agree = g.classify(d, 'example.com')
        self.assertEqual(rows[0]['verdict'], 'wins')
        self.assertEqual(rows[0]['own_pages'], ['/sounds/bee'])
        self.assertEqual((styles['dl']['n'], styles['kw']['searched']), (2, 0))
        self.assertEqual((agree['dl:pairs'], agree['dl:same']), (1, 0))


class ProbeBilling(unittest.TestCase):
    def test_idem_key_stable_per_file_and_payload(self):
        k = g.idem_key('raw/a--1.json', {'keyword': 'q'})
        self.assertEqual(k, g.idem_key('raw/a--1.json', {'keyword': 'q'}))
        self.assertNotEqual(k, g.idem_key('raw/a--2.json', {'keyword': 'q'}))
        self.assertNotEqual(k, g.idem_key('raw/a--1.json', {'keyword': 'q2'}))

    def test_cost_guard_and_skip_saved(self):
        calls = []
        orig = g.run_glasser
        g.run_glasser = lambda *a: calls.append(a[4]) or ('Succeeded', '$0.004')
        try:
            with tempfile.TemporaryDirectory() as d:
                jobs = os.path.join(d, 'jobs.tsv'); out = os.path.join(d, 'raw')
                open(jobs, 'w').write(''.join(f'n{i}--1\tq{i}\n' for i in range(300)))
                with self.assertRaises(SystemExit):
                    g.main(['probe', '--jobs', jobs, '--out', out])
                self.assertEqual(calls, [])
                open(os.path.join(out, 'n0--1.json'), 'w').write('{}')
                g.main(['probe', '--jobs', jobs, '--out', out, '--yes', '--parallel', '2'])
                self.assertEqual(len(calls), 299)
        finally:
            g.run_glasser = orig


class Inventory(unittest.TestCase):
    def test_finds_pages_linked_only_from_deeper_pages_and_llms(self):
        pages = {
            'https://ex.com/robots.txt': 'Sitemap: https://ex.com/sitemap.xml',
            'https://ex.com/sitemap.xml': '<urlset><url><loc>https://ex.com/sounds/mechanical-siren</loc></url></urlset>',
            'https://ex.com/sounds/mechanical-siren': '<a href="/sound-effects/ambulance-siren">a</a>',
            'https://ex.com/llms.txt': '- [Camera](https://ex.com/sound-effects/rapid-camera-shutter)',
            'https://ex.com/sound-effects': '<a href="/sound-effects/police-siren">p</a>',
        }
        orig = g.fetch
        g.fetch = lambda url, timeout=20: pages.get(url, '')
        try:
            paths, maps, hubs = g.inventory('https://ex.com')
        finally:
            g.fetch = orig
        self.assertEqual(hubs, ['/sound-effects'])
        for p in ('/sound-effects/ambulance-siren', '/sound-effects/rapid-camera-shutter', '/sound-effects/police-siren', '/sounds/mechanical-siren'):
            self.assertIn(p, paths)


if __name__ == '__main__':
    unittest.main()
