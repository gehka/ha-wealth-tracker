from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "wealthyexile"))

from calculations import _divines_per_hour, compute_derived  # noqa: E402
from parser import extract_stash_payload  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "stash_response.txt"


def _payload():
    return extract_stash_payload(FIXTURE.read_text())


def test_divine_price_selected_for_correct_league():
    derived = compute_derived(_payload())
    # Fixture has Divine Orb at 370.8 chaos for Allflame, 151.8 for Hardcore
    # Allflame, 666.4 for Standard -- make sure we didn't grab the wrong row.
    assert derived.divine_price_chaos == 370.8


def test_total_value_sums_latest_tab_values():
    derived = compute_derived(_payload())
    # Sum of each tab's latest tabValues entry (49472 + 39472), matching
    # what WealthyExile's own "Wealth" figure shows -- not the separate,
    # independently-tracked `snapshots` history (which can be stale or
    # contain manually-created test entries disconnected from the tabs).
    assert derived.total_value_chaos == 88944.0
    assert derived.total_value_divine == 88944.0 / 370.8


def test_top_items_sorted_by_value_descending():
    derived = compute_derived(_payload())
    assert len(derived.top_items) == 3  # fixture only has 3 priced items
    values = [item.value_chaos for item in derived.top_items]
    assert values == sorted(values, reverse=True)
    assert derived.top_items[0].name == "Divine Orb"  # 90 * 370.8 is the biggest stack
    # null-price item should have been skipped entirely
    assert all(item.name != "?" for item in derived.top_items)


def test_tab_summaries_use_latest_tab_value():
    derived = compute_derived(_payload())
    currency_tab = next(t for t in derived.tabs if t.tab_type == "CurrencyStash")
    assert currency_tab.value_chaos == 49472
    assert currency_tab.name == "$$"
    assert currency_tab.color == "dddddd"


def test_divines_per_hour_uses_newest_snapshots_own_value():
    derived = compute_derived(_payload())
    # Fixture's newest snapshot has value=0 -- a legitimate "no change"
    # reading (isComplete=true), not a placeholder to skip. The rate is
    # that snapshot's own value over its own window, so 0 in, 0 out,
    # regardless of how long the window was.
    assert derived.divines_per_hour == 0.0


def test_divines_per_hour_has_no_minimum_time_gap():
    # Two snapshots only 6 minutes apart should still produce a rate --
    # no 30-minute floor. The rate is the newest snapshot's own value
    # (360 chaos = 1.2 divine at 300 chaos/divine) over its own window
    # (6 min = 0.1h): 1.2 / 0.1 = 12 divine/h. Not a diff against the
    # older snapshot's value -- snapshot values are already per-window
    # deltas, not cumulative totals.
    snapshots = [
        {"value": 360, "createdAt": "$D2026-10-06T20:06:00.000Z", "isComplete": True},
        {"value": 300, "createdAt": "$D2026-10-06T20:00:00.000Z", "isComplete": True},
    ]
    assert _divines_per_hour(snapshots, divine_price=300) == pytest.approx(12.0)
