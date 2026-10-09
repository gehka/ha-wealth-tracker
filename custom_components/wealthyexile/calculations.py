"""Pure data-shaping helpers that turn a raw stash payload into the values
the Home Assistant sensors expose.

Kept free of Home Assistant imports so it can be unit tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TopItem:
    name: str
    icon: str | None
    quantity: int
    category: str | None
    value_chaos: float
    value_divine: float


@dataclass
class TabSummary:
    tab_id: int
    tab_type: str
    name: str
    color: str
    value_chaos: float
    value_divine: float


@dataclass
class DerivedData:
    league: str
    divine_price_chaos: float
    total_value_chaos: float
    total_value_divine: float
    divines_per_hour: float | None
    last_synced: str | None
    session_gain_divine: float | None
    top_items: list[TopItem] = field(default_factory=list)
    tabs: list[TabSummary] = field(default_factory=list)


def compute_derived(payload: dict[str, Any]) -> DerivedData:
    """Build a DerivedData from a parsed `{"user": ..., "priceMap": ...}`."""
    user = payload["user"]
    league = user["preferredLeague"]
    divine_price = _select_divine_price(payload.get("priceMap", []), league)
    snapshots = user.get("snapshots", [])

    total_chaos = _total_value_chaos(user)
    total_divine = total_chaos / divine_price if divine_price else 0.0

    return DerivedData(
        league=league,
        divine_price_chaos=divine_price,
        total_value_chaos=total_chaos,
        total_value_divine=total_divine,
        divines_per_hour=_divines_per_hour(snapshots, divine_price),
        session_gain_divine=_session_gain_divine(snapshots, divine_price),
        last_synced=_strip_date_prefix(user.get("lastSynced")),
        top_items=_top_items(user.get("tabs", []), divine_price, limit=8),
        tabs=_tab_summaries(user.get("tabs", []), divine_price),
    )


def _select_divine_price(price_map: list[dict], league: str) -> float:
    for entry in price_map:
        if entry.get("name") == "Divine Orb" and entry.get("league") == league:
            return float(entry["value"])
    return 0.0


def _strip_date_prefix(value: str | None) -> str | None:
    if value and value.startswith("$D"):
        return value[2:]
    return value


def _parse_timestamp(value: str | None) -> datetime | None:
    stripped = _strip_date_prefix(value)
    if not stripped:
        return None
    return datetime.fromisoformat(stripped.replace("Z", "+00:00"))


def _total_value_chaos(user: dict) -> float:
    """Current total stash value: sum of each tab's latest tabValues entry.

    This is what WealthyExile's own "Wealth" figure on wealthyexile.com
    shows -- the live total across all synced tabs right now. The
    `snapshots` list is a separate, independent history feed (used below
    for the divines/hour rate) that can be sparse, stale, or contain
    manually-created test entries completely disconnected from the
    tabs' real current value; summing tabs directly avoids ever showing
    a number that doesn't match what's on the website.
    """
    total = 0.0
    for tab in user.get("tabs", []):
        tab_values = tab.get("tabValues", [])
        if tab_values:
            total += float(tab_values[-1]["value"])
    return total


def _divines_per_hour(snapshots: list[dict], divine_price: float) -> float | None:
    """Rate of change from the newest snapshot's own value and duration.

    Confirmed against a live payload and WealthyExile's own Snapshot
    detail card (Start/End/Duration/Revenue/Cost/Net): a snapshot's
    `value` is NOT a cumulative stash total, it's the net chaos change
    *within that one snapshot's own window* -- the span from the
    previous snapshot's createdAt to this one's createdAt. So the rate
    is just this snapshot's value over that one duration, not a diff
    between two snapshots' values (they're already deltas, not totals;
    diffing two deltas was the bug in the previous version of this
    function). Zero is a legitimate value here ("no change"), not a
    sign of an incomplete snapshot -- `isComplete` is the real gate for
    that.
    """
    if not divine_price:
        return None

    ordered = sorted(
        (s for s in snapshots if s.get("isComplete") and s.get("createdAt")),
        key=lambda s: _parse_timestamp(s.get("createdAt")) or datetime.min,
        reverse=True,
    )
    if len(ordered) < 2:
        return None

    newest = ordered[0]
    newest_ts = _parse_timestamp(newest["createdAt"])
    if newest_ts is None:
        return None

    for older in ordered[1:]:
        older_ts = _parse_timestamp(older.get("createdAt"))
        if older_ts is None:
            continue
        hours = (newest_ts - older_ts).total_seconds() / 3600
        if hours <= 0:
            continue
        return (float(newest["value"]) / divine_price) / hours

    return None


_SESSION_GAP_HOURS = 1
_SESSION_MAX_LOOKBACK = 10


def _session_gain_divine(snapshots: list[dict], divine_price: float) -> float | None:
    """Net change across the current "session", purely from snapshot data.

    A session boundary is a >1h gap between two consecutive snapshots --
    no boundary found means still playing, a gap means a break happened
    and syncing resumed. Starting from the newest snapshot, walk
    backwards summing each snapshot's own value (snapshots are per-window
    deltas, see `_divines_per_hour`) until hitting such a gap, and stop
    there (that older snapshot belongs to the *previous* session, not
    this one). Capped at the 10 most recent snapshots so a long
    continuous play session (or a very sparse history with no gaps at
    all) doesn't require scanning unbounded history.
    """
    if not divine_price:
        return None

    ordered = sorted(
        (s for s in snapshots if s.get("isComplete") and s.get("createdAt")),
        key=lambda s: _parse_timestamp(s.get("createdAt")) or datetime.min,
        reverse=True,
    )[:_SESSION_MAX_LOOKBACK]
    if not ordered:
        return None

    session = [ordered[0]]
    for newer, older in zip(ordered, ordered[1:]):
        newer_ts = _parse_timestamp(newer.get("createdAt"))
        older_ts = _parse_timestamp(older.get("createdAt"))
        if newer_ts is None or older_ts is None:
            break
        gap_hours = (newer_ts - older_ts).total_seconds() / 3600
        if gap_hours > _SESSION_GAP_HOURS:
            break
        session.append(older)

    total_chaos = sum(float(s["value"]) for s in session)
    return total_chaos / divine_price


def _top_items(tabs: list[dict], divine_price: float, limit: int) -> list[TopItem]:
    flat: list[TopItem] = []
    for tab in tabs:
        for item in tab.get("items", []):
            price = item.get("price")
            if not price:
                continue
            quantity = item.get("quantity", 0)
            value_chaos = quantity * float(price["value"])
            if value_chaos <= 0:
                continue
            value_divine = value_chaos / divine_price if divine_price else 0.0
            flat.append(
                TopItem(
                    name=price.get("name", "?"),
                    icon=price.get("icon"),
                    quantity=quantity,
                    category=price.get("category"),
                    value_chaos=value_chaos,
                    value_divine=value_divine,
                )
            )
    flat.sort(key=lambda i: i.value_chaos, reverse=True)
    return flat[:limit]


def _tab_summaries(tabs: list[dict], divine_price: float) -> list[TabSummary]:
    summaries: list[TabSummary] = []
    for tab in tabs:
        tab_values = tab.get("tabValues", [])
        value_chaos = float(tab_values[-1]["value"]) if tab_values else 0.0
        value_divine = value_chaos / divine_price if divine_price else 0.0
        summaries.append(
            TabSummary(
                tab_id=tab["id"],
                tab_type=tab.get("type", ""),
                name=tab.get("name", ""),
                color=tab.get("color", ""),
                value_chaos=value_chaos,
                value_divine=value_divine,
            )
        )
    return summaries
