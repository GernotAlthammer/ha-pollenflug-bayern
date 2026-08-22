"""Binary sensor platform for Pollenflug Bayern (ePIN)."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PollenflugCoordinator
from .entity import PollenflugTaxonEntity
from .taxon_translations import get_display_name, get_icon

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors and keep tracking newly seen taxa."""
    coordinator: PollenflugCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[tuple[str, str]] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[BinarySensorEntity] = []
        for location, loc_data in coordinator.data.items():
            for taxon in loc_data.taxa:
                key = (location, taxon)
                if key not in known:
                    known.add(key)
                    new_entities.append(
                        PollenflugActiveBinarySensor(coordinator, entry, location, taxon)
                    )
        if new_entities:
            _LOGGER.debug(
                "Lege %d neue Binary-Sensor-Entitäten an: %s",
                len(new_entities),
                [e.unique_id for e in new_entities],
            )
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class PollenflugActiveBinarySensor(PollenflugTaxonEntity, BinarySensorEntity):
    """On while the current 3-hour period shows measurable pollen/spore flight.

    Handy for automations, e.g. "close the windows while birch pollen
    is flying".
    """

    def __init__(
        self,
        coordinator: PollenflugCoordinator,
        entry: ConfigEntry,
        location: str,
        taxon: str,
    ) -> None:
        super().__init__(coordinator, entry, location, taxon)
        self._attr_unique_id = f"{entry.entry_id}_{location}_{taxon}_active"
        self._attr_name = f"{get_display_name(taxon)} aktiv"
        self._attr_icon = get_icon(taxon)

    @property
    def is_on(self) -> bool | None:
        taxon_data = self._taxon_data()
        if taxon_data is None or taxon_data.current is None:
            return None
        return taxon_data.current.value > 0
