# TD03 — Du workflow outillé à l'agent ReAct contrôlé

## 1. Position du TD dans le projet

Le TD02 contrôlait une **donnée produite par le LLM** : des questions de
recherche devaient respecter un contrat avant de devenir exploitables.

Le TD03 contrôle maintenant une **décision d'action** : le système peut proposer
d'appeler un outil, mais cette proposition doit être validée, autorisée,
exécutée et transformée en observation.

```text
TD02                                    TD03
texte LLM                                 objectif + état
   ↓                                          ↓
ResearchQuestion validée                 AgentAction proposée
   ↓                                          ↓
requêtes scientifiques                  validation Pydantic
                                              ↓
                                         registre d'outils
                                              ↓
                                      exécution ou refus
                                              ↓
                                         Observation
```

Le TD03 charge réellement `artifacts/search_plan.json` avec
`load_search_plan()`. Pour éviter de refaire le TD02 pendant cette séance, le
fichier distribué contient des requêtes préremplies et porte
`origin="pedagogical_seed"`. Il respecte néanmoins le même contrat Pydantic que
l'artefact exportable par le TD02. Le TD03 ne reconstruit jamais les
requêtes. La procédure facultative de continuité complète est détaillée dans
`CONTINUITE_REELLE_TD02.md`.

## 2. Question centrale

Où se trouve la décision concernant le prochain outil ?

### Version A — Workflow outillé contrôlé

```python
for tool_name, query in queries.items():
    # Le programme impose l'ordre des outils.
```

La logique Python connaît à l'avance toutes les étapes.

### Version B — SearchAgent ReAct contrôlé

```text
décider → valider → autoriser → agir → observer → mettre l'état à jour
   ↑                                                               |
   └───────────────────────────────────────────────────────────────┘
```

Le décideur choisit l'action suivante à partir de l'objectif, de l'état et des
observations précédentes. Le programme conserve toutefois la frontière de
contrôle : le LLM ne lance jamais directement un outil.

## 3. Objectifs pédagogiques

À la fin du TD, vous devez savoir :

1. distinguer workflow outillé et agent ReAct ;
2. représenter une décision avec un contrat Pydantic `AgentAction` ;
3. appliquer une liste blanche d'outils avec un registre ;
4. transformer succès, résultat vide, erreur et refus en `Observation` ;
5. distinguer état du système et contexte exposé au LLM ;
6. conserver une trace action–observation ;
7. écrire une baseline déterministe ;
8. demander au LLM de proposer une action sans lui donner l'exécution ;
9. borner une boucle ReAct par `max_steps`, `finish` et une règle d'arrêt ;
10. expliquer comment une observation modifie une décision ultérieure.

## 4. Organisation des fichiers

Vous complétez uniquement :

```text
slrresearch/contracts.py    # TODO 1
slrresearch/tools.py        # TODO 2
slrresearch/real_tools.py   # TODO 3
slrresearch/runtime.py      # TODO 4 et TODO 5
slrresearch/workflow.py     # TODO 6
slrresearch/policies.py     # TODO 7
slrresearch/react_agent.py  # TODO 8, assemblage guidé de la boucle ReAct
```

Les fichiers suivants sont fournis :

- `slrresearch/research_questions.py` : acquis complet du TD01, conservé sans
  nouveau travail demandé ;
- `slrresearch/search_plan.py` : acquis complet du TD02, conservé sans nouveau
  travail demandé ;
- `artifacts/search_plan.json` : artefact réellement lu, prérempli pour ce TD ;
- `slrresearch/handoff.py` : contrat et validation du handoff TD02 → TD03 ;
- `slrresearch/demo.py` : outils locaux et politique reproductible ;
- `slrresearch/config.py` : sélection Groq/Ollama ;
- `main.py` : comparaison en terminal ;
- `streamlit_app.py` : comparaison visuelle ;
- `data/papers.json` : petit catalogue pédagogique ;
- `tests/test_td03.py` : contrat exécutable des TODO.

## 5. Installation et premier diagnostic

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m pytest --collect-only -q
```

Les tests échouent au départ à cause des `NotImplementedError`. Ne commencez
pas par l'interface : avancez TODO par TODO avec les tests ciblés.

---

# Partie A — Définir la frontière de contrôle

## TODO 1 — Valider le contrat `AgentAction`

**Fichier :** `slrresearch/contracts.py`  
**Fonction :** `AgentAction.validate_action_arguments()`

Le modèle possède quatre champs :

```python
action: Literal["search", "finish"]
tool: str | None
query: str | None
limit: int | None
```

Les types seuls ne suffisent pas. Par exemple, `tool` est optionnel pour que
`finish` puisse l'omettre, mais il devient obligatoire lorsque
`action="search"`. Le TODO contrôle donc la **cohérence entre les champs**.

Le décorateur `@model_validator(mode="after")` indique que Pydantic a déjà
contrôlé les types. Vous travaillez sur l'objet `self`, vous pouvez consulter
ses quatre attributs et vous devez retourner `self` si tout est cohérent.

Vous modifiez uniquement :

```text
slrresearch/contracts.py
└── AgentAction.validate_action_arguments()
```

### Règles

| Action | `tool` | `query` | `limit` |
|---|---|---|---|
| `search` | obligatoire | chaîne non vide | obligatoire, entre 1 et 20 |
| `finish` | doit être `None` | doit être `None` | doit être `None` |

### Étape 1.1 — Retirer l'exception provisoire

Repérez exactement :

```python
@model_validator(mode="after")
def validate_action_arguments(self):
    """TODO 1 - Appliquer les règles conditionnelles search/finish."""
    # search exige tool, query non vide et limit.
    # finish interdit ces trois arguments.
    raise NotImplementedError
```

Supprimez uniquement `raise NotImplementedError`, puis écrivez les contrôles à
sa place.

### Étape 1.2 — Valider une action `search`

Une recherche complète ressemble à ceci :

```python
AgentAction(
    action="search",
    tool="openalex",
    query="LLM AND systematic review",
    limit=5,
)
```

Commencez par :

```python
if self.action == "search":
```

Puis appliquez trois contrôles indépendants :

1. `if not self.tool` refuse un outil absent ou vide ;
2. `if not self.query or not self.query.strip()` refuse une requête absente,
   vide ou composée uniquement d'espaces ;
3. `if self.limit is None` refuse une limite absente.

La contrainte `1 <= limit <= 20` existe déjà dans
`Field(default=None, ge=1, le=20)`. Ne la réécrivez pas.

### Étape 1.3 — Valider une action `finish`

Une demande d'arrêt correcte ne transporte aucun argument d'outil :

```python
AgentAction(action="finish")
```

Dans la branche `else`, levez une seule `ValueError` si **au moins un** des
trois champs est différent de `None` :

```python
else:
    if (
        self.tool is not None
        ___ self.query is not None
        ___ self.limit is not None
    ):
        raise ValueError(
            "finish ne doit contenir aucun argument d'outil"
        )
```

Remplacez les deux blancs par l'opérateur logique Python correspondant à « au
moins une condition vraie ». N'utilisez pas `and` : avec `and`, une action
`finish` contenant seulement `tool` serait acceptée à tort.

### Étape 1.4 — Retourner le modèle

Après les deux branches, ajoutez `return self`. Cette ligne doit être alignée
avec le premier `if`, car elle concerne les deux actions.

### Travail demandé, en résumé

Dans le validateur `mode="after"` :

1. remplacer `NotImplementedError` par une branche `search` et une branche
   `finish` ;
2. lever une `ValueError` dès qu'une combinaison est incohérente ;
3. utiliser `.strip()` pour détecter une requête composée d'espaces ;
4. terminer par `return self`.

### Squelette

```python
if self.action == "search":
    if not self.tool:
        raise ValueError("...")
    if not self.query or not self.query.________():
        raise ValueError("...")
    if self.limit is None:
        raise ValueError("...")
else:
    if (
        self.tool is not None
        ___ self.query is not None
        ___ self.limit is not None
    ):
        raise ValueError("...")

return self
```

Remplacez `.________()` par la méthode expliquée à l'étape 1.2, puis les deux
`___` par l'opérateur expliqué à l'étape 1.3. Le contrôle de `limit` est déjà
donné entièrement.

### Exemples attendus

Ces deux constructions doivent réussir :

```python
AgentAction(action="search", tool="openalex", query="LLM AND SLR", limit=5)
AgentAction(action="finish")
```

Chacune des constructions suivantes doit lever une erreur :

```python
AgentAction(action="search", tool=None, query="LLM", limit=5)
AgentAction(action="search", tool="openalex", query="   ", limit=5)
AgentAction(action="search", tool="openalex", query="LLM", limit=None)
AgentAction(action="finish", tool="openalex")
AgentAction(action="finish", query="LLM")
AgentAction(action="finish", limit=5)
```

Ne lancez aucun outil dans ce validateur. Il ne choisit pas l'outil et ne
vérifie pas encore s'il est autorisé : ce seront les objectifs des TODO 2 et 3.

```bash
python -m pytest -v -k "todo_1"
```

Résultat attendu :

```text
test_todo_1_search_exige_des_arguments_complets PASSED
test_todo_1_finish_interdit_les_arguments_outil PASSED
```

Si `NotImplementedError` apparaît encore, vous n'avez pas remplacé la bonne
ligne. Si `finish` accepte un seul argument, vérifiez l'opérateur logique de la
branche `else`.

---

## TODO 2 — Autoriser un outil avec `ToolRegistry`

**Fichier :** `slrresearch/tools.py`  
**Méthode :** `ToolRegistry.authorize()`

Le registre est construit par :

```python
self._tools = {tool.name: tool for tool in tools}
```

Il constitue une liste blanche. Un nom proposé par le LLM n'est jamais utilisé
directement pour importer une fonction ou exécuter une commande.

### Travail demandé

1. refuser `None` ;
2. refuser un nom absent de `self._tools` ;
3. lever `ToolNotAllowedError` dans les deux cas ;
4. sinon retourner `self._tools[tool_name]`.

### Hint

```python
if tool_name is None or tool_name not in self._tools:
    raise ______________________(f"Outil non autorisé : {tool_name}")

return ______________________
```

```bash
python -m pytest -v -k "todo_2"
```

### Question intermédiaire

Pourquoi valider `tool: str` avec Pydantic ne suffit-il pas pour autoriser
l'outil ?

---

## TODO 3 — Configurer et enregistrer de vrais outils scientifiques

**Fichier :** `slrresearch/real_tools.py`  
**Fonctions :** `semantic_scholar_search()` et `build_real_registry()`

Le catalogue local reste utile pour les tests, mais il ne suffit pas pour
apprendre à connecter un agent au monde extérieur. Dans ce TODO, vous
configurez trois outils qui contactent réellement Internet :

| Nom autorisé | Fonction Python | Service appelé |
|---|---|---|
| `openalex` | `openalex_search` | API OpenAlex |
| `crossref` | `crossref_search` | API Crossref |
| `semantic_scholar` | `semantic_scholar_search` | API Semantic Scholar |

Les fonctions OpenAlex et Crossref sont fournies dans `slrresearch/tools.py` et
servent d'exemples. Vous devez terminer Semantic Scholar puis construire le
registre réel.

### TODO 3.1 — Compléter l'appel Semantic Scholar

Dans `semantic_scholar_search()`, remplacez les trois blancs :

```python
response = httpx.get(
    ______________________________,
    params={
        "query": ______________________________,
        "limit": ______________________________,
        "fields": "title,abstract,externalIds,url,openAccessPdf",
    },
    timeout=20,
)
```

Utilisez respectivement :

1. la constante `SEMANTIC_SCHOLAR_URL` ;
2. l'argument `query` reçu par la fonction ;
3. l'argument `limit` reçu par la fonction.

Le reste du code fourni appelle `raise_for_status()`, lit le JSON et normalise
chaque résultat dans le format commun attendu par `PaperRecord`.

### TODO 3.2 — Construire la liste blanche réelle

Dans `build_real_registry()`, associez chaque nom à la fonction correspondante :

```python
return ToolRegistry(
    [
        SearchTool("openalex", __________________),
        SearchTool("crossref", __________________),
        SearchTool("semantic_scholar", __________________),
    ]
)
```

Complétez avec `openalex_search`, `crossref_search` et
`semantic_scholar_search`, dans cet ordre. Vous transmettez les fonctions sans
parenthèses : elles seront appelées plus tard par le runtime avec une requête et
une limite.

### Validation sans dépendre d'Internet

```bash
python -m pytest -v -k "todo_3"
```

Les tests remplacent temporairement `httpx.get` par une fausse réponse. Ils
vérifient la configuration de la requête HTTP et la normalisation, sans appeler
Internet. Après leur réussite, lancez Streamlit et sélectionnez **API
scientifiques réelles** pour effectuer les véritables appels.

Les API publiques peuvent être lentes, indisponibles ou répondre HTTP 429. Ce
n'est pas nécessairement un défaut de votre code : le TODO 4 transformera ces
issues externes en observations exploitables par l'agent.

---

# Partie B — Agir et observer

## TODO 4 — Exécuter une action autorisée

**Fichier :** `slrresearch/runtime.py`  
**Fonction :** `execute_authorized_action()`

Cette fonction représente la frontière d'exécution. Elle reçoit une action
déjà structurée, mais elle doit encore demander l'autorisation au registre.

Elle ne doit pas laisser une erreur `httpx` interrompre la boucle. Toute issue
devient une `Observation`.

Le corps de `execute_authorized_action()` est maintenant presque entièrement
fourni. Vous écrivez seulement les deux lignes conceptuelles présentes dans les
slides : **autoriser** l'outil puis **exécuter** sa fonction. Ne modifiez pas
encore `paper_key()` ni `update_state()`.

### Travail étudiant — seulement deux blancs

Dans `slrresearch/runtime.py`, complétez :

```python
tool = registry.________________(action.tool)
raw_papers = tool.________________(action.query or "", action.limit or 1)
```

Les noms recherchés ont déjà été utilisés aux TODO précédents. Tout le code de
chronométrage, normalisation et traitement des erreurs est fourni.

### Comprendre le contrat de la fonction

La fonction reçoit une `AgentAction` et un `ToolRegistry`, puis retourne
toujours une seule `Observation` :

```text
AgentAction
  → autorisation du nom par ToolRegistry
  → récupération du véritable SearchTool
  → appel de tool.search(query, limit)
  → normalisation du résultat ou de l'erreur
  → Observation
```

Elle doit contenir deux blocs `try` séparés : le premier protège
l'autorisation, le second protège l'appel externe.

### Cas à traiter

| Situation | `Observation.status` |
|---|---|
| outil refusé | `unauthorized` |
| au moins un article | `success` |
| liste vide | `empty` |
| HTTP 429 | `rate_limited` |
| autre erreur HTTP | `http_error` |
| erreur réseau | `network_error` |

### Code fourni — démarrer le chronomètre

```python
started = perf_counter()
```

Chaque branche calcule ensuite `perf_counter() - started`.

### Ligne à compléter 4.1 — Autoriser l'outil

```python
try:
    tool = registry.authorize(action.tool)
except ToolNotAllowedError as exc:
    return Observation(
        tool=action.tool,
        status="unauthorized",
        latency_seconds=perf_counter() - started,
        error=str(exc),
    )
```

Seul le nom de la méthode après `registry.` est à compléter dans le fichier
Python. Le reste de cette branche est fourni. Le `return` empêche l'exécution
de continuer sans outil autorisé.

### Ligne à compléter 4.2 — Appeler le véritable backend

Dans le second `try` déjà fourni, complétez le nom de la fonction portée par
`SearchTool` :

```python
try:
    raw_papers = tool.search(
        action.query or "",
        action.limit or 1,
    )
```

En mode réel, `tool.search` désigne `openalex_search`, `crossref_search` ou
`semantic_scholar_search`. Le TODO 1 garantit normalement la présence de la
requête et de la limite ; les valeurs de secours satisfont également le typage
Python.

### Code fourni — normaliser toute la liste

`raw_papers` est une liste de dictionnaires. Le code fourni transforme chaque
dictionnaire :

```python
papers = [
    PaperRecord(source=tool.name, **raw_paper)
    for raw_paper in raw_papers
]
```

La variable `raw_paper` n'existe que dans cette compréhension de liste.
L'expression `PaperRecord(source=tool.name, **raw_paper)` ne doit donc pas être
écrite seule avant la boucle.

### Code fourni — retourner `success` ou `empty`

Toujours dans le second `try` :

```python
return Observation(
    tool=tool.name,
    status="success" if papers else "empty",
    count=len(papers),
    latency_seconds=perf_counter() - started,
    papers=papers,
)
```

Une liste vide n'est pas une exception : l'outil a répondu, mais n'a trouvé
aucun article.

### Code fourni — convertir les erreurs de statut HTTP

```python
except httpx.HTTPStatusError as exc:
    status_code = exc.response.status_code
    return Observation(
        tool=tool.name,
        status="rate_limited" if status_code == 429 else "http_error",
        latency_seconds=perf_counter() - started,
        error=f"HTTP {status_code}",
    )
```

### Code fourni — convertir les autres erreurs réseau

```python
except httpx.HTTPError as exc:
    return Observation(
        tool=tool.name,
        status="network_error",
        latency_seconds=perf_counter() - started,
        error=str(exc),
    )
```

Placez `HTTPStatusError` avant `HTTPError`, car le premier est un cas plus
précis du second. N'utilisez pas `except Exception`, qui masquerait vos erreurs
de programmation.

### Algorithme à obtenir

```text
chronométrer
essayer d'autoriser l'outil
    si refus : retourner unauthorized
essayer d'appeler tool.search
    normaliser tous les articles
    retourner success ou empty
si statut HTTP incorrect
    retourner rate_limited ou http_error
si autre erreur HTTP/réseau
    retourner network_error
```

### Vérification progressive

```bash
python -m pytest -v -k "todo_4_execution_distingue"
python -m pytest -v -k "todo_4_execution_transforme_http_429"
python -m pytest -v -k "todo_4"
```

Les deux tests doivent passer.

### Erreurs fréquentes

- `tool is not defined` : `registry.authorize()` n'a pas été appelé avant
  `tool.search()` ;
- `raw_paper is not defined` : la compréhension de liste manque ;
- la fonction retourne `None` : une branche ne contient pas de
  `return Observation(...)` ;
- le statut 429 est calculé mais le test échoue : vous n'avez pas retourné
  l'observation ;
- toutes les erreurs deviennent `network_error` : les deux `except` sont dans
  le mauvais ordre.

---

## TODO 5 — Mettre à jour `SearchState`

**Fichier :** `slrresearch/runtime.py`  
**Fonction :** `update_state()`

Une observation n'est utile à ReAct que si elle modifie un état persistant.

### Champs à mettre à jour

```text
step              +1 à chaque observation
actions_executed  action valide, si elle existe
observations      observation reçue
trace             couple action–observation numéroté
errors            message si observation.error existe
papers            articles uniques accumulés
```

### Déduplication

La déduplication, la mémorisation des erreurs et l'incrément de `step` sont
fournis. Vous devez seulement matérialiser la ligne du slide :

```text
state.add(action, observation)
```

Dans notre modèle, cette idée correspond à deux listes distinctes.

### Travail étudiant — seulement deux noms de champs

Complétez uniquement :

```python
# Mémoriser ce que la dernière action a appris.
state.________________.append(observation)

# Mémoriser le couple action-observation dans l'historique numéroté.
state.________________.append(
    TraceEvent(
        step=state.step,
        action=action_dump,
        observation=observation,
    )
)
```

Cherchez les noms exacts dans la classe `SearchState` de `contracts.py`. Ne
réécrivez ni la déduplication ni la gestion des erreurs : elles sont déjà dans
le squelette.

```bash
python -m pytest -v -k "todo_5"
```

### Point d'exécution A

À ce stade, vous avez le cadre sécurisé, mais aucune politique de parcours.
Vérifiez :

```bash
python -m pytest -v -k "todo_1 or todo_2 or todo_3 or todo_4 or todo_5"
```

---

# Partie C — Construire la baseline déterministe

## TODO 6 — Implémenter le workflow outillé

**Fichier :** `slrresearch/workflow.py`  
**Fonction :** `run_tool_workflow()`

Ici, le programme choisit les actions. Pour chaque entrée de `queries`, il
construit une action `search`, exécute l'outil puis met l'état à jour.

### Étapes

1. créer `SearchState(objective=objective, queries=queries)` ;
2. parcourir `queries.items()` ;
3. créer `AgentAction(action="search", ...)` ;
4. appeler `execute_authorized_action()` ;
5. appeler `update_state()` ;
6. après la boucle, positionner `finished=True` ;
7. positionner `stop_reason="workflow_complete"` ;
8. retourner l'état.

### Squelette

```python
state = SearchState(objective=objective, queries=queries)

for tool_name, query in queries.________():
    action = AgentAction(
        action="search",
        tool=________,
        query=________,
        limit=limit,
    )
    observation = ______________________________
    ______________________________

state.finished = ________
state.stop_reason = "________________"
return state
```

Le workflow doit continuer après un HTTP 429 puisque l'erreur est devenue une
observation.

```bash
python -m pytest -v -k "todo_6"
python main.py
```

Dans la Version A, vérifiez que les trois outils sont visités dans l'ordre des
requêtes, même si le premier échoue.

---

# Partie D — Demander une décision sans céder l'exécution

## TODO 7 — Construire la politique de décision LLM

Ce TODO relie le modèle de langage à la boucle sans lui donner directement le
droit d'exécuter un outil. Le prompt complet est fourni ; l'étudiant écrit
seulement l'appel LLM et l'extraction de sa décision.

### Code fourni — construire le prompt de décision

**Fichier :** `slrresearch/policies.py`  
**Fonction :** `build_decision_prompt()`

Le prompt ne doit pas recevoir automatiquement tout l'objet `SearchState`.
`state_for_decision()` produit une projection contenant seulement les éléments
utiles : objectif, requêtes, nombre d'articles, outils déjà appelés, dernière
observation et numéro d'étape.

Le prompt fourni inclut :

- l'objectif ;
- la projection JSON de l'état ;
- la liste des outils autorisés ;
- un exemple JSON `search` ;
- un exemple JSON `finish` ;
- la règle d'adaptation après une erreur ou un résultat vide ;
- l'interdiction d'exécuter directement un outil ;
- l'interdiction d'ajouter du Markdown ou une explication.

Il utilise :

```python
json.dumps(state_for_decision(state), ensure_ascii=False, indent=2)
json.dumps(allowed_tools, ensure_ascii=False)
```

### Travail étudiant — deux lignes dans `LLMDecisionPolicy`

**Classe :** `LLMDecisionPolicy`  
**Méthode :** `__call__()`

Cette méthode doit uniquement :

1. appeler la méthode `invoke` du modèle avec le prompt fourni ;
2. transmettre `response.content` à `extract_json_object()`.

```python
response = self.model.________________(
    build_decision_prompt(state, allowed_tools)
)
return ______________________________(str(response.content))
```

Les deux éléments à écrire sont donc `invoke` et le nom de la fonction
d'extraction déjà définie juste au-dessus.

Cette écriture matérialise la ligne du slide :

```python
action = llm_decide(state, tools)
```

Dans le projet, `LLMDecisionPolicy` joue le rôle de `llm_decide` : elle reçoit
l'état et les outils autorisés, appelle le LLM, puis retourne une proposition
d'action sans l'exécuter.

La validation `AgentAction` sera effectuée par le runtime, pas par la politique.

```bash
python -m pytest -v -k "todo_7"
```

---

# Partie E — Assembler la boucle ReAct

## TODO 8 — Compléter la boucle ReAct contrôlée

**Fichier :** `slrresearch/react_agent.py`  
**Fonction :** `run_react_agent()`

Le squelette complet, les erreurs, les conditions d'arrêt et la mise à jour des
statuts sont fournis. Vous complétez uniquement les cinq opérations centrales
du schéma présenté en cours :

```text
DÉCIDER → VALIDER → FINISH ? → AGIR → OBSERVER
```

### Travail étudiant — cinq blancs seulement

Dans `slrresearch/react_agent.py`, complétez :

```python
# 1. Décider
raw_action = __________________(state, registry.names)

# 2. Valider
action = AgentAction.________________(raw_action)

# 3. Reconnaître l'arrêt demandé par le décideur
if action.action == "________________":
    ...  # traitement fourni

# 4. Agir à travers la frontière contrôlée
observation = __________________(action, registry)

# 5. Observer et mettre l'état à jour
__________________(state, action, observation)
```

Les cinq réponses sont toutes des fonctions ou valeurs déjà utilisées dans les
TODO précédents. Vous ne devez écrire ni nouveau `try/except`, ni nouvelle
condition d'arrêt, ni logique de déduplication.

### Invariants obligatoires

Votre boucle doit garantir simultanément que :

1. le décideur reçoit l'état courant et `registry.names` ;
2. toute proposition passe par `AgentAction.model_validate()` ;
3. une action invalide devient une observation `invalid_action` ;
4. `finish` arrête sans appeler d'outil ;
5. `search` passe toujours par `execute_authorized_action()` ;
6. toute observation passe par `update_state()` ;
7. atteindre `target_papers` arrête immédiatement ;
8. l'absence de `finish` ne permet jamais de dépasser `max_steps` ;
9. une erreur 429, un outil interdit ou une action invalide n'arrête pas
   automatiquement la boucle ;
10. `stop_reason` indique exactement la cause de l'arrêt.

### Valeurs de `stop_reason`

| Cause | Valeur |
|---|---|
| le décideur propose `finish` | `agent_finish` |
| assez d'articles uniques | `target_reached` |
| budget d'étapes épuisé | `max_steps` |

### Code fourni — Initialiser l'état

Créez un `SearchState` avec l'objectif et les requêtes. Ne stockez pas l'état
dans une variable globale.

### Code fourni — Borner la boucle

Utilisez une boucle qui ne peut exécuter que `max_steps` tours. Une boucle
`while True` est interdite.

### Blancs 8.1 et 8.2 — Décider puis valider

À chaque tour :

```text
raw_action = decide(état courant, outils autorisés)
                    ↓
AgentAction.model_validate(raw_action)
```

Le `try/except` est fourni. En cas d'échec, il construit automatiquement :

```python
Observation(
    status="invalid_action",
    error=str(exc),
    raw_action=...,
)
```

L'appel `update_state()` avec `action=None` et le passage au tour suivant sont
également fournis.

### Blanc 8.3 — Reconnaître `finish`

Complétez uniquement la chaîne comparée à `action.action`. Le traitement
suivant est fourni :

- ajoutez-la à `actions_executed` ;
- incrémentez `step` ;
- positionnez `finished=True` ;
- choisissez la bonne raison d'arrêt ;
- retournez immédiatement l'état ;
- n'appelez ni le registre ni `update_state()` puisqu'il n'existe aucune
  observation d'outil.

### Blancs 8.4 et 8.5 — Exécuter et observer

Pour une action `search`, complétez les noms des deux fonctions déjà réalisées :

1. appelez `execute_authorized_action(action, registry)` ;
2. appelez `update_state(state, action, observation)` ;
Le test `len(state.papers) >= target_papers` et l'arrêt correspondant sont
fournis.

### Code fourni — Fermer la boucle

Si la boucle se termine sans `finish` et sans atteindre la cible, le squelette :

- positionnez `finished=True` ;
- utilisez la raison indiquant l'épuisement du budget ;
- retournez l'état.

### Pseudocode global

```text
créer state

pour au maximum max_steps tours :
    demander raw_action

    essayer de construire AgentAction
    si validation impossible :
        créer observation invalid_action
        mettre state à jour
        continuer

    si action == finish :
        enregistrer l'arrêt
        retourner state

    observation = contrôler et exécuter search
    mettre state à jour

    si cible atteinte :
        enregistrer l'arrêt
        retourner state

enregistrer max_steps
retourner state
```

### Tests progressifs du TODO 8

```bash
python -m pytest -v -k "todo_8_finish"
python -m pytest -v -k "todo_8_observation_429"
python -m pytest -v -k "todo_8_action_invalide"
python -m pytest -v -k "todo_8_outil_interdit"
python -m pytest -v -k "todo_8_target_reached"
python -m pytest -v -k "todo_8_max_steps"
```

Puis :

```bash
python -m pytest -v -k "todo_8"
```

### Scénario clé

Le test adaptatif impose cette trajectoire :

```text
1. search(openalex)
2. Observation(status="rate_limited")
3. search(crossref)
4. Observation(status="success")
5. finish
```

Le workflow A appelle simplement toutes les sources. L'agent B reçoit
l'observation 429 avant que la politique ne propose l'action suivante.

### Pourquoi la politique reproductible et le LLM peuvent-ils s'arrêter différemment ?

Les deux modes de la Version B utilisent exactement la même boucle ReAct, le
même état et les mêmes outils. **Seule la politique qui propose la prochaine
action change.**

| Mode | Choix de l'action suivante | Condition d'arrêt observée dans ce TD |
|---|---|---|
| Version A — workflow | ordre fixé dans le code | toutes les sources sont appelées |
| Version B — politique reproductible | règles Python de `build_demo_policy()` | succès d'OpenAlex, ou tentative de Crossref après l'échec d'OpenAlex |
| Version B — LLM réel | interprétation du prompt à partir de l'état | le LLM peut estimer qu'une autre source reste utile avant `finish` |

Dans le scénario HTTP 429, la politique reproductible suit volontairement :

```text
OpenAlex (429) → Crossref (succès) → finish
```

Elle n'appelle donc pas Semantic Scholar. Le LLM réel peut, lui, proposer
Semantic Scholar après Crossref, car le prompt lui demande de terminer quand
il dispose d'« assez d'articles ». Ce critère est ambigu : le LLM peut juger
qu'une seule source réussie ne donne pas encore une couverture suffisante.

Cette différence ne prouve pas que le LLM possède une meilleure stratégie. La
boucle ReAct exécute la politique qu'elle reçoit. Dans une véritable SLR, une
condition aussi importante doit être mesurable et reproductible. Une politique
hybride pourrait, par exemple, n'autoriser `finish` que si :

- au moins deux sources ont répondu avec succès ;
- ou toutes les sources autorisées ont été essayées ;
- tandis que `max_steps` conserve son rôle de garde-fou ultime.

Le LLM peut alors proposer l'ordre des outils, mais le programme garde le
contrôle de la couverture minimale.

---

## 6. Validation finale

```bash
python -m pytest -v
python main.py
python -m streamlit run streamlit_app.py
```

Résultat attendu :

```text
23 passed
```

Dans Streamlit :

1. gardez le scénario `OpenAlex répond HTTP 429` ;
2. exécutez la Version A ;
3. exécutez la Version B en politique reproductible ;
4. comparez les traces ;
5. vérifiez qui choisit l'action suivante ;
6. seulement ensuite, essayez le mode LLM réel configuré dans `.env`.

## 7. Questions d'interprétation

1. Où la décision de l'outil est-elle prise dans la Version A ?
2. Où est-elle prise dans la Version B ?
3. Pourquoi `AgentAction` ne doit-elle pas exécuter elle-même l'outil ?
4. Pourquoi Pydantic ne remplace-t-il pas `ToolRegistry` ?
5. Quelle différence existe entre une erreur et une observation d'erreur ?
6. Pourquoi un résultat vide doit-il être conservé dans l'état ?
7. Pourquoi l'état complet n'est-il pas automatiquement envoyé au LLM ?
8. Comment un HTTP 429 peut-il modifier la prochaine décision ?
9. Pourquoi `finish` ne produit-il pas une observation d'outil ?
10. Que protège `max_steps` ?
11. Quelle différence existe entre `target_reached` et `agent_finish` ?
12. Pourquoi les tests utilisent-ils `ScriptedPolicy` plutôt qu'un vrai LLM ?
13. La politique reproductible est-elle réellement intelligente ?
14. À partir de quel moment peut-on raisonnablement parler d'agent dans ce TD ?
15. Pourquoi ReAct contrôlé ne signifie-t-il pas autonomie illimitée ?
16. Le LLM appelle Semantic Scholar alors que la politique reproductible peut
    s'arrêter après Crossref. Cette différence prouve-t-elle que le LLM possède
    une meilleure stratégie ? Proposez une condition d'arrêt hybride,
    mesurable et reproductible.
17. Pourquoi les tests des outils réels remplacent-ils `httpx.get`, alors que
    la validation finale dans Streamlit doit appeler les véritables API ?

## 8. Critères de réussite

- les 23 tests passent, dont 3 vérifient le handoff JSON, 2 la présence des
  acquis TD01–TD02 et 2 la configuration des outils réels ;
- les requêtes du TD02 ne sont pas recopiées dans l'agent ;
- le contrat distingue strictement `search` et `finish` ;
- seuls les outils du registre sont exécutables ;
- toute issue externe devient une observation structurée ;
- l'état conserve actions, observations, erreurs et articles uniques ;
- la Version A montre une décision prédéfinie ;
- la Version B montre une décision répétée à partir de l'état ;
- la boucle respecte les trois conditions d'arrêt ;
- l'interface rend la comparaison visible ;
- l'étudiant peut expliquer chaque ligne du TODO 8.
