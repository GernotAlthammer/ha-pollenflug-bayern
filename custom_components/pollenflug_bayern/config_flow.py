"""Config flow for Pollenflug Bayern (ePIN)."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    EpinLocation,
    PollenflugApiClient,
    PollenflugApiError,
    PollenflugConnectionError,
    async_get_locations,
)
from .const import (
    CONF_LOCATIONS,
    CONF_NAME,
    CONF_STATION_INFO,
    CONF_UPDATE_INTERVAL,
    DEFAULT_LOCATION,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _parse_locations(raw: str) -> list[str]:
    """Split a comma-separated list of station codes into a clean list."""
    return [loc.strip().upper() for loc in raw.split(",") if loc.strip()]


def _normalize_locations(raw: Any) -> list[str]:
    """Accept either a list (from the station selector) or a raw string.

    The station field is a multi-select when the live station list could
    be loaded (returns a list of codes), and a free-text fallback field
    otherwise (returns a comma-separated string).
    """
    if isinstance(raw, list):
        return [str(loc).strip().upper() for loc in raw if str(loc).strip()]
    return _parse_locations(str(raw or ""))


def _location_label(location: EpinLocation) -> str:
    kind = "manuelle Pollenfalle" if location.is_manual else "elektronische Messstation"
    return f"{location.name} ({location.id}, {kind})"


class PollenflugConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pollenflug Bayern."""

    VERSION = 1

    def __init__(self) -> None:
        self._available_locations: list[EpinLocation] | None = None
        self._locations_fetch_failed = False

    async def _async_ensure_locations_fetched(self) -> None:
        """Fetch the official station list once per flow session."""
        if self._available_locations is not None or self._locations_fetch_failed:
            return
        try:
            self._available_locations = await async_get_locations(
                async_get_clientsession(self.hass)
            )
        except PollenflugApiError as err:
            _LOGGER.debug("Standortliste konnte nicht geladen werden: %s", err)
            self._locations_fetch_failed = True

        if not self._available_locations:
            # Empty list is treated the same as a failed fetch: fall back
            # to manual entry rather than showing an empty dropdown.
            self._locations_fetch_failed = True
            self._available_locations = None

    def _location_name(self, code: str) -> str:
        """Return the human-readable station name, or the raw code."""
        for loc in self._available_locations or []:
            if loc.id == code:
                return loc.name
        return code

    def _build_schema(self) -> vol.Schema:
        if self._available_locations:
            options = [
                selector.SelectOptionDict(value=loc.id, label=_location_label(loc))
                for loc in self._available_locations
            ]
            default: Any = (
                [DEFAULT_LOCATION]
                if any(loc.id == DEFAULT_LOCATION for loc in self._available_locations)
                else [self._available_locations[0].id]
            )
            locations_field: Any = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        else:
            default = DEFAULT_LOCATION
            locations_field = str

        return vol.Schema(
            {
                vol.Required(CONF_LOCATIONS, default=default): locations_field,
                vol.Optional(CONF_NAME, default=""): str,
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Handle the initial (and only) setup step."""
        await self._async_ensure_locations_fetched()
        errors: dict[str, str] = {}

        if user_input is not None:
            locations = _normalize_locations(user_input[CONF_LOCATIONS])

            if not locations:
                errors["base"] = "no_location"
            else:
                await self.async_set_unique_id(",".join(sorted(locations)))
                self._abort_if_unique_id_configured()

                client = PollenflugApiClient(
                    async_get_clientsession(self.hass), locations
                )
                try:
                    raw = await client.async_get_measurements()
                except PollenflugConnectionError as err:
                    _LOGGER.debug("Verbindung fehlgeschlagen für %s: %s", locations, err)
                    errors["base"] = "cannot_connect"
                except PollenflugApiError as err:
                    _LOGGER.debug("Ungültige Antwort für %s: %s", locations, err)
                    errors["base"] = "invalid_response"
                else:
                    if not raw.get("measurements"):
                        _LOGGER.debug("Keine Messungen für %s zurückgegeben", locations)
                        errors["base"] = "no_data"

                if not errors:
                    name = (user_input.get(CONF_NAME) or "").strip()
                    title = name or ", ".join(
                        self._location_name(code) for code in locations
                    )
                    station_info = {
                        loc.id: {
                            "name": loc.name,
                            "network": loc.network,
                            "latitude": loc.latitude,
                            "longitude": loc.longitude,
                        }
                        for loc in (self._available_locations or [])
                        if loc.id in locations
                    }
                    return self.async_create_entry(
                        title=title,
                        data={
                            CONF_LOCATIONS: locations,
                            CONF_NAME: name,
                            CONF_STATION_INFO: station_info,
                        },
                    )

        placeholders = {
            "fallback_notice": (
                ""
                if self._available_locations
                else (
                    "⚠️ Die offizielle Stationsliste konnte gerade nicht geladen "
                    "werden – bitte Stationscode(s) manuell eingeben, "
                    "kommagetrennt (z. B. DEVIEC für Viechtach)."
                )
            )
        }

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema(),
            errors=errors,
            description_placeholders=placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PollenflugOptionsFlow:
        """Return the options flow for this config entry."""
        return PollenflugOptionsFlow()


class PollenflugOptionsFlow(OptionsFlow):
    """Handle options (currently just the update interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Manage the update interval option."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=current): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
