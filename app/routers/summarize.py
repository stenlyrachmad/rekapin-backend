import os

from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.models import SummarizeRequest
from app.auth import get_user_from_token
from app.services.supabase_client import get_supabase
from app.services.groq_client import call_groq_summarize
from app.services.queue import queue
from worker.summarize_worker import summarize_task
from rq.job import Job
from app.services.queue import redis_conn


router = APIRouter(prefix="")

supabase = get_supabase()

@router.post("/summarize")
async def summarize(payload: SummarizeRequest, authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed Authorization header")

    token = parts[1]
    user = await get_user_from_token(token)
    user_id = user.get("id") or user.get("sub")

    if not (payload.transcript_id or payload.text):
        raise HTTPException(status_code=400, detail="Need transcript_id or text in request body")

    # decide text_to_summarize
    if payload.transcript_id:
        res = supabase.table("transcripts").select("*").eq("id", payload.transcript_id).execute()
        rows = res.data if hasattr(res, "data") else res.get("data")
        if not rows:
            raise HTTPException(status_code=404, detail="Transcript not found")
        transcript = rows[0]
        if str(transcript.get("user_id")) != str(user_id):
            raise HTTPException(status_code=403, detail="Not allowed to summarize this transcript")
        text_to_summarize = transcript.get("text")
        supabase.table("transcripts").update({"status": "summarizing"}).eq("id", payload.transcript_id).execute()
    else:
        text_to_summarize = payload.text.strip()
        if not text_to_summarize:
            raise HTTPException(status_code=400, detail="Empty text")
        inserted = supabase.table("transcripts").insert({
            "user_id": user_id,
            "text": text_to_summarize,
            "status": "summarizing"
        }).execute().data[0]
        payload.transcript_id = inserted.get("id")

    # call LLM
    summary_text = await call_groq_summarize(text_to_summarize)

    # persist summary
    summary_insert = supabase.table("summaries").insert({
        "user_id": user_id,
        "transcript_id": payload.transcript_id,
        "summary_text": summary_text,
        "model": settings.GROQ_MODEL
    }).execute()
    summary_id = None
    try:
        summary_id = summary_insert.data[0].get("id")
    except Exception:
        pass

    supabase.table("transcripts").update({
        "status": "summarized",
        "summary_id": summary_id
    }).eq("id", payload.transcript_id).execute()

    job = queue.enqueue(summarize_task, payload.transcript_id, text_to_summarize, user_id)
    return {"job_id": job.id, "transcript_id": payload.transcript_id, "status": "queued"}


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, authorization: str | None = Header(None)):
    """To Get the Summary Result when the worker is done processing"""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed Authorization header")

    token = parts[1]
    await get_user_from_token(token)

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "status": job.get_status(),
        "result": job.return_value(),
    }

