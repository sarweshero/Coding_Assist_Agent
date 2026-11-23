from app.agents.developer import DeveloperAgent
from app.agents.fixer import FixerAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.qa import QAAgent
from app.agents.reviewer import ReviewerAgent
from app.config_manager import config_manager
from app.orchestrator.gatekeeper import ModuleGatekeeper
from app.schemas.module import Module, ModuleStatus
from app.schemas.project import OrchestrationState, Project
from app.schemas.review import CodeReview, ReviewIssue
from app.schemas.test_run import TestRun, TestCaseResult
from app.storage import repository


MAX_FIX_ATTEMPTS = 3


class Orchestrator:
    """Coordinates the agent roster for one autonomous project session."""

    def __init__(
        self,
        developer: DeveloperAgent,
        qa: QAAgent,
        orchestrator_agent: OrchestratorAgent,
        fixer: FixerAgent = None,
        reviewer: ReviewerAgent = None,
    ):
        self.developer = developer
        self.qa = qa
        self.orchestrator_agent = orchestrator_agent
        self.fixer = fixer
        self.reviewer = reviewer
        self.gatekeeper = ModuleGatekeeper()

    async def plan_modules(self, project: Project) -> list:
        response = await self.orchestrator_agent.run(
            {
                "project_name": project.name,
                "phase": "PLAN",
                "requirements": project.requirements,
                "approved_requirements": project.approved_requirements or project.requirements,
            }
        )
        modules_data = response.structured.get("modules") or []
        modules = [
            Module(
                name=m.get("module") or "module",
                description=m.get("description") or "",
                dependencies=m.get("dependencies") or [],
            )
            for m in modules_data
            if isinstance(m, dict)
        ]
        project.modules = modules
        project.current_module_index = 0 if modules else -1
        return modules

    async def _run_qa(self, module: Module) -> None:
        qa_response = await self.qa.run(
            {
                "module_name": module.name,
                "module_code": module.code or "",
            }
        )
        qa_structured = qa_response.structured or {}
        qa_test_run = qa_structured.get("test_run") or {}
        module.test_code = qa_structured.get("test_code") or ""
        module.test_run = TestRun(
            module_id=module.id,
            module_name=module.name,
            status=qa_test_run.get("status") or "FAILED",
            exit_code=int(qa_test_run.get("exit_code") or 1),
            test_cases=[TestCaseResult(**tc) for tc in qa_test_run.get("test_cases") or []],
            output=qa_test_run.get("output") or "",
            duration_seconds=float(qa_test_run.get("duration_seconds") or 0.0),
        )
        module.status = ModuleStatus.PASSED if module.test_run.status == "PASSED" else ModuleStatus.FAILED

    async def _run_review(self, project: Project, module: Module) -> CodeReview:
        if self.reviewer is None:
            return None
        if not config_manager.get_auto_review():
            return None
        response = await self.reviewer.run(
            {
                "module_name": module.name,
                "old_code": None,
                "new_code": module.code or "",
                "test_code": module.test_code or "",
                "requirements": project.approved_requirements or project.requirements or "",
                "test_results": module.test_run.output if module.test_run else "",
                "policy": config_manager.get_review_policy(),
            }
        )
        structured = response.structured or {}
        review = CodeReview(
            module_id=module.id,
            module_name=module.name,
            approved=bool(structured.get("approved")),
            summary=structured.get("summary") or "",
            issues=[ReviewIssue(**i) for i in structured.get("issues") or []],
            policy=config_manager.get_review_policy(),
        )
        module.review = review
        repository.save_review(module.id, review)
        return review

    async def review_module(self, project: Project, module: Module) -> CodeReview:
        return await self._run_review(project, module)

    async def start_module(self, project: Project, module: Module) -> Module:
        module.status = ModuleStatus.CODING
        project.state = OrchestrationState.IMPLEMENTING_MODULE

        developer_response = await self.developer.run(
            {
                "module_name": module.name,
                "module_description": module.description,
                "approved_requirements": project.approved_requirements or project.requirements,
                "dependencies": module.dependencies,
            }
        )
        module.code = (developer_response.structured or {}).get("code") or developer_response.content
        module.status = ModuleStatus.TESTING
        project.state = OrchestrationState.TESTING_MODULE

        fix_attempts = 0
        while module.status != ModuleStatus.PASSED:
            await self._run_qa(module)
            if module.status == ModuleStatus.PASSED:
                break
            project.state = OrchestrationState.FIXING_MODULE
            if self.fixer is None or fix_attempts >= MAX_FIX_ATTEMPTS:
                break
            fixer_response = await self.fixer.run(
                {
                    "module_name": module.name,
                    "module_code": module.code or "",
                    "test_output": module.test_run.output if module.test_run else "",
                }
            )
            module.code = (fixer_response.structured or {}).get("code") or module.code
            module.status = ModuleStatus.FIXING
            fix_attempts += 1

        if module.status == ModuleStatus.PASSED:
            review = await self._run_review(project, module)
            if review is not None and not review.approved:
                module.status = ModuleStatus.FAILED
                project.state = OrchestrationState.FAILED
                return module
            next_index = project.current_module_index + 1
            if next_index < len(project.modules):
                project.current_module_index = next_index
                project.state = OrchestrationState.IMPLEMENTING_MODULE
            else:
                project.state = OrchestrationState.COMPLETED
        else:
            module.status = ModuleStatus.FAILED
            project.state = OrchestrationState.FAILED

        return module
