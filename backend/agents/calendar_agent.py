
from services.google_calendar_service import create_meeting


def calendar_agent(action, **kwargs):
    print(f"CHIEF Calendar Agent: Executing {action}")

    if action == "create_meeting":
        return create_meeting(
            title=kwargs.get("title"),
            start=kwargs.get("start"),
            end=kwargs.get("end"),
            description=kwargs.get("description", ""),
            location=kwargs.get("location", "")
        )

    return {
        "success": False,
        "message": "I couldn't identify that calendar operation."
    }
