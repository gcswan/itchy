import unittest
from pathlib import Path

from scratchiq.scripts.fetch_nc_data import parse_html


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FetchNcDataTests(unittest.TestCase):
    def test_parse_current_databox_structure(self):
        html = (FIXTURES_DIR / "nc_prizes_remaining_fragment.html").read_text(encoding="utf-8")

        data = parse_html(html, source="fixture://nc")

        self.assertEqual(data["game_count"], 2)
        games_by_number = {game["number"]: game for game in data["games"]}

        self.assertEqual(set(games_by_number), {995, 996})
        self.assertEqual(games_by_number[996]["price"], 10)
        self.assertEqual(games_by_number[996]["name"], "$1,000,000 Triple Play")
        self.assertGreaterEqual(len(games_by_number[996]["tiers"]), 10)

    def test_rejects_page_chrome_without_games(self):
        html = (FIXTURES_DIR / "nc_prizes_remaining_chrome_only.html").read_text(encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "Could not parse any valid scratch-off games"):
            parse_html(html, source="fixture://chrome-only")


if __name__ == "__main__":
    unittest.main()
