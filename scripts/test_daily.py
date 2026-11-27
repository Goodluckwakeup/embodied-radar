import copy
import unittest

from daily import build_edition, finish_edition, prioritize


def papers(count=30):
    return [dict(id=str(i), title='Robot manipulation framework ' + str(i),
                 abstract=('We introduce a robot benchmark with real world experiments, '
                           '25% improvement, generalization analysis and released code. ') * 2,
                 kind='论文', basis='论文摘要', topics=['VLA'],
                 published_at='2026-11-25T00:00:00Z', url='https://example.com/' + str(i))
            for i in range(count)]


class DailyTests(unittest.TestCase):
    def test_selection_and_score_bounds(self):
        rows = papers()
        edition = build_edition(rows, [], '2026-11-27T00:00:00Z', {})
        self.assertEqual(len(edition['items']), 12)
        self.assertEqual(sum(i['reading'] == 'deep' for i in edition['items']), 2)
        self.assertEqual(len({i['id'] for i in edition['items']}), 12)
        self.assertTrue(all(0 <= r['rating']['score'] <= 100 for r in rows))
        self.assertTrue(all(sum(r['rating']['components'].values()) == r['rating']['score'] for r in rows))

    def test_same_day_retry_preserves_selection_and_prioritizes_summaries(self):
        rows = papers()
        edition = build_edition(rows, [], '2026-11-27T00:00:00Z', {})
        retry = build_edition(list(reversed(rows)), [edition], '2026-11-27T03:00:00Z', {})
        self.assertEqual(edition['items'], retry['items'])
        ordered = prioritize(list(reversed(rows)), edition)
        self.assertEqual([i['id'] for i in edition['items']], [r['id'] for r in ordered[:12]])

    def test_beijing_day_boundary_excludes_recent_recommendations(self):
        rows = papers()
        first = build_edition(rows, [], '2026-11-27T15:59:00Z', {})
        second = build_edition(rows, [first], '2026-11-27T16:00:00Z', {})
        self.assertEqual(second['date'], '2026-11-28')
        self.assertFalse({i['id'] for i in first['items']} & {i['id'] for i in second['items']})

    def test_ineligible_sources_future_old_and_missing_dates(self):
        rows = papers(5)
        rows[0]['kind'] = '待核验'
        rows[1]['published_at'] = '2026-12-01'
        rows[2]['published_at'] = '2020-01-01'
        rows[3]['published_at'] = None
        rows[4]['abstract'] = 'too short'
        edition = build_edition(rows, [], '2026-11-27T00:00:00Z', {})
        self.assertEqual(edition['items'], [])

    def test_partial_summary_status_and_historical_snapshot(self):
        rows = papers(12)
        edition = build_edition(rows, [], '2026-11-27T00:00:00Z', {})
        data = {'articles': rows}
        finish_edition(data, edition)
        self.assertEqual(edition['state'], 'partial')
        for row in rows:
            row['summary_zh'] = '中文摘要'
        finish_edition(data, edition)
        self.assertEqual(edition['state'], 'complete')
        self.assertEqual(edition['summary_count'], 12)
        self.assertEqual(len(data['daily_editions']), 1)
        snapshot = copy.deepcopy(edition)
        rows[0]['abstract'] = 'changed'
        self.assertEqual(edition, snapshot)


if __name__ == '__main__':
    unittest.main()
