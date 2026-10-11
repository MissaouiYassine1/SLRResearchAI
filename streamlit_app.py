import streamlit as st

from slrresearch.config import Settings, build_model
from slrresearch.demo import build_demo_policy, build_demo_registry
from slrresearch.handoff import DEFAULT_ARTIFACT_PATH, load_search_plan
from slrresearch.policies import LLMDecisionPolicy
from slrresearch.real_tools import build_real_registry
from slrresearch.react_agent import run_react_agent
from slrresearch.workflow import run_tool_workflow


OBJECTIVE = "Trouver des études sur les LLM pour le screening des SLR"


def state_summary(state) -> dict:
    return {
        "steps": state.step,
        "papers": len(state.papers),
        "errors": len(state.errors),
        "stop_reason": state.stop_reason,
    }


def stop_explanation(state, version: str, decision_mode: str) -> str:
    """Traduit la raison technique d'arrêt en explication pédagogique."""
    if state.stop_reason == "workflow_complete":
        return (
            "Le workflow s'arrête parce que la boucle programmée a parcouru "
            "toutes les sources, même si l'une d'elles a échoué."
        )
    if state.stop_reason == "target_reached":
        return (
            "Le runtime a interrompu la boucle dès que le nombre cible "
            "d'articles uniques a été atteint. Cette règle déterministe est "
            "prioritaire sur la prochaine décision."
        )
    if state.stop_reason == "max_steps":
        return (
            "Le décideur n'a pas demandé `finish` assez tôt. Le runtime a "
            "arrêté la boucle lorsque le budget maximal d'étapes a été épuisé."
        )
    if state.stop_reason == "agent_finish":
        if decision_mode == "Politique reproductible":
            return (
                "La politique Python a demandé `finish` : elle termine après "
                "le succès d'OpenAlex, ou après avoir tenté Crossref lorsque "
                "OpenAlex a échoué."
            )
        return (
            "Le LLM a lui-même proposé `finish` en interprétant l'état et le "
            "critère ambigu « assez d'articles ». Ce choix n'est pas une preuve "
            "de couverture scientifique suffisante."
        )
    return f"Arrêt technique signalé par le runtime : `{state.stop_reason}`."


def trace_rows(state) -> list[dict]:
    return [
        {
            "étape": event.step,
            "outil": event.action.get("tool"),
            "statut": event.observation.status,
            "articles": event.observation.count,
        }
        for event in state.trace
    ]


def render_compact_trajectory(state) -> None:
    """Affiche uniquement les informations nécessaires à l'interprétation."""
    labels = {
        "success": "succès",
        "empty": "aucun résultat",
        "rate_limited": "HTTP 429",
        "http_error": "erreur HTTP",
        "network_error": "erreur réseau",
        "unauthorized": "outil refusé",
        "invalid_action": "action invalide",
    }
    for event in state.trace:
        tool = event.action.get("tool") or "aucun outil"
        status = labels.get(event.observation.status, event.observation.status)
        count = event.observation.count
        st.write(
            f"**{event.step}. {tool}** → {status} → "
            f"{count} article{'s' if count != 1 else ''}"
        )

    finish_actions = [
        action for action in state.actions_executed if action.action == "finish"
    ]
    if finish_actions:
        st.write(f"**{state.step}. finish** → arrêt demandé par le décideur")


def render_technical_trace(state) -> None:
    """Conserve les détails complets sans encombrer la vue principale."""
    with st.expander("Détails techniques de la trace"):
        for event in state.trace:
            st.markdown(f"**Étape {event.step}**")
            st.json(
                {
                    "action": event.action,
                    "observation": event.observation.model_dump(
                        mode="json", exclude={"papers"}
                    ),
                },
                expanded=False,
            )


def paper_rows(state) -> list[dict]:
    return [
        {
            "source": paper.source,
            "titre": paper.title,
            "doi": paper.doi or "—",
            "accès ouvert": paper.open_access,
            "lien": paper.url,
        }
        for paper in state.papers
    ]


def search_metrics(state) -> dict:
    raw_results = sum(observation.count for observation in state.observations)
    unique_results = len(state.papers)
    successful_sources = sum(
        observation.status == "success" for observation in state.observations
    )
    return {
        "raw_results": raw_results,
        "unique_results": unique_results,
        "duplicates_removed": max(0, raw_results - unique_results),
        "successful_sources": successful_sources,
    }


def render_search_results(state, version: str) -> None:
    metrics = search_metrics(state)
    st.markdown(f"**{version}**")
    with st.container(horizontal=True):
        st.metric("Résultats bruts", metrics["raw_results"], border=True)
        st.metric("Articles uniques", metrics["unique_results"], border=True)
        st.metric("Doublons retirés", metrics["duplicates_removed"], border=True)
        st.metric("Sources réussies", metrics["successful_sources"], border=True)

    rows = paper_rows(state)
    if not rows:
        st.warning("Aucun article n'a été conservé par cette exécution.")
    else:
        st.dataframe(
            rows,
            hide_index=True,
            column_order=["source", "titre", "doi", "accès ouvert", "lien"],
            column_config={
                "source": st.column_config.TextColumn("Source"),
                "titre": st.column_config.TextColumn("Titre", width="large"),
                "doi": st.column_config.TextColumn("DOI"),
                "accès ouvert": st.column_config.CheckboxColumn("Open access"),
                "lien": st.column_config.LinkColumn("Consulter"),
            },
        )

    st.caption("Bilan compact par outil")
    st.dataframe(
        trace_rows(state),
        hide_index=True,
        column_order=["étape", "outil", "statut", "articles"],
        column_config={
            "étape": st.column_config.NumberColumn("Étape", format="%d"),
            "outil": st.column_config.TextColumn("Outil"),
            "statut": st.column_config.TextColumn("Statut"),
            "articles": st.column_config.NumberColumn("Trouvés", format="%d"),
        },
    )
    render_technical_trace(state)


st.set_page_config(
    page_title="SLRResearchAI · TD03",
    page_icon=":material/account_tree:",
    layout="wide",
)
st.title("TD03 · Workflow outillé vs agent ReAct contrôlé")
st.write(
    "Le même objectif, les mêmes requêtes et les mêmes outils sont exécutés "
    "selon deux logiques de décision différentes."
)

st.session_state.setdefault("td03_workflow", None)
st.session_state.setdefault("td03_react", None)
st.session_state.setdefault("td03_error", None)


def reset_all_results() -> None:
    st.session_state.td03_workflow = None
    st.session_state.td03_react = None
    st.session_state.td03_error = None


def reset_react_result() -> None:
    st.session_state.td03_react = None
    st.session_state.td03_error = None

artifact = load_search_plan()
queries = artifact.queries
with st.container(border=True):
    st.subheader("Handoff réel TD02 → TD03")
    with st.container(horizontal=True):
        st.metric("Producteur déclaré", artifact.produced_by, border=True)
        st.metric("Version du contrat", artifact.schema_version, border=True)
        st.metric("Requêtes validées", len(artifact.queries), border=True)
    if artifact.origin == "pedagogical_seed":
        st.info(
            "Mode autonome : ce JSON est prérempli pour commencer directement "
            "le TD03. Il respecte exactement le contrat que le TD02 peut exporter."
        )
    else:
        st.success(
            "Continuité réelle activée : ce JSON a été exporté par le TD02 puis "
            "chargé et validé par le TD03."
        )
    st.write(f"**Fichier réellement lu :** `{DEFAULT_ARTIFACT_PATH}`")
    st.write(f"**Sujet transmis :** {artifact.topic}")
    with st.expander("Voir l'artefact transmis", expanded=False):
        st.json(artifact.model_dump())

with st.container(border=True):
    st.subheader("Cadre de l'expérience")
    tool_backend = st.segmented_control(
        "Backend des outils",
        ["Catalogue local reproductible", "API scientifiques réelles"],
        default="Catalogue local reproductible",
        key="td03_tool_backend",
        on_change=reset_all_results,
    )
    if tool_backend == "Catalogue local reproductible":
        scenario = st.segmented_control(
            "Observation imposée",
            ["OpenAlex répond HTTP 429", "Toutes les sources répondent"],
            default="OpenAlex répond HTTP 429",
            key="td03_scenario",
            on_change=reset_all_results,
        )
    else:
        scenario = "Réponses réelles non imposées"
    decision_mode = st.segmented_control(
        "Décideur de la version ReAct",
        ["Politique reproductible", "LLM réel (.env)"],
        default="Politique reproductible",
        key="td03_decision_mode",
        on_change=reset_react_result,
    )
    max_steps = st.slider(
        "Nombre maximal d'étapes ReAct",
        2,
        8,
        5,
        key="td03_max_steps",
        on_change=reset_react_result,
    )

use_real_tools = tool_backend == "API scientifiques réelles"
simulate_429 = not use_real_tools and scenario == "OpenAlex répond HTTP 429"


def selected_registry():
    if use_real_tools:
        return build_real_registry()
    return build_demo_registry(simulate_429)


if use_real_tools:
    st.warning(
        "Mode réel : OpenAlex, Crossref et Semantic Scholar seront contactés "
        "sur Internet. Les résultats, la latence et les erreurs 429 ne sont "
        "pas contrôlés par le TD."
    )
elif simulate_429:
    st.warning(
        "Scénario actif : OpenAlex échoue avec HTTP 429. La politique ReAct "
        "doit observer cet échec puis essayer Crossref."
    )
else:
    st.success(
        "Scénario actif : OpenAlex répond avec un article. La politique ReAct "
        "peut terminer sans appeler Crossref."
    )

with st.container(border=True):
    st.subheader("Conditions d'arrêt de tous les scénarios")
    st.dataframe(
        [
            {
                "version / scénario": "A · avec ou sans 429",
                "trajectoire attendue": "les trois sources",
                "condition d'arrêt": "toutes les sources ont été parcourues",
            },
            {
                "version / scénario": "B reproductible · OpenAlex réussit",
                "trajectoire attendue": "OpenAlex → finish",
                "condition d'arrêt": "premier succès prévu par la politique",
            },
            {
                "version / scénario": "B reproductible · OpenAlex 429",
                "trajectoire attendue": "OpenAlex → Crossref → finish",
                "condition d'arrêt": "Crossref a été tenté après le repli",
            },
            {
                "version / scénario": "B LLM · avec ou sans 429",
                "trajectoire attendue": "dépend des observations",
                "condition d'arrêt": "finish du LLM, cible ou max_steps",
            },
        ],
        hide_index=True,
    )
    if use_real_tools:
        st.info(
            "Cas réel sélectionné : la Version A tente les trois API. Dans la "
            "Version B reproductible, un succès OpenAlex mène à `finish`; une "
            "erreur ou un résultat vide mène à Crossref puis à `finish`. Avec "
            "le LLM, la trajectoire dépend des observations réelles."
        )
    elif decision_mode == "Politique reproductible" and simulate_429:
        st.info(
            "Cas B sélectionné : OpenAlex retourne 429, Crossref est alors "
            "tenté, puis la politique demande `finish`, quel que soit le "
            "résultat de Crossref. Semantic Scholar n'est pas appelée."
        )
    elif decision_mode == "Politique reproductible":
        st.info(
            "Cas B sélectionné : OpenAlex réussit. La politique demande "
            "immédiatement `finish`; Crossref et Semantic Scholar ne sont pas "
            "appelées."
        )
    elif simulate_429:
        st.info(
            "Cas B sélectionné : le LLM observe le 429 puis décide s'il faut "
            "essayer Crossref, Semantic Scholar ou terminer. Le runtime impose "
            f"toujours la limite de {max_steps} étapes."
        )
    else:
        st.info(
            "Cas B sélectionné : après le succès d'OpenAlex, le LLM peut "
            "terminer ou rechercher une meilleure couverture dans les autres "
            f"sources. Le runtime impose toujours la limite de {max_steps} étapes."
        )
    st.caption(
        "Dans la version B, trois arrêts restent possibles : `agent_finish`, "
        "`target_reached` ou `max_steps`. Dans cette démonstration, la cible "
        "est volontairement fixée à 99 articles afin d'observer surtout les "
        "décisions `finish` et la limite d'étapes."
    )

with st.container(horizontal=True):
    run_workflow = st.button(
        "Exécuter la version A",
        icon=":material/linear_scale:",
        type="primary",
        key="td03_run_workflow",
    )
    run_react = st.button(
        "Exécuter la version B",
        icon=":material/cycle:",
        type="primary",
        key="td03_run_react",
    )
    clear = st.button(
        "Réinitialiser",
        icon=":material/restart_alt:",
        key="td03_clear",
    )

if clear:
    reset_all_results()
    st.rerun()

if run_workflow:
    try:
        st.session_state.td03_workflow = run_tool_workflow(
            OBJECTIVE,
            queries,
            selected_registry(),
        )
        st.session_state.td03_error = None
    except NotImplementedError:
        st.session_state.td03_error = "Complétez les TODO 1 à 6 avant cette exécution."
    except Exception as exc:
        st.session_state.td03_error = f"Version A impossible : {exc}"

if run_react:
    try:
        if decision_mode == "Politique reproductible":
            policy = build_demo_policy(queries)
        else:
            settings = Settings()
            policy = LLMDecisionPolicy(build_model(settings))
        st.session_state.td03_react = run_react_agent(
            OBJECTIVE,
            queries,
            selected_registry(),
            policy,
            max_steps=max_steps,
            target_papers=99,
        )
        st.session_state.td03_error = None
    except NotImplementedError:
        st.session_state.td03_error = "Complétez tous les TODO, notamment la boucle difficile du TODO 8."
    except Exception as exc:
        st.session_state.td03_error = f"Version B impossible : {exc}"

if st.session_state.td03_error:
    st.error(st.session_state.td03_error)

left, right = st.columns(2)
with left.container(border=True, height="stretch"):
    st.subheader("Version A · Workflow outillé")
    st.write("Le programme appelle toutes les sources dans l'ordre prédéfini.")
    state = st.session_state.td03_workflow
    if state is None:
        st.info("Exécutez la version A pour afficher sa trace.")
    else:
        summary = state_summary(state)
        with st.container(horizontal=True):
            st.metric("Étapes", summary["steps"], border=True)
            st.metric("Articles", summary["papers"], border=True)
        st.write(f'**Raison d’arrêt :** `{summary["stop_reason"]}`')
        st.info(stop_explanation(state, "workflow", decision_mode))
        st.caption("Trajectoire de contrôle")
        render_compact_trajectory(state)

with right.container(border=True, height="stretch"):
    st.subheader("Version B · SearchAgent ReAct")
    st.write("Le décideur reçoit l'état et les observations avant l'action suivante.")
    state = st.session_state.td03_react
    if state is None:
        st.info("Exécutez la version B pour afficher sa trajectoire.")
    else:
        summary = state_summary(state)
        with st.container(horizontal=True):
            st.metric("Étapes", summary["steps"], border=True)
            st.metric("Articles", summary["papers"], border=True)
        st.write(f'**Raison d’arrêt :** `{summary["stop_reason"]}`')
        st.info(stop_explanation(state, "react", decision_mode))
        st.caption("Trajectoire décision–observation")
        render_compact_trajectory(state)

if st.session_state.td03_workflow or st.session_state.td03_react:
    st.subheader("Résultats de recherche")
    st.write(
        "Cette section affiche les articles réellement conservés après "
        "normalisation et déduplication."
    )
    available_tabs = []
    available_states = []
    if st.session_state.td03_workflow:
        available_tabs.append("Version A · workflow")
        available_states.append(st.session_state.td03_workflow)
    if st.session_state.td03_react:
        available_tabs.append("Version B · ReAct")
        available_states.append(st.session_state.td03_react)

    tabs = st.tabs(available_tabs)
    for tab, label, result_state in zip(tabs, available_tabs, available_states):
        with tab:
            render_search_results(result_state, label)

if st.session_state.td03_workflow and st.session_state.td03_react:
    st.subheader("Comparaison observable")
    workflow = st.session_state.td03_workflow
    react = st.session_state.td03_react
    st.dataframe(
        [
            {
                "version": "A - workflow",
                **state_summary(workflow),
                "qui choisit l'action": "programme",
            },
            {
                "version": "B - ReAct",
                **state_summary(react),
                "qui choisit l'action": "politique / LLM",
            },
        ],
        hide_index=True,
    )
    st.info(
        "Cherchez dans les traces le passage décision → action autorisée → "
        "observation → nouvelle décision. Une erreur n'est plus seulement "
        "capturée : elle peut modifier l'action suivante."
    )
    workflow_tools = [action.tool for action in workflow.actions_executed]
    react_tools = [action.tool for action in react.actions_executed if action.tool]
    st.write(f"**Outils appelés par le workflow :** {', '.join(workflow_tools)}")
    st.write(f"**Outils appelés par ReAct :** {', '.join(react_tools)}")
    if workflow_tools != react_tools:
        st.success(
            "La différence est maintenant visible : les deux versions n'ont "
            "pas suivi la même trajectoire et n'ont pas nécessairement produit "
            "le même ensemble d'articles."
        )

    st.write("**Pourquoi les trajectoires peuvent-elles différer ?**")
    st.dataframe(
        [
            {
                "mode": "Workflow A",
                "décision": "ordre fixé par le programme",
                "arrêt": "après toutes les sources",
            },
            {
                "mode": "ReAct reproductible",
                "décision": "règles Python explicites",
                "arrêt": "après le succès prévu par la politique",
            },
            {
                "mode": "ReAct avec LLM",
                "décision": "interprétation du prompt et de l'état",
                "arrêt": "quand le LLM estime le résultat suffisant",
            },
        ],
        hide_index=True,
    )
    st.warning(
        "« Assez d'articles » est ambigu. En production, on peut laisser le "
        "LLM proposer la prochaine source tout en autorisant `finish` seulement "
        "après deux sources réussies ou après avoir essayé toutes les sources."
    )

with st.expander("Voir les états complets"):
    if st.session_state.td03_workflow:
        st.write("Version A")
        st.json(st.session_state.td03_workflow.model_dump(mode="json"))
    if st.session_state.td03_react:
        st.write("Version B")
        st.json(st.session_state.td03_react.model_dump(mode="json"))
