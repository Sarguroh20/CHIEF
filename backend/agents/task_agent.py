
from tools.task_tools import (
    create_task,
    get_all_tasks,
    update_task_status,
    get_tasks_by_status
)


def task_agent(action, **kwargs):

    print(f"CHIEF Task Agent: Executing {action}")

    if action == "create":
        return create_task(**kwargs)

    elif action == "list":
        return get_all_tasks()

    elif action == "update_status":
        return update_task_status(**kwargs)

    elif action == "filter":
        return get_tasks_by_status(**kwargs)

    else:
        raise ValueError("Unsupported task action.")
