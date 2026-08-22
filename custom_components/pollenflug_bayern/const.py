"""Constants for the Pollenflug Bayern (ePIN) integration."""
from __future__ import annotations

DOMAIN = "pollenflug_bayern"
DEFAULT_NAME = "Pollenflug Bayern"

CONF_LOCATIONS = "locations"
CONF_NAME = "name"
CONF_UPDATE_INTERVAL = "update_interval"
# Snapshot of {code: {"name", "network", "latitude", "longitude"}} for the
# stations chosen at config-time, taken from the official /api/locations
# endpoint. Used to show nice device/entity names without having to call
# that endpoint again at runtime. Empty if the endpoint was unreachable
# during setup (manual code entry fallback).
CONF_STATION_INFO = "station_info"

# Fallback default / example station code. Confirmed against the live
# /api/locations endpoint (Viechtach). The full, authoritative list of
# stations is fetched dynamically in the config flow via that endpoint
# rather than hardcoded here, since the LGL can add or rename stations.
DEFAULT_LOCATION = "DEVIEC"

DEFAULT_UPDATE_INTERVAL = 60
MIN_UPDATE_INTERVAL = 15
MAX_UPDATE_INTERVAL = 1440

ATTRIBUTION = (
    "Datenquelle: Bayerisches Landesamt für Gesundheit und Lebensmittelsicherheit "
    "(LGL) – Elektronisches Polleninformationsnetzwerk (ePIN)"
)

MANUFACTURER = "Bayerisches Landesamt für Gesundheit und Lebensmittelsicherheit (LGL)"
MODEL = "ePIN Messstation"
CONFIGURATION_URL = "https://epin.lgl.bayern.de/pollenflug-aktuell"
