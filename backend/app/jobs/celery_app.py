"""
Celery application instance and configuration (§8.12).
Broker: Redis DB 0. Serializer: JSON only (no pickle). Prefetch: 1.
Queues: ingest, eval, review.
"""

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import get_settings

settings = get_settings()

# Use DB 0 for Celery broker
broker_url = settings.get_redis_url(db=0)

celery_app = Celery(
    "repogpt",
    broker=broker_url,
    backend=None,  # State is stored in MongoDB jobs collection
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 9000},
    task_default_queue="ingest",
    task_queues={
        "ingest": {"exchange": "ingest", "routing_key": "ingest"},
        "eval": {"exchange": "eval", "routing_key": "eval"},
        "review": {"exchange": "review", "routing_key": "review"},
    },
    task_annotations={
        "ingest_repository_task": {
            "time_limit": 4200,  # 70 minutes hard limit
            "soft_time_limit": 3600,  # 60 minutes soft limit
        },
        "evaluate_benchmark_task": {
            "time_limit": 7800,  # 130 minutes hard limit
            "soft_time_limit": 7200,  # 120 minutes soft limit
        },
        "review_pull_request_task": {
            "time_limit": 1500,  # 25 minutes hard limit
            "soft_time_limit": 1200,  # 20 minutes soft limit
        },
    },
)

# Auto-discover tasks in app.jobs
celery_app.autodiscover_tasks(["app.jobs"])
