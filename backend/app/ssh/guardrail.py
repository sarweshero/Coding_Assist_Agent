import re
from typing import List, Tuple

from pydantic import BaseModel


class GuardrailDecision(BaseModel):
    decision: str  # ALLOWED | REQUIRES_APPROVAL | BLOCKED
    reason: str = ""


CRITICAL_PATTERNS: List[Tuple[str, "re.Pattern"]] = [
    ("rm", re.compile(r"^rm\b", re.I)),
    ("sudo", re.compile(r"^sudo\b", re.I)),
    ("chmod", re.compile(r"^chmod\b", re.I)),
    ("chown", re.compile(r"^chown\b", re.I)),
    ("systemctl", re.compile(r"^systemctl\b", re.I)),
    ("docker rm", re.compile(r"^docker\s+rm\b", re.I)),
    ("drop", re.compile(r"^(drop|truncate)\b", re.I)),
]

SAFE_COMMAND_PREFIXES: List[str] = [
    "ls",
    "cd",
    "cat",
    "pwd",
    "echo",
    "git",
    "python",
    "pytest",
    "curl",
    "wget",
    "mkdir",
    "touch",
    "cp",
    "mv",
    "export",
    "source",
    "which",
    "whoami",
    "date",
    "head",
    "tail",
    "grep",
    "find",
    "ps",
    "ping",
]


def _normalize(command: str) -> str:
    cmd = (command or "").strip()
    cmd = re.sub(r"^[A-Z_][A-Z0-9_]*=[^\s]+\s+", "", cmd)
    return cmd.strip()


def classify(command: str) -> GuardrailDecision:
    cmd = _normalize(command)
    if not cmd:
        return GuardrailDecision(decision="ALLOWED", reason="empty command")
    tokens = re.split(r"[\s;]+", cmd)
    first = tokens[0].lower().rstrip("/") if tokens else ""
    safe = False
    for prefix in SAFE_COMMAND_PREFIXES:
        if first == prefix or first.startswith(prefix + "/"):
            safe = True
            break
    if safe:
        return GuardrailDecision(decision="ALLOWED", reason=f"safe command: {first}")
    for name, pattern in CRITICAL_PATTERNS:
        if pattern.match(cmd) or pattern.match(first):
            return GuardrailDecision(decision="REQUIRES_APPROVAL", reason=f"critical command pattern: {name}")
    return GuardrailDecision(decision="ALLOWED", reason=f"unclassified command: {first}")
