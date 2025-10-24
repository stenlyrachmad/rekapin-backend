import httpx
from fastapi import HTTPException, status
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def get_user_from_token(token: str) -> dict:
    """
    Validate the Supabase access token using Supabase's /auth/v1/user endpoint.
    Works when legacy tokens are disabled.
    """
    url = f"{settings.SUPABASE_URL}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.SUPABASE_ANON_KEY,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        logger.debug("Supabase token verify failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return resp.json()
