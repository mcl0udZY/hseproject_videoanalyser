from rq import Worker

from .config import settings
from .queue import redis_conn


def main() -> None:
    worker = Worker([settings.queue_name], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    main()
