from slrresearch.config import Settings, build_model, resolve_decoding
from slrresearch.research_questions import generate_questions

# PARTIE 2 — Modifier uniquement ces valeurs pour comparer les décodages.
DECODING_MODE = "sampling"         # TODO 2.1 : essayer ensuite "sampling"
SAMPLING_TEMPERATURE = 0.8     # TODO 2.2 : comparer ensuite 0.2 et 0.8
TOP_P = 0.9                    # utilisée seulement en mode sampling
MAX_OUTPUT_TOKENS = 400


def main():
    settings = Settings()
    model_name = (
        settings.ollama_model
        if settings.provider == "ollama"
        else settings.groq_model
    )
    decoding = resolve_decoding(
        mode=DECODING_MODE,
        sampling_temperature=SAMPLING_TEMPERATURE,
        top_p=TOP_P,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    print(f"Mode LLM réel : {settings.provider} / {model_name}")
    print(
        f"Décodage : {decoding.mode} | température effective : "
        f"{decoding.temperature} | top_p : {decoding.top_p}"
    )
    topic = input("Sujet de la revue : ").strip()
    model = build_model(settings, decoding)
    result = generate_questions(model, topic, settings.provider)
    print("\n=== SYSTEM PROMPT ===")
    print(result.system_prompt)
    print("\n=== USER PROMPT ===")
    print(result.user_prompt)
    print("\n=== SORTIE ===")
    print(f"Latence : {result.latency_seconds:.2f} s")
    print(result.text)


if __name__ == "__main__":
    main()
