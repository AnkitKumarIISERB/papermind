"""Celery app configuration and task definitions."""

import logging

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "papermind",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@worker_process_init.connect
def preload_model(**kwargs):
    """Pre-load the embedding model at worker startup to avoid cold-start latency."""
    logger.info("Pre-loading embedding model at worker startup...")
    from app.services.embeddings import get_embedding_model
    get_embedding_model()
    logger.info("Embedding model pre-loaded.")


@celery_app.task(bind=True, name="papermind.ingest_topic", max_retries=2)
def ingest_topic_task(self, topic: str, max_papers: int, topic_search_id: int):
    """
    Celery task that runs the full paper ingestion pipeline.
    Runs synchronously inside the Celery worker using a sync DB session.
    """
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

    async def _run():
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as db:
            from app.services.ingestion import ingest_topic
            result = await ingest_topic(
                topic=topic,
                max_papers=max_papers,
                topic_search_id=topic_search_id,
                db=db,
            )
            return result

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        logger.info(f"Ingestion task completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Ingestion task failed: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        loop.close()
