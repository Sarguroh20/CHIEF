
from datetime import datetime
from uuid import uuid4

from services.database import get_connection


def create_task(employee, task, deadline):

    if not employee or not task or not deadline:
        raise ValueError("All task fields are required.")

    result = {
        "task_id": str(uuid4()),
        "employee": employee,
        "task": task,
        "deadline": deadline,
        "status": "Created",
        "created_at": datetime.now().isoformat()
    }

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO tasks
        (task_id, employee, task, deadline, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        result["task_id"],
        result["employee"],
        result["task"],
        result["deadline"],
        result["status"],
        result["created_at"]
    ))

    connection.commit()
    connection.close()

    return result


def get_all_tasks():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM tasks")

    rows = cursor.fetchall()

    connection.close()

    columns = [
        "task_id",
        "employee",
        "task",
        "deadline",
        "status",
        "created_at"
    ]

    return [dict(zip(columns, row)) for row in rows]


def update_task_status(task_id, status):

    allowed_statuses = ["Created", "In Progress", "Completed"]

    if status not in allowed_statuses:
        raise ValueError("Invalid task status.")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE tasks
        SET status = ?
        WHERE task_id = ?
    """, (status, task_id))

    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return updated


def get_tasks_by_status(status):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM tasks
        WHERE status = ?
    """, (status,))

    rows = cursor.fetchall()
    connection.close()

    columns = [
        "task_id", "employee", "task",
        "deadline", "status", "created_at"
    ]

    return [dict(zip(columns, row)) for row in rows]



def _get_deadline_datetime(deadline):
    """Parse an ISO deadline and return local time as a naive datetime."""
    if not deadline:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(deadline).strip().replace("Z", "+00:00")
        )

        # Convert timezone-aware deadlines to the computer's local timezone.
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)

        return parsed

    except (ValueError, TypeError):
        return None


def _get_deadline_date(deadline):
    """Extract the date from a valid deadline."""
    deadline_datetime = _get_deadline_datetime(deadline)

    if deadline_datetime is None:
        return None

    return deadline_datetime.date()


def get_overdue_tasks():
    """Return incomplete tasks whose exact deadlines have passed."""
    now = datetime.now()
    tasks = get_all_tasks()

    return [
        task for task in tasks
        if task["status"] != "Completed"
        and (deadline := _get_deadline_datetime(task["deadline"]))
        and deadline < now
    ]


def get_tasks_due_today():
    """Return incomplete tasks due later today."""
    now = datetime.now()
    today = now.date()
    tasks = get_all_tasks()

    return [
        task for task in tasks
        if task["status"] != "Completed"
        and (deadline := _get_deadline_datetime(task["deadline"]))
        and deadline.date() == today
        and deadline >= now
    ]


def get_tasks_by_employee(employee):
    """Return tasks assigned to a specific employee."""
    if not employee:
        raise ValueError("Employee name is required.")

    tasks = get_all_tasks()

    return [
        task for task in tasks
        if task["employee"].strip().lower() == employee.strip().lower()
    ]

def get_executive_briefing():
    """Generate a management overview of CHIEF tasks."""
    
    now = datetime.now()
    tasks = get_all_tasks()

    # Identify tasks requiring attention using exact deadline times.
    overdue_tasks = [
        task for task in tasks
        if task["status"] != "Completed"
        and (deadline := _get_deadline_datetime(task["deadline"]))
        and deadline < now
    ]

    due_today_tasks = [
        task for task in tasks
        if task["status"] != "Completed"
        and (deadline := _get_deadline_datetime(task["deadline"]))
        and deadline.date() == now.date()
        and deadline >= now
    ]

    overdue_task_ids = {
        task["task_id"] for task in overdue_tasks
    }

    # Calculate employee-wise workload.
    employee_workload = {}

    for task in tasks:
        employee = task["employee"].strip()
        key = employee.lower()

        if key not in employee_workload:
            employee_workload[key] = {
                "employee": employee,
                "total": 0,
                "created": 0,
                "in_progress": 0,
                "completed": 0,
                "overdue": 0
            }

        workload = employee_workload[key]
        workload["total"] += 1

        status = task["status"]

        if status == "Created":
            workload["created"] += 1
        elif status == "In Progress":
            workload["in_progress"] += 1
        elif status == "Completed":
            workload["completed"] += 1

        if task["task_id"] in overdue_task_ids:
            workload["overdue"] += 1

    employee_workload = sorted(
        employee_workload.values(),
        key=lambda item: item["total"],
        reverse=True
    )

    active_tasks = [
        task for task in tasks
        if task["status"] != "Completed"
    ]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_tasks": len(tasks),
        "active_tasks": len(active_tasks),
        "completed_tasks": len(tasks) - len(active_tasks),
        "overdue_count": len(overdue_tasks),
        "due_today_count": len(due_today_tasks),
        "overdue_tasks": overdue_tasks,
        "due_today_tasks": due_today_tasks,
        "employee_workload": employee_workload
    }