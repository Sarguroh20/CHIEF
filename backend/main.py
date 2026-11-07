
import sys

from services.database import initialize_database
from agents.orchestrator import chief_orchestrator
from agents.nl_task_agent import handle_natural_language


if __name__ == "__main__":

    initialize_database()

    if len(sys.argv) > 1:
        instruction = " ".join(sys.argv[1:])
        response = handle_natural_language(instruction)
        print("\nCHIEF Natural-Language Response:")
    else:
        response = chief_orchestrator(
            action="list_tasks"
        )
        print("\nCHIEF Executive Response:")

    print(response)
