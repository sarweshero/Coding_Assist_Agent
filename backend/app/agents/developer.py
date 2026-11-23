from typing import Optional

from app.agents.base import AgentResponse, BaseAgent


DEVELOPER_SYSTEM_PROMPT = (
    "You are the Developer Agent of an autonomous software engineering platform. "
    "You write clean, modular source code for exactly one module at a time, guided by the "
    "approved requirements and the module specification. "
    "Respond with a JSON object of the shape {\"module\": \"<module_name>\", \"code\": \"<source code>\"}."
)


class DeveloperAgent(BaseAgent):
    def __init__(self, llm):
        super().__init__("developer", llm)

    async def run(self, context: dict) -> AgentResponse:
        prompt = self.render(
            "code_module.j2",
            module_name=context.get("module_name") or "module",
            module_description=context.get("module_description") or "",
            approved_requirements=context.get("approved_requirements") or "",
            dependencies=", ".join(context.get("dependencies") or []),
        )
        content = await self.llm.complete(
            agent_name="developer",
            system_prompt=DEVELOPER_SYSTEM_PROMPT,
            user_content=prompt,
            temperature=0.2,
            max_tokens=4096,
        )
        structured: Optional[dict] = self._extract_json(content)
        if not structured:
            structured = {"module": context.get("module_name") or "module", "code": content}
        return AgentResponse(content=content, structured=structured)
