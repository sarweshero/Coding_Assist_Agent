from datetime import datetime

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    severity: str = "info"
    message: str = ""
    location: str = ""


class CodeReview(BaseModel):
    module_id: str = ""
    module_name: str = ""
    approved: bool = False
    summary: str = ""
    issues: list[ReviewIssue] = []
    policy: str = "balanced"
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
