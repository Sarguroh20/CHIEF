
import os
import json
import secrets
from datetime import datetime, timezone

from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
STATE_FILE = os.path.join(BASE_DIR, "oauth_state.json")

REDIRECT_URI = "http://127.0.0.1:8000/oauth2callback"

SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]


class CalendarNotConnected(Exception):
    pass


def create_oauth_flow():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError("credentials.json not found.")

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        autogenerate_code_verifier=True
    )

    flow.redirect_uri = REDIRECT_URI

    return flow


def save_oauth_state(flow, state):
    if not flow.code_verifier:
        raise ValueError("OAuth code verifier was not generated.")

    data = {
        "state": state,
        "code_verifier": flow.code_verifier
    }

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file)

def load_oauth_state(state):
    if not os.path.exists(STATE_FILE):
        raise ValueError("OAuth session not found. Please reconnect.")

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not secrets.compare_digest(data["state"], state):
        raise ValueError("Invalid OAuth state.")

    os.remove(STATE_FILE)

    return data["code_verifier"]


def get_calendar_credentials():
    credentials = None

    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        with open(TOKEN_FILE, "w", encoding="utf-8") as file:
            file.write(credentials.to_json())

    if not credentials or not credentials.valid:
        raise CalendarNotConnected(
            "Google Calendar is not connected. Please connect your account."
        )

    return credentials


def list_upcoming_meetings(max_results=20):
    credentials = get_calendar_credentials()

    calendar = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    now = datetime.now(timezone.utc).isoformat()

    response = calendar.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    meetings = []

    for event in response.get("items", []):
        start = event.get("start", {})
        end = event.get("end", {})

        meetings.append({
            "id": event.get("id"),
            "title": event.get("summary", "Untitled meeting"),
            "description": event.get("description", ""),
            "start": start.get("dateTime", start.get("date")),
            "end": end.get("dateTime", end.get("date")),
            "location": event.get("location", ""),
            "html_link": event.get("htmlLink", ""),
            "status": event.get("status", "")
        })

    return meetings

def create_meeting(
    title,
    start,
    end,
    description="",
    location=""
):
    if not title or not title.strip():
        raise ValueError("Meeting title is required.")

    try:
        start_datetime = datetime.fromisoformat(start)
        end_datetime = datetime.fromisoformat(end)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Invalid meeting date or time. Please provide a valid date and time."
        ) from error

    local_timezone = ZoneInfo("Asia/Kolkata")

    if start_datetime.tzinfo is None:
        start_datetime = start_datetime.replace(
            tzinfo=local_timezone
        )

    if end_datetime.tzinfo is None:
        end_datetime = end_datetime.replace(
            tzinfo=local_timezone
        )

    if end_datetime <= start_datetime:
        raise ValueError("Meeting end time must be after its start time.")

    credentials = get_calendar_credentials()

    calendar = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    event = {
        "summary": title.strip(),
        "description": description,
        "location": location,
        "start": {
            "dateTime": start_datetime.isoformat()
        },
        "end": {
            "dateTime": end_datetime.isoformat()
        }
    }

    created_event = calendar.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return {
        "success": True,
        "event_id": created_event.get("id"),
        "title": created_event.get("summary"),
        "start": created_event.get("start", {}).get("dateTime"),
        "end": created_event.get("end", {}).get("dateTime"),
        "html_link": created_event.get("htmlLink")
    }