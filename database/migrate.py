#!/usr/bin/env python3
"""
Database Migration Runner for Junior Counsel

Runs SQL migration files in order to set up or update the database schema.

Usage:
    python database/migrate.py              # Run all pending migrations
    python database/migrate.py --reset      # Drop all tables and re-run migrations
    python database/migrate.py --status     # Show migration status
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.core.db import get_engine, session_scope
from sqlalchemy import text


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_migration_files():
    """Get all SQL migration files in order."""
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [(f.stem, f) for f in files]


def create_migration_table():
    """Create the migrations tracking table if it doesn't exist."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()


def get_applied_migrations():
    """Get list of already-applied migrations."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT migration_name FROM migrations ORDER BY id"))
        return {row[0] for row in result}


def apply_migration(name, filepath):
    """Apply a single migration file."""
    print(f"Applying migration: {name}")

    with open(filepath, 'r') as f:
        sql = f.read()

    engine = get_engine()
    with engine.connect() as conn:
        # Execute migration SQL
        conn.execute(text(sql))

        # Record migration
        conn.execute(
            text("INSERT INTO migrations (migration_name) VALUES (:name)"),
            {"name": name}
        )
        conn.commit()

    print(f"✓ Migration {name} applied successfully")


def run_migrations():
    """Run all pending migrations."""
    create_migration_table()
    applied = get_applied_migrations()
    migrations = get_migration_files()

    pending = [(name, path) for name, path in migrations if name not in applied]

    if not pending:
        print("✓ No pending migrations. Database is up to date.")
        return

    print(f"Found {len(pending)} pending migration(s):")
    for name, _ in pending:
        print(f"  - {name}")
    print()

    for name, filepath in pending:
        try:
            apply_migration(name, filepath)
        except Exception as e:
            print(f"✗ Migration {name} failed: {e}")
            print("Stopping migration process.")
            sys.exit(1)

    print(f"\n✓ All {len(pending)} migration(s) applied successfully!")


def show_status():
    """Show migration status."""
    create_migration_table()
    applied = get_applied_migrations()
    migrations = get_migration_files()

    print("Migration Status:\n")
    print(f"{'Migration Name':<40} {'Status':<10}")
    print("-" * 50)

    for name, _ in migrations:
        status = "APPLIED" if name in applied else "PENDING"
        print(f"{name:<40} {status:<10}")

    pending_count = sum(1 for name, _ in migrations if name not in applied)
    print(f"\nTotal: {len(migrations)} migrations, {len(applied)} applied, {pending_count} pending")


def reset_database():
    """Drop all tables and re-run migrations."""
    print("WARNING: This will drop all tables and data!")
    confirm = input("Type 'yes' to confirm: ")

    if confirm.lower() != 'yes':
        print("Reset cancelled.")
        return

    print("\nDropping all tables...")
    engine = get_engine()

    with engine.connect() as conn:
        # Drop all tables in public schema
        conn.execute(text("""
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO public;
        """))
        conn.commit()

    print("✓ All tables dropped")
    print("\nRe-running migrations...\n")

    run_migrations()


def main():
    parser = argparse.ArgumentParser(description="Junior Counsel Database Migration Tool")
    parser.add_argument("--reset", action="store_true", help="Drop all tables and re-run migrations")
    parser.add_argument("--status", action="store_true", help="Show migration status")

    args = parser.parse_args()

    if args.reset:
        reset_database()
    elif args.status:
        show_status()
    else:
        run_migrations()


if __name__ == "__main__":
    main()
