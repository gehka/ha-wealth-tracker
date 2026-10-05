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
    top_items: list[TopItem] = field(default_factory=list)
    tabs: list[TabSummary] = field(default_factory=list)
    session_gain_divine: float = 0.0


def compute_derived(payload: dict[str, Any]) -> DerivedData:
    """Build a DerivedData from a parsed `{"user": ..., "priceMap": ...}`."""
    user = payload["user"]
    league = user["preferredLeague"]
    divine_price = _select_divine_price(payload.get("priceMap", []), league)

    total_chaos = _total_value_chaos(user)
    total_divine = total_chaos / divine_price if divine_price else 0.0

    return DerivedData(
        league=league,
        divine_price_chaos=divine_price,
        total_value_chaos=total_chaos,
        total_value_divine=total_divine,
        divines_per_hour=_divines_per_hour(user.get("snapshots", []), divine_price),
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


def _latest_complete_snapshot(snapshots: list[dict]) -> dict | None:
    """Most recent snapshot with an already-computed (non-zero) value.

    WealthyExile's newest snapshot can briefly show value=0 while its
    valuation is still being computed server-side, so we skip those.
    """
    ordered = sorted(
        snapshots,
        key=lambda s: _parse_timestamp(s.get("createdAt")) or datetime.min,
        reverse=True,
    )
    for snap in ordered:
        if snap.get("value"):
            return snap
    return None


def _total_value_chaos(user: dict) -> float:
    latest = _latest_complete_snapshot(user.get("snapshots", []))
    if latest is not None:
        return float(latest["value"])

    # Fallback: sum each tab's most recent tabValues entry.
    total = 0.0
    for tab in user.get("tabs", []):
        tab_values = tab.get("tabValues", [])
        if tab_values:
            total += float(tab_values[-1]["value"])
    return total


def _divines_per_hour(snapshots: list[dict], divine_price: float) -> float | None:
    if not divine_price:
        return None

    ordered = sorted(
        (s for s in snapshots if s.get("value")),
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
        older_ts = _parse_timestamp(older["createdAt"])
        if older_ts is None:
            continue
        hours = (newest_ts - older_ts).total_seconds() / 3600
        if hours >= 0.5:
            value_diff_chaos = float(newest["value"]) - float(older["value"])
            return (value_diff_chaos / divine_price) / hours

    return None


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
