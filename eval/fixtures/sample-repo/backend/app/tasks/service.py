from datetime import datetime, timezone
from typing import Any
from app.tasks.repository import TaskRepository


class TaskService:
    def __init__(self, repo: TaskRepository):
        self.repo = repo

    async def create_task(self, user_id: int, title: str, description: str | None = None, priority: str = "medium", due_date: str | None = None) -> dict[str, Any]:
        """Validates and creates a new task for the user."""
        if not title or len(title.strip()) == 0:
            raise ValueError("Task title cannot be empty")
        if len(title) > 200:
            raise ValueError("Task title cannot exceed 200 characters")
        if priority not in ["low", "medium", "high", "urgent"]:
            priority = "medium"

        return await self.repo.create(
            user_id=user_id,
            title=title.strip(),
            description=description,
            priority=priority,
            due_date=due_date,
        )

    async def complete_task(self, task_id: int, user_id: int) -> dict[str, Any]:
        """Marks a specific task as completed after verifying ownership."""
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise KeyError("Task not found")
        if task["user_id"] != user_id:
            raise PermissionError("Access forbidden to this task")

        updated = await self.repo.update(task_id, {"status": "completed"})
        return updated

    async def list_overdue(self, reference_time: datetime | None = None) -> list[dict[str, Any]]:
        """Retrieves all tasks whose due date is earlier than the reference timestamp."""
        ref = reference_time or datetime.now(timezone.utc)
        iso_str = ref.isoformat()
        return await self.repo.list_overdue(iso_str)
