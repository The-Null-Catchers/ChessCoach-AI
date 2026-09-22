from __future__ import annotations

from app.ai.openai_compatible import OpenAICompatibleProvider
from app.ai.template_provider import TemplateCoachProvider
from app.core.config import settings


def get_ai_provider():
    if settings.ai_provider == "template" or not settings.ai_api_key:
        return TemplateCoachProvider()
    return OpenAICompatibleProvider(
        name=settings.ai_provider,
        model=settings.ai_model,
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
    )
