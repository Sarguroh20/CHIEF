
from agents.task_agent import task_agent

from tools.task_tools import (
    get_overdue_tasks,
    get_tasks_due_today,
    get_tasks_by_employee
)
from agents.calendar_agent import calendar_agent


def chief_orchestrator(action, **kwargs):
    print("\nCHIEF Executive Orchestrator activated...")

    if action == "create_task":
        result = task_agent("create", **kwargs)

    elif action == "list_tasks":
        result = task_agent("list")

    elif action == "update_task":
        result = task_agent("update_status", **kwargs)

    elif action == "filter_tasks":
        result = task_agent("filter", **kwargs)

    elif action == "get_overdue_tasks":
        print("CHIEF Task Intelligence: Finding overdue tasks...")
        result = get_overdue_tasks()

    elif action == "get_tasks_due_today":
        print("CHIEF Task Intelligence: Finding tasks due today...")
        result = get_tasks_due_today()

    elif action == "get_employee_tasks":
        print("CHIEF Task Intelligence: Finding employee tasks...")
        result = get_tasks_by_employee(kwargs.get("employee"))

    elif action == "create_meeting":
        result = calendar_agent("create_meeting", **kwargs)
    else:
        return {
            "success": False,
            "message": "I couldn't identify that operation."
        }

    return {
        "success": True,
        "agent": (
            "Calendar Agent"
            if action == "create_meeting"
            else "Task Intelligence"
            if action in (
                "get_overdue_tasks",
                "get_tasks_due_today",
                "get_employee_tasks"
            )
            else "Task Agent"
            ),"result": result
    }
