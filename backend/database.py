from functools import lru_cache

from supabase import Client, create_client

from backend.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> Client:
    cfg = get_settings()
    return create_client(cfg.supabase_url, cfg.supabase_key)
