#!/usr/bin/env python3
"""
Fetch and parse NC Education Lottery scratch-off prize data.

Usage:
    python fetch_nc_data.py                  # prints JSON to stdout
    python fetch_nc_data.py -o data.json     # writes to file
    python fetch_nc_data.py --pretty         # pretty-printed JSON
    python fetch_nc_data.py --compute-ev --budget 50  # computes EV and optimal buy

The script fetches https://nclottery.com/scratch-off-prizes-remaining,
parses every active scratch-off game's prize table, and outputs structured
JSON with game metadata and per-tier prize data.
"""

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser


DATA_URL = "https://nclottery.com/scratch-off-prizes-remaining"
GAME_CONTAINER_CLASSES = {"box", "cloudfx", "databox"}


def _normalize_whitespace(text):
    return " ".join(text.split())


def _parse_int(text):
    match = re.search(r"\d[\d,]*", text or "")
    if not match:
        return None
    return int(match.group().replace(",", ""))


def _parse_float(text):
    match = re.search(r"\d[\d,]*(?:\.\d+)?", text or "")
    if not match:
        return None
    return float(match.group().replace(",", ""))


def _extract_price_from_classes(classes):
    for token in classes:
        if token.startswith("price_"):
            return _parse_int(token.split("_", 1)[1])
    return None


def _is_valid_tier(tier):
    return (
        tier["prize"] is not None
        and tier["odds"] is not None
        and tier["total_prizes"] is not None
        and tier["remaining_prizes"] is not None
        and tier["odds"] > 0
        and tier["total_prizes"] > 0
        and tier["remaining_prizes"] >= 0
    )


def _is_valid_game(game):
    if not game["name"] or not game["number"] or not game["price"]:
        return False

    if len(game["tiers"]) < 3:
        return False

    chrome_markers = ("price:", "prizes remaining", "win up to")
    lowered_name = game["name"].lower()
    if any(marker in lowered_name for marker in chrome_markers):
        return False

    return all(_is_valid_tier(tier) for tier in game["tiers"])


def _dedupe_games(games):
    deduped = {}
    for game in games:
        existing = deduped.get(game["number"])
        if existing is None or len(game["tiers"]) > len(existing["tiers"]):
            deduped[game["number"]] = game
    return list(sorted(deduped.values(), key=lambda game: game["number"]))


class LotteryParser(HTMLParser):
    """Parse the NC Lottery scratch-off page using the current databox structure."""

    def __init__(self):
        super().__init__()
        self.games = []
        self._current_game = None
        self._game_div_depth = 0
        self._capture_field = None
        self._capture_parts = []
        self._in_tbody = False
        self._in_row = False
        self._in_cell = False
        self._current_row = []
        self._current_cell_parts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = set(attrs_dict.get("class", "").split())

        if tag == "div":
            if self._current_game is None and GAME_CONTAINER_CLASSES.issubset(classes):
                price = _extract_price_from_classes(classes)
                if price is not None:
                    self._current_game = {
                        "name": "",
                        "number": None,
                        "price": price,
                        "tiers": [],
                    }
                    self._game_div_depth = 1
                    return

            if self._current_game is not None:
                self._game_div_depth += 1

        if self._current_game is None:
            return

        if tag == "span":
            if "gamename" in classes:
                self._start_capture("name")
            elif "gamenumber" in classes:
                self._start_capture("number")

        elif tag == "tbody":
            self._in_tbody = True

        elif tag == "tr" and self._in_tbody:
            self._in_row = True
            self._current_row = []

        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._current_cell_parts = []

    def handle_endtag(self, tag):
        if self._current_game is None:
            return

        if tag == "span" and self._capture_field is not None:
            text = _normalize_whitespace("".join(self._capture_parts))
            if self._capture_field == "name" and text:
                self._current_game["name"] = text
            elif self._capture_field == "number":
                self._current_game["number"] = _parse_int(text)
            self._capture_field = None
            self._capture_parts = []

        elif tag == "td" and self._in_cell:
            self._in_cell = False
            text = _normalize_whitespace("".join(self._current_cell_parts))
            self._current_row.append(text)
            self._current_cell_parts = []

        elif tag == "tr" and self._in_row:
            self._in_row = False
            tier = self._build_tier(self._current_row)
            if tier is not None:
                self._current_game["tiers"].append(tier)
            self._current_row = []

        elif tag == "tbody":
            self._in_tbody = False

        elif tag == "div":
            self._game_div_depth -= 1
            if self._game_div_depth == 0:
                if _is_valid_game(self._current_game):
                    self.games.append(self._current_game)
                self._current_game = None

    def handle_data(self, data):
        if self._capture_field is not None:
            self._capture_parts.append(data)
        if self._in_cell:
            self._current_cell_parts.append(data)

    def _start_capture(self, field_name):
        self._capture_field = field_name
        self._capture_parts = []

    def _build_tier(self, row):
        if len(row) < 4:
            return None

        tier = {
            "prize": _parse_float(row[0]),
            "odds": _parse_float(row[1]),
            "total_prizes": _parse_int(row[2]),
            "remaining_prizes": _parse_int(row[3]),
        }
        return tier if _is_valid_tier(tier) else None


def parse_with_regex(html):
    """Fallback parser that targets the databox/table structure directly."""
    games = []

    block_pattern = re.compile(
        r'(<div class="box cloudfx databox price_\d+">.*?</table>\s*</div>)',
        re.DOTALL,
    )
    row_pattern = re.compile(r"<tr>\s*(.*?)\s*</tr>", re.DOTALL)
    cell_pattern = re.compile(r"<td>\s*(.*?)\s*</td>", re.DOTALL)

    for block in block_pattern.findall(html):
        class_match = re.search(r'class="box cloudfx databox (price_\d+)"', block)
        name_match = re.search(r'<span class="gamename">.*?<a [^>]*>(.*?)</a>', block, re.DOTALL)
        number_match = re.search(r'<span class="gamenumber"><b>Game Number:</b>\s*(\d+)</span>', block)

        game = {
            "name": _normalize_whitespace(re.sub(r"<[^>]+>", "", name_match.group(1))) if name_match else "",
            "number": int(number_match.group(1)) if number_match else None,
            "price": _extract_price_from_classes({class_match.group(1)}) if class_match else None,
            "tiers": [],
        }

        tbody_match = re.search(r"<tbody>(.*?)</tbody>", block, re.DOTALL)
        if tbody_match:
            for row_html in row_pattern.findall(tbody_match.group(1)):
                cells = [
                    _normalize_whitespace(re.sub(r"<[^>]+>", "", cell))
                    for cell in cell_pattern.findall(row_html)
                ]
                if len(cells) >= 4:
                    tier = {
                        "prize": _parse_float(cells[0]),
                        "odds": _parse_float(cells[1]),
                        "total_prizes": _parse_int(cells[2]),
                        "remaining_prizes": _parse_int(cells[3]),
                    }
                    if _is_valid_tier(tier):
                        game["tiers"].append(tier)

        if _is_valid_game(game):
            games.append(game)

    return _dedupe_games(games)


def parse_html(html, source=DATA_URL):
    parser = LotteryParser()
    parser.feed(html)

    games = _dedupe_games(parser.games)
    if not games:
        games = parse_with_regex(html)

    if not games:
        raise ValueError("Could not parse any valid scratch-off games from the NC Lottery page.")

    return {
        "source": source,
        "games": games,
        "game_count": len(games),
    }


def fetch_and_parse(url=DATA_URL):
    """Fetch the NC lottery page and parse game data."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ScratchIQ/1.0 (lottery data fetcher)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    return parse_html(html, source=url)


def compute_ev_metrics(games, budget=None):
    computed_games = []
    
    for game in games:
        if not game.get("tiers"):
            continue
            
        tiers = game["tiers"]
        
        tier_estimates = [t["odds"] * t["total_prizes"] for t in tiers if t["odds"] > 0 and t["total_prizes"] > 0]
        if not tier_estimates:
            continue
            
        highest_volume_tier = max(tiers, key=lambda t: t["total_prizes"])
        total_tickets = highest_volume_tier["odds"] * highest_volume_tier["total_prizes"]
        
        max_estimate = max(tier_estimates)
        min_estimate = min(tier_estimates)
        if max_estimate == 0 or (max_estimate - min_estimate) / max_estimate > 0.05:
            game["ev_validation_error"] = "Ticket estimates across tiers differ by > 5%"
            continue
            
        mid_tiers = [t for t in tiers if 10 <= t["prize"] <= 50]
        if not mid_tiers:
            mid_tiers = tiers
        mid_tier_anchor = max(mid_tiers, key=lambda t: t["total_prizes"])
        
        if mid_tier_anchor["total_prizes"] == 0:
            continue
            
        pct_remaining = mid_tier_anchor["remaining_prizes"] / mid_tier_anchor["total_prizes"]
        
        if pct_remaining < 0.15:
            game["ev_validation_error"] = "Pool depleted (< 15% remaining)"
            continue
            
        top_tier = max(tiers, key=lambda t: t["prize"])
        if top_tier["remaining_prizes"] <= 0:
            game["ev_validation_error"] = "All top prizes claimed"
            continue
            
        if budget is not None and game["price"] > budget:
            game["ev_validation_error"] = "Ticket price exceeds budget"
            continue
            
        remaining_tickets = total_tickets * pct_remaining
        if remaining_tickets <= 0:
            continue
            
        total_prize_pool = sum(t["prize"] * t["total_prizes"] for t in tiers)
        payout_ratio = total_prize_pool / (total_tickets * game["price"])
        
        if not (0.50 <= payout_ratio <= 0.90):
            game["ev_validation_error"] = f"Abnormal payout ratio: {payout_ratio:.2f}"
            continue

        ev = 0
        p_win = 0
        for t in tiers:
            net_value = t["prize"] * 0.7075 if t["prize"] > 600 else t["prize"]
            prob = t["remaining_prizes"] / remaining_tickets
            ev += net_value * prob
            p_win += prob
            
        ev_per_dollar = ev / game["price"] if game["price"] > 0 else 0
        
        top_remaining_pct = top_tier["remaining_prizes"] / top_tier["total_prizes"] if top_tier["total_prizes"] > 0 else 0
        top_concentration = top_remaining_pct / pct_remaining if pct_remaining > 0 else 0
        
        game["metrics"] = {
            "total_tickets": total_tickets,
            "pct_remaining": pct_remaining,
            "remaining_tickets": remaining_tickets,
            "ev": ev,
            "ev_per_dollar": ev_per_dollar,
            "p_win": p_win,
            "top_concentration": top_concentration,
            "payout_ratio": payout_ratio
        }
        computed_games.append(game)
        
    computed_games.sort(key=lambda g: g["metrics"]["ev_per_dollar"], reverse=True)
    
    optimal_buy = []
    budget_left = budget if budget is not None else float('inf')
    total_expected_payout = 0
    total_spend = 0
    overall_no_win_prob = 1.0
    
    if budget is not None and budget > 0:
        for game in computed_games:
            price = game["price"]
            if price <= budget_left:
                count = int(budget_left // price)
                budget_left -= count * price
                spend = count * price
                expected_payout = count * game["metrics"]["ev"]
                
                total_spend += spend
                total_expected_payout += expected_payout
                overall_no_win_prob *= (1 - game["metrics"]["p_win"]) ** count
                
                optimal_buy.append({
                    "game_number": game["number"],
                    "name": game["name"],
                    "price": price,
                    "count": count,
                    "spend": spend,
                    "expected_payout": expected_payout
                })
                if budget_left <= 0:
                    break

    rankings = []
    for i, game in enumerate(computed_games):
        rank_entry = {
            "game_number": game["number"],
            "name": game["name"],
            "price": game["price"],
            "metrics": game["metrics"]
        }
        if i < 5:
            rank_entry["tiers"] = game["tiers"]
        rankings.append(rank_entry)
        
    return {
        "rankings": rankings,
        "optimal_buy": optimal_buy,
        "summary": {
            "total_spend": total_spend,
            "total_expected_payout": total_expected_payout,
            "net_expected_gain": total_expected_payout - total_spend,
            "return_rate": total_expected_payout / total_spend if total_spend > 0 else 0,
            "overall_p_any_win": 1.0 - overall_no_win_prob if total_spend > 0 else 0
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch NC Lottery scratch-off prize data")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--compute-ev", action="store_true", help="Compute EV metrics and output a summary instead of raw game data")
    parser.add_argument("--budget", type=int, help="Budget for EV optimization (only used with --compute-ev)")
    args = parser.parse_args()

    try:
        data = fetch_and_parse()
    except Exception as e:
        print(f"Error fetching lottery data: {e}", file=sys.stderr)
        sys.exit(1)

    if args.compute_ev:
        output_data = compute_ev_metrics(data["games"], args.budget)
    else:
        output_data = data

    indent = 2 if args.pretty else None
    json_str = json.dumps(output_data, indent=indent)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Wrote output to {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
