import aiosqlite
from typing import Any


class TaskRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create(self, user_id: int, title: str, description: str | None, priority: str, due_date: str | None) -> dict[str, Any]:
        """Inserts a new task row into the database."""
        async with self.db.execute(
            """
            INSERT INTO tasks (user_id, title, description, priority, due_date, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (user_id, title, description, priority, due_date),
        ) as cursor:
            task_id = cursor.lastrowid
            await self.db.commit()

        return await self.get_by_id(task_id)

    async def get_by_id(self, task_id: int) -> dict[str, Any] | None:
        """Retrieves a task by its unique ID."""
        async with self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        """Lists all tasks belonging to a specific user."""
        async with self.db.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update(self, task_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Updates fields of an existing task."""
        fields = []
        values = []
        for k, v in updates.items():
            if v is not None:
                fields.append(f"{k} = ?")
                values.append(v)
        if not fields:
            return await self.get_by_id(task_id)

        values.append(task_id)
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
        await self.db.execute(query, tuple(values))
        await self.db.commit()
        return await self.get_by_id(task_id)

    async def delete(self, task_id: int) -> bool:
        """Deletes a task by ID."""
        await self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await self.db.commit()
        return True

    async def search(self, user_id: int, query: str) -> list[dict[str, Any]]:
        """Searches tasks by title or description pattern."""
        search_pattern = f"%{query}%"
        async with self.db.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND (title LIKE ? OR description LIKE ?)",
            (user_id, search_pattern, search_pattern),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def list_overdue(self, before_iso: str) -> list[dict[str, Any]]:
        """Finds all non-completed tasks past their due date."""
        async with self.db.execute(
            "SELECT t.*, u.email as user_email FROM tasks t JOIN users u ON t.user_id = u.id WHERE t.status != 'completed' AND t.due_date < ?",
            (before_iso,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
