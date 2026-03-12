#!/usr/bin/env python3
"""
Fetch and parse NC Education Lottery winner data from the Winners Highlights page.
"""

import argparse
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser

WINNERS_URL = "https://nclottery.com/Winners"

class WinnersParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.winners = []
        self._in_winner_box = False
        self._in_name = False
        self._in_location = False
        self._current_winner = {}
        self._current_data = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = set(attrs_dict.get("class", "").split())

        if tag == "div" and "box" in classes and "tile" in classes:
            self._in_winner_box = True
            self._current_winner = {}
            return
        
        if not self._in_winner_box:
            return

        if tag == "span" and "name" in classes:
            self._in_name = True
            self._current_data = []
        elif tag == "span" and "location" in classes:
            self._in_location = True
            self._current_data = []

    def handle_endtag(self, tag):
        if not self._in_winner_box:
            return

        if tag == "span":
            text = " ".join("".join(self._current_data).split()).strip()
            if self._in_name:
                self._current_winner["name"] = text
                self._in_name = False
            elif self._in_location:
                self._current_winner["location_raw"] = text
                self._in_location = False
            self._current_data = []
        
        elif tag == "div":
            # The box tile has nested divs. We save only if we have collected name and location.
            if self._current_winner.get("name") and self._current_winner.get("location_raw"):
                self.winners.append(self._current_winner)
                self._current_winner = {}
                self._in_winner_box = False

    def handle_data(self, data):
        if self._in_name or self._in_location:
            self._current_data.append(data)

def fetch_winners(url=WINNERS_URL):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    
    parser = WinnersParser()
    parser.feed(html)
    
    # Cleanup locations
    for w in parser.winners:
        loc = w.get("location_raw", "")
        # Try to split by common patterns if they merged
        # Example: "Han-Dee Hugo # 10 Clinton, NC"
        if "NC" in loc:
            parts = loc.split(",")
            if len(parts) > 1:
                w["city"] = parts[0].strip().split()[-1] # Simple heuristic
                w["retailer"] = loc.replace(parts[-1], "").replace(",", "").strip()
            else:
                w["retailer"] = loc
        else:
            w["retailer"] = loc

    return parser.winners

def main():
    parser = argparse.ArgumentParser(description="Fetch NC Lottery winner data")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    try:
        winners = fetch_winners()
        indent = 2 if args.pretty else None
        print(json.dumps(winners, indent=indent))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
