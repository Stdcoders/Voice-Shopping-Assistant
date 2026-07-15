
import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "shopping_list.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_history_table():
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
