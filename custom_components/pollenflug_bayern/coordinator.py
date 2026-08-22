"""DataUpdateCoordinator for Pollenflug Bayern (ePIN)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import PollenflugApiClient, PollenflugApiError, PollenflugConnectionError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class PollenDataPoint:
    """A single 3-hour measurement/forecast slot for one taxon."""

    start: datetime
    end: datetime
    value: float
    algorithm: str | None = None


@dataclass
class TaxonData:
    """All known data points for one pollen/spore taxon at one location."""

    taxon: str
    location: str
    points: list[PollenDataPoint] = field(default_factory=list)

    @property
    def current(self) -> PollenDataPoint | None:
        """Return the data point covering the current time.

        Falls back to the most recent (past) data point if none of the
        returned slots covers "now" exactly (e.g. right at the edge of
        a 3-hour window before the API has published the next slot).
        """
        now = dt_util.utcnow()
        for point in self.points:
            if point.start <= now < point.end:
                return point
        return self.points[-1] if self.points else None


@dataclass
class LocationData:
    """All taxa known for a single ePIN location code."""

    location: str
    taxa: dict[str, TaxonData] = field(default_factory=dict)
    last_updated: datetime | None = None


class PollenflugCoordinator(DataUpdateCoordinator[dict[str, LocationData]]):
    """Coordinator that polls the ePIN API and structures the response."""

    def __init__(
        self,
        hass: HomeAssistant,
        locations: list[str],
        update_interval_minutes: int,
    ) -> None:
        self._locations = locations
        self.client = PollenflugApiClient(async_get_clientsession(hass), locations)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )

    async def _async_update_data(self) -> dict[str, LocationData]:
        try:
            raw = await self.client.async_get_measurements()
        except PollenflugConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except PollenflugApiError as err:
            raise UpdateFailed(str(err)) from err

        measurements = raw.get("measurements")
        if measurements is None:
            raise UpdateFailed("Antwort der ePIN-API enthält keine 'measurements'")

        locations: dict[str, LocationData] = {}
        for entry in measurements:
            location = entry.get("location")
            taxon = entry.get("polle")
            if not location or not taxon:
                continue

            points: list[PollenDataPoint] = []
            for raw_point in entry.get("data", []):
                point = self._parse_point(raw_point)
                if point is not None:
                    points.append(point)
            points.sort(key=lambda p: p.start)

            loc_data = locations.setdefault(location, LocationData(location=location))
            loc_data.taxa[taxon] = TaxonData(taxon=taxon, location=location, points=points)
            if points:
                latest = points[-1].start
                if loc_data.last_updated is None or latest > loc_data.last_updated:
                    loc_data.last_updated = latest

        if not locations:
            raise UpdateFailed(
                "Die ePIN-API hat für die konfigurierten Standorte keine Daten geliefert"
            )

        return locations

    @staticmethod
    def _parse_point(raw_point: dict[str, Any]) -> PollenDataPoint | None:
        """Parse one raw {from, to, value, algorithm} entry defensively."""
        try:
            return PollenDataPoint(
                start=dt_util.utc_from_timestamp(raw_point["from"]),
                end=dt_util.utc_from_timestamp(raw_point["to"]),
                value=float(raw_point["value"]),
                algorithm=raw_point.get("algorithm"),
            )
        except (KeyError, TypeError, ValueError):
            _LOGGER.debug("Überspringe unlesbaren Datenpunkt: %s", raw_point)
            return None
