# Spécification cohorting MCD-ST

## Statut

Le moteur de cohorting v0.1 filtre une population sur des critères statiques :
âge, territoire, exposition, type de visite, conclusion médicale ou indicateurs
booléens.

La tranche v0.2 ajoute un premier contrat longitudinal. Il permet d'exprimer des
événements datés et des séquences temporelles simples sans écrire de SQL.

## Principe

Une cohorte longitudinale sépare trois niveaux :

1. `population` : critères généraux appliqués à la population source.
2. `longitudinal.events` : événements datés extraits des tables MCD-ST.
3. `longitudinal.sequences` : ordre temporel attendu entre deux événements.

Le moteur reste déterministe. Il ne décide pas médicalement ; il applique une
définition YAML versionnable et produit un rapport de comptage par étape.

## Exemple v0.2

```yaml
name: manutention_avant_restriction_2024
reference_year: 2026
population:
  min_age: 45
longitudinal:
  events:
    exposition_manutention:
      table: exposition_professionnelle
      date_field: date_debut
      filters:
        exposition_concept_id:
          any:
            - MANUTENTION_MANUELLE
    restriction_medicale:
      table: conclusion_medicale
      date_field: visite_sante_travail.date_visite
      filters:
        restriction_flag: true
  sequences:
    - id: exposition_before_restriction
      label: Exposition manutention avant restriction médicale
      first: exposition_manutention
      then: restriction_medicale
      relation: before
      min_days: 0
```

## Tables Supportées

Le moteur sait dater directement :

- `visite_sante_travail` par `date_visite` ;
- `exposition_professionnelle` par `date_debut` ;
- `examen_complementaire` par `date_examen` ;
- `pathologie_atmp` par `date_evenement` ;
- `arret_travail` par `date_debut` ;
- `vaccination` par `date_vaccination`.

Pour `conclusion_medicale`, la date et le travailleur sont récupérés via
`visite_sante_travail`, car la conclusion est rattachée à une visite.

## Relations Temporelles

Relations disponibles en v0.2 :

- `before` : le premier événement est antérieur ou égal au second ;
- `strictly_before` : le premier événement est strictement antérieur ;
- `same_day` : les deux événements sont le même jour ;
- `after` : le premier événement est postérieur ou égal au second.

Les bornes `min_days` et `max_days` limitent l'écart entre les deux événements.

## Sortie

Quand une définition contient `longitudinal.sequences`, le rapport indique :

- `schema_version: mcdst-cohort-v0.2` ;
- `summary.longitudinal_sequences_count` ;
- `feasibility.status` et `feasibility.diagnostics` ;
- `longitudinal.events` avec le nombre d'événements et de travailleurs trouvés ;
- `longitudinal.sequences` avec les paires temporelles trouvées ;
- une étape `longitudinal:<id>` par séquence ;
- `matched_pairs_count`, c'est-à-dire le nombre de couples d'événements trouvés.

La compatibilité v0.1 est conservée pour les cohortes sans bloc longitudinal.

## Diagnostics

Les diagnostics de faisabilité distinguent :

- `missing_table` : table MCD-ST requise absente, bloquant ;
- `missing_field` : champ requis absent, bloquant ;
- `empty_table` : table disponible mais sans ligne, avertissement ;
- `empty_event` : aucun événement ne correspond à une définition, avertissement ;
- `temporal_no_match` : les événements existent mais aucune paire ne respecte la
  relation temporelle, avertissement.

Le statut global est :

- `not_feasible` si un diagnostic bloquant existe ;
- `feasible_empty` si la définition est exécutable mais ne retient aucun
  travailleur ;
- `feasible` si la cohorte est exécutable et retient au moins un travailleur, ou
  si la population source est vide.

## Rapport HTML

La CLI peut produire un rapport HTML en plus du JSON :

```bash
mcdst cohort evaluate \
  tests/fixtures/cohorts/arret_avant_visite_reprise.yaml \
  --tables work/mapping_fixture/mcdst_tables \
  --out work/mapping_fixture/cohort_report.json \
  --html-out work/mapping_fixture/cohort_report.html
```

Le rapport HTML reprend les métriques, les étapes, les diagnostics, la
disponibilité des tables, les événements longitudinaux, les séquences et les
travailleurs inclus.
