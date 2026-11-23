from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel

from app.prompts import get_template


class AgentResponse(BaseModel):
    content: str
    structured: Optional[dict] = None


class BaseAgent(ABC):
    def __init__(self, name: str, llm, prompt_renderer=None):
        self.name = name
        self.llm = llm
        self.prompt_renderer = prompt_renderer or get_template

    @abstractmethod
    async def run(self, context: dict) -> AgentResponse:
        raise NotImplementedError

    def render(self, template_name: str, **context) -> str:
        return self.prompt_renderer(template_name).render(**context)

    @staticmethod
    def _extract_json(content: str) -> Optional[dict]:
        import json

        text = content.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
