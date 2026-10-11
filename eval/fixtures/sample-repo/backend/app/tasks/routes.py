from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import TaskCreate, TaskResponse, TaskUpdate
from app.tasks.repository import TaskRepository
from app.tasks.service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(db: aiosqlite.Connection = Depends(get_db)) -> TaskService:
    repo = TaskRepository(db)
    return TaskService(repo)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: dict = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Creates a new task for the authenticated user."""
    try:
        task = await service.create_task(
            user_id=current_user["id"],
            title=task_in.title,
            description=task_in.description,
            priority=task_in.priority,
            due_date=task_in.due_date,
        )
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Lists all tasks for the authenticated user."""
    repo = TaskRepository(db)
    return await repo.list_by_user(current_user["id"])


@router.patch("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    """Marks a task as completed."""
    try:
        return await service.complete_task(task_id, current_user["id"])
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Deletes a task owned by the authenticated user."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    await repo.delete(task_id)
    return None
