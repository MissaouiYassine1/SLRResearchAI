from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from slrresearch.config import resolve_decoding
from slrresearch.research_questions import (
    build_system_prompt,
    build_user_prompt,
    build_zero_shot_messages,
    generate_questions,
)


class FakeModel:
    """Faux modèle rapide : les tests ne dépendent ni d'Internet ni d'un LLM."""

    def __init__(self):
        self.calls = 0
        self.received = None

    def invoke(self, messages):
        self.calls += 1
        self.received = messages
        return SimpleNamespace(
            content="  RQ1. Comment évaluer les LLM pour le screening ?  ",
            usage_metadata={"input_tokens": 42, "output_tokens": 18},
            response_metadata={"finish_reason": "stop"},
        )


def test_todo_1_1_system_prompt():
    prompt = build_system_prompt()
    prompt_lower = prompt.lower()

    assert "slr" in prompt_lower or "revue systématique" in prompt_lower
    assert "sujet" in prompt_lower
    assert "invent" in prompt_lower
    assert "français" in prompt_lower


def test_todo_1_2_user_prompt():
    topic = "LLM et screening des SLR"
    prompt = build_user_prompt(topic)

    assert topic in prompt

    sections = (
        "[OBJECTIF]",
        "[CONTEXTE]",
        "[ENTRÉE]",
        "[CONTRAINTES]",
        "[SORTIE ATTENDUE]",
    )
    for section in sections:
        assert prompt.count(section) == 1

    assert "3" in prompt
    assert "5" in prompt
    assert "RQ1." in prompt


def test_todo_1_2_sujet_vide():
    with pytest.raises(ValueError):
        build_user_prompt("   ")


def test_todo_1_3_messages_langchain():
    topic = "LLM et screening des SLR"
    messages = build_zero_shot_messages(topic)

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[0].content == build_system_prompt()
    assert messages[1].content == build_user_prompt(topic)
    assert topic not in str(messages[0].content)
    assert topic in str(messages[1].content)


def test_todo_1_4_appel_unique():
    model = FakeModel()
    result = generate_questions(
        model,
        "LLM et screening des SLR",
        provider="fake",
    )

    assert model.calls == 1
    assert model.received is not None
    assert len(model.received) == 2
    assert result.text == "RQ1. Comment évaluer les LLM pour le screening ?"


def test_todo_1_4_metadonnees():
    model = FakeModel()
    result = generate_questions(
        model,
        "LLM et screening des SLR",
        provider="fake",
    )

    assert result.provider == "fake"
    assert result.latency_seconds >= 0
    assert result.system_prompt == build_system_prompt()
    assert "LLM et screening des SLR" in result.user_prompt
    assert result.input_tokens == 42
    assert result.output_tokens == 18
    assert result.finish_reason == "stop"


def test_todo_1_4_sujet_invalide_refuse_avant_appel():
    model = FakeModel()

    with pytest.raises(ValueError):
        generate_questions(model, "   ")

    assert model.calls == 0


def test_todo_2_1_greedy_et_sampling():
    greedy = resolve_decoding(
        mode="greedy",
        sampling_temperature=0.8,
        top_p=0.9,
        max_output_tokens=400,
    )
    sampling = resolve_decoding(
        mode="sampling",
        sampling_temperature=0.8,
        top_p=0.9,
        max_output_tokens=400,
    )

    assert greedy.mode == "greedy"
    assert greedy.temperature == 0
    assert greedy.top_p == 1
    assert greedy.top_k == 1
    assert sampling.mode == "sampling"
    assert sampling.temperature == 0.8
    assert sampling.top_p == 0.9
    assert sampling.top_k == 40


def test_todo_2_2_effet_temperature():
    low_temperature = resolve_decoding(
        mode="sampling",
        sampling_temperature=0.2,
        top_p=0.9,
        max_output_tokens=400,
    )
    high_temperature = resolve_decoding(
        mode="sampling",
        sampling_temperature=0.8,
        top_p=0.9,
        max_output_tokens=400,
    )

    assert low_temperature.temperature == 0.2
    assert high_temperature.temperature == 0.8
    assert low_temperature.mode == high_temperature.mode == "sampling"
    assert low_temperature.top_p == high_temperature.top_p == 0.9
    assert low_temperature.top_k == high_temperature.top_k == 40
    assert low_temperature.max_output_tokens == 400
    assert high_temperature.max_output_tokens == 400
