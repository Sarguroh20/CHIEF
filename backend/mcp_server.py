
from mcp.server.fastmcp import FastMCP

from services.database import initialize_database
from services.google_calendar_service import (
    create_meeting as calendar_create_meeting,
    list_upcoming_meetings,
)

from tools.task_tools import (
    create_task as db_create_task,
    get_all_tasks,
    update_task_status as db_update_task_status,
    get_tasks_by_status,
    get_executive_briefing,
)

mcp = FastMCP("CHIEF Executive Assistant")


# ---------------- TASK TOOLS ----------------

@mcp.tool()
def create_task(employee: str, task: str, deadline: str) -> dict:
    """Assign a task to an employee with a deadline."""
    initialize_database()

    return db_create_task(
        employee=employee,
        task=task,
        deadline=deadline,
    )


@mcp.tool()
def list_tasks() -> list:
    """Retrieve all tasks from CHIEF."""
    initialize_database()
    return get_all_tasks()


@mcp.tool()
def update_task_status(task_id: str, status: str) -> dict:
    """Update a task to Created, In Progress, or Completed."""
    initialize_database()

    updated = db_update_task_status(
        task_id=task_id,
        status=status,
    )

    return {
        "success": updated,
        "message": (
            "Task status updated successfully."
            if updated
            else "No task found with that task ID."
        ),
    }


@mcp.tool()
def filter_tasks(status: str) -> list:
    """Filter CHIEF tasks by their exact status."""
    initialize_database()
    return get_tasks_by_status(status=status)


@mcp.tool()
def executive_briefing() -> dict:
    """Generate a management briefing with task statistics,
    overdue tasks, today's deadlines, and employee workload."""
    initialize_database()
    return get_executive_briefing()


# ---------------- GOOGLE CALENDAR TOOLS ----------------

@mcp.tool()
def create_meeting(
    title: str,
    start: str,
    end: str,
    description: str = "",
    location: str = "",
) -> dict:
    """Create a meeting in the connected Google Calendar."""
    return calendar_create_meeting(
        title=title,
        start=start,
        end=end,
        description=description,
        location=location,
    )


@mcp.tool()
def list_meetings() -> dict:
    """Retrieve upcoming meetings from the connected Google Calendar."""
    return list_upcoming_meetings()


# ---------------- START MCP SERVER ----------------

if __name__ == "__main__":
    initialize_database()
    mcp.run(transport="stdio")
