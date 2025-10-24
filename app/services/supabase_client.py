from supabase import create_client
from app.config import settings

_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(str(settings.SUPABASE_URL), settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client
