
import json
import os
import re
import urllib.error
import urllib.request

from datetime import date, datetime, timedelta

from agents.orchestrator import chief_orchestrator


OLLAMA_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "CHIEF_OLLAMA_MODEL",
    "qwen2.5:1.5b"
)

OLLAMA_TIMEOUT = float(
    os.getenv("CHIEF_OLLAMA_TIMEOUT", "60")
)


# Task actions
CREATE_ACTION = "create_task"
LIST_ACTION = "list_tasks"
UPDATE_ACTION = "update_task"
FILTER_ACTION = "filter_tasks"

# Calendar actions
CREATE_MEETING_ACTION = "create_meeting"

# Task intelligence actions
OVERDUE_ACTION = "get_overdue_tasks"
DUE_TODAY_ACTION = "get_tasks_due_today"
EMPLOYEE_TASKS_ACTION = "get_employee_tasks"


ALLOWED_ACTIONS = {
    CREATE_ACTION,
    LIST_ACTION,
    UPDATE_ACTION,
    FILTER_ACTION,
    CREATE_MEETING_ACTION,
    OVERDUE_ACTION,
    DUE_TODAY_ACTION,
    EMPLOYEE_TASKS_ACTION,
}


ALLOWED_STATUSES = {
    "Created",
    "In Progress",
    "Completed",
}


ACTION_ALIASES = {
    "create": CREATE_ACTION,
    "assign": CREATE_ACTION,
    "add": CREATE_ACTION,
    "create_task": CREATE_ACTION,

    "list": LIST_ACTION,
    "show": LIST_ACTION,
    "list_tasks": LIST_ACTION,

    "update": UPDATE_ACTION,
    "update_task": UPDATE_ACTION,

    "filter": FILTER_ACTION,
    "filter_tasks": FILTER_ACTION,

    "schedule_meeting": CREATE_MEETING_ACTION,
    "schedule": CREATE_MEETING_ACTION,
    "book_meeting": CREATE_MEETING_ACTION,
    "create_meeting": CREATE_MEETING_ACTION,

    "get_overdue_tasks": OVERDUE_ACTION,
    "overdue": OVERDUE_ACTION,

    "get_tasks_due_today": DUE_TODAY_ACTION,
    "due_today": DUE_TODAY_ACTION,

    "get_employee_tasks": EMPLOYEE_TASKS_ACTION,
    "employee_tasks": EMPLOYEE_TASKS_ACTION,
}


STATUS_ALIASES = {
    "created": "Created",
    "in progress": "In Progress",
    "in_progress": "In Progress",
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
}


FIELD_LABELS = {
    "instruction": "the instruction",
    "action": "the action",
    "employee": "the employee or attendee",
    "task": "the task description",
    "deadline": "the deadline",
    "status": "the task status",
    "task_id": "the task id",
    "title": "the meeting title",
    "start": "the meeting start date and time",
    "end": "the meeting end date and time",
}


TIME_ONLY_PATTERN = re.compile(
    r"^\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?$",
    re.IGNORECASE,
)


class ClarificationNeeded(Exception):

    def __init__(self, fields, message=None):

        self.fields = list(dict.fromkeys(fields))

        if message is None:
            labels = [
                FIELD_LABELS.get(field, field)
                for field in self.fields
            ]

            message = (
                "I need more information: "
                + ", ".join(labels)
                + "."
            )

        self.message = message

        super().__init__(message)


class TaskExtractionError(Exception):
    pass


def _system_prompt():

    today = date.today()
    today_text = today.isoformat()
    weekday = today.strftime("%A")

    return f"""You are CHIEF, an Executive Assistant.

Convert one natural-language instruction into a single JSON object.

Return only the JSON object, with no markdown or extra text.

Today is {today_text} ({weekday}).

Allowed actions:
create_task,
list_tasks,
update_task,
filter_tasks,
get_overdue_tasks,
get_tasks_due_today,
get_employee_tasks,
create_meeting.

Allowed statuses:
Created, In Progress, Completed.

The JSON object must have these keys:

action,
employee,
task,
deadline,
status,
task_id,
title,
start,
end,
description,
location,
missing,
clarification.

TASK RULES:

- create_task needs employee, task, and deadline.
- list_tasks needs nothing else.
- update_task needs task_id and status.
- filter_tasks needs status.
- get_overdue_tasks needs no additional fields.
- get_tasks_due_today needs no additional fields.
- get_employee_tasks needs the employee name.
- If a required value is missing or ambiguous, put its field name in "missing" and ask a short question in "clarification".
- Resolve relative dates such as today, tomorrow, Friday, or next week into a concrete ISO date.
- If only a time is given, such as 5 PM, use today's date, for example {today_text}T17:00:00.
- Use null for values that are not present.
- Never invent an employee, team member, deadline, status, or task id.
- Never write or suggest SQL.
- If the user asks about overdue or past-deadline tasks, use get_overdue_tasks.
- If the user asks what tasks are due today, use get_tasks_due_today.
- If the user asks what a particular employee is working on or what tasks are assigned to them, use get_employee_tasks.
- Extract the employee name exactly as provided by the user.

CALENDAR MEETING RULES:

- For meeting requests, use create_meeting.
- A meeting requires a title and start date/time.
- Extract the attendee's name into employee when mentioned.
- Extract meeting details into description.
- Extract meeting location into location when mentioned.
- Resolve relative dates such as tomorrow and next Monday.
- Resolve meeting times into ISO 8601 date-time values.
- If the user does not specify an end time, return null for end.
- CHIEF will automatically use a 30-minute duration when end is missing.
- Never invent a meeting title, date, time, attendee, or location.
- If the title or start date/time is missing, request clarification.
- Do not confuse meeting requests with task creation requests.
- A meeting with an attendee does not require their email address.
- Do not claim that an attendee has been invited.

Example 1

User: Assign Rahul to submit the sales report by 5 PM.

Assistant:
{{"action":"create_task","employee":"Rahul","task":"submit the sales report","deadline":"{today_text}T17:00:00","status":null,"task_id":null,"title":null,"start":null,"end":null,"description":null,"location":null,"missing":[],"clarification":null}}

Example 2

User: Show all completed tasks.

Assistant:
{{"action":"filter_tasks","employee":null,"task":null,"deadline":null,"status":"Completed","task_id":null,"title":null,"start":null,"end":null,"description":null,"location":null,"missing":[],"clarification":null}}

Example 3

User: Mark task 4f2a as completed.

Assistant:
{{"action":"update_task","employee":null,"task":null,"deadline":null,"status":"Completed","task_id":"4f2a","title":null,"start":null,"end":null,"description":null,"location":null,"missing":[],"clarification":null}}

Example 4

User: Show all tasks.

Assistant:
{{"action":"list_tasks","employee":null,"task":null,"deadline":null,"status":null,"task_id":null,"title":null,"start":null,"end":null,"description":null,"location":null,"missing":[],"clarification":null}}

Example 5

User: Assign someone to prepare the report.

Assistant:
{{"action":"create_task","employee":null,"task":"prepare the report","deadline":null,"status":null,"task_id":null,"title":null,"start":null,"end":null,"description":null,"location":null,"missing":["employee","deadline"],"clarification":"Who should prepare the report, and by when?"}}

Example 6

User: Schedule a meeting with Rahul tomorrow at 3 PM about the sales review.

Assistant:
{{"action":"create_meeting","employee":"Rahul","task":null,"deadline":null,"status":null,"task_id":null,"title":"Sales review","start":"ACTUAL_TOMORROW_DATE T15:00:00","end":null,"description":"Meeting with Rahul about the sales review","location":null,"missing":[],"clarification":null}}

The ACTUAL_TOMORROW_DATE placeholder above is illustrative. Always return the actual ISO date.
"""


def _parse_model_json(raw):

    if not isinstance(raw, str):
        raise TaskExtractionError(
            "The language model did not return valid JSON."
        )

    text = raw.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise TaskExtractionError(
            "I couldn't understand that instruction. Please rephrase it."
        )

    try:
        data = json.loads(text[start:end + 1])

    except json.JSONDecodeError as error:
        raise TaskExtractionError(
            "I couldn't understand that instruction. Please rephrase it."
        ) from error

    if not isinstance(data, dict):
        raise TaskExtractionError(
            "I couldn't understand that instruction. Please rephrase it."
        )

    return data


def _call_ollama(instruction):

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": _system_prompt()
            },
            {
                "role": "user",
                "content": instruction
            },
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 512
        },
    }

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT
        ) as response:

            body = json.loads(
                response.read().decode("utf-8")
            )

    except (
        urllib.error.URLError,
        TimeoutError,
        OSError
    ) as error:

        raise TaskExtractionError(
            "I couldn't reach the local language model. Please try again."
        ) from error

    content = body.get(
        "message", {}
    ).get("content", "")

    return _parse_model_json(content)


def extract_task_fields(instruction, llm_fn=None):

    if not isinstance(instruction, str) or not instruction.strip():

        raise ClarificationNeeded(
            ["instruction"],
            "Please tell me what you would like CHIEF to do."
        )

    model_client = llm_fn or _call_ollama

    extracted = model_client(instruction)

    if isinstance(extracted, str):
        extracted = _parse_model_json(extracted)

    if not isinstance(extracted, dict):

        raise TaskExtractionError(
            "I couldn't understand that instruction. Please rephrase it."
        )

    return extracted


def _clean_text(value):

    if not isinstance(value, str):
        return None

    text = value.strip()

    if not text:
        return None

    if text.lower() in {
        "null",
        "none",
        "unknown",
        "n/a",
        "na",
        "not specified"
    }:
        return None

    return text


def _normalize_action(value):

    text = _clean_text(value)

    if text is None:
        return None

    key = text.lower().replace("-", "_").replace(" ", "_")

    key = ACTION_ALIASES.get(key, key)

    return key if key in ALLOWED_ACTIONS else None


def _normalize_status(value):

    text = _clean_text(value)

    if text is None:
        return None

    key = text.lower().replace("_", " ")

    key = STATUS_ALIASES.get(key, text)

    return key if key in ALLOWED_STATUSES else None


def _normalize_deadline(value):

    text = _clean_text(value)

    if text is None:
        return None

    candidate = text.replace("Z", "+00:00")

    for parser in (
        datetime.fromisoformat,
        date.fromisoformat
    ):

        try:
            return parser(candidate).isoformat()

        except ValueError:
            pass

    for date_format in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%B %d %Y",
        "%b %d %Y",
    ):

        try:

            return datetime.strptime(
                text,
                date_format
            ).isoformat()

        except ValueError:
            pass

    if TIME_ONLY_PATTERN.match(text):

        cleaned_time = text.upper().replace(".", "")

        for time_format in (
            "%I:%M %p",
            "%I %p",
            "%H:%M"
        ):

            try:

                parsed_time = datetime.strptime(
                    cleaned_time,
                    time_format
                ).time()

                return datetime.combine(
                    date.today(),
                    parsed_time
                ).isoformat()

            except ValueError:
                pass

    return None


def _deadline_has_passed(deadline):

    deadline_datetime = datetime.fromisoformat(deadline)

    if deadline_datetime.tzinfo is not None:
        now = datetime.now(deadline_datetime.tzinfo)

    else:
        now = datetime.now()

    return deadline_datetime <= now


def _declared_missing(extracted):

    raw_missing = extracted.get("missing")

    if not isinstance(raw_missing, list):
        return []

    return [
        str(field).strip().lower()
        for field in raw_missing
        if isinstance(field, str) and field.strip()
    ]


def validate_task_fields(extracted):

    action = _normalize_action(
        extracted.get("action")
    )

    if action is None:

        raise ClarificationNeeded(
            ["action"],
            "I couldn't identify that operation."
        )

    employee = _clean_text(
        extracted.get("employee")
    )

    task = _clean_text(
        extracted.get("task")
    )

    deadline = _normalize_deadline(
        extracted.get("deadline")
    )

    status = _normalize_status(
        extracted.get("status")
    )

    task_id = _clean_text(
        extracted.get("task_id")
    )

    declared_missing = _declared_missing(extracted)

    # ----------------------------------
    # CREATE GOOGLE CALENDAR MEETING
    # ----------------------------------

    if action == CREATE_MEETING_ACTION:

        title = _clean_text(
            extracted.get("title")
        )

        start = _normalize_deadline(
            extracted.get("start")
        )

        end = _normalize_deadline(
            extracted.get("end")
        )

        description = (
            _clean_text(extracted.get("description")) or ""
        )

        location = (
            _clean_text(extracted.get("location")) or ""
        )

        required = {
            "title": title,
            "start": start,
        }

        missing = [
            field
            for field, value in required.items()
            if not value
        ]

        missing.extend(
            field
            for field in declared_missing
            if field in required and field not in missing
        )

        if missing:

            raise ClarificationNeeded(missing)

        try:

            start_datetime = datetime.fromisoformat(start)

            if end:

                end_datetime = datetime.fromisoformat(end)

            else:

                end_datetime = (
                    start_datetime + timedelta(minutes=30)
                )

        except ValueError:

            raise ClarificationNeeded(
                ["start"],
                "Please provide a valid meeting date and time."
            )

        # Make both datetimes timezone-compatible.

        if start_datetime.tzinfo and end_datetime.tzinfo is None:

            end_datetime = end_datetime.replace(
                tzinfo=start_datetime.tzinfo
            )

        elif end_datetime.tzinfo and start_datetime.tzinfo is None:

            start_datetime = start_datetime.replace(
                tzinfo=end_datetime.tzinfo
            )

        if start_datetime.tzinfo:

            now = datetime.now(
                start_datetime.tzinfo
            )

        else:

            now = datetime.now()

        if start_datetime <= now:

            raise ClarificationNeeded(
                ["start"],
                "That meeting start time has already passed. Please provide a future time."
            )

        if end_datetime <= start_datetime:

            raise ClarificationNeeded(
                ["end"],
                "The meeting end time must be after its start time."
            )

        # Include the attendee name in the description.
        # This does not send an invitation.

        if employee:
            if not description:
                description = f"Meeting with {employee}."
        return {
            "action": action,
            "employee": employee,
            "title": title,
            "start": start_datetime.isoformat(),
            "end": end_datetime.isoformat(),
            "description": description,
            "location": location,
        }

    # ----------------------------------
    # CREATE TASK
    # ----------------------------------

    if action == CREATE_ACTION:

        required = {
            "employee": employee,
            "task": task,
            "deadline": deadline,
        }

        missing = [
            field
            for field, value in required.items()
            if not value
        ]

        missing.extend(
            field
            for field in declared_missing
            if field in required and field not in missing
        )

        if missing:
            raise ClarificationNeeded(missing)

        if _deadline_has_passed(deadline):

            raise ClarificationNeeded(
                ["deadline"],
                "That deadline has already passed. Please provide a future deadline."
            )

        return {
            "action": action,
            "employee": employee,
            "task": task,
            "deadline": deadline,
        }

    # ----------------------------------
    # FILTER TASKS
    # ----------------------------------

    if action == FILTER_ACTION:

        missing = [] if status else ["status"]

        missing.extend(
            field
            for field in declared_missing
            if field == "status" and field not in missing
        )

        if missing:
            raise ClarificationNeeded(missing)

        return {
            "action": action,
            "status": status
        }

    # ----------------------------------
    # TASK INTELLIGENCE
    # ----------------------------------

    if action in {
        OVERDUE_ACTION,
        DUE_TODAY_ACTION
    }:

        return {
            "action": action
        }

    if action == EMPLOYEE_TASKS_ACTION:

        if not employee:
            raise ClarificationNeeded(["employee"])

        return {
            "action": action,
            "employee": employee
        }

    # ----------------------------------
    # UPDATE TASK
    # ----------------------------------

    if action == UPDATE_ACTION:

        required = {
            "task_id": task_id,
            "status": status,
        }

        missing = [
            field
            for field, value in required.items()
            if not value
        ]

        missing.extend(
            field
            for field in declared_missing
            if field in required and field not in missing
        )

        if missing:
            raise ClarificationNeeded(missing)

        return {
            "action": action,
            "task_id": task_id,
            "status": status
        }

    # ----------------------------------
    # LIST TASKS
    # ----------------------------------

    if action == LIST_ACTION:

        return {
            "action": action
        }

    raise ClarificationNeeded(["action"])


def _dispatch(validated):

    action = validated["action"]

    # ----------------------------------
    # CALENDAR AGENT
    # ----------------------------------

    if action == CREATE_MEETING_ACTION:

        return chief_orchestrator(
            action=CREATE_MEETING_ACTION,
            title=validated["title"],
            start=validated["start"],
            end=validated["end"],
            description=validated["description"],
            location=validated["location"],
        )

    # ----------------------------------
    # TASK AGENT
    # ----------------------------------

    if action == CREATE_ACTION:

        return chief_orchestrator(
            action=CREATE_ACTION,
            employee=validated["employee"],
            task=validated["task"],
            deadline=validated["deadline"],
        )

    if action == LIST_ACTION:

        return chief_orchestrator(
            action=LIST_ACTION
        )

    if action == FILTER_ACTION:

        return chief_orchestrator(
            action=FILTER_ACTION,
            status=validated["status"],
        )

    if action == UPDATE_ACTION:

        return chief_orchestrator(
            action=UPDATE_ACTION,
            task_id=validated["task_id"],
            status=validated["status"],
        )

    # ----------------------------------
    # TASK INTELLIGENCE
    # ----------------------------------

    if action == OVERDUE_ACTION:

        return chief_orchestrator(
            action=OVERDUE_ACTION
        )

    if action == DUE_TODAY_ACTION:

        return chief_orchestrator(
            action=DUE_TODAY_ACTION
        )

    if action == EMPLOYEE_TASKS_ACTION:

        return chief_orchestrator(
            action=EMPLOYEE_TASKS_ACTION,
            employee=validated["employee"]
        )

    raise ClarificationNeeded(["action"])


def _clarification_response(error):

    return {
        "success": False,
        "needs_clarification": True,
        "message": error.message,
        "missing_fields": error.fields,
    }


def handle_natural_language(instruction, llm_fn=None):

    try:

        extracted = extract_task_fields(
            instruction,
            llm_fn=llm_fn
        )

        text = instruction.lower()

        detected_action = _normalize_action(
            extracted.get("action")
        )

        # Do not override meeting requests
        # with task-intelligence detection.

        if detected_action != CREATE_MEETING_ACTION:

            # Overdue task detection

            if any(word in text for word in (
                "overdue",
                "past deadline",
                "late tasks"
            )):

                extracted["action"] = OVERDUE_ACTION

            # Due today detection

            elif any(phrase in text for phrase in (
                "due today",
                "today's tasks",
                "tasks for today"
            )):

                extracted["action"] = DUE_TODAY_ACTION

            # Employee task detection

            elif any(phrase in text for phrase in (
                "working on",
                "assigned to",
                "tasks for",
                "tasks assigned to"
            )):

                if extracted.get("employee"):

                    extracted["action"] = EMPLOYEE_TASKS_ACTION

            # Task status filtering

            if "in progress" in text:

                extracted["action"] = FILTER_ACTION
                extracted["status"] = "In Progress"

            elif "completed" in text:

                extracted["action"] = FILTER_ACTION
                extracted["status"] = "Completed"

            elif "pending" in text or "created" in text:

                extracted["action"] = FILTER_ACTION
                extracted["status"] = "Created"

        validated = validate_task_fields(extracted)

    except ClarificationNeeded as error:

        return _clarification_response(error)

    except TaskExtractionError as error:

        return {
            "success": False,
            "needs_clarification": True,
            "message": str(error),
            "missing_fields": [],
        }

    try:

        response = _dispatch(validated)

        response["action"] = validated["action"]

        if "status" in validated:

            response["status"] = validated["status"]

        response["needs_clarification"] = False

        return response

    except Exception as error:

        return {
            "success": False,
            "needs_clarification": False,
            "message": f"CHIEF operation failed: {error}",
        }
