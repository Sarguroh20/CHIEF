
import sqlite3

DB_NAME = "chief.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    # Existing task table — preserve all existing records.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            employee TEXT NOT NULL,
            task TEXT NOT NULL,
            deadline TEXT NOT NULL,
            status TEXT DEFAULT 'Created',
            created_at TEXT NOT NULL
        )
    """)

    # New notification table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            employee TEXT NOT NULL,
            task TEXT NOT NULL,
            deadline TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            UNIQUE(task_id, deadline, notification_type)
        )
    """)

    connection.commit()
    connection.close()
