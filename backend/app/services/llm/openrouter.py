import json
import logging

import httpx

from app.config import settings
from app.services.llm.models import LLMMessage, LLMResponse
from app.services.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(LLMProvider):
    def __init__(self) -> None:
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL

    def chat(self, messages: list[LLMMessage], temperature: float = 0.7) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }

        logger.info("Calling OpenRouter API with model=%s", self.model)

        try:
            response = httpx.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=settings.LLM_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
            )

        except httpx.HTTPStatusError as e:
            logger.error("OpenRouter API error: %s - %s", e.response.status_code, e.response.text)
            raise RuntimeError(f"OpenRouter API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error("OpenRouter API call failed: %s", e)
            raise RuntimeError(f"OpenRouter API call failed: {e}") from e

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != "your-api-key-here")
