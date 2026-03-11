# ScratchIQ Skill Audit Report

**Date:** 2026-03-11
**Scope:** Math correctness, overall flow, eval coverage, parser reliability

---

## Executive Summary

ScratchIQ is an LLM skill that advises NC scratch-off lottery ticket purchases using live prize data, expected value math, and budget optimization. The skill specification is well-structured and the core math is sound. The live data parser correctly extracts 79 games from the current NC Lottery page. Eval scenarios cover the three main use cases but could be deepened with numeric oracle checks. Several minor math and flow issues remain worth addressing.

**Overall assessment: Solid foundation, ready for iteration with targeted improvements.**

---

## 1. Math Audit

### 1.1 Total Tickets Printed — ✅ Correct

```
total_tickets = odds × total_prizes
```

Uses the highest-volume tier as anchor and cross-validates across tiers. The 5% divergence threshold is a reasonable heuristic. No issues found.

### 1.2 Estimated Remaining Tickets — ✅ Correct with caveat

```
pct_remaining = remaining_prizes / total_prizes   (mid-tier anchor)
remaining_tickets = total_tickets × pct_remaining
```

The mid-tier proxy ($10–$50) is a well-reasoned choice. The rationale (bottom-tier under-redeemed, top-tier too sparse) is documented.

**Caveat:** The spec uses two different "anchor" concepts — the highest-volume tier for `total_tickets` and the highest-volume mid-tier for `pct_remaining`. These are typically different tiers. The spec documents this correctly, but the terminology overlap ("anchor tier") could confuse an LLM executor. Consider labeling them distinctly (e.g., "volume anchor" vs. "depletion proxy").

### 1.3 Current Live Odds — ✅ Correct

```
current_odds[tier] = remaining_tickets / remaining_prizes[tier]
```

Standard conditional probability given the remaining pool. No issues.

### 1.4 Tax-Adjusted Net Prize Value — ✅ Correct

```
net_value = prize > 600 ? prize × 0.7075 : prize
```

NC state (5.25%) + federal (24%) = 29.25% withholding. Multiplier 1 - 0.2925 = 0.7075. Verified correct.

**Note:** The $600 threshold is correct for NC withholding requirements. Prizes of exactly $600 are not subject to withholding; the spec uses `> 600` which is right.

### 1.5 Expected Payout Per Ticket — ✅ Correct

```
EV = Σ ( net_value[tier] × remaining_prizes[tier] / remaining_tickets )
```

Each term is `(post-tax prize) × P(winning that tier)`. The sum gives expected payout per ticket. The spec now correctly labels this as "expected payout" rather than "expected value" (which could be confused with expected profit). The separate `net_ev = EV - ticket_price` formula for expected profit is also provided.

### 1.6 EV Per Dollar — ✅ Correct

```
ev_per_dollar = EV / ticket_price
```

Standard normalization for cross-price comparison. No issues.

### 1.7 Win Probability — ✅ Correct

```
p_win = Σ ( remaining_prizes[tier] / remaining_tickets )
```

This is the probability of winning any prize on a single ticket. The multi-ticket formula `1 − (1 − p_win)^count` is also correct.

**Note:** `p_win` could theoretically exceed 1.0 if the remaining pool is very depleted and many prize tiers still have prizes. This is a data quality signal — the spec's 15% `pct_remaining` floor should prevent it in practice, but the spec does not explicitly say to clamp or flag `p_win > 1`.

### 1.8 Top Prize Concentration Score — ✅ Correct

```
top_concentration = (top_remaining / top_total) / (mid_remaining / mid_total)
```

Ratio of top-tier depletion rate to mid-tier depletion rate. Interpretation (>1 favorable, <1 unfavorable) is correct.

**Edge case:** If `top_total` is 0 (no top prizes ever existed) or `mid_total` is 0, the formula divides by zero. The exclusion filter removes games where all top prizes are claimed, but doesn't guard against games where `top_total = 0` from the start (unlikely but possible). Not a practical risk given NC data.

### 1.9 Budget Optimizer — ✅ Improved, one remaining concern

The spec now correctly frames this as a bounded integer optimization problem rather than claiming greedy is optimal. For typical in-store budgets ($20–$100) with 8 price points ($1–$50), the search space is small enough for exact optimization.

**Remaining concern:** The spec says "use exact search / bounded integer optimization" but provides no algorithm or complexity bound. An LLM may still default to greedy. Consider providing an explicit algorithm (e.g., dynamic programming over ticket prices) or at minimum a worked example showing where greedy fails.

### 1.10 Exclusion Filters — ✅ Correct

- All top prizes claimed → removes games with no jackpot upside
- `pct_remaining < 15%` → guards against stale/unreliable data
- `ticket_price > budget` → obvious constraint

No issues. The 15% threshold is conservative and reasonable.

### 1.11 Cross-Game Summary Probabilities — ✅ Now specified

```
overall_p_any_win = 1 − Π (1 − p_win_i)^count_i
overall_p_top_prize = 1 − Π (1 − 1/current_top_odds_i)^count_i
```

These correctly aggregate independent per-game probabilities across a mixed buy list. Previously unspecified; now documented.

---

## 2. Overall Flow Audit

### 2.1 Data Flow

```
User request → Fetch live NC page → Parse HTML → Per-game math → Filters → Optimize → Output
```

The flow is linear and well-documented across `SKILL.md`, `instructions.md`, and `references/formulas.md`.

**Strength:** The spec explicitly instructs the skill to fail closed if data can't be fetched or parsed. This prevents hallucinated recommendations.

**Weakness:** No caching or staleness detection. If the NC page returns stale data (their updates are roughly daily), the skill has no way to know. This is acceptable given the use case but worth noting.

### 2.2 Photo Handling Flow

The photo flow (identify games → match to live data → filter analysis) is well-specified. The fallback to all games when identification fails is appropriate.

**Gap:** No guidance on confidence calibration. The spec says "if you can't confidently identify any games" but doesn't define confidence. An LLM might over- or under-match. Consider adding examples of partial matches and when to fall back.

### 2.3 Document Consistency

`SKILL.md`, `instructions.md`, and `references/formulas.md` are now well-aligned on:
- EV terminology (expected payout, not profit)
- Budget optimization (integer optimization, not greedy)
- Summary probability formulas
- Fail-closed behavior on parse errors

**Minor inconsistency:** `instructions.md` still uses the section header "The Math" while `SKILL.md` uses "Step 3: The Math". The Table of Contents in `formulas.md` still says "Expected Value" (section 5) while the body says "Expected Payout Per Ticket". This is cosmetic but could cause subtle prompt-following drift.

### 2.4 Parser (`fetch_nc_data.py`)

The parser targets the actual NC Lottery page structure (`div.box.cloudfx.databox.price_*` containers) and includes:
- Record-level validation (`_is_valid_game`, `_is_valid_tier`)
- Chrome rejection (filters out page navigation elements mistaken for games)
- Fallback regex parser if the HTMLParser approach fails
- Deduplication by game number
- Fail-closed behavior (raises `ValueError` if no valid games found)

**Live test result:** 79 games parsed, all with valid name/number/price and 3–16 tiers each. No missing metadata.

**Potential issue:** The regex fallback's block pattern (`.*?</table>\s*</div>`) uses a non-greedy match that could fail if the page structure has nested divs between the table and the closing div. The HTMLParser handles this correctly via depth tracking, so the regex fallback is truly a last resort.

---

## 3. Eval Coverage Audit

### 3.1 Eval Scenarios

| ID | Name | Scenario | Photo? | Budget? |
|----|------|----------|--------|---------|
| 1  | budget-20-basic | All-games analysis with $20 budget | No | $20 |
| 2  | photo-display-50 | Photo-constrained analysis with $50 budget | Yes | $50 |
| 3  | ten-dollar-filter | $10-only filter with save-your-money fallback | No | Implicit |

**Coverage strengths:**
- All three primary user journeys are represented (budget-only, photo+budget, price-filter)
- Each eval has 4 concrete assertions covering behavior, constraints, and failure safety
- The photo eval references an actual fixture image (`fixtures/nc_display_photo.png`)

**Coverage gaps:**

1. **No numeric oracle eval.** None of the evals verify that the math produces correct numbers given known input data. A fixture-based eval with pre-computed expected values would catch formula implementation errors.

2. **No edge case evals:**
   - What happens when all games are excluded by filters? (Expected: "save your money today")
   - What happens when the budget is $1? (Only $1 tickets eligible)
   - What happens when the live fetch fails? (Expected: graceful error message)
   - What happens when `pct_remaining` is exactly at the 15% boundary?

3. **No negative/adversarial evals:**
   - User asks about a state other than NC
   - User provides a photo with no NC tickets visible
   - User provides an unreasonably large budget ($10,000)

4. **Assertions are behavioral, not quantitative.** The assertions check that the skill "provides a concrete buy list" and "includes per-game metrics" but don't verify mathematical correctness of the output. This is understandable given live data variability, but a fixture-based eval could pin down exact expected outputs.

### 3.2 Test Infrastructure

The repo includes 4 Python unit tests:
- `test_parse_current_databox_structure` — parser correctness on fixture HTML
- `test_rejects_page_chrome_without_games` — parser fail-closed behavior
- `test_top_level_evals_file_references_existing_photo_fixture` — photo fixture exists
- `test_iteration_eval_metadata_has_non_empty_assertions` — no empty assertions

All 4 tests pass. The parser tests use frozen HTML fixtures, which is good for regression but will need updating if the NC page structure changes.

---

## 4. Recommendations

### High Priority

1. **Add a numeric oracle eval.** Create a fixture with 3–5 games of known prize data, pre-compute the expected EV/dollar and buy list by hand, and assert the skill produces matching results. This is the single highest-value improvement for catching math errors.

2. **Disambiguate anchor terminology.** Rename "anchor tier" to "volume anchor" (for total tickets) and "depletion proxy" (for remaining tickets) throughout all three spec documents to prevent LLM confusion.

3. **Provide a budget optimization worked example.** Show a case where greedy allocation ($5 game at 0.72 EV/$ vs $3 game at 0.71 EV/$, budget $8) produces a suboptimal result, and demonstrate the correct integer optimization. This gives the LLM a concrete pattern to follow.

### Medium Priority

4. **Add edge case evals.** At minimum: all-games-excluded, fetch-failure, and single-dollar-budget scenarios.

5. **Clamp or flag `p_win > 1`.** Add a note that if `p_win` exceeds 1.0 after calculation, the remaining-tickets estimate is likely too low and the game should be flagged or excluded.

6. **Sync cosmetic inconsistencies.** Update the `formulas.md` Table of Contents entry from "Expected Value" to "Expected Payout" and normalize section headers across documents.

### Low Priority

7. **Add a staleness indicator.** If the skill can detect the page's last-updated timestamp, surface it in the output so the user knows how fresh the data is.

8. **Document photo confidence thresholds.** Provide examples of "confident" vs. "uncertain" game identification to calibrate the LLM's fallback behavior.

9. **Consider parser versioning.** The NC Lottery page structure could change at any time. A version comment or checksum of the expected page skeleton would help detect breakage early.

---

## 5. File Inventory

| File | Purpose | Status |
|------|---------|--------|
| `instructions.md` | Top-level skill prompt | ✅ Current |
| `scratchiq/SKILL.md` | Detailed skill specification | ✅ Current |
| `scratchiq/references/formulas.md` | Formula reference | ✅ Current |
| `scratchiq/references/lotteries/nc.md` | NC-specific data/tax reference | ✅ Current |
| `scratchiq/scripts/fetch_nc_data.py` | Live data parser | ✅ Working (79 games) |
| `scratchiq/evals/evals.json` | Eval scenario definitions | ✅ 3 scenarios |
| `scratchiq/evals/fixtures/nc_display_photo.png` | Photo eval fixture | ✅ Present |
| `scratchiq/tests/test_fetch_nc_data.py` | Parser regression tests | ✅ 2 tests passing |
| `scratchiq/tests/test_eval_metadata.py` | Eval metadata integrity tests | ✅ 2 tests passing |
| `scratchiq/tests/fixtures/` | HTML fixtures for parser tests | ✅ 2 fixtures |
| `scratchiq-workspace/iteration-1/*/eval_metadata.json` | Per-eval assertions | ✅ 4 assertions each |

---

## 6. Test Results (as of audit date)

```
test_iteration_eval_metadata_has_non_empty_assertions ... ok
test_top_level_evals_file_references_existing_photo_fixture ... ok
test_parse_current_databox_structure ... ok
test_rejects_page_chrome_without_games ... ok

Ran 4 tests in 0.004s — OK
```

Live parser smoke test:
```
game_count: 79
price_points: [1, 2, 3, 5, 10, 20, 30, 50]
tier_counts: min=3 max=16 avg=10.8
missing_name=0 missing_number=0
```
