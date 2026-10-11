"""TODO 3 — Configurer les véritables outils de recherche scientifique."""

import httpx

from .tools import SearchTool, ToolRegistry, crossref_search, openalex_search


SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def semantic_scholar_search(query: str, limit: int) -> list[dict]:
    """Appelle la véritable API Semantic Scholar puis normalise sa réponse."""
    # TODO 3.1 — Compléter l'URL et les paramètres indiqués dans l'énoncé.
    response = httpx.get(
        ______________________________,
        params={
            "query": ______________________________,
            "limit": ______________________________,
            "fields": "title,abstract,externalIds,url,openAccessPdf",
        },
        timeout=20,
    )
    response.raise_for_status()
    return [
        {
            "id": item.get("paperId", ""),
            "title": item.get("title") or "Sans titre",
            "abstract": item.get("abstract") or "",
            "doi": (item.get("externalIds") or {}).get("DOI", ""),
            "url": (
                (item.get("openAccessPdf") or {}).get("url")
                or item.get("url", "")
            ),
            "open_access": bool((item.get("openAccessPdf") or {}).get("url")),
        }
        for item in response.json().get("data", [])
    ]


def build_real_registry() -> ToolRegistry:
    """Enregistre uniquement les trois outils externes explicitement autorisés."""
    # TODO 3.2 — Associer chaque nom à sa véritable fonction de recherche.
    return ToolRegistry(
        [
            SearchTool("openalex", ______________________________),
            SearchTool("crossref", ______________________________),
            SearchTool("semantic_scholar", ______________________________),
        ]
    )
