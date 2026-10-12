"""
API v1 root router aggregator.
"""

from fastapi import APIRouter

from app.api.v1 import auth, conversations, eval, health, jobs, messages, repos, users

api_v1_router = APIRouter(prefix="/api/v1")

# Mount routes
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(repos.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(conversations.router)
api_v1_router.include_router(messages.router)
api_v1_router.include_router(eval.router)
