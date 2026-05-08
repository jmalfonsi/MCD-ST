# MCD-ST

MCD-ST est un projet de plateforme open source pour standardiser, qualifier, explorer et réutiliser les données issues des Services de Prévention et de Santé au Travail Interentreprises.

Le projet part d'un principe simple : les données santé-travail ont une forte valeur de pilotage, de prévention et de recherche, mais elles sont souvent enfermées dans des exports hétérogènes, peu documentés et difficiles à comparer. MCD-ST propose un modèle commun de données, un pipeline de transformation, un moteur qualité, un moteur de cohorting et des assistants capables d'aider à comprendre les données disponibles ou à préparer une étude.

## Documents de cadrage

- [Cadrage produit](CADRAGE_PRODUIT.md)
- [Spécification produit](docs/SPEC_PRODUIT.md)
- [Spécification UI web](docs/SPEC_UI_WEB.md)
- [Périmètre des données MCD-ST](docs/PERIMETRE_DONNEES_MCD.md)
- [Schéma MCD-ST v0.1](docs/SCHEMA_MCD_ST_V0_1.md)
- [Domaines métier sensibles intégrés v0.1](docs/EXTENSIONS_MODELE_METIER.md)
- [Spécification moteur de mapping](docs/MAPPING_ENGINE_SPEC.md)
- [Spécification moteur de cohorting](docs/COHORTING_ENGINE_SPEC.md)
- [Roadmap](docs/ROADMAP.md)

## Deux usages fondamentaux

1. Partir d'exports SPSTi et comprendre ce qu'ils contiennent, ce qui est exploitable et ce qui doit être amélioré.
2. Partir d'une question métier ou scientifique et déterminer les données nécessaires, les critères de cohorte et la faisabilité.

## MVP visé

Le MVP doit permettre de :

- profiler des exports CSV ou Excel ;
- proposer un mapping vers un modèle commun ;
- générer une file de revue pour les mappings incertains et les valeurs métier ;
- générer des tables MCD-ST standardisées ;
- produire un rapport qualité ;
- définir une cohorte en YAML ;
- piloter ces étapes dans une interface web avec suivi ETL temps réel ;
- modifier et valider les fichiers YAML depuis le web ;
- administrer les mappings, sources, vocabulaires, règles et cohortes ;
- générer un rapport de faisabilité ou un diagramme de flux ;
- fonctionner sur données synthétiques sans données personnelles réelles.

## Première CLI moteur

Une première tranche du moteur de mapping existe dans `src/mcdst`.

Installation locale recommandée :

```bash
python3 -m venv .env
.env/bin/python -m pip install -e '.[dev]'
```

Le prototype bavard peut toujours être relancé pour démonstration :

```bash
python3 prototypes/mapping_poc/mapping_poc.py
```

Le scénario d'acceptation stable utilise les fixtures versionnées :

```bash
.env/bin/mcdst mapping propose \
  tests/fixtures/mapping_poc_exports \
  --out work/mapping_fixture \
  --source-system POC_SPSTI_MULTI_EXPORT \
  --registry work/mapping_registry.yaml

.env/bin/mcdst mapping review \
  tests/fixtures/mapping_poc_review_decisions.yaml \
  --workdir work/mapping_fixture \
  --registry work/mapping_registry.yaml

.env/bin/mcdst mapping apply \
  work/mapping_fixture/mapping_valide.yaml \
  --exports tests/fixtures/mapping_poc_exports \
  --out work/mapping_fixture/mcdst_tables
```

Le comportement est couvert par un premier test d'acceptation :

```bash
.env/bin/python -m pytest -q
```

## Première cohorte YAML

Une première tranche de cohorting évalue une définition YAML sur les tables
MCD-ST générées et produit un rapport JSON avec les comptages par étape :

```bash
.env/bin/mcdst cohort evaluate \
  tests/fixtures/cohorts/travailleurs_45_plus_manutention.yaml \
  --tables work/mapping_fixture/mcdst_tables \
  --out work/mapping_fixture/cohort_report.json
```

Une première extension longitudinale v0.2 permet aussi d'exprimer un ordre entre
événements, par exemple une exposition qui précède une restriction médicale :

```bash
.env/bin/mcdst cohort evaluate \
  tests/fixtures/cohorts/manutention_avant_restriction.yaml \
  --tables work/mapping_fixture/mcdst_tables \
  --out work/mapping_fixture/cohort_report_v02.json
```

## Dataset d'apprentissage mapping

Les artefacts validés peuvent alimenter un dataset JSONL local pour entraîner le
petit assistant de mapping :

```bash
.env/bin/mcdst learning dataset \
  --workdir work/mapping_fixture \
  --out work/training/mapping_dataset.jsonl
```

Le dataset contient des exemples positifs de mapping de colonnes, des mappings
de valeurs vers concepts, et des exemples `blocked_s4` à ne jamais mapper vers
le MCD-ST standardisé.

Un premier modèle local, en pur Python, peut être entraîné et évalué sur ce
dataset :

```bash
.env/bin/mcdst learning train \
  --dataset work/training/mapping_dataset.jsonl \
  --out work/training/column_model.json

.env/bin/mcdst learning evaluate \
  --dataset work/training/mapping_dataset.jsonl \
  --model work/training/column_model.json

.env/bin/mcdst learning suggest \
  --workdir work/mapping_fixture \
  --model work/training/column_model.json \
  --out work/training/mapping_suggestions.json
```

Le fichier `mapping_suggestions.json` sert de sortie de travail : il liste les
cibles probables par colonne, les scores du modèle et les colonnes bloquées par
la garde `S4`. Par défaut, seules les suggestions fortes sont conservées
(`--min-score 0.65`).

Une fois le modèle disponible, `mapping propose` peut générer ces suggestions
dans le même workdir :

```bash
.env/bin/mcdst mapping propose \
  tests/fixtures/mapping_poc_exports \
  --out work/mapping_fixture_with_model \
  --source-system POC_SPSTI_MULTI_EXPORT \
  --registry work/mapping_registry.yaml \
  --learning-model work/training/column_model.json
```

## Mémoire locale

Quand un registre est fourni, les validations humaines alimentent une mémoire déterministe :

```text
work/mapping_registry.yaml
```

Au prochain `mapping propose`, les colonnes déjà validées pour le même `source_system` peuvent être proposées en `validated_by_registry` au lieu de revenir dans la file de revue.

## API locale

Une première interface web locale expose le même flux :

```bash
.env/bin/mcdst serve --host 127.0.0.1 --port 8765
```

Puis ouvrir :

```text
http://127.0.0.1:8765/
```

Endpoints disponibles :

- `GET /health`
- `GET /`
- `GET /api/artifact?path=...`
- `POST /api/artifact`
- `POST /api/mapping/propose`
- `GET /api/mapping/review-queue?workdir=...`
- `POST /api/mapping/review`
- `POST /api/mapping/apply`
- `POST /api/cohort/evaluate`
