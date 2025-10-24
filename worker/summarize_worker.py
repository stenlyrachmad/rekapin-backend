# import redis
# from rq import Worker, Queue
# from app.config import settings
#
#
#
# def main():
#     # Connect to Redis
#     redis_url = settings.REDIS_URL or "redis://redis:6379/0"
#     conn = redis.from_url(redis_url)
#
#     # Define the queue name (optional: customize)
#     queue = Queue("summaries", connection=conn)
#
#     # Start the worker process
#     print(f"🚀 Worker connected to {redis_url} and listening on queue: {queue.name}")
#     worker = Worker([queue])
#     worker.work(with_scheduler=True)
#
# if __name__ == "__main__":
#     main()


import asyncio
from app.services.groq_client import call_groq_summarize
from app.services.supabase_client import get_supabase

supabase = get_supabase()

def summarize_task(transcript_id:str, text_to_summarize:str, user_id:str):
    """
    This is executed by the worker asynchronously.
    """
    async def run_summary():
        try:
            supabase.table("transcripts").update({"status": "summarizing"}).eq("id", transcript_id).execute()
            summary_text = await call_groq_summarize(text_to_summarize)

            summary_insert = supabase.table("summaries").insert({
                "user_id": user_id,
                "transcript_id": transcript_id,
                "summary_text": summary_text,
                "model": "llama-3.3-70b-versatile"
            }).execute()

            summary_id = summary_insert.data[0]["id"]

            supabase.table("transcripts").update({
                "status": "summarized",
                "summary_id": summary_id
            }).eq("id", transcript_id).execute()

            return {"summary_id": summary_id, "summary_text": summary_text}

        except Exception as e:
            supabase.table("transcripts").update({"status": "failed"}).eq("id", transcript_id).execute()
            raise e

    return asyncio.run(run_summary())
