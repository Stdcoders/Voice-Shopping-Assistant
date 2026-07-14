import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "shopping_list.db")

_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode = WAL;")
_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS shopping_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity REAL NOT NULL DEFAULT 1,
        unit TEXT,
        category TEXT NOT NULL DEFAULT 'other',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
)
_conn.commit()


def _normalize(value):
    return (value or "").strip().lower()


def _name_variants(name):
    """
    Return normalized (singular, plural) forms of a name for tolerant
    matching, e.g. "onion" and "onions" resolve to the same pair.
    Naive suffix-based — doesn't handle irregular plurals (tomato/tomatoes,
    knife/knives), but covers the common case cheaply.
    """
    norm = _normalize(name)
    if norm.endswith("s"):
        return norm[:-1], norm
    return norm, norm + "s"


def _canonical_name(name):
    """
    Canonical (singular) form of a name, used when inserting new rows so
    that "onion" and "onions" converge on the same stored name over time
    instead of creating parallel duplicate entries.
    """
    singular, _ = _name_variants(name)
    return singular


def get_all_items():
    rows = _conn.execute(
        "SELECT * FROM shopping_list ORDER BY category, name"
    ).fetchall()
    return [dict(row) for row in rows]


def _find_match(name, unit=None):
    # unit is intentionally not used as a filter — matching by name is
    # sufficient, consistent with how removal/update already behave.
    singular, plural = _name_variants(name)
    row = _conn.execute(
        "SELECT * FROM shopping_list WHERE LOWER(name) IN (?, ?)",
        (singular, plural),
    ).fetchone()
    return dict(row) if row else None


def _find_by_name_any_unit(name):
    # Matches by name only, ignoring unit — used for corrections ("make it
    # 2 litres") and removals ("delete orange juice"), since neither
    # naturally restates the item's original unit.
    singular, plural = _name_variants(name)
    row = _conn.execute(
        """SELECT * FROM shopping_list
           WHERE LOWER(name) IN (?, ?)
           ORDER BY updated_at DESC
           LIMIT 1""",
        (singular, plural),
    ).fetchone()
    return dict(row) if row else None


# action: "add" — quantity defaults to 1 if not specified by the LLM
def add_item(command: dict):
    item = command.get("item")
    quantity = command.get("quantity")
    unit = command.get("unit")
    category = command.get("category") or "other"
    qty = 1 if quantity is None else quantity

    existing = _find_match(item, unit)
    if existing:
        _conn.execute(
            """UPDATE shopping_list
               SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (qty, existing["id"]),
        )
    else:
        _conn.execute(
            """INSERT INTO shopping_list (name, quantity, unit, category)
               VALUES (?, ?, ?, ?)""",
            (_canonical_name(item), qty, unit, category),
        )
    _conn.commit()
    return get_all_items()


# action: "remove" — no quantity specified means remove the item entirely;
# a specified quantity decrements, deleting once it hits zero or below.
# Matches by name only (ignoring unit) — a user saying "remove orange juice"
# won't necessarily restate the unit it was added with (e.g. "bottle").
def remove_item(command: dict):
    item = command.get("item")
    quantity = command.get("quantity")

    existing = _find_by_name_any_unit(item)
    if not existing:
        return get_all_items()  # nothing to remove, silent no-op

    if quantity is None or quantity >= existing["quantity"]:
        _conn.execute("DELETE FROM shopping_list WHERE id = ?", (existing["id"],))
    else:
        _conn.execute(
            """UPDATE shopping_list
               SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (quantity, existing["id"]),
        )
    _conn.commit()
    return get_all_items()


# action: "update" — a contextual correction (e.g. "make it 2 litres").
# Sets quantity/unit directly rather than incrementing. Matches the exact
# behavior already tested in the Node version: unit is always overwritten
# with whatever the LLM returns (even null), quantity falls back to the
# existing value only when the LLM didn't return one.
def update_item(command: dict):
    item = command.get("item")
    quantity = command.get("quantity")
    unit = command.get("unit")
    category = command.get("category") or "other"

    existing = _find_by_name_any_unit(item)
    if existing:
        new_quantity = existing["quantity"] if quantity is None else quantity
        _conn.execute(
            """UPDATE shopping_list
               SET quantity = ?, unit = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (new_quantity, unit, existing["id"]),
        )
    else:
        _conn.execute(
            """INSERT INTO shopping_list (name, quantity, unit, category)
               VALUES (?, ?, ?, ?)""",
            (_canonical_name(item), 1 if quantity is None else quantity, unit, category),
        )
    _conn.commit()
    return get_all_items()


def delete_item_by_id(item_id: int):
    _conn.execute("DELETE FROM shopping_list WHERE id = ?", (item_id,))
    _conn.commit()
    return get_all_items()


def clear_list():
    _conn.execute("DELETE FROM shopping_list")
    _conn.commit()
    return get_all_items()