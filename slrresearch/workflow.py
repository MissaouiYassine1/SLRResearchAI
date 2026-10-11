from .contracts import AgentAction, SearchState
from .runtime import execute_authorized_action, update_state
from .tools import ToolRegistry


def run_tool_workflow(
    objective: str,
    queries: dict[str, str],
    registry: ToolRegistry,
    limit: int = 5,
) -> SearchState:
    """TODO 6 - Baseline : le programme choisit tous les outils dans l'ordre."""
    # Pour chaque entrée de queries, construire AgentAction(search), exécuter,
    # puis mettre l'état à jour. Terminer avec stop_reason="workflow_complete".
    raise NotImplementedError

