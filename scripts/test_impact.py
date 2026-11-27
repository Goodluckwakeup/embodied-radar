import datetime as dt
import json
import unittest
from unittest.mock import patch

import collect
from daily import assess_impact, build_edition, fingerprint, prioritize
from subscriptions import PaperLinks, official_papers
from test_daily import papers

STAMP = '2026-11-27T00:00:00Z'


def rate(instructions, source):
    return json.dumps([dict(id=row['id'], score=18, reason='摘要显示可复用的机器人方法，但实际泛化范围仍需核对全文实验。') for row in json.loads(source)])


class ImpactTests(unittest.TestCase):
    def test_impact_cache_and_content_invalidation(self):
        rows = papers(12)
        self.assertEqual(assess_impact(rows, [], STAMP, {}, rate, 'test')['count'], 12)
        with patch('test_impact.rate', side_effect=AssertionError('cache missed')) as cached:
            self.assertEqual(assess_impact(rows, [], STAMP, {}, cached, 'test')['count'], 0)
        rows[0]['abstract'] += ' revised'
        self.assertEqual(assess_impact(rows, [], STAMP, {}, rate, 'test')['count'], 1)
        self.assertEqual(assess_impact(rows, [], STAMP, {}, rate, 'other-model')['count'], 12)

    def test_invalid_batch_never_partially_mutates(self):
        rows = papers(12)
        invalid = lambda *_: json.dumps([dict(id=str(i), score=99 if i == 11 else 10, reason='reason') for i in range(12)])
        self.assertEqual(assess_impact(rows, [], STAMP, {}, invalid, 'test')['state'], 'partial')
        self.assertFalse(any('impact_assessment' in r for r in rows))

    def test_influence_affects_selection_and_only_selected_summarized(self):
        rows = papers(30)
        for row in rows:
            row['impact_assessment'] = dict(score=20 if row['id'] == '29' else 1, reason='reason', content_hash=fingerprint(row))
        edition = build_edition(rows, [], STAMP, {})
        self.assertEqual(edition['items'][0]['id'], '29')
        self.assertEqual(len(prioritize(rows, edition)), 12)
        with patch.dict(collect.os.environ, {'OPENAI_API_KEY':'test','OPENAI_MODEL':'test'}, clear=True), patch.object(collect, 'generate_text', return_value='摘要'), patch.object(collect, 'assess_impact', return_value={'source':'潜在影响力评分','state':'ok'}):
            collect.prepare_daily({'articles':rows}, STAMP, {'max_summaries_per_run':100})
        self.assertEqual(sum(bool(r.get('summary_zh')) for r in rows), 12)

    def test_official_links_reject_lookalike_domains(self):
        parser = PaperLinks()
        parser.feed('<a href="https://arxiv.org/abs/2611.12345v2">yes</a><a href="https://arxiv.org.evil.test/abs/2611.11111">no</a>')
        self.assertEqual(parser.ids, {'2611.12345'})

    def test_official_metadata_and_provenance_merge(self):
        xml = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>https://arxiv.org/abs/2611.12345v1</id><title>Robot manipulation</title><summary>Robot experiments</summary><published>2026-11-25T00:00:00Z</published><updated>2026-11-25T00:00:00Z</updated></entry></feed>'
        def fetch(url):
            return xml if 'export.arxiv.org' in url else b'<a href="https://arxiv.org/abs/2611.12345">Paper</a>'
        rows = official_papers({'name':'Lab A','url':'https://example.org'}, dt.datetime(2026,11,20,tzinfo=dt.timezone.utc), fetch, collect.article)
        first = collect.merge([], rows, STAMP)
        second = dict(rows[0], official_sources=['Lab B'])
        merged = collect.merge(first, [second], STAMP)
        self.assertEqual(merged[0]['official_sources'], ['Lab A','Lab B'])
        self.assertEqual(merged[0]['kind'], '论文')


if __name__ == '__main__':
    unittest.main()
