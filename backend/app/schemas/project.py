import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.module import Module


class OrchestrationState(str, Enum):
    GATHERING_REQUIREMENTS = "GATHERING_REQUIREMENTS"
    AWAITING_PLAN_APPROVAL = "AWAITING_PLAN_APPROVAL"
    IMPLEMENTING_MODULE = "IMPLEMENTING_MODULE"
    TESTING_MODULE = "TESTING_MODULE"
    FIXING_MODULE = "FIXING_MODULE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class UserMode(str, Enum):
    PLAN = "PLAN"
    EDIT = "EDIT"
    FIX = "FIX"
    EXPLAIN = "EXPLAIN"


class ProjectCreate(BaseModel):
    name: str = "Untitled Project"


class Project(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Untitled Project"
    requirements: str = ""
    approved_requirements: Optional[str] = None
    state: OrchestrationState = OrchestrationState.GATHERING_REQUIREMENTS
    current_mode: UserMode = UserMode.PLAN
    modules: list[Module] = []
    current_module_index: int = -1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
