import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.review import CodeReview
from app.schemas.test_run import TestRun


class ModuleStatus(str, Enum):
    PENDING = "PENDING"
    CODING = "CODING"
    TESTING = "TESTING"
    FIXING = "FIXING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class Module(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str = Field(..., description="Module identifier, e.g. 'auth.service'")
    description: str = ""
    status: ModuleStatus = ModuleStatus.PENDING
    dependencies: list[str] = []
    code: Optional[str] = None
    test_code: Optional[str] = None
    test_run: Optional[TestRun] = None
    review: Optional[CodeReview] = None
