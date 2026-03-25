import sentry_sdk
from celery import Celery
from sentry_sdk.integrations.celery import CeleryIntegration
from kombu import Exchange, Queue


from core.config import settings

# Initialize Sentry for Celery workers
if settings.environment == "production" and settings.sentry_dsn_celery:
    sentry_sdk.init(
        dsn=settings.sentry_dsn_celery,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        send_default_pii=False,
        integrations=[
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
        ],
    )



task_queues = (
    Queue("default",  Exchange("default"),  routing_key="default"),
    Queue("high",     Exchange("high"),     routing_key="high"),
    Queue("low",      Exchange("low"),      routing_key="low"),
)

celery_app = Celery(
    "fastapi_app",
    broker=settings.rabbitmq_url,
    # backend="rpc://",
    include=["app.tasks.notifications"],
)

celery_app.conf.update(
    task_queues=task_queues,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    task_ack_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    timezone="Asia/Tashkent",
    enable_utc=True,
)
