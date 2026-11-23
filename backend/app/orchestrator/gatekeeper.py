from app.schemas.module import Module, ModuleStatus


class ModuleGatekeeper:
    """Lock progression to module i+1 until module i's test suite passes (exit code 0)."""

    def is_module_passed(self, module: Module) -> bool:
        return module.status == ModuleStatus.PASSED

    def should_start_module(self, modules: list[Module], module_index: int) -> bool:
        if module_index < 0 or module_index >= len(modules):
            return False
        return modules[module_index].status == ModuleStatus.PASSED
