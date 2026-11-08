import unittest
from unittest.mock import patch
import datetime as dt
import collect


class CollectorTests(unittest.TestCase):
    def test_revised_arxiv_does_not_duplicate_or_keep_stale_summary(self):
        first = collect.article('A VLA robot', 'https://arxiv.org/abs/2601.12345v1',
                                'vision-language-action robot', 'arXiv', '论文', updated='2026-01-01')
        rows = collect.merge([], [first], '2026-01-02')
        rows[0]['summary_zh'] = 'old'
        revision = dict(first, url='https://arxiv.org/abs/2601.12345v2', abstract='new text', updated_at='2026-01-03')
        result = collect.merge(rows, [revision], '2026-01-04')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['first_seen_at'], '2026-01-02')
        self.assertNotIn('summary_zh', result[0])

    def test_search_snippet_cannot_replace_paper(self):
        paper = collect.article('Robot world action model', 'https://arxiv.org/abs/2601.12345',
                                'world action model for robot', 'arXiv', '论文', basis='论文摘要')
        rows = collect.merge([], [paper], '2026-01-01')
        snippet = dict(paper, url='https://example.com/blog?utm_source=test', abstract='short',
                       kind='待核验', basis='搜索片段（待核验）')
        result = collect.merge(rows, [snippet], '2026-01-02')
        self.assertEqual(result[0]['basis'], '论文摘要')
        self.assertEqual(len(result[0]['links']), 2)

    def test_atom_feed_date_and_safe_links(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>VLA robot</title>
        <link href="https://example.org/paper"/><summary>vision-language-action</summary>
        <updated>2026-11-01T00:00:00Z</updated></entry></feed>'''
        with patch.object(collect, 'request', return_value=xml):
            rows = collect.feed({'url':'https://example.org/feed','name':'test','kind':'高校'},
                                dt.datetime(2026, 10, 31, tzinfo=dt.timezone.utc))
        self.assertEqual(len(rows), 1)
        self.assertEqual(collect.canonical('javascript:alert(1)'), '')


if __name__ == '__main__':
    unittest.main()
