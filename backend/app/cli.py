import asyncio
import difflib
import sys

from app import llm
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
from app.schemas.project import OrchestrationState, ProjectCreate, UserMode
from app.schemas.review import CodeReview
from app.storage import repository


_orchestrator = None
_current_project_id: str = ""


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        developer = DeveloperAgent(llm=llm)
        qa = QAAgent(llm=llm, workspace_root=settings.LOCAL_WORKSPACE_ROOT)
        orchestrator_agent = OrchestratorAgent(llm=llm)
        fixer = FixerAgent(llm=llm)
        reviewer = ReviewerAgent(llm=llm)
        _orchestrator = Orchestrator(developer=developer, qa=qa, orchestrator_agent=orchestrator_agent, fixer=fixer, reviewer=reviewer)
    return _orchestrator


def _print_status() -> None:
    project = repository.get_project(_current_project_id) if _current_project_id else None
    if project is None:
        print("No active project. Create one with: new <name>")
        return
    print(f"Project: {project.name}")
    print(f"State: {project.state}")
    print(f"Mode: {project.current_mode}")
    print(f"Requirements: {project.requirements or '(none)'}")
    print(f"Approved: {project.approved_requirements or '(not yet)'}")
    for i, module in enumerate(project.modules):
        extra = ""
        if module.test_run is not None:
            extra = f" | tests: {module.test_run.status} (exit {module.test_run.exit_code})"
        if module.review is not None:
            extra += f" | review: approved={module.review.approved} policy={module.review.policy}"
        print(f"  [{i}] {module.name} -> {module.status}{extra}")


async def _cmd_requirements(text: str) -> None:
    if not _current_project_id:
        print("No active project. Create one with: new <name>")
        return
    repository.update_requirements(_current_project_id, text)
    print("Requirements updated.")


async def _cmd_plan() -> None:
    project = repository.get_project(_current_project_id) if _current_project_id else None
    if project is None:
        print("No active project. Create one with: new <name>")
        return
    modules = await _get_orchestrator().plan_modules(project)
    project.modules = modules
    project.current_module_index = 0 if modules else -1
    print(f"Planned {len(modules)} module(s):")
    for i, module in enumerate(modules):
        print(f"  [{i}] {module.name} - {module.description} (deps: {', '.join(module.dependencies) or 'none'})")


async def _cmd_run(index: int) -> None:
    project = repository.get_project(_current_project_id) if _current_project_id else None
    if project is None:
        print("No active project. Create one with: new <name>")
        return
    if index < 0 or index >= len(project.modules):
        print(f"No module at index {index}. Modules: {list(range(len(project.modules)))}")
        return
    module = await _get_orchestrator().start_module(project, project.modules[index])
    print(f"Module {module.name} finished with status: {module.status}")
    if module.test_run is not None:
        print(f"Test run status: {module.test_run.status}, exit code: {module.test_run.exit_code}")
        print(f"Test output:\n{module.test_run.output}")


async def _cmd_review(index_str: str) -> None:
    project = repository.get_project(_current_project_id) if _current_project_id else None
    if project is None:
        print("No active project. Create one with: new <name>")
        return
    try:
        index = int(index_str)
    except ValueError:
        print("Usage: review <module_index>")
        return
    if index < 0 or index >= len(project.modules):
        print(f"No module at index {index}. Modules: {list(range(len(project.modules)))}")
        return
    module = project.modules[index]
    review = await _get_orchestrator().review_module(project, module)
    if review is None:
        print("Reviewer unavailable.")
        return
    print(f"Review approved: {review.approved}")
    print(f"Review policy: {review.policy}")
    print(f"Summary: {review.summary}")
    for issue in review.issues:
        print(f"  [{issue.severity}] {issue.message} @ {issue.location}")
    await _print_live_diff(module.code or "", "")


def _cmd_review_history(index_str: str) -> None:
    project = repository.get_project(_current_project_id) if _current_project_id else None
    if project is None:
        print("No active project. Create one with: new <name>")
        return
    try:
        index = int(index_str)
    except ValueError:
        print("Usage: review history <module_index>")
        return
    if index < 0 or index >= len(project.modules):
        print(f"No module at index {index}. Modules: {list(range(len(project.modules)))}")
        return
    module = project.modules[index]
    reviews = repository.get_reviews(module.id)
    if not reviews:
        print("No reviews recorded for this module yet.")
        return
    for r in reviews:
        print(f"Review at {r.created_at} | approved={r.approved} | policy={r.policy}")
        print(f"Summary: {r.summary}")
        for issue in r.issues:
            print(f"  [{issue.severity}] {issue.message} @ {issue.location}")


async def _print_live_diff(new_code: str, old_code: str = "") -> None:
    old_lines = (old_code or "").splitlines()
    new_lines = (new_code or "").splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            print(f"\033[92m{line}\033[0m")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"\033[91m{line}\033[0m")
        else:
            print(line)
        await asyncio.sleep(0.005)


def _cmd_config() -> None:
    while True:
        print("Config actions:")
        print("  1) Add provider")
        print("  2) Set model for agent")
        print("  3) List config")
        print("  4) Delete provider")
        print("  5) Set review policy")
        print("  6) Set auto-review toggle")
        print("  7) Back")
        choice = input("> ").strip()
        if choice == "1":
            name = input("Provider name: ").strip()
            base_url = input("Base URL: ").strip()
            api_key = input("API key: ").strip()
            if not name or not base_url or not api_key:
                print("Provider fields cannot be empty.")
                continue
            config_manager.add_provider(name, base_url, api_key)
            print(f"Provider '{name}' added.")
        elif choice == "2":
            agent = input("Agent name (orchestrator/planner/developer/qa/fixer/reviewer): ").strip()
            model_id = input("Model ID: ").strip()
            if not agent or not model_id:
                print("Agent and model cannot be empty.")
                continue
            config_manager.set_model(agent, model_id)
            print(f"Model for '{agent}' set to {model_id}.")
        elif choice == "3":
            import json as _json

            print(_json.dumps(config_manager.get_config(), indent=2))
        elif choice == "4":
            name = input("Provider name to delete: ").strip()
            config_manager.delete_provider(name)
            print("Provider deleted.")
        elif choice == "5":
            policy = input("Review policy (strict/balanced/permissive): ").strip()
            config_manager.set_review_policy(policy)
            print("Review policy set.")
        elif choice == "6":
            answer = input("Auto-review after tests pass? [y/N]: ").strip().lower()
            enabled = answer in ("y", "yes")
            config_manager.set_auto_review(enabled)
            print("Auto-review set.")
        elif choice in ("7", "q", "quit"):
            break
        else:
            print("Invalid choice.")


def _print_help() -> None:
    print("Commands:")
    print("  new <name>            Create a new project")
    print("  requirements <text>  Update client requirements")
    print("  plan                  Orchestrator plans modules from requirements")
    print("  approve               Approve requirements -> start IMPLEMENTING_MODULE")
    print("  run <index>           Run developer + QA agent loop for module at index")
    print("  review <index>        Run code review on module at index")
    print("  review history <i>   Show review history for module at index")
    print("  status                Show project / module / test status")
    print("  mode <PLAN|EDIT|FIX|EXPLAIN>  Switch operating mode")
    print("  config                Open interactive config wizard")
    print("  help                  Show this help")
    print("  quit                  Exit")


async def main() -> None:
    global _current_project_id
    print("Conding-Assist terminal chat. Type 'help' for commands.")
    pending_commands = list(sys.argv[1:])
    while True:
        if pending_commands:
            raw = pending_commands.pop(0)
        else:
            try:
                raw = await asyncio.to_thread(input, "> ")
            except EOFError:
                break
        parts = raw.strip().split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd in ("quit", "exit"):
            break
        elif cmd == "help":
            _print_help()
        elif cmd == "new":
            project = repository.create_project(ProjectCreate(name=arg or "Untitled Project"))
            _current_project_id = project.id
            print(f"Created project {project.id}")
        elif cmd == "status":
            _print_status()
        elif cmd == "requirements":
            await _cmd_requirements(arg)
        elif cmd == "plan":
            await _cmd_plan()
        elif cmd == "approve":
            project = repository.get_project(_current_project_id) if _current_project_id else None
            if project is None:
                print("No active project. Create one with: new <name>")
                continue
            project.approved_requirements = project.requirements
            state_machine = StateMachine()
            state_machine.transition(OrchestrationState.IMPLEMENTING_MODULE)
            repository.set_state(_current_project_id, state_machine.state, current_mode=UserMode.PLAN)
            print("Plan approved. Orchestrator transitioning to IMPLEMENTING_MODULE.")
        elif cmd == "run":
            try:
                index = int(arg)
            except ValueError:
                print("Usage: run <module_index>")
                continue
            await _cmd_run(index)
        elif cmd == "review":
            tokens = arg.split()
            if not tokens:
                print("Usage: review <module_index> | review history <module_index>")
            elif tokens[0] == "history":
                if len(tokens) < 2:
                    print("Usage: review history <module_index>")
                else:
                    _cmd_review_history(tokens[1])
            else:
                await _cmd_review(arg)
        elif cmd == "mode":
            if arg.upper() in [mode.value for mode in UserMode]:
                mode = UserMode(arg.upper())
                repository.set_current_mode(_current_project_id, mode)
                project = repository.get_project(_current_project_id) if _current_project_id else None
                state = OrchestrationState.FIXING_MODULE if mode == UserMode.FIX else (project.state if project else OrchestrationState.GATHERING_REQUIREMENTS)
                repository.set_state(_current_project_id, state, current_mode=mode)
                print(f"Mode switched to {mode}")
            else:
                print(f"Invalid mode. Choose from: {[m.value for m in UserMode]}")
        elif cmd == "config":
            _cmd_config()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for the list of commands.")


if __name__ == "__main__":
    asyncio.run(main())
