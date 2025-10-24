# import os
# import logging
# import pprint
# from typing import Optional, Coroutine
#
# import jwt
# from dotenv import load_dotenv
# from pydantic import BaseModel
# from fastapi import FastAPI, Header, HTTPException, status, Request
# from supabase import create_client  # supabase-py
# import httpx
# import requests
# from jose import JWTError
#
# load_dotenv()
#
# # ====================================================================================================================
#
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
# SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# GROQ_MODEL = "llama-3.3-70b-versatile"
#
# if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GROQ_API_KEY]):
#     raise RuntimeError("Missing required env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GROQ_API_KEY")
#
# # ---------- clients ----------
# # Server-side client that uses the service_role key (bypasses RLS) for writes/reads by server
# supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
#
# app = FastAPI()
# utils = logging.getLogger("uvicorn")
# utils.setLevel(logging.INFO)
#
# # ---------- request models ----------
# class SummarizeRequest(BaseModel):
#     transcript_id: Optional[str] = None
#     text: Optional[str] = None
#     # If the client prefers to pass plain text instead of transcript_id (one-shot),
#     # include `text`. If transcript_id is supplied, we read text from the DB.
#
# # ---------- helper: call summarizer (Groq) ----------
# async def call_groq_summarize(text:str) -> str:
#     prompt = f"""
#     You are an expert transcription summarizer.
#     The transcript below might be in English or Bahasa Indonesia (including informal Jakarta-style slang).
#     Summarize it concisely **in the same language** as the original text.
#     If it's in Bahasa Indonesia, keep the summary natural and clear — not too formal, but still professional.
#
#     Transcript:
#     {text}
#
#     Summary:
#     """.strip()
#     url = "https://api.groq.com/openai/v1/chat/completions"
#
#     json_payload = {
#         "model": GROQ_MODEL,
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": 0.2,
#         "max_tokens": 512
#     }
#
#     headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
#     async with httpx.AsyncClient(timeout=60.0) as client:
#         response = await client.post(url, json=json_payload, headers=headers)
#
#     if response.status_code != 200:
#         utils.error("Groq API error: %s %s", response.status_code, response.text)
#         raise HTTPException(status_code=502, detail="Summarization service failure")
#
#     data = response.json()
#     try:
#         summary = data["choices"][0]["message"]["content"].strip()
#     except Exception:
#         utils.exception("Unexpected Groq response schema")
#         raise HTTPException(status_code=502, detail="Unexpected summarizer response")
#
#     return summary
#
# # ---------- helper: validate user token ----------
# def get_current_user(token:str):
#     res = requests.get(
#         f"{SUPABASE_URL}/auth/v1/user",
#         headers={
#             "Authorization": f"Bearer {token}",
#             "apikey": os.getenv("SUPABASE_ANON_KEY"),
#         },
#         timeout=10,
#     )
#     if res.status_code != 200:
#         raise HTTPException(status_code=401, detail="Invalid or expired token")
#     return res.json()
#
#
# # ---------- main endpoint ----------
# @app.post("/summarize")
# async def summarize(
#         payload:SummarizeRequest,
#         authorization: Optional[str] = Header(None)
# ):
#     """
#     two modes:
#       - client provides transcript_id: we read transcript from DB (and validate owner)
#       - client provides text: server will summarize immediately and optionally store transcript+summary
#     Client must attach Authorization: Bearer <access_token> (Supabase user token) so we can validate ownership.
#     """
#
#     if not authorization:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
#
#
#     if not (payload.transcript_id or payload.text):
#         raise HTTPException(status_code=400, detail="Need transcript_id or text in request body")
#
#     # parse token
#     parts = authorization.split()
#     if len(parts) != 2 or parts[0].lower() != "bearer":
#         raise HTTPException(status_code=401, detail="Malformed Authorization header")
#
#     token = parts[1]
#
#     user = get_current_user(token)
#
#     if not user:
#         raise HTTPException(status_code=401, detail="Invalid or expired token")
#
#     user_id = user.get("id")
#
#     # If transcript_id given: fetch transcript and verify ownership
#     if payload.transcript_id:
#         # Use service_role client to fetch the transcript row
#         res = supabase.table("transcripts").select("*").eq("id", payload.transcript_id).execute()
#         rows = res.data if hasattr(res, "data") else res.get("data")
#         if not rows:
#             raise HTTPException(404, detail="Transcript not found")
#         transcript = rows[0]
#         if str(transcript.get("user_id")) != str(user_id):
#             raise HTTPException(status_code=403, detail="Not allowed to summarize this transcript")
#         text_to_summarize = transcript.get("text")
#         # update status to 'summarizing'
#         supabase.table("transcripts").update({"status": "summarizing"}).eq("id", payload.transcript_id).execute()
#     else:
#         # client provided text directly: we can optionally persist it
#         text_to_summarize = payload.text.strip()
#         if not text_to_summarize:
#             raise HTTPException(status_code=400, detail="Empty text")
#         # Insert a transcript row (server writes with service_role)
#         insert_resp = supabase.table("transcripts").insert({
#             "user_id": user_id,
#             "text": text_to_summarize,
#             "status": "summarizing"
#         }).execute()
#         inserted = insert_resp.data[0] if getattr(insert_resp, "data", None) else insert_resp.get("data", [None])[0]
#         payload.transcript_id = inserted.get("id")
#
#         # call summarizer
#     try:
#         summary_text = await call_groq_summarize(text_to_summarize)
#     except HTTPException:
#         # push 'failed' into transcripts
#         supabase.table("transcripts").update({"status": "failed"}).eq("id", payload.transcript_id).execute()
#         raise
#
#         # insert summary (server-side)
#     summary_insert = supabase.table("summaries").insert({
#         "user_id": user_id,
#         "transcript_id": payload.transcript_id,
#         "summary_text": summary_text,
#         "model": GROQ_MODEL
#     }).execute()
#
#     # get summary id (best-effort)
#     summary_id = None
#     try:
#         summary_id = summary_insert.data[0].get("id")
#     except Exception:
#         utils.warning("Couldn't parse summary insert response: %s", getattr(summary_insert, "data", summary_insert))
#
#     # update transcript to point to summary and mark summarized
#     supabase.table("transcripts").update({
#         "status": "summarized",
#         "summary_id": summary_id
#     }).eq("id", payload.transcript_id).execute()
#
#     return {"summary": summary_text, "transcript_id": payload.transcript_id, "summary_id": summary_id}
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#




import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.config import settings
from app.routers import summarize
from app.utils.logger import get_logger

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = get_logger("rekapin")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Rekapin backend...")
    yield
    logger.info("Shutting down Rekapin backend...")

app = FastAPI(lifespan=lifespan,title="Rekapin Summarizer")

# include routers
app.include_router(summarize.router)