
import time
import logging

from tools.notification_tools import generate_notifications

logging.basicConfig(level=logging.INFO)


def run_notification_monitor():
    """Continuously check task deadlines in the background."""

    while True:
        try:
            generated = generate_notifications()

            if generated:
                logging.info(
                    "CHIEF generated %s new notification(s).",
                    generated
                )

        except Exception:
            logging.exception("CHIEF notification monitor error")

        time.sleep(60)
