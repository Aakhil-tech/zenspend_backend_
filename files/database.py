"""
database.py
===========
Creates and manages the SQLite database for ZenSpend.
Run this once to set up all tables: python database.py
"""

import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "zenspend.db")


def get_db():
    """Get a database connection. Used by FastAPI as a dependency."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create all tables. Safe to run multiple times (uses IF NOT EXISTS)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    cur.executescript("""

    -- ── Users ────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS users (
        user_id           TEXT PRIMARY KEY,
        email             TEXT UNIQUE NOT NULL,
        display_name      TEXT NOT NULL DEFAULT 'ZenSpender',
        current_budget    REAL NOT NULL DEFAULT 2500.0,
        saving_allowance  REAL NOT NULL DEFAULT 345.0,
        personality_score INTEGER NOT NULL DEFAULT 0,
        personality_type  TEXT NOT NULL DEFAULT 'Unknown',
        streak_count      INTEGER NOT NULL DEFAULT 0,
        high_legibility   INTEGER NOT NULL DEFAULT 0,
        exam_mode_active  INTEGER NOT NULL DEFAULT 0,
        onboarding_done   INTEGER NOT NULL DEFAULT 0,
        created_at        TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ── Transactions ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id  TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        title           TEXT NOT NULL,
        amount          REAL NOT NULL,
        category        TEXT NOT NULL CHECK(category IN ('Essentials', 'Savings', 'Wants')),
        txn_date        TEXT NOT NULL DEFAULT (date('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_txn_user_date ON transactions(user_id, txn_date);

    -- ── Bills ────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS bills (
        bill_id   TEXT PRIMARY KEY,
        user_id   TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        title     TEXT NOT NULL,
        amount    REAL NOT NULL,
        due_date  TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_bills_user ON bills(user_id);

    -- ── Goals ────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS goals (
        goal_id        TEXT PRIMARY KEY,
        user_id        TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        title          TEXT NOT NULL,
        target_amount  REAL NOT NULL,
        current_amount REAL NOT NULL DEFAULT 0.0,
        deadline       TEXT,
        is_complete    INTEGER NOT NULL DEFAULT 0,
        created_at     TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);

    -- ── Restaurants ──────────────────────────────────────────────────────────
    -- Shared table — same for all users (CravingMode catalogue)
    CREATE TABLE IF NOT EXISTS restaurants (
        restaurant_id TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        price_tier    TEXT NOT NULL,
        distance_km   REAL NOT NULL,
        rating        REAL NOT NULL,
        category      TEXT NOT NULL CHECK(category IN ('Local', 'Western')),
        is_cheap      INTEGER NOT NULL DEFAULT 0,
        is_healthy    INTEGER NOT NULL DEFAULT 0,
        review_count  INTEGER NOT NULL DEFAULT 0,
        taste_profile TEXT NOT NULL DEFAULT ''
    );

    """)

    # Seed restaurants if empty (matches your constants.ts exactly)
    cur.execute("SELECT COUNT(*) FROM restaurants")
    if cur.fetchone()[0] == 0:
        restaurants = [
            ('1', 'Spice Garden',   '$$', 1.2, 4.5, 'Local',   0, 1, 1240, 'Spicy,Aromatic,Traditional'),
            ('2', 'Burger King',    '$',  0.8, 4.0, 'Western', 1, 0, 8500, 'Savory,Flame-grilled'),
            ('3', 'Dosa Plaza',     '$',  0.5, 4.8, 'Local',   1, 1, 3200, 'Crispy,Tangy'),
            ('4', 'Pizza Hut',      '$$', 2.1, 4.2, 'Western', 0, 0, 5400, 'Cheesy,Classic'),
            ('5', 'Biryani House',  '$$', 1.5, 4.7, 'Local',   0, 0, 2100, 'Rich,Flavorful'),
            ('6', 'Street Tacos',   '$',  0.3, 4.3, 'Western', 1, 1,  980, 'Fresh,Zesty'),
            ('7', "Amma's Kitchen", '$',  0.9, 4.9, 'Local',   1, 1,  450, 'Home-cooked,Nutritious'),
            ('8', 'Noodle Bar',     '$',  1.1, 4.1, 'Western', 1, 1, 1100, 'Umami,Quick'),
        ]
        cur.executemany(
            "INSERT INTO restaurants VALUES (?,?,?,?,?,?,?,?,?,?)",
            restaurants
        )
        print(f"  Seeded {len(restaurants)} restaurants.")

    conn.commit()
    conn.close()
    print(f"✓ Database ready at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
