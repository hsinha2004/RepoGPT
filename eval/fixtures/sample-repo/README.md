# TaskFlow — Modern Collaborative Task Management System

TaskFlow is a distributed task management application demonstrating full-stack architecture with a Python FastAPI backend, React TypeScript SPA frontend, Go background reminder worker, and Java reporting utility.

## Architecture

- **Backend (`backend/`)**: FastAPI REST API with SQLite persistence, JWT authentication, task lifecycle management, and email reminder notifications.
- **Frontend (`frontend/`)**: React 19 + TypeScript single-page application using modern hooks and modular component hierarchy.
- **Reminder Worker (`services/reminder-worker/`)**: Go daemon periodically polling overdue tasks and dispatching alerts.
- **Report Tool (`tools/report/`)**: Java reporting utility generating productivity analytics and CSV exports.

## Quickstart with Docker Compose

```bash
docker compose up -d
```

Frontend is accessible at http://localhost:3000, and API docs at http://localhost:8000/docs.

## Environment Variables

Copy `.env.example` to `.env` and configure:
- `SECRET_KEY`: 32+ character HMAC secret for JWT signing.
- `DATABASE_URL`: SQLite connection URI (`sqlite:///./data/taskflow.db`).
