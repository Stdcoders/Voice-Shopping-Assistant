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
    norm = _normalize(name)
    if norm.endswith("s"):
        return norm[:-1], norm
    return norm, norm + "s"


def _canonical_name(name):
    singular, _ = _name_variants(name)
    return singular


def get_all_items():
    rows = _conn.execute(
        "SELECT * FROM shopping_list ORDER BY category, name"
    ).fetchall()
    return [dict(row) for row in rows]


def _find_match(name, unit=None):
    singular, plural = _name_variants(name)
    print(f"[_find_match] name={name!r} singular={singular!r} plural={plural!r}")
    row = _conn.execute(
        "SELECT * FROM shopping_list WHERE LOWER(name) IN (?, ?)",
        (singular, plural),
    ).fetchone()
    return dict(row) if row else None


def _find_by_name_any_unit(name):
    singular, plural = _name_variants(name)
    row = _conn.execute(
        """SELECT * FROM shopping_list
           WHERE LOWER(name) IN (?, ?)
           ORDER BY updated_at DESC
           LIMIT 1""",
        (singular, plural),
    ).fetchone()
    return dict(row) if row else None
def add_item(command: dict):
    print(f"[add_item] command={command}")
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

def remove_item(command: dict):
    item = command.get("item")
    quantity = command.get("quantity")

    existing = _find_by_name_any_unit(item)
    if not existing:
        return get_all_items()  

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
