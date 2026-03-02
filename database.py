"""
Database module for PantryPal.
Handles all SQLite database operations for pantry items.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class Database:
    """SQLite database interface for PantryPal pantry items."""

    def __init__(self, db_path: str):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create pantry_items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pantry_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 1,
                unit TEXT DEFAULT NULL,
                category TEXT DEFAULT 'Other',
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by TEXT NOT NULL,
                notes TEXT DEFAULT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def add_item(self, name: str, quantity: float, unit: Optional[str],
                 category: str, added_by: str, notes: Optional[str] = None) -> int:
        """
        Add an item to the pantry.
        If an item with the same name already exists, update its quantity instead.
        Returns the ID of the item.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if item already exists (case-insensitive)
        cursor.execute(
            'SELECT id, quantity FROM pantry_items WHERE LOWER(name) = LOWER(?)',
            (name.strip(),)
        )
        existing = cursor.fetchone()

        if existing:
            item_id = existing[0]
            new_qty = existing[1] + quantity
            cursor.execute(
                'UPDATE pantry_items SET quantity = ?, unit = ?, category = ?, notes = ? WHERE id = ?',
                (new_qty, unit, category, notes, item_id)
            )
        else:
            cursor.execute('''
                INSERT INTO pantry_items
                (name, quantity, unit, category, added_by, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name.strip(), quantity, unit, category, added_by, notes))
            item_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return item_id

    def remove_item(self, item_id: int) -> bool:
        """Remove an item from the pantry by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM pantry_items WHERE id = ?', (item_id,))
        conn.commit()

        affected_rows = cursor.rowcount
        conn.close()

        return affected_rows > 0

    def get_all_items(self) -> List[Dict]:
        """Retrieve all items from the pantry."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, quantity, unit, category, date_added, added_by, notes
            FROM pantry_items
            ORDER BY category, name
        ''')

        items = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return items

    def get_items_by_category(self) -> Dict[str, List[Dict]]:
        """Retrieve all items grouped by category."""
        items = self.get_all_items()
        categorized = {}

        for item in items:
            category = item['category'] or 'Other'
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)

        return categorized

    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Retrieve a single item by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, quantity, unit, category, date_added, added_by, notes
            FROM pantry_items
            WHERE id = ?
        ''', (item_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def update_item(self, item_id: int, quantity: Optional[float] = None,
                    unit: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """Update an existing pantry item."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Build dynamic update query
        updates = []
        params = []

        if quantity is not None:
            updates.append('quantity = ?')
            params.append(quantity)
        if unit is not None:
            updates.append('unit = ?')
            params.append(unit)
        if notes is not None:
            updates.append('notes = ?')
            params.append(notes)

        if not updates:
            conn.close()
            return False

        params.append(item_id)
        query = f"UPDATE pantry_items SET {', '.join(updates)} WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()

        affected_rows = cursor.rowcount
        conn.close()

        return affected_rows > 0

    def clear_pantry(self) -> int:
        """Clear all items from the pantry. Use with caution."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM pantry_items')
        conn.commit()

        affected_rows = cursor.rowcount
        conn.close()

        return affected_rows

    def get_pantry_summary(self) -> Dict:
        """Get a summary of the pantry for display."""
        items = self.get_all_items()
        categories = {}
        contributors = set()

        for item in items:
            cat = item['category'] or 'Other'
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
            contributors.add(item['added_by'])

        return {
            'total_items': len(items),
            'total_unique_items': len(set(i['name'].lower() for i in items)),
            'categories': categories,
            'contributors': sorted(list(contributors)),
            'last_updated': items[-1]['date_added'] if items else None
        }
