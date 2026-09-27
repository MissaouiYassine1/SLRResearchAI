from dataclasses import dataclass
from time import perf_counter

from langchain_core.messages import HumanMessage, SystemMessage

#   Afin de réussir ce TD et de bien assimiler les concepts introduits, il est recommandé d’étudier le module "langchain_core.messages", notamment les classes SystemMessage, HumanMessage et AIMessage, ainsi que la méthode invoke(), qui constitue le mécanisme principal d’invocation des LLM.

@dataclass
class FreeTextQuestions:
    text: str
    provider: str
    latency_seconds: float
    system_prompt: str
    user_prompt: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None


def build_system_prompt() -> str:
    """TODO 1.1 — Compléter les règles stables du modèle."""
    return (
        "Tu es un assistant méthodologique spécialisé dans les revues "
        "systématiques de la littérature (SLR). "
        "Tu dois strictement te limiter au sujet fourni par l'utilisateur. "   # ← périmètre 
        "Tu ne dois jamais inventer de faits, sources ou données. "            # ← garde-fou 
        "Tu dois toujours répondre en français."                              # ← langue 
    )


def build_user_prompt(topic: str) -> str:
    """TODO 1.2 — Construire un prompt zero-shot en cinq rubriques."""
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("Sujet vide")
    return f"""[OBJECTIF]
Formule des questions de recherche pertinentes et strictement centrées sur le sujet fourni, sans t'écarter vers des thématiques connexes non demandées.

[CONTEXTE]
Ces questions serviront de point de départ à une recherche bibliographique systématique : elles guideront la sélection des articles scientifiques et la définition des critères d'inclusion.

[ENTRÉE]
Sujet de la revue : {clean_topic}

[CONTRAINTES]
Propose entre 3 et 5 questions, ouvertes (pas de réponse par oui/non) et distinctes les unes des autres. N'utilise aucun format JSON ni balisage structuré. N'invente aucune donnée, référence ou statistique.

[SORTIE ATTENDUE]
Retourne uniquement une liste en texte libre, chaque question précédée de sa numérotation au format RQ1., RQ2., RQ3., etc."""


def build_zero_shot_prompt(topic: str) -> str:
    """Compatibilité avec le TD2 : renvoie le User Prompt du TD1."""
    return build_user_prompt(topic)


def build_zero_shot_messages(topic: str) -> list[SystemMessage | HumanMessage]:
    """TODO 1.3 — Construire [SystemMessage, HumanMessage]."""
    # Remplacer les deux chaînes par les appels aux fonctions précédentes.
    return [
        SystemMessage(content=build_system_prompt()),
        HumanMessage(content=build_user_prompt(topic)),
    ]
    

def _observable_metadata(response) -> tuple[int | None, int | None, str | None]:
    usage = getattr(response, "usage_metadata", None) or {}
    metadata = getattr(response, "response_metadata", None) or {}
    return (
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        metadata.get("finish_reason") or metadata.get("done_reason"),
    )


def generate_questions(model, topic: str, provider: str = "demo") -> FreeTextQuestions:
    """TODO 1.4 — Effectuer exactement un appel et conserver le texte libre."""
    messages = build_zero_shot_messages(topic)
    started = perf_counter()

    # TODO : remplacer None par UN appel model.invoke(messages).
    response = None    # type de retour de invoke est AImessage

    latency = perf_counter() - started
    # TODO : lire et nettoyer response.content.
    text = "" 
    input_tokens, output_tokens, finish_reason = _observable_metadata(response)

    # TODO : remplacer ce bloc par FreeTextQuestions(...) avec tous les champs.
    raise NotImplementedError("Complétez le TODO 1.4")
