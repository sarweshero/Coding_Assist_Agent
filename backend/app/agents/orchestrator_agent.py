from typing import Optional

from app.agents.base import AgentResponse, BaseAgent


PLAN_SYSTEM_PROMPT = (
    "You are the Orchestrator Agent. You break approved client requirements into an "
    "ordered list of small, independently testable modules. "
    "Respond with a JSON object of the shape "
    "{\"modules\": [{\"module\": \"<name>\", \"description\": \"...\", \"dependencies\": [\"...\"]}]}."
)


class OrchestratorAgent(BaseAgent):
    def __init__(self, llm):
        super().__init__("orchestrator", llm)

    async def run(self, context: dict) -> AgentResponse:
        prompt = self.render(
            "plan.j2",
            project_name=context.get("project_name") or "project",
            phase=context.get("phase") or "PLAN",
            requirements=context.get("requirements") or "",
            approved_requirements=context.get("approved_requirements") or context.get("requirements") or "",
            modules=context.get("modules") or [],
        )
        content = await self.llm.complete(
            agent_name="orchestrator",
            system_prompt=PLAN_SYSTEM_PROMPT,
            user_content=prompt,
            temperature=0.2,
            max_tokens=4096,
        )
        structured: Optional[dict] = self._extract_json(content)
        if not structured:
            structured = {"modules": []}
        return AgentResponse(content=content, structured=structured)
