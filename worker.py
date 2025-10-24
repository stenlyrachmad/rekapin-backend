from rq import Worker, Queue
from app.services.queue import redis_conn

if __name__ == "__main__":
    queue = Queue("summaries", connection=redis_conn)
    worker = Worker([queue])
    print(f"🚀 Worker started, listening on queue '{queue.name}' with Redis {redis_conn}")
    worker.work(with_scheduler=True)
