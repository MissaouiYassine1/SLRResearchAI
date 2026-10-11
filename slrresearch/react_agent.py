from pydantic import ValidationError

from .contracts import AgentAction, Observation, SearchState
from .policies import DecisionPolicy
from .runtime import execute_authorized_action, update_state
from .tools import ToolRegistry


def run_react_agent(
    objective: str,
    queries: dict[str, str],
    registry: ToolRegistry,
    decide: DecisionPolicy,
    max_steps: int = 5,
    target_papers: int = 3,
) -> SearchState:
    """TODO 8 - Compléter les cinq décisions centrales de la boucle ReAct.

    À chaque tour : décider, valider, traiter finish ou exécuter, observer,
    mettre à jour. Les actions invalides/refusées deviennent des observations.
    La boucle doit aussi s'arrêter sur target_papers ou max_steps.
    """
    # Fourni : état initial et budget maximal de tours.
    state = SearchState(objective=objective, queries=queries)

    for _ in range(max_steps):
        # TODO 8.1 — DÉCIDER : appeler la politique avec l'état et les noms.
        raw_action = ______________________________(state, registry.names)

        try:
            # TODO 8.2 — VALIDER : appliquer le contrat AgentAction.
            action = AgentAction.________________(raw_action)
        except (ValidationError, ValueError) as exc:
            # Fourni : une décision invalide devient une observation.
            observation = Observation(
                status="invalid_action",
                error=str(exc),
                raw_action=raw_action if isinstance(raw_action, dict) else None,
            )
            update_state(state, None, observation, raw_action=raw_action)
            continue

        # TODO 8.3 — ARRÊTER : compléter la valeur de l'action terminale.
        if action.action == "________________":
            state.actions_executed.append(action)
            state.step += 1
            state.finished = True
            state.stop_reason = "agent_finish"
            return state

        # TODO 8.4 — AGIR : appeler la frontière d'exécution contrôlée.
        observation = ______________________________(action, registry)

        # TODO 8.5 — OBSERVER : mémoriser action et observation dans l'état.
        ______________________________(state, action, observation)

        # Fourni : arrêt déterministe lorsque la cible est atteinte.
        if len(state.papers) >= target_papers:
            state.finished = True
            state.stop_reason = "target_reached"
            return state

    # Fourni : garde-fou lorsque le décideur ne termine jamais.
    state.finished = True
    state.stop_reason = "max_steps"
    return state
