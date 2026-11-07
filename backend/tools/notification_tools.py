import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

from services.database import get_connection
from tools.task_tools import (
    get_all_tasks,
    _get_deadline_datetime
)


def generate_notifications():
    """Generate due-soon and overdue notifications without duplicates."""

    now = datetime.now()
    due_soon_limit = now + timedelta(hours=24)

    tasks = get_all_tasks()
    connection = get_connection()
    cursor = connection.cursor()

    generated = 0

    try:
        for task in tasks:
            if task["status"] == "Completed":
                continue

            deadline = _get_deadline_datetime(task["deadline"])

            # Skip deadlines that cannot be parsed.
            if deadline is None:
                continue

            notification_type = None

            if deadline < now:
                notification_type = "overdue"

            elif now <= deadline <= due_soon_limit:
                notification_type = "due_soon"

            if notification_type is None:
                continue

            if notification_type == "overdue":
                message = (
                    f'{task["employee"]} has an overdue task: '
                    f'{task["task"]}. Deadline: {task["deadline"]}.'
                )
            else:
                message = (
                    f'{task["employee"]} has a task due within 24 hours: '
                    f'{task["task"]}. Deadline: {task["deadline"]}.'
                )

            cursor.execute("""
                INSERT OR IGNORE INTO notifications (
                    notification_id,
                    task_id,
                    employee,
                    task,
                    deadline,
                    notification_type,
                    message,
                    created_at,
                    is_read
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                str(uuid4()),
                task["task_id"],
                task["employee"],
                task["task"],
                task["deadline"],
                notification_type,
                message,
                now.isoformat(timespec="seconds")
            ))

            generated += cursor.rowcount

        connection.commit()
        return generated

    finally:
        connection.close()


def get_notifications(unread_only=False):
    """Retrieve notification history, newest first."""

    connection = get_connection()
    connection.row_factory = sqlite3.Row    
    cursor = connection.cursor()

    query = "SELECT * FROM notifications"
    if unread_only:
        query += " WHERE is_read = 0"

    query += " ORDER BY created_at DESC"

    cursor.execute(query)
    notifications = [dict(row) for row in cursor.fetchall()]

    connection.close()
    return notifications


def mark_notification_read(notification_id):
    """Mark one notification as read."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE notification_id = ?
    """, (notification_id,))

    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return updated
