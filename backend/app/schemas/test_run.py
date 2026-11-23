from pydantic import BaseModel, Field


class TestCaseResult(BaseModel):
    name: str = ""
    status: str = "PENDING"


class TestRun(BaseModel):
    module_id: str = ""
    module_name: str = ""
    status: str = "FAILED"
    exit_code: int = 1
    test_cases: list[TestCaseResult] = []
    output: str = ""
    duration_seconds: float = 0.0
