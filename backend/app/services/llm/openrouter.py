import json
import logging

import httpx

from app.config import settings
from app.services.llm.models import LLMMessage, LLMResponse
from app.services.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _message_to_dict(m: LLMMessage) -> dict:
    msg = {"role": m.role, "content": m.content}
    if m.role == "tool" and m.tool_call_id:
        msg["tool_call_id"] = m.tool_call_id
    if m.role == "assistant" and m.tool_calls:
        msg["tool_calls"] = m.tool_calls
    return msg


class OpenRouterProvider(LLMProvider):
    def __init__(self) -> None:
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL

    def chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [_message_to_dict(m) for m in messages],
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

        logger.info("Calling OpenRouter API with model=%s, tools=%s", self.model, len(tools) if tools else 0)

        try:
            response = httpx.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=settings.LLM_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]["message"]
            content = choice.get("content") or ""
            tool_calls = choice.get("tool_calls")
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                tool_calls=tool_calls,
            )

        except httpx.HTTPStatusError as e:
            logger.error("OpenRouter API error: %s - %s", e.response.status_code, e.response.text)
            raise RuntimeError(f"OpenRouter API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error("OpenRouter API call failed: %s", e)
            raise RuntimeError(f"OpenRouter API call failed: {e}") from e

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != "your-api-key-here")