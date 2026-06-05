from redis import Redis
from rq import Queue

from config.app import appConfig


def get_redis_connection() -> Redis:
    return Redis.from_url(appConfig.worker.redis_url)


def get_cv_queue() -> Queue:
    return Queue(appConfig.worker.queue_name, connection=get_redis_connection())
