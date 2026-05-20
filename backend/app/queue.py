from redis import Redis
from rq import Queue

from .config import settings


redis_conn = Redis.from_url(settings.redis_url)
queue = Queue(settings.queue_name, connection=redis_conn)


def enqueue_video_job(job_id: str):
    from .tasks import process_video_job

    return queue.enqueue(
        process_video_job,
        job_id,
        job_timeout=settings.job_timeout_sec,
    )
