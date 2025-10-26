import httpx
from typing import Optional
from app.config import settings
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

_httpx_client: Optional[httpx.AsyncClient] = None

def get_httpx_client() -> httpx.AsyncClient:
    """Return a shared async HTTP client (connection pooled)."""
    global _httpx_client
    if _httpx_client is None or _httpx_client.is_closed:
        _httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
    return _httpx_client


async def call_groq_summarize(text: str) -> str:
    """Call Groq ChatCompletion API to summarize text."""
    client = get_httpx_client()
    prompt = f"""
You are an expert transcription summarizer.
The transcript below may be in English or Bahasa Indonesia (including informal Jakarta-style slang).
Summarize it concisely **in the same language** as the original text.
If it's in Bahasa Indonesia, keep the tone natural and clear — not too formal, but still professional.

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

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
    except httpx.RequestError as e:
        logger.error("Groq API request failed: %s", e)
        raise HTTPException(status_code=502, detail="Summarization service unavailable")
    except httpx.HTTPStatusError as e:
        logger.error("Groq API returned bad status: %s - %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=502, detail="Summarization service error")

    data = resp.json()
    try:
        summary = data["choices"][0]["message"]["content"].strip()
        return summary
    except (KeyError, IndexError, TypeError) as e:
        logger.exception("Unexpected Groq response schema: %s", e)
        raise HTTPException(status_code=502, detail="Unexpected summarizer response")


async def aclose_httpx_client():
    """Gracefully close the global async client (for app shutdown)."""
    global _httpx_client
    if _httpx_client and not _httpx_client.is_closed:
        await _httpx_client.aclose()
        _httpx_client = None
