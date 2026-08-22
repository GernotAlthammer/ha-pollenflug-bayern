"""Shared entity base class for Pollenflug Bayern (ePIN)."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_LOCATIONS,
    CONF_NAME,
    CONF_STATION_INFO,
    CONFIGURATION_URL,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import LocationData, PollenflugCoordinator, TaxonData


def _model_for_network(network: str | None) -> str:
    """Return a model string reflecting the station type, if known."""
    if not network:
        return MODEL
    if "manu" in network.lower():
        return f"{MODEL} – manuelle Pollenfalle"
    return f"{MODEL} – elektronisch"


def build_device_info(entry: ConfigEntry, location: str) -> DeviceInfo:
    """Build a DeviceInfo grouping all entities of one ePIN station.

    If the config entry covers exactly one station and the user gave it
    a custom display name, that name is used. Otherwise, the official
    station name resolved at config-time (via /api/locations) is used
    if available, falling back to the raw station code (e.g. when the
    station list could not be loaded during setup).
    """
    locations: list[str] = entry.data.get(CONF_LOCATIONS, [])
    custom_name = entry.data.get(CONF_NAME)
    station_info: dict[str, Any] = entry.data.get(CONF_STATION_INFO, {}).get(location, {})
    station_name = station_info.get("name")

    if custom_name and len(locations) == 1:
        name = custom_name
    elif station_name:
        name = f"Pollenflug {station_name}"
    else:
        name = f"Pollenflug {location}"

    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{location}")},
        name=name,
        manufacturer=MANUFACTURER,
        model=_model_for_network(station_info.get("network")),
        configuration_url=CONFIGURATION_URL,
    )


class PollenflugTaxonEntity(CoordinatorEntity[PollenflugCoordinator]):
    """Base class for entities tied to one taxon at one ePIN location."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: PollenflugCoordinator,
        entry: ConfigEntry,
        location: str,
        taxon: str,
    ) -> None:
        super().__init__(coordinator)
        self._location = location
        self._taxon = taxon
        self._attr_device_info = build_device_info(entry, location)

    def _location_data(self) -> LocationData | None:
        return self.coordinator.data.get(self._location)

    def _taxon_data(self) -> TaxonData | None:
        loc_data = self._location_data()
        return loc_data.taxa.get(self._taxon) if loc_data else None

    @property
    def available(self) -> bool:
        return super().available and self._taxon_data() is not None
