from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app import llm
from app.api.sse import sse_manager
from app.agents.developer import DeveloperAgent
from app.agents.fixer import FixerAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.qa import QAAgent
from app.agents.reviewer import ReviewerAgent
from app.config import settings
from app.config_manager import config_manager
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state_machine import StateMachine
from app.schemas.module import Module
from app.schemas.project import OrchestrationState, Project, ProjectCreate, UserMode
from app.schemas.review import CodeReview
from app.schemas.test_run import TestRun
from app.storage import repository


router = APIRouter(prefix="/api", tags=["api"])

_state_machines: dict = {}
_orchestrators: dict = {}


def _get_state_machine(project_id: str) -> StateMachine:
    state_machine = _state_machines.get(project_id)
    if state_machine is None:
        state_machine = StateMachine()
        _state_machines[project_id] = state_machine
    return state_machine


def _get_orchestrator() -> Orchestrator:
    orchestrator = _orchestrators.get("default")
    if orchestrator is None:
        developer = DeveloperAgent(llm=llm)
        qa = QAAgent(llm=llm, workspace_root=settings.LOCAL_WORKSPACE_ROOT)
        orchestrator_agent = OrchestratorAgent(llm=llm)
        fixer = FixerAgent(llm=llm)
        reviewer = ReviewerAgent(llm=llm)
        orchestrator = Orchestrator(developer=developer, qa=qa, orchestrator_agent=orchestrator_agent, fixer=fixer, reviewer=reviewer)
        _orchestrators["default"] = orchestrator
    return orchestrator


@router.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate) -> Project:
    return repository.create_project(project)


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/projects/{project_id}", response_model=Project)
async def update_requirements(project_id: str, requirements: str) -> Project:
    project = repository.update_requirements(project_id, requirements)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/approvals", response_model=Project)
async def approve_plan(project_id: str) -> Project:
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project.approved_requirements = project.requirements
    state_machine = _get_state_machine(project_id)
    state_machine.transition(OrchestrationState.IMPLEMENTING_MODULE)
    return repository.set_state(project_id, state_machine.state, current_mode=UserMode.PLAN)


@router.post("/projects/{project_id}/mode")
async def switch_mode(project_id: str, mode: UserMode) -> Project:
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    repository.set_current_mode(project_id, mode)
    state = OrchestrationState.FIXING_MODULE if mode == UserMode.FIX else project.state
    return repository.set_state(project_id, state, current_mode=mode)


@router.post("/projects/{project_id}/modules/{module_id}/run", response_model=Module)
async def run_module(project_id: str, module_id: str) -> Module:
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    module = next((m for m in project.modules if m.id == module_id), None)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    module = await _get_orchestrator().start_module(project, module)
    return module


@router.get("/projects/{project_id}/modules/{module_id}/tests", response_model=Optional[TestRun])
async def get_test_run(project_id: str, module_id: str) -> Optional[TestRun]:
    module = repository.get_module(project_id, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return module.test_run


@router.post("/projects/{project_id}/modules/{module_id}/review")
async def review_module(project_id: str, module_id: str) -> Optional[CodeReview]:
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    module = next((m for m in project.modules if m.id == module_id), None)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    review = await _get_orchestrator().review_module(project, module)
    return review


@router.get("/projects/{project_id}/events")
async def stream_events(project_id: str):
    return StreamingResponse(sse_manager.create_stream(project_id), media_type="text/event-stream")
