
import os
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from agents.nl_task_agent import OLLAMA_URL, handle_natural_language
from services.database import get_connection, initialize_database


INSTRUCTION = "Assign Rahul to submit the sales report by 5 PM."
LIVE_INSTRUCTION = "Assign Rahul to submit the sales report by 5 PM tomorrow."


def _deadline_in(hours):
    return (datetime.now() + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def _ollama_is_available():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


class NaturalLanguageTaskTests(unittest.TestCase):

    def setUp(self):
        self.previous_directory = os.getcwd()
        self.temp_directory = tempfile.TemporaryDirectory()
        os.chdir(self.temp_directory.name)
        initialize_database()

    def tearDown(self):
        os.chdir(self.previous_directory)
        self.temp_directory.cleanup()

    def _count_tasks(self):
        connection = get_connection()
        try:
            return connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        finally:
            connection.close()

    def _all_tasks(self):
        connection = get_connection()
        try:
            return connection.execute(
                "SELECT employee, task, deadline, status FROM tasks"
            ).fetchall()
        finally:
            connection.close()

    def test_instruction_creates_exactly_one_database_record(self):
        deadline = _deadline_in(24)

        def fake_model(instruction):
            self.assertEqual(instruction, INSTRUCTION)
            return {
                "action": "create_task",
                "employee": "Rahul",
                "task": "submit the sales report",
                "deadline": deadline,
            }

        response = handle_natural_language(INSTRUCTION, llm_fn=fake_model)

        self.assertTrue(response["success"])
        self.assertFalse(response["needs_clarification"])
        self.assertEqual(response["agent"], "Task Agent")
        self.assertEqual(self._count_tasks(), 1)
        self.assertEqual(
            self._all_tasks(),
            [("Rahul", "submit the sales report", deadline, "Created")],
        )

    def test_missing_deadline_asks_for_clarification_and_creates_nothing(self):
        def fake_model(instruction):
            return {
                "action": "create_task",
                "employee": "Rahul",
                "task": "submit the sales report",
                "deadline": None,
            }

        response = handle_natural_language(INSTRUCTION, llm_fn=fake_model)

        self.assertFalse(response["success"])
        self.assertTrue(response["needs_clarification"])
        self.assertIn("deadline", response["missing_fields"])
        self.assertEqual(self._count_tasks(), 0)

    def test_past_deadline_asks_for_future_deadline_and_creates_nothing(self):
        deadline = _deadline_in(-1)

        def fake_model(instruction):
            return {
                "action": "create_task",
                "employee": "Rahul",
                "task": "submit the sales report",
                "deadline": deadline,
            }

        response = handle_natural_language(INSTRUCTION, llm_fn=fake_model)

        self.assertFalse(response["success"])
        self.assertTrue(response["needs_clarification"])
        self.assertIn("deadline", response["missing_fields"])
        self.assertIn("future deadline", response["message"].lower())
        self.assertEqual(self._count_tasks(), 0)

    def test_future_deadline_creates_exactly_one_record(self):
        deadline = _deadline_in(24)

        def fake_model(instruction):
            return {
                "action": "create_task",
                "employee": "Rahul",
                "task": "submit the sales report",
                "deadline": deadline,
            }

        response = handle_natural_language(INSTRUCTION, llm_fn=fake_model)

        self.assertTrue(response["success"])
        self.assertFalse(response["needs_clarification"])
        self.assertEqual(self._count_tasks(), 1)
        self.assertEqual(self._all_tasks()[0][2], deadline)

    def test_unknown_action_asks_for_clarification_and_creates_nothing(self):
        def fake_model(instruction):
            return {"action": "unknown"}

        response = handle_natural_language(INSTRUCTION, llm_fn=fake_model)

        self.assertFalse(response["success"])
        self.assertTrue(response["needs_clarification"])
        self.assertEqual(self._count_tasks(), 0)

    def test_list_action_still_works_through_natural_language(self):
        def fake_model(instruction):
            return {"action": "list_tasks"}

        response = handle_natural_language("Show all tasks.", llm_fn=fake_model)

        self.assertTrue(response["success"])
        self.assertEqual(response["result"], [])

    @unittest.skipUnless(
        _ollama_is_available(),
        f"Ollama is not running at {OLLAMA_URL}",
    )
    def test_live_ollama_instruction_creates_exactly_one_record(self):
        response = handle_natural_language(LIVE_INSTRUCTION)

        self.assertTrue(response["success"], response)
        self.assertFalse(response["needs_clarification"])
        self.assertEqual(self._count_tasks(), 1)

        employee, task, deadline, status = self._all_tasks()[0]
        self.assertEqual(employee, "Rahul")
        self.assertIn("sales report", task.lower())
        self.assertEqual(status, "Created")
        self.assertTrue(deadline)
