from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.db.init_db import init_db
from app.db.provider_dao import get_provider_by_id, seed_default_providers, update_provider


def sync_provider_from_env(
    provider_id: str,
    api_key_env_var: str,
    base_url_env_var: str,
) -> bool:
    api_key = os.getenv(api_key_env_var)
    base_url = os.getenv(base_url_env_var)

    if not api_key and not base_url:
        return False

    provider = get_provider_by_id(provider_id)
    if not provider:
        return False

    updates = {}
    if api_key:
        updates["api_key"] = api_key
    if base_url:
        updates["base_url"] = base_url

    if not updates:
        return False

    update_provider(provider_id, **updates)
    return True


def initialize_backend_runtime(dotenv_path: Path | None = None) -> None:
    if dotenv_path is not None:
        load_dotenv(dotenv_path, override=True)
    else:
        load_dotenv(override=False)

    init_db()
    seed_default_providers()
    sync_provider_from_env(
        provider_id="openai",
        api_key_env_var="OPENAI_API_KEY",
        base_url_env_var="OPENAI_API_BASE_URL",
    )
