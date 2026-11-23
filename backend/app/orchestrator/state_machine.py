from app.schemas.project import OrchestrationState


class StateMachine:
    """Finite state machine tracking the autonomous project lifecycle."""

    ALLOWED_TRANSITIONS = {
        OrchestrationState.GATHERING_REQUIREMENTS: {OrchestrationState.AWAITING_PLAN_APPROVAL},
        OrchestrationState.AWAITING_PLAN_APPROVAL: {
            OrchestrationState.IMPLEMENTING_MODULE,
            OrchestrationState.GATHERING_REQUIREMENTS,
        },
        OrchestrationState.IMPLEMENTING_MODULE: {OrchestrationState.TESTING_MODULE},
        OrchestrationState.TESTING_MODULE: {
            OrchestrationState.FIXING_MODULE,
            OrchestrationState.IMPLEMENTING_MODULE,
            OrchestrationState.COMPLETED,
        },
        OrchestrationState.FIXING_MODULE: {OrchestrationState.TESTING_MODULE},
        OrchestrationState.COMPLETED: set(),
        OrchestrationState.FAILED: set(),
    }

    def __init__(self, initial: OrchestrationState = OrchestrationState.GATHERING_REQUIREMENTS):
        self.state = initial

    @property
    def is_terminal(self) -> bool:
        return self.state in (OrchestrationState.COMPLETED, OrchestrationState.FAILED)

    def can_transition(self, to: OrchestrationState) -> bool:
        return to in self.ALLOWED_TRANSITIONS.get(self.state, set())

    def transition(self, to: OrchestrationState) -> bool:
        if not self.can_transition(to):
            return False
        self.state = to
        return True

    def reset(self, initial: OrchestrationState = OrchestrationState.GATHERING_REQUIREMENTS) -> None:
        self.state = initial
