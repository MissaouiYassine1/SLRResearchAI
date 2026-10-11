from slrresearch.demo import build_demo_policy, build_demo_registry
from slrresearch.handoff import DEFAULT_ARTIFACT_PATH, load_search_plan
from slrresearch.react_agent import run_react_agent
from slrresearch.workflow import run_tool_workflow


OBJECTIVE = "Trouver des études sur les LLM pour le screening des SLR"


def print_trace(label, state):
    print(f"\n=== {label} ===")
    for event in state.trace:
        print(
            f"étape={event.step} "
            f"action={event.action.get('action')} "
            f"outil={event.action.get('tool')} "
            f"observation={event.observation.status} "
            f"articles={event.observation.count}"
        )
    print("arrêt :", state.stop_reason)
    print("articles uniques :", len(state.papers))


def main():
    artifact = load_search_plan()
    queries = artifact.queries
    print("=== OUTPUT TD02 → INPUT TD03 ===")
    print("fichier :", DEFAULT_ARTIFACT_PATH)
    print("origine :", artifact.origin)
    print("sujet :", artifact.topic)
    for tool, query in queries.items():
        print(f"{tool}: {query}")

    workflow_state = run_tool_workflow(
        OBJECTIVE,
        queries,
        build_demo_registry(simulate_429=True),
    )
    print_trace("VERSION A - WORKFLOW OUTILLÉ", workflow_state)

    react_state = run_react_agent(
        OBJECTIVE,
        queries,
        build_demo_registry(simulate_429=True),
        build_demo_policy(queries),
        max_steps=5,
        target_papers=99,
    )
    print_trace("VERSION B - AGENT ReAct CONTRÔLÉ", react_state)


if __name__ == "__main__":
    main()
