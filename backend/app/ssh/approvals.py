import uuid


class CommandApprovalStore:
    """Stores pending destructive-command approvals until user decides."""

    def __init__(self) -> None:
        self._pending: dict = {}

    def create(self, command: str, reason: str) -> str:
        approval_id = uuid.uuid4().hex
        self._pending[approval_id] = {
            "id": approval_id,
            "command": command,
            "reason": reason,
            "status": "pending",
        }
        return approval_id

    def get(self, approval_id: str):
        return self._pending.get(approval_id)

    def resolve(self, approval_id: str, decision: str) -> dict:
        approval = self._pending.get(approval_id)
        if approval is None:
            return {"found": False}
        approval["status"] = decision
        return {"found": True, "approval": approval}


command_approvals = CommandApprovalStore()
