"""Lightweight async client for the Bavarian ePIN pollen network (LGL)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://epin.lgl.bayern.de/api/measurements"
LOCATIONS_URL = "https://epin.lgl.bayern.de/api/locations"
REQUEST_TIMEOUT = 15  # seconds


class PollenflugApiError(Exception):
    """Generic error raised for problems talking to the ePIN API."""


class PollenflugConnectionError(PollenflugApiError):
    """Raised when the ePIN API cannot be reached at all."""


@dataclass
class EpinLocation:
    """One measurement/monitoring station of the ePIN network."""

    id: str
    name: str
    network: str
    latitude: float | None = None
    longitude: float | None = None

    @property
    def is_manual(self) -> bool:
        """Whether this is a manually read Hirst-type trap (vs. electronic)."""
        return "manu" in self.network.lower()


async def async_get_locations(session: aiohttp.ClientSession) -> list[EpinLocation]:
    """Fetch the official, current list of ePIN stations.

    Queried live from the LGL rather than hardcoded, so newly added or
    renamed stations show up automatically without an integration update.
    """
    _LOGGER.debug("Rufe ePIN-Standortliste ab: %s", LOCATIONS_URL)
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with session.get(LOCATIONS_URL) as response:
                if response.status != 200:
                    raise PollenflugApiError(
                        f"Unerwarteter HTTP-Status {response.status} von der ePIN-Standortliste"
                    )
                raw = await response.json(content_type=None)
    except TimeoutError as err:
        raise PollenflugConnectionError(
            "Zeitüberschreitung beim Abruf der ePIN-Standortliste"
        ) from err
    except aiohttp.ClientError as err:
        raise PollenflugConnectionError(
            f"Verbindung zur ePIN-Standortliste fehlgeschlagen: {err}"
        ) from err

    if not isinstance(raw, list):
        raise PollenflugApiError("Unerwartetes Format der ePIN-Standortliste")

    locations: list[EpinLocation] = []
    for item in raw:
        try:
            locations.append(
                EpinLocation(
                    id=str(item["id"]).strip().upper(),
                    name=str(item["name"]).strip(),
                    network=str(item.get("network", "")).strip(),
                    latitude=float(item["lat"]) if item.get("lat") is not None else None,
                    longitude=float(item["lon"]) if item.get("lon") is not None else None,
                )
            )
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug("Überspringe unlesbaren Standort-Eintrag: %s", item)
            continue

    locations.sort(key=lambda loc: loc.name)
    return locations


class PollenflugApiClient:
    """Thin wrapper around the public ePIN ``/api/measurements`` endpoint.

    The endpoint is not officially documented but is publicly reachable
    and used by the official ePIN website/app. It returns near-real-time
    and short-term forecast pollen/spore concentrations in 3-hour steps
    for one or more ePIN station codes (e.g. ``DEVIEC`` for Viechtach).
    """

    def __init__(self, session: aiohttp.ClientSession, locations: list[str]) -> None:
        self._session = session
        self._locations = locations

    async def async_get_measurements(self) -> dict[str, Any]:
        """Fetch and return the raw JSON payload for the configured stations."""
        params = {"locations": ",".join(self._locations)}
        _LOGGER.debug("Rufe ePIN-Daten ab: %s?locations=%s", API_BASE_URL, params["locations"])
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(API_BASE_URL, params=params) as response:
                    if response.status != 200:
                        raise PollenflugApiError(
                            f"Unerwarteter HTTP-Status {response.status} von der ePIN-API"
                        )
                    return await response.json(content_type=None)
        except TimeoutError as err:
            raise PollenflugConnectionError(
                "Zeitüberschreitung bei der Anfrage an die ePIN-API"
            ) from err
        except aiohttp.ClientError as err:
            raise PollenflugConnectionError(
                f"Verbindung zur ePIN-API fehlgeschlagen: {err}"
            ) from err
