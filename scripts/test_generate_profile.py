import io
import json
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from xml.etree import ElementTree

from generate_profile import calendar_days, fetch_data, render_cards, streaks


def collection(counts=()):
    today = date(2026, 9, 23)
    return {
        "totalCommitContributions": 3,
        "totalIssueContributions": 0,
        "totalPullRequestContributions": 1,
        "totalPullRequestReviewContributions": 0,
        "contributionCalendar": {
            "totalContributions": sum(counts),
            "weeks": [{"contributionDays": [
                {"date": (today - timedelta(days=len(counts) - i - 1)).isoformat(),
                 "contributionCount": count} for i, count in enumerate(counts)
            ]}],
        },
    }


class ProfileTests(unittest.TestCase):
    def test_streak_allows_unfinished_today(self):
        days = calendar_days(collection([1, 2, 3, 0]), date(2026, 9, 23))
        self.assertEqual(streaks(days), (3, 3))
        self.assertEqual(len(days), 365)

    def test_streak_break_and_new_run(self):
        for counts, expected in [([1, 1, 0, 0], (0, 2)),
                                 ([1, 1, 1, 0, 1], (1, 3)),
                                 ([], (0, 0))]:
            self.assertEqual(streaks(calendar_days(collection(counts), date(2026, 9, 23))), expected)

    def test_render_empty_data_and_escape_languages(self):
        repo = {"languages": {"pageInfo": {"hasNextPage": False}, "edges": [
            {"size": 60, "node": {"name": "A&B"}},
            {"size": 40, "node": {"name": "Python"}},
        ]}}
        for repos in [[], [repo]]:
            cards = render_cards(collection(), repos, date(2026, 9, 23))
            self.assertEqual(len(cards), 4)
            for svg in cards.values():
                ElementTree.fromstring(svg)
            if repos:
                self.assertIn('A&amp;B: 60.0%', cards['top-languages.svg'])

    def test_pagination_and_api_errors(self):
        def response(next_page):
            return io.BytesIO(json.dumps({"data": {"user": {
                "contributionsCollection": collection(),
                "repositories": {"nodes": [{"stargazerCount": 1}],
                                 "pageInfo": {"hasNextPage": next_page, "endCursor": "page2"}},
            }}}).encode())
        with patch('generate_profile.urlopen', side_effect=[response(True), response(False)]) as request:
            _, repos = fetch_data('example', 'fake-token', date(2026, 9, 23))
            self.assertEqual(len(repos), 2)
            self.assertEqual(json.loads(request.call_args.args[0].data)['variables']['cursor'], 'page2')
        with patch('generate_profile.urlopen', return_value=io.BytesIO(b'{"errors":[{"message":"Denied"}]}')):
            with self.assertRaises(RuntimeError):
                fetch_data('example', 'fake-token', date(2026, 9, 23))

    def test_incomplete_languages_rejected(self):
        with self.assertRaises(RuntimeError):
            render_cards(collection(), [{"languages": {"pageInfo": {"hasNextPage": True}}}],
                         date(2026, 9, 23))


if __name__ == '__main__':
    unittest.main()
