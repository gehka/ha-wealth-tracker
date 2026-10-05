from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "wealthyexile"))

from calculations import compute_derived  # noqa: E402
from parser import extract_stash_payload  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "stash_response.txt"


def _payload():
    return extract_stash_payload(FIXTURE.read_text())


def test_divine_price_selected_for_correct_league():
    derived = compute_derived(_payload())
    # Fixture has Divine Orb at 370.8 chaos for Allflame, 151.8 for Hardcore
    # Allflame, 666.4 for Standard -- make sure we didn't grab the wrong row.
    assert derived.divine_price_chaos == 370.8


def test_total_value_uses_latest_nonzero_snapshot():
    derived = compute_derived(_payload())
    # Fixture's newest snapshot has value=0 (still being computed server-side);
    # the next one down (79224.87...) should be used instead.
    assert derived.total_value_chaos == 79224.87558605643
    assert derived.total_value_divine == 79224.87558605643 / 370.8


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


def test_divines_per_hour_computed_from_snapshot_history():
    derived = compute_derived(_payload())
    # Newest usable snapshot (79224.87...) vs the oldest one (6326.67...),
    # ~2.5 months apart in the fixture -- just check it's a small positive
    # number per hour, not None, and not something wildly implausible.
    assert derived.divines_per_hour is not None
    assert 0 < derived.divines_per_hour < 1
