"""Sensor platform for Pollenflug Bayern (ePIN)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, CONF_STATION_INFO, DOMAIN
from .coordinator import PollenflugCoordinator
from .entity import PollenflugTaxonEntity, build_device_info
from .taxon_translations import get_display_name, get_icon

_LOGGER = logging.getLogger(__name__)

# Standard-Einheit für Pollen-/Sporenkonzentrationen in der Aerobiologie.
POLLEN_UNIT = "P/m³"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a config entry and keep tracking newly seen taxa.

    The set of pollen/spore taxa returned by the API is not fixed (the
    LGL has extended it in the past, e.g. for Ambrosia). This listener
    re-checks the coordinator data on every refresh and adds sensors
    for any taxon that has not been seen before, so the integration
    stays correct without a restart if the upstream list changes.
    """
    coordinator: PollenflugCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[tuple[str, str]] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[SensorEntity] = []
        for location, loc_data in coordinator.data.items():
            summary_key = (location, "__last_updated__")
            if summary_key not in known:
                known.add(summary_key)
                new_entities.append(
                    PollenflugLastUpdateSensor(coordinator, entry, location)
                )
            for taxon in loc_data.taxa:
                key = (location, taxon)
                if key not in known:
                    known.add(key)
                    new_entities.append(
                        PollenflugTaxonSensor(coordinator, entry, location, taxon)
                    )
        if new_entities:
            _LOGGER.debug(
                "Lege %d neue Sensor-Entitäten an: %s",
                len(new_entities),
                [e.unique_id for e in new_entities],
            )
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class PollenflugTaxonSensor(PollenflugTaxonEntity, SensorEntity):
    """Concentration (current + short-term forecast) of one taxon.

    ``native_value`` holds the value for the current 3-hour period.
    The full set of returned time slots (past and near-future) is
    exposed via the ``forecast`` attribute for use in templates,
    history graphs or cards such as apexcharts-card.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = POLLEN_UNIT

    def __init__(
        self,
        coordinator: PollenflugCoordinator,
        entry: ConfigEntry,
        location: str,
        taxon: str,
    ) -> None:
        super().__init__(coordinator, entry, location, taxon)
        self._attr_unique_id = f"{entry.entry_id}_{location}_{taxon}_concentration"
        self._attr_name = get_display_name(taxon)
        self._attr_icon = get_icon(taxon)

    @property
    def native_value(self) -> float | None:
        taxon_data = self._taxon_data()
        if taxon_data is None or taxon_data.current is None:
            return None
        return round(taxon_data.current.value, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        taxon_data = self._taxon_data()
        if taxon_data is None:
            return {}

        forecast = [
            {
                "from": dt_util.as_local(point.start).isoformat(),
                "to": dt_util.as_local(point.end).isoformat(),
                "value": round(point.value, 2),
            }
            for point in taxon_data.points
        ]
        attrs: dict[str, Any] = {
            "location": self._location,
            "taxon_latin": self._taxon,
            "forecast": forecast,
        }
        current = taxon_data.current
        if current is not None:
            attrs["period_start"] = dt_util.as_local(current.start).isoformat()
            attrs["period_end"] = dt_util.as_local(current.end).isoformat()
            attrs["algorithm"] = current.algorithm
        return attrs


class PollenflugLastUpdateSensor(CoordinatorEntity[PollenflugCoordinator], SensorEntity):
    """Diagnostic sensor: timestamp of the newest data point from the API."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-check-outline"
    _attr_name = "Letzte Aktualisierung"

    def __init__(
        self,
        coordinator: PollenflugCoordinator,
        entry: ConfigEntry,
        location: str,
    ) -> None:
        super().__init__(coordinator)
        self._location = location
        self._attr_unique_id = f"{entry.entry_id}_{location}_last_updated"
        self._attr_device_info = build_device_info(entry, location)
        self._station_info = entry.data.get(CONF_STATION_INFO, {}).get(location, {})

    @property
    def native_value(self):
        loc_data = self.coordinator.data.get(self._location)
        return loc_data.last_updated if loc_data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._station_info:
            return {"location": self._location}
        return {
            "location": self._location,
            "network": self._station_info.get("network"),
            "latitude": self._station_info.get("latitude"),
            "longitude": self._station_info.get("longitude"),
        }
