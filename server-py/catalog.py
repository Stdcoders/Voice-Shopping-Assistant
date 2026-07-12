"""
catalog.py

Loads product_catalog.json once at startup and exposes small query
helpers used by:
  - recommendations.py (Seasonal Recommendations, Substitutes)
  - search.py (Section 4: Item Search + Price Filtering) — later

Drop product_catalog.json into server-py/ next to this file.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "product_catalog.json")

_catalog: List[Dict[str, Any]] = []


def load_catalog():
    """Call once at startup (same place history.init_history_table() runs)."""
    global _catalog
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        _catalog = json.load(f)
    return _catalog


def _normalize(name: str) -> str:
    return name.strip().lower()


def get_all() -> List[Dict[str, Any]]:
    return _catalog


def find_by_name(name: str) -> List[Dict[str, Any]]:
    """All product variants (brands/sizes) matching a generic item name."""
    target = _normalize(name)
    return [p for p in _catalog if p["name"] == target]


def get_substitutes(name: str) -> List[str]:
    """
    Returns the substitute item names for a given generic item.
    Pulls from the first matching variant (substitutes are the same
    across brand variants of the same item in this dataset).
    """
    matches = find_by_name(name)
    if not matches:
        return []
    return matches[0].get("substitutes", [])


def get_in_season(month: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Returns one representative product per generic item name that is
    in season for the given month (defaults to current month).
    """
    if month is None:
        month = datetime.utcnow().month

    seen_names = set()
    results = []
    for p in _catalog:
        if p["name"] in seen_names:
            continue
        if month in p.get("in_season_months", []):
            # Treat year-round (all 12 months) items as "not seasonal" —
            # they're not an interesting seasonal *suggestion*.
            if len(p.get("in_season_months", [])) >= 12:
                continue
            seen_names.add(p["name"])
            results.append(p)
    return results


def get_on_sale() -> List[Dict[str, Any]]:
    seen_names = set()
    results = []
    for p in _catalog:
        if p.get("on_sale") and p["name"] not in seen_names:
            seen_names.add(p["name"])
            results.append(p)
    return results


def search(
    query: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    organic: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Generic filtered search over the catalog. All filters are AND'd
    together and are optional. `query` matches against item name
    (substring match, case-insensitive).
    """
    results = _catalog

    if query:
        q = _normalize(query)
        results = [p for p in results if q in p["name"]]

    if brand:
        b = _normalize(brand)
        results = [p for p in results if b in _normalize(p["brand"])]

    if category:
        c = _normalize(category)
        results = [p for p in results if _normalize(p["category"]) == c]

    if min_price is not None:
        results = [p for p in results if p["price"] >= min_price]

    if max_price is not None:
        results = [p for p in results if p["price"] <= max_price]

    if organic is not None:
        results = [p for p in results if p.get("organic") == organic]

    return results