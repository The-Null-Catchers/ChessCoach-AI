from __future__ import annotations

import json
import httpx
from app.ai.base import CoachingContext, CoachingExplanation


class OpenAICompatibleProvider:
    def __init__(self, *, name: str, model: str, base_url: str, api_key: str, timeout: float = 20.0):
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def explain(self, context: CoachingContext) -> CoachingExplanation:
        system = (
            "You are a chess coach. Stockfish facts are authoritative. "
            "Explain the concept for the player's level. Never contradict the provided best move or evaluation. "
            "Return strict JSON with explanation, coaching_tip, concept, avoid_next_time."
        )
        user = json.dumps(context.model_dump())
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return CoachingExplanation.model_validate_json(content)
