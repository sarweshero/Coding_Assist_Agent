from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.sse import sse_manager
from app.ssh.approvals import command_approvals
from app.ssh.guardrail import classify
from app.ssh.ssh_manager import ssh_manager


router = APIRouter(prefix="/api/ssh", tags=["ssh"])


class ExecRequestModel(BaseModel):
    command: str


class ApprovalDecisionRequestModel(BaseModel):
    decision: str


@router.post("/connect")
async def ssh_connect(host: str, port: int = 22, username: str = "ubuntu", password: str = None, private_key: str = None) -> dict:
    connected = await ssh_manager.connect(host=host, port=port, username=username, password=password, private_key=private_key)
    return {"connected": connected}


@router.post("/disconnect")
async def ssh_disconnect() -> dict:
    await ssh_manager.disconnect()
    return {"connected": False}


@router.get("/status")
async def ssh_status() -> dict:
    return {"connected": ssh_manager.is_connected}


@router.post("/exec")
async def ssh_exec(request: ExecRequestModel) -> dict:
    decision = classify(request.command)
    if decision.decision == "BLOCKED":
        raise HTTPException(status_code=403, detail={"decision": "BLOCKED", "reason": decision.reason})
    if decision.decision == "REQUIRES_APPROVAL":
        approval_id = command_approvals.create(request.command, decision.reason)
        sse_manager.emit(
            f"ssh:approval:{approval_id}",
            {
                "type": "COMMAND_APPROVAL_REQUIRED",
                "approval_id": approval_id,
                "command": request.command,
                "reason": decision.reason,
            },
        )
        return {"status": "pending", "approval_id": approval_id, "command": request.command, "reason": decision.reason}
    result = await ssh_manager.exec_command(request.command)
    sse_manager.emit(f"ssh:exec:{approval_id if approval_id else 'x'}", {"type": "COMMAND_EXECUTED", "result": result})
    return result


@router.post("/approvals/{approval_id}")
async def ssh_approval(approval_id: str, decision_request: ApprovalDecisionRequestModel) -> dict:
    stored = command_approvals.get(approval_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if stored.get("status") != "pending":
        return {"status": stored.get("status")}
    if decision_request.decision == "approve":
        command_approvals.resolve(approval_id, "approved")
        result = await ssh_manager.exec_command(stored["command"])
        sse_manager.emit(
            f"ssh:approval:{approval_id}",
            {"type": "COMMAND_EXECUTED", "approval_id": approval_id, "result": result},
        )
        return {"status": "approved", "result": result}
    command_approvals.resolve(approval_id, "rejected")
    sse_manager.emit(
        f"ssh:approval:{approval_id}",
        {"type": "COMMAND_REJECTED", "approval_id": approval_id},
    )
    return {"status": "rejected"}


@router.get("/files")
async def ssh_files(path: str = "/") -> dict:
    try:
        entries = await ssh_manager.list_dir(path)
        return {"path": path, "type": "directory", "entries": entries}
    except Exception:
        content = await ssh_manager.read_file(path)
        return {"path": path, "type": "file", "content": content}


@router.post("/files")
async def ssh_write_file(path: str, content: str) -> dict:
    written = await ssh_manager.write_file(path=path, content=content)
    return {"path": path, "written": written}
