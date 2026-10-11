from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.auth.routes import router as auth_router
from app.db import init_db
from app.tasks.routes import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    """Application factory for TaskFlow REST API."""
    app = FastAPI(
        title="TaskFlow API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "app": "TaskFlow"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
