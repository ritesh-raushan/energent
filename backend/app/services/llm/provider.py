from abc import ABC, abstractmethod

from app.services.llm.models import LLMMessage, LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[LLMMessage], temperature: float = 0.7) -> LLMResponse:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...
