
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from statistics import mean
from typing import List, Dict, Any, Optional

import history
import catalog


MIN_ADD_EVENTS_FOR_PATTERN = 2       
RUNNING_LOW_THRESHOLD_RATIO = 0.8    
DISMISS_SNOOZE_DAYS = 3              
COLD_START_MIN_TOTAL_ADDS = 5        
FREQUENTLY_BOUGHT_TOGETHER_WINDOW_DAYS = 0 
MAX_SUGGESTIONS_PER_TYPE = 5

COLD_START_STAPLES = [
    {"item": "milk", "category": "dairy"},
    {"item": "bread", "category": "bakery"},
    {"item": "eggs", "category": "dairy"},
    {"item": "bananas", "category": "produce"},
    {"item": "rice", "category": "grains"},
]


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _normalize(name: str) -> str:
    return name.strip().lower()


def dismiss_recommendation(item_name: str):
    history.log_event(item_name, action="dismiss")


def _recently_dismissed(item_name: str, all_history: List[Dict[str, Any]]) -> bool:
    cutoff = datetime.utcnow() - timedelta(days=DISMISS_SNOOZE_DAYS)
    for row in all_history:
        if row["action"] == "dismiss" and row["item_name"] == item_name:
            if _parse_ts(row["timestamp"]) >= cutoff:
                return True
    return False


def _most_common_quantity_unit(add_events: List[Dict[str, Any]]):
    pairs = [
        (e["quantity"], e["unit"])
        for e in add_events
        if e["quantity"] is not None
    ]
    if not pairs:
        return None, None
    most_common, _ = Counter(pairs).most_common(1)[0]
    return most_common  # (quantity, unit)


def _running_low_recommendations(
    current_items_normalized: set,
    all_history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_item = defaultdict(list)
    for row in all_history:
        if row["action"] == "add":
            by_item[row["item_name"]].append(row)

    suggestions = []
    now = datetime.utcnow()

    for item_name, events in by_item.items():
        if item_name in current_items_normalized:
            continue  
        if len(events) < MIN_ADD_EVENTS_FOR_PATTERN:
            continue  
        if _recently_dismissed(item_name, all_history):
            continue  

        events_sorted = sorted(events, key=lambda e: _parse_ts(e["timestamp"]))
        timestamps = [_parse_ts(e["timestamp"]) for e in events_sorted]
        intervals_days = [
            (timestamps[i] - timestamps[i - 1]).total_seconds() / 86400
            for i in range(1, len(timestamps))
        ]
        avg_interval = mean(intervals_days)
        if avg_interval <= 0:
            continue

        last_add = timestamps[-1]
        days_since_last = (now - last_add).total_seconds() / 86400

        if days_since_last >= avg_interval * RUNNING_LOW_THRESHOLD_RATIO:
            quantity, unit = _most_common_quantity_unit(events_sorted)
            category = events_sorted[-1].get("category")
            suggestions.append({
                "item": item_name,
                "category": category,
                "type": "running_low",
                "reason": (
                    f"You usually add {item_name} every ~{round(avg_interval)} "
                    f"day(s) — it's been {round(days_since_last)} day(s)"
                ),
                "suggested_quantity": quantity,
                "suggested_unit": unit,
            })

    suggestions.sort(
        key=lambda s: s["reason"], reverse=False
    )
    return suggestions[:MAX_SUGGESTIONS_PER_TYPE]


def _cold_start_recommendations(
    current_items_normalized: set,
    all_history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    total_adds = sum(1 for row in all_history if row["action"] == "add")
    if total_adds >= COLD_START_MIN_TOTAL_ADDS:
        return []  

    suggestions = []
    for staple in COLD_START_STAPLES:
        item_name = _normalize(staple["item"])
        if item_name in current_items_normalized:
            continue
        if _recently_dismissed(item_name, all_history):
            continue
        suggestions.append({
            "item": item_name,
            "category": staple["category"],
            "type": "cold_start",
            "reason": "Popular staple to get you started",
            "suggested_quantity": None,
            "suggested_unit": None,
        })
    return suggestions[:MAX_SUGGESTIONS_PER_TYPE]


def _frequently_bought_together(
    current_items_normalized: set,
    all_history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not current_items_normalized:
        return []

    day_to_items = defaultdict(set)
    day_to_categories = {}
    for row in all_history:
        if row["action"] != "add":
            continue
        day_key = _parse_ts(row["timestamp"]).date()
        day_to_items[day_key].add(row["item_name"])
        day_to_categories[row["item_name"]] = row.get("category")

    co_occurrence = Counter()
    for day, items_that_day in day_to_items.items():
        overlap = items_that_day & current_items_normalized
        if not overlap:
            continue
        for other_item in items_that_day - current_items_normalized:
            co_occurrence[other_item] += 1

    suggestions = []
    for item_name, count in co_occurrence.most_common(MAX_SUGGESTIONS_PER_TYPE):
        if count < 1:
            continue
        if _recently_dismissed(item_name, all_history):
            continue
        suggestions.append({
            "item": item_name,
            "category": day_to_categories.get(item_name),
            "type": "frequently_bought_together",
            "reason": "Often added alongside items already on your list",
            "suggested_quantity": None,
            "suggested_unit": None,
        })
    return suggestions


def _seasonal_recommendations(
    current_items_normalized: set,
    all_history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    in_season = {p["name"]: p for p in catalog.get_in_season()}
    on_sale = {p["name"]: p for p in catalog.get_on_sale()}

    all_names = set(in_season.keys()) | set(on_sale.keys())

    suggestions = []
    for item_name in all_names:
        if item_name in current_items_normalized:
            continue
        if _recently_dismissed(item_name, all_history):
            continue

        is_seasonal = item_name in in_season
        is_on_sale = item_name in on_sale
        product = in_season.get(item_name) or on_sale.get(item_name)

        if is_seasonal and is_on_sale:
            reason = "In season right now and currently on sale"
        elif is_seasonal:
            reason = "In season right now"
        else:
            reason = "Currently on sale"

        suggestions.append({
            "item": item_name,
            "category": product.get("category"),
            "type": "seasonal",
            "reason": reason,
            "suggested_quantity": None,
            "suggested_unit": None,
        })

    return suggestions[:MAX_SUGGESTIONS_PER_TYPE]


def _substitute_recommendations(
    current_items_normalized: set,
    all_history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    suggestions = []
    for item_name in current_items_normalized:
        substitute_names = catalog.get_substitutes(item_name)
        for sub_name in substitute_names:
            sub_name = _normalize(sub_name)
            if sub_name in current_items_normalized:
                continue
            if _recently_dismissed(sub_name, all_history):
                continue
            sub_products = catalog.find_by_name(sub_name)
            category = sub_products[0]["category"] if sub_products else None
            suggestions.append({
                "item": sub_name,
                "category": category,
                "type": "substitute",
                "for_item": item_name,
                "reason": f"Alternative to {item_name}",
                "suggested_quantity": None,
                "suggested_unit": None,
            })

    return suggestions[:MAX_SUGGESTIONS_PER_TYPE]


def get_recommendations(current_items: List[str]) -> List[Dict[str, Any]]:
    current_normalized = {_normalize(i) for i in current_items}
    all_history = history.get_all_history()

    running_low = _running_low_recommendations(current_normalized, all_history)
    seen = {s["item"] for s in running_low}

    substitutes = [
        s for s in _substitute_recommendations(current_normalized, all_history)
        if s["item"] not in seen
    ]
    seen |= {s["item"] for s in substitutes}

    seasonal = [
        s for s in _seasonal_recommendations(current_normalized, all_history)
        if s["item"] not in seen
    ]
    seen |= {s["item"] for s in seasonal}

    together = [
        s for s in _frequently_bought_together(current_normalized, all_history)
        if s["item"] not in seen
    ]
    seen |= {s["item"] for s in together}

    cold_start = [
        s for s in _cold_start_recommendations(current_normalized, all_history)
        if s["item"] not in seen
    ]

    return running_low + substitutes + seasonal + together + cold_start