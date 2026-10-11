# TaskFlow System Architecture

## Overview

TaskFlow follows a microservice-lite distributed pattern:

```
[ React SPA ] ---> HTTP ---> [ FastAPI API Gateway & Core ]
                                    |
                            [ SQLite Database ]
                                    ^
                                    | (Read overdue tasks)
                       [ Go Reminder Worker ]
```

## Request Flow: Creating a Task

1. User submits task creation form on React `TasksPage`.
2. `useAuth` hook supplies the Bearer JWT token to `src/api/client.ts`.
3. POST request sent to `/api/v1/tasks` with JSON payload `{ title, description, due_date }`.
4. FastAPI route `app.tasks.routes.create_task` authenticates request via `get_current_user`.
5. Business logic validated in `TaskService.create_task` (`app/tasks/service.py`).
6. Persistence layer `TaskRepository.create` inserts row into SQLite `tasks` table.
7. Serialized task object returned with 201 Created status.
8. Frontend appends new task into local reactive state in `TasksPage`.
