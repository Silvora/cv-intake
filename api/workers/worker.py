from rq import Worker

from api.services.worker_queue import get_cv_queue, get_redis_connection


def main() -> None:
    queue = get_cv_queue()
    worker = Worker([queue], connection=get_redis_connection())
    worker.work()


if __name__ == "__main__":
    main()
