"""
history.py

Event log for shopping actions (add/remove/update), used to power
"running low" style product recommendations.

Drop this file into server-py/ alongside db.py, context.py, etc.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

# Reuse the exact same DB file db.py uses, so history and shopping_list
# tables always live side by side in one shopping_list.db.
DB_PATH = os.path.join(os.path.dirname(__file__), "shopping_list.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_history_table():
    """Call this once on startup (same place db.py's init runs)."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            action TEXT NOT NULL,          -- 'add' | 'remove' | 'update'
            quantity REAL,
            unit TEXT,
            category TEXT,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def log_event(
    item_name: str,
    action: str,
    quantity: Optional[float] = None,
    unit: Optional[str] = None,
    category: Optional[str] = None,
):
    """
    Call this right after a successful add / remove / update.
    item_name should be normalized (lowercase, trimmed) so history
    matching lines up with how items are matched elsewhere in the app.
    """
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO history (item_name, action, quantity, unit, category, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            item_name.strip().lower(),
            action,
            quantity,
            unit,
            category,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_add_events(item_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns all 'add' events, optionally filtered to one item.
    Ordered oldest -> newest per item (needed for interval math).
    """
    conn = get_connection()
    if item_name:
        rows = conn.execute(
            """
            SELECT * FROM history
            WHERE action = 'add' AND item_name = ?
            ORDER BY timestamp ASC
            """,
            (item_name.strip().lower(),),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM history
            WHERE action = 'add'
            ORDER BY item_name ASC, timestamp ASC
            """
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_history() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM history ORDER BY timestamp ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]