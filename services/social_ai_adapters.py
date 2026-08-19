"""Compatibility adapters that plug the shared Groq engine into existing automations."""

from __future__ import annotations

import os
from typing import Optional

from services import social_ai_service


async def instagram_generate_reply(
    *,
    user_text: str,
    username: Optional[str],
    channel: str,
    trusted_data: str,
    history: list[dict],
) -> Optional[str]:
    return await social_ai_service.generate_instagram_reply(
        user_text=user_text,
        username=username,
        channel=channel,
        trusted_data=trusted_data,
        history=history,
    )


async def facebook_generate_reply(
    user_text: str,
    user_name: str,
    trusted_data: str,
) -> Optional[str]:
    return await social_ai_service.generate_reply(
        user_text=user_text,
        user_name=user_name,
        channel="comment",
        history=[],
        trusted_data=trusted_data,
        max_chars=int(os.getenv("FACEBOOK_AI_COMMENT_MAX_CHARS", "500")),
    )
