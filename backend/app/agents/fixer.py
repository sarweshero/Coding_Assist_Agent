from typing import Optional

from app.agents.base import AgentResponse, BaseAgent


FIXER_SYSTEM_PROMPT = (
    "You are the Debugger / Fixer Agent of an autonomous software engineering platform. "
    "You analyze failing test output and broken module code, then produce corrected source code. "
    "Respond with a JSON object of the shape {\"module\": \"<module_name>\", \"code\": \"<fixed source code>\"}."
)


class FixerAgent(BaseAgent):
    def __init__(self, llm):
        super().__init__("fixer", llm)

    async def run(self, context: dict) -> AgentResponse:
        prompt = self.render(
            "fix_error.j2",
            module_name=context.get("module_name") or "module",
            module_code=context.get("module_code") or "",
            test_output=context.get("test_output") or "",
        )
        content = await self.llm.complete(
            agent_name="fixer",
            system_prompt=FIXER_SYSTEM_PROMPT,
            user_content=prompt,
            temperature=0.2,
            max_tokens=4096,
        )
        structured: Optional[dict] = self._extract_json(content)
        if not structured:
            structured = {"module": context.get("module_name") or "module", "code": content}
        return AgentResponse(content=content, structured=structured)
