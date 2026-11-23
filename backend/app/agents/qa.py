import os
import subprocess
import tempfile
import time
from typing import Optional

from app.agents.base import AgentResponse, BaseAgent
from app.schemas.test_run import TestRun, TestCaseResult


QA_SYSTEM_PROMPT = (
    "You are the QA / Test Engineer Agent. You generate comprehensive pytest unit tests "
    "for a single module given its source code. "
    "Respond with a JSON object of the shape {\"module\": \"<module_name>\", \"test_code\": \"<pytest code>\"}."
)


class QAAgent(BaseAgent):
    def __init__(self, llm, workspace_root: str = "./data/workspace"):
        super().__init__("qa", llm)
        self.workspace_root = workspace_root

    async def run(self, context: dict) -> AgentResponse:
        module_code = context.get("module_code") or ""
        module_name = context.get("module_name") or "module"
        prompt = self.render(
            "write_tests.j2",
            module_name=module_name,
            code=module_code,
        )
        content = await self.llm.complete(
            agent_name="qa",
            system_prompt=QA_SYSTEM_PROMPT,
            user_content=prompt,
            temperature=0.2,
            max_tokens=4096,
        )
        structured: Optional[dict] = self._extract_json(content)
        if not structured:
            structured = {"module": module_name, "test_code": ""}
        test_code = structured.get("test_code") or ""
        test_run: Optional[dict] = self.run_tests(module_code, test_code, module_name)
        structured["test_run"] = test_run
        return AgentResponse(content=content, structured=structured)

    def run_tests(self, module_code: str, test_code: str, module_name: str) -> dict:
        module_file = module_name.replace(".", "_")
        tmpdir = tempfile.mkdtemp(prefix="conding_qa_")
        module_path = os.path.join(tmpdir, f"{module_file}.py")
        test_path = os.path.join(tmpdir, f"test_{module_file}.py")
        with open(module_path, "w") as f:
            f.write(module_code)
        with open(test_path, "w") as f:
            f.write(test_code)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", "-v", test_path],
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=120,
            )
            exit_code = proc.returncode
            output = proc.stdout + "\n" + str(proc.stderr)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "FAILED",
                "exit_code": 1,
                "test_cases": [],
                "output": str(exc),
                "duration_seconds": 0.0,
            }
        test_cases: list[dict] = []
        for line in output.splitlines():
            clean = line.strip()
            if " PASSED" in clean or clean.endswith("PASSED"):
                status = "PASSED"
            elif " FAILED" in clean or clean.endswith("FAILED"):
                status = "FAILED"
            else:
                continue
            name = clean.split("::")[-1].strip()
            test_cases.append(TestCaseResult(name=name, status=status).model_dump())
        return {
            "status": "PASSED" if exit_code == 0 else "FAILED",
            "exit_code": exit_code,
            "test_cases": test_cases,
            "output": output,
            "duration_seconds": time.monotonic() - start,
        }
