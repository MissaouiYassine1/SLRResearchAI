# Activer la continuité réelle TD02 → TD03

## Pourquoi le JSON est-il déjà rempli ?

`artifacts/search_plan.json` contient des requêtes préparées à l'avance. Ce
choix permet de commencer le TD03 sans refaire le TD02 et sans dépendre
d'une ancienne exécution. Ce n'est toutefois plus une valeur cachée dans du
code : `main.py` et Streamlit lisent réellement ce fichier puis le valident.

La valeur initiale suivante permet de reconnaître ce mode :

```json
"origin": "pedagogical_seed"
```

## Activer le véritable export depuis le TD02

À la fin du TD02, dans `streamlit_app.py`, repérez :

```python
if final:=st.session_state.get("td02_final"):
```

Ajoutez d'abord ces imports au début du fichier :

```python
import json
from pathlib import Path
```

Puis ajoutez le bloc suivant **dans ce `if`**, après l'affichage des requêtes :

```python
# CONTINUITÉ RÉELLE TD02 → TD03
td03_file = (
    Path(__file__).resolve().parent.parent
    / "SLRResearchAI-TD03"
    / "artifacts"
    / "search_plan.json"
)

# Le TD02 utilise encore les noms pédagogiques scholar/ieee/acm.
# Le handoff les adapte aux trois outils libres réellement présents au TD03.
base_query = final["queries"]["scholar"]
artifact = {
    "schema_version": "1.0",
    "origin": "td02_runtime_export",
    "produced_by": "TD02",
    "topic": topic,
    "questions": final["questions"],
    "queries": {
        "openalex": base_query,
        "crossref": base_query,
        "semantic_scholar": base_query,
    },
}

if st.button("Exporter vers TD03", icon=":material/output:"):
    td03_file.parent.mkdir(parents=True, exist_ok=True)
    td03_file.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    st.success(f"Artefact TD02 écrit dans {td03_file}")
```

Cette écriture directe suppose que les dossiers `SLRResearchAI-TD02` et
`SLRResearchAI-TD03` se trouvent côte à côte. Sinon, remplacez uniquement la
construction de `td03_file` par le chemin de votre dossier TD03.

## Vérifier la transmission

1. Terminez l'étape 4 du TD02.
2. Cliquez sur **Exporter vers TD03**.
3. Lancez le TD03 avec `python -m streamlit run streamlit_app.py`.
4. Vérifiez que l'interface affiche `origin = td02_runtime_export` et le sujet
   réellement saisi au TD02.

Le TD03 ne reconstruit aucune requête : il consomme uniquement le JSON.
