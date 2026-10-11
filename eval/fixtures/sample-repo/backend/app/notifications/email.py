import logging

logger = logging.getLogger("taskflow.notifications")


def send_reminder(recipient_email: str, task_title: str, due_date: str) -> bool:
    """Dispatches an email reminder notification for an upcoming or overdue task."""
    logger.info(
        "Sending task reminder to %s for task '%s' (due %s)",
        recipient_email,
        task_title,
        due_date,
    )
    # Simulated email sending
    return True
