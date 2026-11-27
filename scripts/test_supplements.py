import unittest
from unittest.mock import patch
import collect


class SupplementTests(unittest.TestCase):
    def test_arxiv_first_supplements_deduplicated_with_counts(self):
        events = []
        paper = collect.article('Robot VLA study', 'https://arxiv.org/abs/2611.10001',
                                'robot manipulation vision-language-action', 'arXiv', '论文',
                                '2026-11-25T00:00:00Z', '2026-11-25T00:00:00Z', basis='论文摘要')
        def primary(*args):
            events.append('arxiv')
            return [paper], True
        def supplement(spec, cutoff, *args):
            events.append('institution')
            self.assertEqual(cutoff.day, 28)  # October 28, 30 days before November 27.
            return [dict(paper, official_sources=[spec['name']]),
                    dict(paper, title='Another robot VLA study', url='https://arxiv.org/abs/2611.10002', official_sources=[spec['name']])]
        config = {'lookback_days':7, 'official_pages':[{'name':'Lab','url':'https://example.org'}]}
        with patch.object(collect, 'arxiv', side_effect=primary), patch.object(collect, 'official_papers', side_effect=supplement):
            rows, statuses, _ = collect.collect_sources([], config, '2026-11-27T00:00:00Z', no_search=True)
        self.assertEqual(events, ['arxiv', 'institution'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(statuses[0]['phase'], 'primary')
        self.assertEqual(statuses[1]['new_count'], 1)
        self.assertEqual(statuses[1]['matched_count'], 1)
        self.assertEqual(rows[0]['official_sources'], ['Lab'])

    def test_failed_primary_still_uses_institution_and_preserves_history(self):
        existing = collect.merge([], [collect.article('Robot VLA study', 'https://arxiv.org/abs/2611.10001',
                                                     'robot manipulation', 'arXiv', '论文', basis='论文摘要')], '2026-11-26T00:00:00Z')
        existing[0]['summary_zh'] = '已有摘要'
        config = {'lookback_days':7, 'official_pages':[{'name':'Lab','url':'https://example.org'}]}
        with patch.object(collect, 'arxiv', side_effect=TimeoutError), patch.object(collect, 'official_papers', return_value=[]) as supplement:
            rows, statuses, _ = collect.collect_sources(existing, config, '2026-11-27T00:00:00Z', no_search=True)
        supplement.assert_called_once()
        self.assertEqual(statuses[0]['state'], 'error')
        self.assertEqual(statuses[1]['state'], 'ok')
        self.assertEqual(rows[0]['summary_zh'], '已有摘要')


if __name__ == '__main__':
    unittest.main()
