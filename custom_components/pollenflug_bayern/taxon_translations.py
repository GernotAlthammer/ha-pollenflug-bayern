"""German display names and icon categories for ePIN pollen/spore taxa.

The ePIN API returns Latin genus/family names for each measured taxon
(e.g. "Betula", "Poaceae"). This module maps the taxa that are
currently known to appear in the API response to their common German
names, purely for nicer entity names, and to a rough category used to
pick a sensible icon.

If the LGL adds a taxon that is not (yet) listed here, the integration
keeps working: the raw Latin name is used as a fallback display name
and a generic pollen icon is shown.
"""
from __future__ import annotations

CATEGORY_TREE = "tree"
CATEGORY_GRASS = "grass"
CATEGORY_WEED = "weed"
CATEGORY_FUNGUS = "fungus"
CATEGORY_OTHER = "other"

# taxon (as returned by the API) -> (German display name, category)
TAXON_INFO: dict[str, tuple[str, str]] = {
    "Acer": ("Ahorn", CATEGORY_TREE),
    "Aesculus": ("Rosskastanie", CATEGORY_TREE),
    "Alnus": ("Erle", CATEGORY_TREE),
    "Ambrosia": ("Ambrosia (Traubenkraut)", CATEGORY_WEED),
    "Artemisia": ("Beifuß", CATEGORY_WEED),
    "Asteraceae": ("Korbblütler", CATEGORY_WEED),
    "Betula": ("Birke", CATEGORY_TREE),
    "Carpinus": ("Hainbuche", CATEGORY_TREE),
    "Castanea": ("Edelkastanie", CATEGORY_TREE),
    "Chenopodium": ("Gänsefuß", CATEGORY_WEED),
    "Corylus": ("Hasel", CATEGORY_TREE),
    "Cruciferae": ("Kreuzblütler", CATEGORY_WEED),
    "Brassicaceae": ("Kreuzblütler", CATEGORY_WEED),
    "Cyperaceae": ("Sauergräser", CATEGORY_GRASS),
    "Erica": ("Heidekraut", CATEGORY_WEED),
    "Fagus": ("Buche", CATEGORY_TREE),
    "Fraxinus": ("Esche", CATEGORY_TREE),
    "Fungus": ("Pilzsporen", CATEGORY_FUNGUS),
    "Impatiens": ("Springkraut", CATEGORY_WEED),
    "Juglans": ("Walnuss", CATEGORY_TREE),
    "Larix": ("Lärche", CATEGORY_TREE),
    "Picea": ("Fichte", CATEGORY_TREE),
    "Pinaceae": ("Kieferngewächse", CATEGORY_TREE),
    "Pinus": ("Kiefer", CATEGORY_TREE),
    "Plantago": ("Wegerich", CATEGORY_WEED),
    "Platanus": ("Platane", CATEGORY_TREE),
    "Poaceae": ("Gräser", CATEGORY_GRASS),
    "Populus": ("Pappel", CATEGORY_TREE),
    "Quercus": ("Eiche", CATEGORY_TREE),
    "Rumex": ("Ampfer", CATEGORY_WEED),
    "Salix": ("Weide", CATEGORY_TREE),
    "Sambucus": ("Holunder", CATEGORY_TREE),
    "Secale": ("Roggen", CATEGORY_GRASS),
    "Taxus": ("Eibe", CATEGORY_TREE),
    "Tilia": ("Linde", CATEGORY_TREE),
    "Ulmus": ("Ulme", CATEGORY_TREE),
    "Urtica": ("Brennnessel", CATEGORY_WEED),
    "Varia": ("Sonstige Pollen", CATEGORY_OTHER),
}

_CATEGORY_ICONS: dict[str, str] = {
    CATEGORY_TREE: "mdi:tree",
    CATEGORY_GRASS: "mdi:grass",
    CATEGORY_WEED: "mdi:sprout",
    CATEGORY_FUNGUS: "mdi:mushroom",
    CATEGORY_OTHER: "mdi:flower-pollen",
}


def get_display_name(taxon: str) -> str:
    """Return the German display name for a taxon, or the raw name."""
    info = TAXON_INFO.get(taxon)
    return info[0] if info else taxon


def get_icon(taxon: str) -> str:
    """Return a fitting mdi icon for a taxon."""
    info = TAXON_INFO.get(taxon)
    category = info[1] if info else CATEGORY_OTHER
    return _CATEGORY_ICONS.get(category, "mdi:flower-pollen")
