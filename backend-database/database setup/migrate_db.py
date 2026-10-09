"""
Database migration script to add detections column.
Run this to update the existing database schema.

Reads credentials from the environment (.env) — never hardcodes them.
The password previously committed here has been revoked; rotate it.
"""
import logging
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "garbage_detection_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}


def migrate_database():
    """Add detections column to garbage_reports table"""
    if not DB_CONFIG["password"]:
        raise RuntimeError("DB_PASSWORD is not set. See backend-database/.env.example.")

    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='garbage_reports' AND column_name='detections';
        """)

        if cursor.fetchone():
            logger.info("Column 'detections' already exists. No migration needed.")
            cursor.close()
            conn.close()
            return

        logger.info("Adding 'detections' column...")
        cursor.execute("""
            ALTER TABLE garbage_reports
            ADD COLUMN detections JSONB;
        """)

        conn.commit()
        logger.info("Migration completed successfully.")

        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='garbage_reports';
        """)

        logger.info("Current table structure:")
        for row in cursor.fetchall():
            logger.info("  - %s: %s", row[0], row[1])

        cursor.close()
        conn.close()

    except Exception as e:
        logger.exception("Migration failed: %s", e)
        raise e


if __name__ == "__main__":
    logger.info("Database Migration: Add Detections Column")
    migrate_database()
    logger.info("Migration complete! You can now restart the server.")
