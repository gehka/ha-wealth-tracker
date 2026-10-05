"""Sensor platform for WealthyExile."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .calculations import DerivedData
from .const import DOMAIN, TAB_TYPE_ICON_URLS
from .coordinator import WealthyExileCoordinator

TOP_ITEM_COUNT = 8


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WealthyExileCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        TotalValueSensor(coordinator, entry),
        DivinesPerHourSensor(coordinator, entry),
        DivinePriceSensor(coordinator, entry),
        SessionGainSensor(coordinator, entry),
        LastSyncedSensor(coordinator, entry),
    ]
    entities.extend(TopItemSensor(coordinator, entry, i) for i in range(TOP_ITEM_COUNT))
    async_add_entities(entities)

    # Stash tabs aren't known until the first successful poll, and an
    # account could gain/rename tabs later -- so tab sensors are added
    # dynamically as they show up, not just once at setup.
    known_tab_ids: set[int] = set()

    def _add_new_tab_sensors() -> None:
        new_entities = [
            TabValueSensor(coordinator, entry, tab.tab_id)
            for tab in coordinator.data.tabs
            if tab.tab_id not in known_tab_ids
        ]
        known_tab_ids.update(tab.tab_id for tab in coordinator.data.tabs)
        if new_entities:
            async_add_entities(new_entities)

    _add_new_tab_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_tab_sensors))


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="WealthyExile Loot Tracker",
        manufacturer="WealthyExile (inoffiziell)",
    )


class _BaseSensor(CoordinatorEntity[WealthyExileCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = _device_info(entry)

    @property
    def _data(self) -> DerivedData:
        return self.coordinator.data


class TotalValueSensor(_BaseSensor):
    # Plain _attr_name rather than translation_key: translation_key-based
    # entity naming did not resolve for this custom component in testing
    # (entities showed up as just the device name, no suffix) even though
    # strings.json has the right entity.sensor.<key>.name entries -- a
    # fixed name is simpler and guaranteed to work.
    _attr_name = "Wealth"
    _attr_native_unit_of_measurement = "divine"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash-multiple"

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_value_divine"

    @property
    def native_value(self) -> float:
        return round(self._data.total_value_divine, 2)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "total_value_chaos": round(self._data.total_value_chaos, 2),
            "league": self._data.league,
        }


class DivinesPerHourSensor(_BaseSensor):
    _attr_name = "Divines per Hour"
    _attr_native_unit_of_measurement = "divine/h"
    _attr_icon = "mdi:trending-up"

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_divines_per_hour"

    @property
    def native_value(self) -> float | None:
        value = self._data.divines_per_hour
        return round(value, 3) if value is not None else None


class DivinePriceSensor(_BaseSensor):
    _attr_name = "Divine Price"
    _attr_native_unit_of_measurement = "chaos"
    _attr_icon = "mdi:scale-balance"

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_divine_price"

    @property
    def native_value(self) -> float:
        return round(self._data.divine_price_chaos, 2)


class SessionGainSensor(_BaseSensor):
    _attr_name = "Session Gain"
    _attr_native_unit_of_measurement = "divine"
    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_session_gain"

    @property
    def native_value(self) -> float:
        return round(self._data.session_gain_divine, 2)


class LastSyncedSensor(_BaseSensor):
    _attr_name = "Last Synced"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_synced"

    @property
    def native_value(self) -> datetime | None:
        raw = self._data.last_synced
        if not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))


class TopItemSensor(_BaseSensor):
    _attr_native_unit_of_measurement = "divine"
    _attr_icon = "mdi:treasure-chest"

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator, entry)
        self._index = index
        self._attr_unique_id = f"{entry.entry_id}_top_item_{index + 1}"
        self._attr_name = f"Top Stack {index + 1}"

    def _item(self):
        items = self._data.top_items
        return items[self._index] if self._index < len(items) else None

    @property
    def native_value(self) -> float | None:
        item = self._item()
        return round(item.value_divine, 2) if item else None

    @property
    def entity_picture(self) -> str | None:
        item = self._item()
        return item.icon if item else None

    @property
    def extra_state_attributes(self) -> dict:
        item = self._item()
        if not item:
            return {}
        return {
            "name": item.name,
            "quantity": item.quantity,
            "category": item.category,
            "value_chaos": round(item.value_chaos, 2),
        }


class TabValueSensor(_BaseSensor):
    _attr_native_unit_of_measurement = "divine"
    _attr_icon = "mdi:archive"
    # Tab names come straight from the user's own stash tab names/colors in
    # PoE, so this one skips translation_key and just sets `name` directly.
    _attr_has_entity_name = True

    def __init__(self, coordinator: WealthyExileCoordinator, entry: ConfigEntry, tab_id: int) -> None:
        super().__init__(coordinator, entry)
        self._tab_id = tab_id
        self._attr_unique_id = f"{entry.entry_id}_tab_{tab_id}"

    def _tab(self):
        return next((t for t in self._data.tabs if t.tab_id == self._tab_id), None)

    @property
    def name(self) -> str:
        tab = self._tab()
        return f"Tab {tab.name}" if tab else f"Tab {self._tab_id}"

    @property
    def native_value(self) -> float | None:
        tab = self._tab()
        return round(tab.value_divine, 2) if tab else None

    @property
    def entity_picture(self) -> str | None:
        tab = self._tab()
        return TAB_TYPE_ICON_URLS.get(tab.tab_type) if tab else None

    @property
    def extra_state_attributes(self) -> dict:
        tab = self._tab()
        if not tab:
            return {}
        return {
            "color": f"#{tab.color}",
            "type": tab.tab_type,
            "value_chaos": round(tab.value_chaos, 2),
        }
