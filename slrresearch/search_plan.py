def extract_non_empty_lines(text: str) -> list[str]:
    lines = [
        line.strip()
        for line in text.strip().splitlines()
        if line.strip()
    ]
    if not lines:
        raise ValueError("Texte vide")
    return lines