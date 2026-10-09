from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "wealthyexile"))

from calculations import _divines_per_hour, _session_gain_divine, compute_derived  # noqa: E402
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


def test_session_gain_from_fixture():
    derived = compute_derived(_payload())
    # Fixture's two newest snapshots (value=0, value=79224.87...) are
    # ~2 minutes apart (well under the 1h session-boundary gap), so both
    # count; the third/oldest snapshot is months older (>1h gap), so it
    # starts a *previous* session and is excluded.
    assert derived.session_gain_divine == pytest.approx(79224.87558605643 / 370.8)


def test_session_gain_stops_at_gap_over_one_hour():
    # Mirrors a real WealthyExile history: a cluster of snapshots today,
    # separated from an older cluster by a 60+ hour gap. Only the values
    # from the newest snapshot back to (and including) the one right
    # after the gap should be summed.
    snapshots = [
        {"value": 0, "createdAt": "$D2026-10-09T10:20:15.000Z", "isComplete": True},
        {"value": 1440, "createdAt": "$D2026-10-09T10:17:52.000Z", "isComplete": True},
        {"value": 1803.5, "createdAt": "$D2026-10-09T09:45:53.000Z", "isComplete": True},
        {"value": 721.4, "createdAt": "$D2026-10-09T09:42:47.000Z", "isComplete": True},
        {"value": 0, "createdAt": "$D2026-10-09T09:18:39.000Z", "isComplete": True},
        # >1h gap here (60.5h) -- everything below belongs to a previous
        # session and must not be included.
        {"value": 0, "createdAt": "$D2026-10-06T20:49:05.000Z", "isComplete": True},
        {"value": 7360, "createdAt": "$D2026-10-06T20:04:23.000Z", "isComplete": True},
        {"value": -3680, "createdAt": "$D2026-10-06T19:46:19.000Z", "isComplete": True},
        {"value": 0, "createdAt": "$D2026-10-06T19:00:40.000Z", "isComplete": True},
    ]
    # 0 + 1440 + 1803.5 + 721.4 + 0 = 3964.9 chaos
    assert _session_gain_divine(snapshots, divine_price=360.7) == pytest.approx(3964.9 / 360.7)


def test_session_gain_caps_lookback_at_ten_snapshots():
    # 12 snapshots, each 10 minutes apart (no gap anywhere near 1h), each
    # worth 1 chaos. Without a cap this would sum all 12; capped at 10,
    # only the 10 most recent (value=1 each) should count.
    base = datetime(2026, 10, 9, 8, 0, 0)
    snapshots = [
        {
            "value": 1,
            "createdAt": "$D" + (base + timedelta(minutes=10 * i)).isoformat() + "Z",
            "isComplete": True,
        }
        for i in range(12)
    ]
    assert _session_gain_divine(snapshots, divine_price=1) == pytest.approx(10.0)
