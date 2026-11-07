
import json
import os
from datetime import datetime, timedelta
from threading import Thread
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from agents.nl_task_agent import handle_natural_language

from services.database import initialize_database
from services.notification_service import run_notification_monitor

from services.google_calendar_service import (
    create_oauth_flow,
    save_oauth_state,
    load_oauth_state,
    list_upcoming_meetings,
    CalendarNotConnected
)

from tools.notification_tools import (
    get_notifications,
    mark_notification_read
)

from tools.task_tools import (
    create_task,
    get_all_tasks,
    update_task_status,
    get_tasks_by_status
)

from google.oauth2.credentials import Credentials


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


class CHIEFHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=FRONTEND_DIR,
            **kwargs
        )

    # --------------------------------
    # JSON RESPONSE
    # --------------------------------

    def send_json(self, data, status=200):

        body = json.dumps(
            data,
            default=str
        ).encode()

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        self.wfile.write(body)

    # --------------------------------
    # READ JSON REQUEST
    # --------------------------------

    def read_json(self):

        length = int(
            self.headers.get("Content-Length", 0)
        )

        return json.loads(
            self.rfile.read(length) or b"{}"
        )

    # ================================================
    # GET REQUESTS
    # ================================================

    def do_GET(self):

        parsed = urlparse(self.path)

        # --------------------------------
        # GOOGLE CALENDAR AUTHENTICATION
        # --------------------------------

        if parsed.path == "/auth/google":

            try:
                flow = create_oauth_flow()

                # Generate authorization URL first.
                # This also generates the PKCE verifier.

                authorization_url, state = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="false",
                    prompt="consent"
                )

                # Save state and verifier after generation.

                save_oauth_state(flow, state)

                self.send_response(302)
                self.send_header("Location", authorization_url)
                self.end_headers()

                return

            except Exception as error:

                return self.send_json({
                    "success": False,
                    "message": str(error)
                }, 500)

        # --------------------------------
        # GOOGLE OAUTH CALLBACK
        # --------------------------------

        if parsed.path == "/oauth2callback":

            try:
                params = parse_qs(parsed.query)

                if "error" in params:

                    return self.send_json({
                        "success": False,
                        "message": params["error"][0]
                    }, 400)

                code = params.get("code", [None])[0]
                state = params.get("state", [None])[0]

                if not code or not state:

                    return self.send_json({
                        "success": False,
                        "message": "Authorization code or state missing."
                    }, 400)

                # Validate state and retrieve original PKCE verifier.

                code_verifier = load_oauth_state(state)

                # Create a new flow and restore the verifier.

                flow = create_oauth_flow()
                flow.code_verifier = code_verifier

                # Exchange authorization code directly.
                # This avoids the strict scope comparison performed
                # by Flow.fetch_token when Google returns additional
                # previously granted scopes.

                token_data = flow.oauth2session.fetch_token(
                    token_url=flow.client_config["token_uri"],
                    code=code,
                    client_secret=flow.client_config["client_secret"],
                    code_verifier=code_verifier
                )

                # Save credentials using only the Calendar scope
                # required by CHIEF.

                credentials = Credentials(
                    token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=flow.client_config["token_uri"],
                    client_id=flow.client_config["client_id"],
                    client_secret=flow.client_config["client_secret"],
                    scopes=[
                        "https://www.googleapis.com/auth/calendar"
                    ],
                    expiry=datetime.utcnow() + timedelta(
                        seconds=int(token_data.get("expires_in", 3600))
                    )
                )

                token_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "token.json"
                )

                with open(
                    token_path,
                    "w",
                    encoding="utf-8"
                ) as token_file:

                    token_file.write(
                        credentials.to_json()
                    )

                # Redirect to CHIEF dashboard.

                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()

                return

            except Exception as error:

                return self.send_json({
                    "success": False,
                    "message": str(error)
                }, 500)

        # --------------------------------
        # GOOGLE CALENDAR MEETINGS API
        # --------------------------------

        if parsed.path == "/api/meetings":

            try:
                meetings = list_upcoming_meetings()

                return self.send_json({
                    "success": True,
                    "connected": True,
                    "meetings": meetings
                })

            except CalendarNotConnected as error:

                return self.send_json({
                    "success": False,
                    "connected": False,
                    "message": str(error),
                    "auth_url": "/auth/google",
                    "meetings": []
                }, 401)

            except Exception as error:

                return self.send_json({
                    "success": False,
                    "message": str(error),
                    "meetings": []
                }, 500)

        # --------------------------------
        # NOTIFICATIONS API
        # --------------------------------

        if parsed.path == "/api/notifications":

            params = parse_qs(parsed.query)

            unread_only = (
                params.get("unread", ["false"])[0].lower() == "true"
            )

            notifications = get_notifications(
                unread_only=unread_only
            )

            return self.send_json(notifications)

        # --------------------------------
        # TASKS API
        # --------------------------------

        if parsed.path == "/api/tasks":

            params = parse_qs(parsed.query)

            status = params.get("status", [None])[0]

            tasks = (
                get_tasks_by_status(status)
                if status
                else get_all_tasks()
            )

            return self.send_json(tasks)

        # --------------------------------
        # DEFAULT FRONTEND ROUTE
        # --------------------------------

        return super().do_GET()

    # ================================================
    # POST REQUESTS
    # ================================================

    def do_POST(self):

        # --------------------------------
        # AI ASSISTANT
        # --------------------------------

        if self.path == "/api/assistant":

            try:
                data = self.read_json()

                instruction = data.get("instruction", "")

                result = handle_natural_language(instruction)

                return self.send_json(result, 200)

            except Exception as error:

                return self.send_json({
                    "success": False,
                    "message": str(error)
                }, 500)

        # --------------------------------
        # CREATE TASK
        # --------------------------------

        if self.path != "/api/tasks":

            return self.send_json({
                "error": "Route not found"
            }, 404)

        try:
            data = self.read_json()

            required = [
                "employee",
                "task",
                "deadline"
            ]

            if not all(data.get(field) for field in required):

                return self.send_json({
                    "error": "Employee, task and deadline are required"
                }, 400)

            result = create_task(
                employee=data["employee"],
                task=data["task"],
                deadline=data["deadline"]
            )

            return self.send_json(result, 201)

        except Exception as error:

            return self.send_json({
                "error": str(error)
            }, 500)

    # ================================================
    # PATCH REQUESTS
    # ================================================

    def do_PATCH(self):

        parsed = urlparse(self.path)

        # --------------------------------
        # MARK NOTIFICATION AS READ
        # --------------------------------

        if parsed.path.startswith("/api/notifications/"):

            notification_id = parsed.path.removeprefix(
                "/api/notifications/"
            )

            if not notification_id:

                return self.send_json({
                    "error": "Invalid notification ID"
                }, 400)

            updated = mark_notification_read(
                notification_id
            )

            if not updated:

                return self.send_json({
                    "error": "Notification not found"
                }, 404)

            return self.send_json({
                "success": True,
                "message": "Notification marked as read"
            })

        # --------------------------------
        # UPDATE TASK STATUS
        # --------------------------------

        task_id = parsed.path.removeprefix(
            "/api/tasks/"
        )

        if not task_id or task_id == parsed.path:

            return self.send_json({
                "error": "Invalid task ID"
            }, 400)

        try:
            data = self.read_json()

            status = data.get("status")

            if status not in [
                "Created",
                "In Progress",
                "Completed"
            ]:

                return self.send_json({
                    "error": "Invalid status"
                }, 400)

            updated = update_task_status(
                task_id,
                status
            )

            if not updated:

                return self.send_json({
                    "error": "Task not found"
                }, 404)

            return self.send_json({
                "success": True,
                "message": "Task status updated",
                "task_id": task_id,
                "status": status
            })

        except Exception as error:

            return self.send_json({
                "error": str(error)
            }, 500)


# ================================================
# START CHIEF SERVER
# ================================================

if __name__ == "__main__":

    initialize_database()

    notification_thread = Thread(
        target=run_notification_monitor,
        daemon=True
    )

    notification_thread.start()

    server = ThreadingHTTPServer(
        ("127.0.0.1", 8000),
        CHIEFHandler
    )

    print("CHIEF server running at http://127.0.0.1:8000")

    server.serve_forever()
