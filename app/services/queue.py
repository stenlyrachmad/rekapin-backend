from redis import Redis
from rq import Queue
from app.config import settings

redis_conn = Redis.from_url(settings.REDIS_URL or "redis://localhost:6379/0")
queue = Queue("summaries", connection=redis_conn)
