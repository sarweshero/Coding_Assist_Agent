from typing import Optional

from app.agents.base import AgentResponse, BaseAgent
from app.schemas.review import CodeReview, ReviewIssue


REVIEW_SYSTEM_PROMPTS = {
    "strict": (
        "You are the Code Reviewer Agent operating under the STRICT policy. "
        "Any security issue is a blocker. Missing tests or documentation are warnings. "
        "Only approve if the code fully satisfies the approved requirements."
    ),
    "balanced": (
        "You are the Code Reviewer Agent operating under the BALANCED policy. "
        "Security issues are blockers; style and coverage gaps are warnings. "
        "Approve only when no blocker-level issues remain."
    ),
    "permissive": (
        "You are the Code Reviewer Agent operating under the PERMISSIVE policy. "
        "Only critical correctness or security bugs block approval. "
        "Anything else is advisory."
    ),
}


class ReviewerAgent(BaseAgent):
    def __init__(self, llm):
        super().__init__("reviewer", llm)

    async def run(self, context: dict) -> AgentResponse:
        policy = context.get("policy") or "balanced"
        system_prompt = REVIEW_SYSTEM_PROMPTS.get(policy, REVIEW_SYSTEM_PROMPTS["balanced"])
        prompt = self.render(
            "review_code.j2",
            module_name=context.get("module_name") or "module",
            code=context.get("new_code") or context.get("code") or "",
            test_code=context.get("test_code") or "",
            test_results=context.get("test_results") or "",
            requirements=context.get("requirements") or "",
            policy=policy,
        )
        content = await self.llm.complete(
            agent_name="reviewer",
            system_prompt=system_prompt,
            user_content=prompt,
            temperature=0.2,
            max_tokens=4096,
        )
        structured = self._extract_json(content) or {}
        return AgentResponse(content=content, structured=structured)
