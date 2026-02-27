#!/usr/bin/env python3
"""Visualize the Market Analyzer database structure and statistics."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market_analyzer.db"


def get_table_info(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Get column info for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [
        {
            "name": row[1],
            "type": row[2],
            "notnull": bool(row[3]),
            "default": row[4],
            "pk": bool(row[5]),
        }
        for row in cursor.fetchall()
    ]


def get_foreign_keys(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Get foreign key info for a table."""
    cursor = conn.execute(f"PRAGMA foreign_key_list({table})")
    return [
        {"from": row[3], "to_table": row[2], "to_col": row[4]}
        for row in cursor.fetchall()
    ]


def get_indexes(conn: sqlite3.Connection, table: str) -> list[dict]:
    """Get index info for a table."""
    cursor = conn.execute(f"PRAGMA index_list({table})")
    indexes = []
    for row in cursor.fetchall():
        idx_name = row[1]
        unique = bool(row[2])
        cols_cursor = conn.execute(f"PRAGMA index_info({idx_name})")
        cols = [c[2] for c in cols_cursor.fetchall()]
        indexes.append({"name": idx_name, "unique": unique, "columns": cols})
    return indexes


def get_row_count(conn: sqlite3.Connection, table: str) -> int:
    """Get row count for a table."""
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]


def format_column(col: dict, fks: list[dict]) -> str:
    """Format a single column line."""
    parts = []
    if col["pk"]:
        parts.append("PK")
    fk_match = next((fk for fk in fks if fk["from"] == col["name"]), None)
    if fk_match:
        parts.append(f"FK -> {fk_match['to_table']}.{fk_match['to_col']}")

    col_type = col["type"] or "TEXT"
    not_null = " NOT NULL" if col["notnull"] and not col["pk"] else ""
    default = f" DEFAULT {col['default']}" if col["default"] is not None else ""

    prefix = f"  {'|' if parts else ' '} "
    tag = f" [{', '.join(parts)}]" if parts else ""

    return f"{prefix}{col['name']:.<30s} {col_type}{not_null}{default}{tag}"


def print_table(conn: sqlite3.Connection, table: str):
    """Print a formatted table diagram."""
    columns = get_table_info(conn, table)
    fks = get_foreign_keys(conn, table)
    indexes = get_indexes(conn, table)
    row_count = get_row_count(conn, table)

    width = 72
    print(f"\n  ╔{'═' * width}╗")
    print(f"  ║ {table.upper():<{width - 2}s} ║")
    print(f"  ║ {f'{row_count:,} rows':<{width - 2}s} ║")
    print(f"  ╠{'═' * width}╣")

    for col in columns:
        line = format_column(col, fks)
        # Pad to fit in the box
        padded = f"{line:<{width}s}"
        print(f"  ║{padded}║")

    if indexes:
        print(f"  ╟{'─' * width}╢")
        print(f"  ║ {'INDEXES':<{width - 2}s} ║")
        for idx in indexes:
            cols_str = ", ".join(idx["columns"])
            uniq = " (UNIQUE)" if idx["unique"] else ""
            line = f"    {idx['name']}: ({cols_str}){uniq}"
            print(f"  ║{line:<{width}s}║")

    print(f"  ╚{'═' * width}╝")


def print_relationships(conn: sqlite3.Connection, tables: list[str]):
    """Print the entity relationship diagram."""
    print("\n" + "=" * 76)
    print("  ENTITY RELATIONSHIPS")
    print("=" * 76)
    print("""
  ┌────────────────────┐       ┌─────────────────────────────────┐
  │  skill_categories  │       │           companies             │
  │  (id, name)        │       │  (id, name, short_name...)      │
  └────────┬───────────┘       └───────────────┬─────────────────┘
           │ 1:N                               │ 1:N
           ▼                                   ▼
  ┌────────────────────┐       ┌─────────────────────────────────┐
  │      skills        │       │             jobs                │
  │  (id, name,        │       │  (id, title,                    │
  │   category_id)     │       │   company_id, description,       │
  └────────┬───────────┘       │   salary, level, status...)     │
           │                   └──────┬──────────────┬───────────┘
           │ M:N                      │ M:N          │ M:N
           │    ┌─────────────────────┘              │
           ▼    ▼                                    ▼
  ┌────────────────────┐               ┌─────────────────────────┐
  │    job_skills       │               │    job_locations         │
  │  (job_id, skill_id) │               │  (job_id, location_id)  │
  └────────────────────┘               └──────────┬──────────────┘
                                                  │ M:N
                                                  ▼
                                       ┌─────────────────────────┐
                                       │       locations          │
                                       │  (id, city, state,       │
                                       │   country)               │
                                       └─────────────────────────┘
  """)


def print_migration_notes():
    """Print PostgreSQL migration notes based on schema analysis."""
    print("=" * 76)
    print("  POSTGRESQL MIGRATION NOTES")
    print("=" * 76)
    print("""
  SQLite -> PostgreSQL type changes needed:
  ─────────────────────────────────────────
  1. INTEGER PRIMARY KEY AUTOINCREMENT  ->  SERIAL PRIMARY KEY (or BIGSERIAL)
  2. TEXT                               ->  TEXT (compatible)
  3. BOOLEAN DEFAULT 0                  ->  BOOLEAN DEFAULT FALSE
  4. TIMESTAMP DEFAULT CURRENT_TIMESTAMP -> TIMESTAMPTZ DEFAULT NOW()
  5. DECIMAL(10,2)                      ->  NUMERIC(10,2)
  6. UNIQUE constraints                 ->  Compatible, no change needed
  7. Foreign keys                       ->  Compatible, but enforced by default

  Other considerations:
  ─────────────────────
  - SQLite's loose typing -> PostgreSQL's strict typing (verify data)
  - sqlite3.Row -> psycopg2.extras.RealDictCursor (for dict-like rows)
  - No connection pooling currently -> Use connection pool (e.g. psycopg2.pool)
  - PRAGMA statements -> PostgreSQL system catalogs / pg_catalog
  - ON DELETE CASCADE is already defined (good, works the same)
  - All indexes use IF NOT EXISTS (PostgreSQL compatible)
  """)


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))

    # Get all tables
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]

    print("=" * 76)
    print("  MARKET ANALYZER DATABASE STRUCTURE")
    print(f"  Database: {DB_PATH}")
    print(f"  Engine: SQLite")
    print(f"  Tables: {len(tables)}")
    print("=" * 76)

    # Print summary
    print("\n  TABLE SUMMARY")
    print("  " + "-" * 40)
    for table in tables:
        count = get_row_count(conn, table)
        print(f"    {table:<25s} {count:>8,} rows")

    # Print each table
    for table in tables:
        print_table(conn, table)

    # Print relationships
    print_relationships(conn, tables)

    # Print migration notes
    print_migration_notes()

    conn.close()


if __name__ == "__main__":
    main()
