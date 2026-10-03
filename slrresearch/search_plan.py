import re
from typing import Literal

from bleach import clean
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field


class ResearchQuestion(BaseModel):
    """Contrat des données utilisables après le contrôle textuel."""

    identifier: str = Field(pattern=r"^RQ[0-9]+$")
    question: str = Field(min_length=15)


class WorkflowOutcome(BaseModel):
    """État observable du workflow après validation et repair éventuel."""

    status: Literal["accepted", "repaired", "human_required"]
    text: str
    questions: list[ResearchQuestion] = Field(default_factory=list)
    error: str | None = None
    repair_attempts: int = 0


RQ_PATTERN = re.compile(r"^(RQ[0-9]+)\.\s*(.{15,})$")
SEARCH_CONCEPTS = {
    "task": [
        "systematic review screening",
        "study selection",
        "title and abstract screening",
    ],
    "technology": ["large language models", "LLM", "generative AI"],
}


def extract_non_empty_lines(text: str) -> list[str]:
    """TODO 1.1 - Nettoyer le texte et retourner les lignes non vides."""
    lines = [
        line.strip()
        for line in text.strip().splitlines()
        if line.strip()
    ]
    if not lines:
        raise ValueError("Texte vide")
    return lines


def parse_rq_line(line: str) -> dict:
    """TODO 1.2 - Contrôler toute la ligne avec RQ_PATTERN.fullmatch."""
    match = RQ_PATTERN.fullmatch(line)
    if match == None:
        raise ValueError(f"Ligne invalide : {line}")
    return {
                "identifier": match.group(1),
                "question": match.group(2).strip(), 
            }

def validate_identifiers(records: list[dict]) -> None:
    """TODO 1.3 - Exiger exactement RQ1, RQ2, RQ3 dans cet ordre."""
    identifiers = [record["identifier"] for record in records]
    if identifiers != ["RQ1", "RQ2", "RQ3"]:
        raise ValueError(
            f"Identifiants invalides : {identifiers}"
        )
    


def validate_no_duplicates(records: list[dict]) -> None:
    """TODO 1.4 - Refuser deux formulations identiques."""
    questions = [record["question"] for record in records]
    unique_questions = set(questions)
    if len(questions) != len(unique_questions):
        raise ValueError("Les trois questions doivent être différentes")


def validate_free_text(text: str) -> list[dict]:
    """TODO 1.5 - Composer les quatre contrôles textuels précédents."""
    non_empty_lines = extract_non_empty_lines(text)
    records = [parse_rq_line(line) for line in non_empty_lines]
    validate_identifiers(records)
    validate_no_duplicates(records)
    return records

def build_few_shot_prompt(topic: str) -> str:
    """TODO 2 - Ajouter deux exemples sans modifier le validateur."""
    clean = topic.strip()
    if not clean:
        raise ValueError("Sujet vide")
    return f"""Propose exactement trois questions de recherche.
    N'ajoute ni introduction, ni conclusion, ni JSON.

    Exemple 1 - Sujet : ...
    RQ1. ...
    RQ2. ...
    RQ3. ...

    Exemple 2 - Sujet : ...
    RQ1. ...
    RQ2. ...
    RQ3. ...

    Sujet courant : {clean}
    Retourne exactement trois lignes RQ1., RQ2. et RQ3."""


def build_repair_prompt(text: str, error: str) -> str:
    """TODO 3 - Demander une correction de forme ciblée."""
    def build_repair_prompt(text: str, error: str) -> str:
        return f"""Tu corriges la forme d'une sortie destinée à un programme.
            [TÂCHE]
            Corrige uniquement la forme du texte à corriger.
            Préserve le sens exact de chaque question, sans en inventer de nouvelles.

            [ERREUR DÉTECTÉE]
            {error}

            [CONTRAT ATTENDU]
            - Exactement trois lignes, une par question.
            - Chaque ligne commence par RQ1., RQ2. ou RQ3. dans cet ordre.
            - N'ajoute ni introduction, ni explication, ni Markdown, ni JSON.

            [EXEMPLE CONFORME]
            RQ1. Comment l'IA influence-t-elle la personnalisation pédagogique ?
            RQ2. Quels risques l'IA introduit-elle dans l'évaluation ?
            RQ3. Quel contrôle humain doit-il être conservé ?

            [TEXTE À CORRIGER]
            {text}

            [SORTIE]
            Retourne uniquement les trois lignes RQ1., RQ2. et RQ3. corrigées."""


def repair_with_llm(model, text: str, error: str) -> str:
    """Code fourni : un seul appel conditionnel de réparation."""
    response = model.invoke(build_repair_prompt(text, error))
    return str(response.content).strip()


def validate_questions(records: list[dict]) -> list[ResearchQuestion]:
    """TODO 4 - Appliquer le contrat Pydantic à chaque dictionnaire."""
    questions = []
    for record in records:
        # TODO 4 - Remplacer None par l'appel Pydantic indiqué dans l'énoncé.
        question = None
        questions.append(question)
    return questions
     


def build_queries(questions: list[ResearchQuestion]) -> dict[str, str]:
    """TODO 5 - Produire synonymes OR, concepts AND."""
    if not questions:
        raise ValueError("Au moins une RQ validée est nécessaire")
    combinations = []
    for task in SEARCH_CONCEPTS["task"]:
        for technology in SEARCH_CONCEPTS["technology"]:
            # TODO 5 - Construire ici ("task" AND "technology").
            expression = ""
            combinations.append(expression)
    base_query = " OR ".join(combinations)
    return {
        "scholar": base_query,
        "ieee": base_query,
        "acm": base_query,
    }


def build_question_pipeline():
    """TODO 6 - Composer regex | Pydantic | requêtes avec LCEL."""
    # TODO 6 - Remplacer chaque fonction identité par la fonction du bon stade.
    text_control = RunnableLambda(lambda value: value)
    data_contract = RunnableLambda(lambda value: value)
    query_builder = RunnableLambda(lambda value: value)
    return text_control | data_contract | query_builder


def run_controlled_workflow(model, text: str) -> WorkflowOutcome:
    """TODO 7 - Valider, réparer une fois, revalider ou escalader."""
    try:
        # Code fourni - chemin nominal : aucune réparation si le texte est valide.
        records = validate_free_text(text)
        questions = validate_questions(records)
        return WorkflowOutcome(
            status="accepted",
            text=text,
            questions=questions,
            repair_attempts=0,
            error=None,
        )

    except ValueError as first_error:
        # Code fourni - une seule tentative de réparation après l'échec.
        repaired_text = repair_with_llm(
            model,
            text,
            str(first_error),
        )
        try:
            # TODO 7.1 — Revalider la réponse produite par le repair.
            #
            # Ligne 1 : appeler validate_free_text(repaired_text) et ranger
            #           son résultat dans repaired_records.
            # Ligne 2 : appeler validate_questions(repaired_records) et ranger
            #           son résultat dans repaired_questions.
            #
            # Vous devez donc remplacer uniquement les deux valeurs None.
            repaired_records = None
            repaired_questions = None

            return WorkflowOutcome(
                status="repaired",
                text=repaired_text,
                questions=repaired_questions,
                repair_attempts=1,
                error=None,
            )

        except ValueError as second_error:
            # TODO 7.2 — Le texte réparé vient d'échouer à son tour.
            # Remplacer uniquement "accepted" par "human_required".
            # Ne modifiez aucune autre ligne et ne rappelez pas le LLM.
            return WorkflowOutcome(
                status="accepted",
                text=repaired_text,
                questions=[],
                repair_attempts=1,
                error=str(second_error),
            )