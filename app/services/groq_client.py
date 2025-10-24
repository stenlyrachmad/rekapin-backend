import httpx
import asyncio
from typing import Optional
from app.config import settings
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# shared HTTPX async client for connection pooling
_httpx_client: Optional[httpx.AsyncClient] = None

def get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=60.0)
    return _httpx_client

async def call_groq_summarize(text: str) -> str:
    client = get_httpx_client()
    prompt = f"""
        You are an expert transcription summarizer. 
        The transcript below might be in English or Bahasa Indonesia (including informal Jakarta-style slang).
        Summarize it concisely **in the same language** as the original text.
        If it's in Bahasa Indonesia, keep the summary natural and clear — not too formal, but still professional.

        Transcript:
        {text}

        Summary:
        """.strip()

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 512,
    }

    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
    resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
    if resp.status_code != 200:
        logger.error("Groq API error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Summarization service failure")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("Unexpected Groq response schema")
        raise HTTPException(status_code=502, detail="Unexpected summarizer response")

async def aclose_httpx_client():
    global _httpx_client
    if _httpx_client:
        await _httpx_client.aclose()
        _httpx_client = None
