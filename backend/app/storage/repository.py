from typing import Optional

from app.schemas.module import Module
from app.schemas.project import OrchestrationState, Project, ProjectCreate, UserMode
from app.schemas.review import CodeReview
from app.schemas.test_run import TestRun, TestCaseResult


_projects: dict = {}
_reviews: dict = {}


def create_project(project_create: ProjectCreate) -> Project:
    project = Project(name=project_create.name)
    _projects[project.id] = project
    return project


def get_project(project_id: str) -> Optional[Project]:
    return _projects.get(project_id)


def update_requirements(project_id: str, requirements: str) -> Optional[Project]:
    project = _projects.get(project_id)
    if project is None:
        return None
    project.requirements = requirements
    return project


def update_approved_requirements(project_id: str, approved_requirements: str) -> Optional[Project]:
    project = _projects.get(project_id)
    if project is None:
        return None
    project.approved_requirements = approved_requirements
    return project


def set_state(project_id: str, state: OrchestrationState, current_mode: Optional[UserMode] = None) -> Optional[Project]:
    project = _projects.get(project_id)
    if project is None:
        return None
    project.state = state
    if current_mode is not None:
        project.current_mode = current_mode
    return project


def set_current_mode(project_id: str, mode: UserMode) -> Optional[Project]:
    project = _projects.get(project_id)
    if project is None:
        return None
    project.current_mode = mode
    return project


def delete_project(project_id: str) -> None:
    _projects.pop(project_id, None)


def get_module(project_id: str, module_id: str) -> Optional[Module]:
    project = _projects.get(project_id)
    if project is None:
        return None
    return next((m for m in project.modules if m.id == module_id), None)


def save_test_run(module: Module, test_run: TestRun) -> None:
    module.test_run = test_run


def save_review(module_id: str, review: CodeReview) -> None:
    _reviews.setdefault(module_id, []).append(review)


def get_reviews(module_id: str) -> list:
    return list(_reviews.get(module_id, []))
