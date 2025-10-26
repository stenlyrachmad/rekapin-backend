import sys, os
import logging
from rq import Connection, Worker, Queue

# ensure 'app/' is importable
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.services.supabase_client import get_supabase
from app.services.groq_client import call_groq_summarize
import asyncio

logger = logging.getLogger(__name__)
supabase = get_supabase()

def summarize_task(transcript_id: str, text_to_summarize: str, user_id: str):
    """
    Executed by RQ worker. Handles summarization and DB updates.
    """
    loop = asyncio.get_event_loop()
    try:
        supabase.table("transcripts").update({"status": "summarizing"}).eq("id", transcript_id).execute()

        summary_text = loop.run_until_complete(call_groq_summarize(text_to_summarize))

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

        logger.info(f"✅ Transcript {transcript_id} summarized successfully.")
        return {"summary_id": summary_id, "summary_text": summary_text}

    except Exception as e:
        logger.exception(f"❌ Summarization failed for {transcript_id}: {e}")
        supabase.table("transcripts").update({"status": "failed"}).eq("id", transcript_id).execute()
        raise

if __name__ == "__main__":
    from redis import Redis

    redis_conn = Redis(host="localhost", port=6379, db=0)
    queue_name = "summaries"

    logger.info(f"🎧 Starting RQ worker for queue: {queue_name}")
    with Connection(redis_conn):
        worker = Worker([queue_name])
        worker.work(with_scheduler=True)
