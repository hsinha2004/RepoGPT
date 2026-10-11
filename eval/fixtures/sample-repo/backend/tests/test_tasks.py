import pytest
from app.tasks.service import TaskService


class MockTaskRepo:
    def __init__(self):
        self.tasks = []

    async def create(self, user_id, title, description, priority, due_date):
        item = {
            "id": len(self.tasks) + 1,
            "user_id": user_id,
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "status": "pending",
        }
        self.tasks.append(item)
        return item


@pytest.mark.asyncio
async def test_task_service_validation():
    repo = MockTaskRepo()
    service = TaskService(repo)

    with pytest.raises(ValueError, match="Task title cannot be empty"):
        await service.create_task(user_id=1, title="")

    created = await service.create_task(user_id=1, title="Refactor Auth")
    assert created["title"] == "Refactor Auth"
    assert created["priority"] == "medium"
