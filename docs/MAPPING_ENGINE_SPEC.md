# Spécification moteur de mapping MCD-ST

## Statut

Cette spécification formalise les décisions validées par le prototype `prototypes/mapping_poc`.

Le prototype reste volontairement jetable. La décision à conserver est la suivante : le mapping automatisé MCD-ST doit être un moteur traçable de propositions, de revue et de validation, pas une transformation opaque.

## Objectif

Le moteur de mapping transforme des exports hétérogènes issus de logiciels SPSTi en tables MCD-ST v0.1.

Il doit aider plusieurs profils :

- un directeur de SPSTi qui veut comprendre la qualité et la valeur exploitable de ses exports ;
- un data manager qui doit fiabiliser les correspondances champ source vers champ MCD-ST ;
- un épidémiologiste qui veut construire une population source et des variables reproductibles ;
- une équipe de recherche qui veut savoir quelles données existent, lesquelles manquent et quels mappings doivent être validés.

Le moteur doit fonctionner sans IA. Les composants IA ou deep learning sont des assistants de scoring et de suggestion, jamais la source unique de vérité.

## Principes

- Le fichier YAML validé est l'artefact de vérité du mapping.
- Les champs S4 sont détectés tôt et exclus des tables MCD-ST standardisées.
- Une proposition incertaine n'est pas silencieusement appliquée.
- La revue distingue le mapping de colonnes et le mapping de valeurs.
- Chaque décision humaine est versionnée, justifiée et auditable.
- Les données RAW ne sont pas corrigées silencieusement.
- Le moteur doit pouvoir produire un dry-run même si certaines propositions restent en revue, en laissant les champs concernés vides, faux ou non alimentés selon le contrat de table.

## Entrées

### Exports sources

Formats cibles :

- CSV ;
- Excel mono ou multi-onglets ;
- Parquet ;
- dossiers contenant plusieurs fichiers d'un même lot.

Chaque lot source doit être décrit par des métadonnées minimales :

- `source_system` : logiciel ou origine déclarée si connue ;
- `source_version` : version source si connue ;
- `source_kind` : synthétique, test, réel local ;
- `received_at` ;
- `schema_version` cible ;
- empreinte ou hash des fichiers.

### Référentiels

Le moteur consomme :

- le schéma MCD-ST cible ;
- le périmètre de données autorisées et exclues ;
- les vocabulaires et concepts ;
- les synonymes connus ;
- les mappings précédemment validés ;
- les packs source par logiciel lorsqu'ils existent.

## Sorties

Le moteur produit des artefacts séparés.

| Artefact | Rôle |
| --- | --- |
| `profiles.json` | Profilage fichiers, colonnes, types, valeurs, complétude |
| `source_graph.json` | Graphe des exports, noeuds, candidats et règles de jointure |
| `join_candidates.json` | Recouvrements détectés entre colonnes sources |
| `join_rules.json` | Jointures explicites orientées, avec cardinalité et statut de revue |
| `mapping_proposals.json` | Propositions scorées champ source vers champ MCD-ST |
| `value_mappings.json` | Propositions valeur source vers concept standardisé |
| `mapping_propose.yaml` | YAML de mapping proposé, non encore validé |
| `review_queue.yaml` | File de revue humaine colonne et valeur |
| `review_decisions.yaml` | Décisions humaines, commentaires et justification |
| `mapping_valide.yaml` | Mapping validé et versionnable |
| `quality_report_draft.json` | Qualité du dry-run avant revue complète |
| `quality_report_validated.json` | Qualité après application des décisions |
| tables MCD-ST | Tables standardisées de dry-run ou de lot validé |

Les noms exacts pourront évoluer, mais la séparation des responsabilités doit rester stable.

## Pipeline

### 1. Ingestion et empreinte

Le moteur recense les fichiers, calcule une empreinte et crée une entrée de provenance.

Il ne modifie pas les fichiers RAW.

### 2. Profilage

Pour chaque colonne :

- nom source ;
- type inféré ;
- taux de valeurs manquantes ;
- nombre de valeurs distinctes ;
- exemples limités ;
- patterns détectés ;
- cardinalité ;
- rôle probable : identifiant, date, code, libellé, booléen, texte libre.

### 3. Classification de sensibilité

Chaque colonne reçoit un niveau probable `S0` à `S4`.

Les colonnes `S4` ne sont pas proposées vers une table MCD-ST standardisée. Elles peuvent seulement recevoir une action explicite :

- exclusion ;
- conservation stricte en RAW local ;
- masquage ;
- pseudonymisation locale si le champ sert uniquement de clé technique ;
- revue DPO ou référent habilité.

### 4. Graphe des sources

Le moteur détecte les relations probables entre exports :

- colonnes aux mêmes valeurs ;
- clés primaires candidates ;
- clés étrangères candidates ;
- cardinalités 1-1, 1-n, n-n ;
- cohérence entre fichiers individu, entreprise, visite, exposition.

Ce graphe évite de mapper chaque fichier isolément et prépare les entités alimentées par plusieurs sources.

Le MVP distingue deux niveaux :

- `join_candidates` : recouvrements de valeurs détectés automatiquement ;
- `join_rules` : règles orientées avec source primaire, source étrangère, cardinalité estimée et statut de revue.

Une jointure entre deux sources événementielles qui partagent seulement une clé travailleur doit rester en revue, même si le recouvrement technique est parfait.

### 5. Inférence des entités

Chaque fichier, onglet ou sous-ensemble est rapproché d'entités MCD-ST probables :

- `travailleur` ;
- `entreprise` ;
- `etablissement` ;
- `unite_travail` ;
- `episode_poste` ;
- `visite_sante_travail` ;
- `conclusion_medicale` ;
- `exposition_professionnelle` ;
- `action_prevention` ;
- `evenement_pdp`.

Le moteur peut choisir une source principale par entité pour le MVP. Les entités multi-sources nécessitent ensuite des jointures explicites.

### 6. Mapping de colonnes

Le score de mapping combine plusieurs signaux :

- similarité de nom ;
- synonymes métier ;
- compatibilité de type ;
- distribution des valeurs ;
- contexte de l'entité source ;
- présence dans le graphe de jointures ;
- mappings précédemment validés ;
- signaux IA optionnels.

Statuts attendus :

- `proposed` : proposition générée ;
- `auto_validable` : proposition robuste, non sensible et sans ambiguïté majeure ;
- `needs_review` : proposition plausible mais à valider ;
- `blocked_s4` : champ exclu du MCD standardisé ;
- `rejected` : proposition écartée ;
- `validated` : décision humaine ou règle validée ;
- `validated_by_pack` : décision issue d'un pack source versionné ;
- `validated_by_human_review` : décision issue de la file de revue.

Règles MVP :

- un champ cible ne doit pas recevoir deux sources concurrentes sans règle explicite ;
- un champ source peut alimenter plusieurs champs cibles seulement si la transformation est déclarée ;
- les champs interprétatifs S3, comme restriction ou aménagement, doivent passer en revue si le libellé source est ambigu ;
- les champs S4 sont bloqués avant score de mapping cible.

### 7. Mapping de valeurs

Le mapping de valeurs rapproche les libellés locaux de concepts standardisés.

Exemples :

- `VIP periodique` vers un concept de type de visite ;
- `apte avec reserve` vers un concept de conclusion ;
- `bruit` vers un concept d'exposition ;
- `occasionnelle` vers une fréquence d'exposition.

Ce niveau a sa propre revue. Un mapping de colonne peut être validé alors que certaines valeurs restent inconnues.

Statuts attendus :

- `known` ;
- `suggested` ;
- `needs_domain_review` ;
- `accepted` ;
- `rejected` ;
- `deprecated`.

Les valeurs critiques inconnues peuvent bloquer certains exports analytiques, même si le dry-run technique reste possible.

### 8. Génération du YAML proposé

Le YAML proposé doit être lisible et éditable par un data manager.

Structure cible indicative :

```yaml
mapping_id: exemple_logiciel_x_v0
schema_version: mcdst-v0.1
source_system: logiciel_x
status: proposed

entities:
  travailleur:
    source: export_01_individus.csv
    primary_key:
      source_field: ClePers
      transform: hash_local
    fields:
      travailleur_id:
        source_field: ClePers
        transform: hash_local
        confidence: 0.98
        review_status: auto_validable
      annee_naissance:
        source_field: AnNaiss
        confidence: 0.93
        review_status: auto_validable

excluded_fields:
  - source: export_01_individus.csv
    field: NomUsuel
    reason: direct_identifier_s4
```

Le YAML validé doit inclure la version, le statut, la date de validation, la source des décisions et les commentaires utiles.

### 9. File de revue

La revue doit être orientée action.

Une entrée de revue doit contenir :

- identifiant stable ;
- type : `column_mapping` ou `value_mapping` ;
- fichier source ;
- champ source ;
- entité cible ;
- champ ou concept cible proposé ;
- score ;
- raisons du score ;
- exemples de valeurs ;
- niveau de sensibilité ;
- décision attendue ;
- commentaire obligatoire pour les mappings sensibles.

Décisions possibles :

- accepter ;
- rejeter ;
- corriger la cible ;
- demander une règle de transformation ;
- exclure ;
- escalader DPO ou référent métier ;
- reporter.

### 10. Application des décisions

Les décisions humaines génèrent un `mapping_valide.yaml`.

Un mapping validé devient immuable. Toute modification ultérieure doit créer une nouvelle version.

### 11. Mémoire locale

Le moteur peut écrire les décisions de revue validées dans un registre local, par exemple `mapping_registry.yaml`.

Cette mémoire sert à réduire la revue répétitive :

- une validation humaine de colonne peut devenir une règle `validated_by_registry` lors d'un prochain lot du même `source_system` ;
- la mémoire reste déterministe, lisible et désactivable ;
- elle ne remplace pas le `mapping_valide.yaml`, qui reste l'artefact de vérité ;
- elle ne doit pas apprendre automatiquement des champs S4 ni des décisions médicales.

### 12. Dry-run et qualité

Le dry-run applique le mapping sur les exports sources et produit les tables MCD-ST.

Le rapport qualité vérifie au minimum :

- complétude des champs obligatoires ;
- unicité des identifiants ;
- cohérence des jointures ;
- cohérence temporelle ;
- valeurs hors nomenclature ;
- champs S4 exclus ;
- mappings en revue ;
- pertes de lignes entre source et cible ;
- taux de concepts inconnus.

## Packs source

Un pack source représente la connaissance réutilisable d'un logiciel ou d'une famille d'exports.

Il peut contenir :

- dictionnaire des fichiers habituels ;
- synonymes de colonnes ;
- transformations connues ;
- mappings validés ;
- valeurs locales vers concepts ;
- règles qualité spécifiques ;
- versions compatibles du logiciel.

Un pack source ne doit pas écraser une décision locale validée sans revue.

## Place de l'IA

L'IA peut enrichir :

- le rapprochement entre noms de colonnes ;
- le rapprochement entre valeurs locales et concepts ;
- l'identification des entités métier ;
- l'explication courte d'une proposition ;
- la priorisation de la file de revue ;
- la suggestion de données nécessaires pour une cohorte.

Elle ne doit pas :

- valider seule un champ S3 interprétatif ;
- mapper un champ S4 vers le MCD standardisé ;
- produire une décision médicale ;
- écraser un mapping humain validé ;
- rendre le pipeline dépendant d'un service externe obligatoire.

Le premier petit modèle de domaine doit être entraîné ou ajusté sur des mappings validés, des jeux synthétiques annotés, des vocabulaires et des synonymes, pas sur des données personnelles réelles sans cadre séparé.

## Critères d'acceptation MVP

Le moteur de mapping MVP est considéré acceptable si :

- il lit un dossier d'exports synthétiques multi-fichiers CSV ou Excel multi-onglets ;
- il accepte les CSV UTF-8 et les exports Windows-1252/latin-1 courants ;
- il produit `profiles.json`, `source_graph.json`, `join_candidates.json`, `join_rules.json`, `mapping_propose.yaml`, `review_queue.yaml`, `mapping_valide.yaml` et optionnellement `mapping_registry.yaml` ;
- il bloque les champs S4 avant génération des tables MCD-ST ;
- il sépare revue de colonnes et revue de valeurs ;
- il applique les décisions de revue sur les valeurs de nomenclature ;
- il génère au moins les tables `travailleur`, `entreprise`, `etablissement`, `unite_travail`, `episode_poste`, `visite_sante_travail`, `conclusion_medicale`, `exposition_professionnelle`, `examen_complementaire`, `pathologie_atmp`, `arret_travail`, `vaccination` et `risque_unite_travail` en dry-run ;
- il signale les valeurs inconnues de nomenclature ;
- il produit un rapport qualité avant et après revue ;
- il peut fonctionner sans composant IA ;
- il peut entraîner un premier assistant local sur les mappings revus et produire des suggestions de colonnes auditables ;
- il expose une commande CLI stable et une première API locale avant intégration web.

Commande cible :

```bash
mcdst mapping propose ./exports --schema mcdst-v0.1 --out ./work --registry ./work/mapping_registry.yaml
mcdst mapping review ./work/review_decisions.yaml --workdir ./work --registry ./work/mapping_registry.yaml
mcdst mapping propose ./exports --schema mcdst-v0.1 --out ./work2 --registry ./work/mapping_registry.yaml
mcdst mapping apply ./work/mapping_valide.yaml --exports ./exports --out ./mcdst_tables
mcdst cohort evaluate ./cohort.yaml --tables ./mcdst_tables --out ./cohort_report.json
mcdst learning dataset --workdir ./work --out ./training/mapping_dataset.jsonl
mcdst learning train --dataset ./training/mapping_dataset.jsonl --out ./training/column_model.json
mcdst learning evaluate --dataset ./training/mapping_dataset.jsonl --model ./training/column_model.json
mcdst learning suggest --workdir ./work --model ./training/column_model.json --out ./training/mapping_suggestions.json
mcdst mapping propose ./exports --schema mcdst-v0.1 --out ./work_model --registry ./work/mapping_registry.yaml --learning-model ./training/column_model.json
mcdst serve --host 127.0.0.1 --port 8765
```

La première implémentation est disponible dans `src/mcdst`. Tant que le paquet n'est pas installé dans l'environnement courant, les commandes peuvent être lancées avec :

```bash
PYTHONPATH=src python3 -m mcdst.cli mapping propose ./exports --schema mcdst-v0.1 --out ./work --registry ./work/mapping_registry.yaml
PYTHONPATH=src python3 -m mcdst.cli mapping review ./work/review_decisions.yaml --workdir ./work --registry ./work/mapping_registry.yaml
PYTHONPATH=src python3 -m mcdst.cli mapping apply ./work/mapping_valide.yaml --exports ./exports --out ./mcdst_tables
PYTHONPATH=src python3 -m mcdst.cli serve --host 127.0.0.1 --port 8765
```

Pour tester les formats Excel, installer les dépendances du paquet :

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
```

## Prochaine industrialisation

Le prototype doit être absorbé en plusieurs morceaux :

1. module de profilage ;
2. module de classification de sensibilité ;
3. module de graphe des sources ;
4. module de scoring colonne ;
5. module de mapping de valeurs ;
6. contrat YAML ;
7. file de revue ;
8. dry-run MCD-ST ;
9. rapport qualité ;
10. commandes CLI.

Le code du prototype ne doit pas être promu tel quel en production. Il sert de comportement de référence pour écrire les premiers tests d'acceptation.
