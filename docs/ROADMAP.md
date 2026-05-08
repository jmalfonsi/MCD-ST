# Roadmap MCD-ST

## Étape 0 - Stabilisation produit

Objectif : transformer le cahier des charges initial en référentiel projet.

Livrables :

- cadrage produit ;
- spécification produit ;
- périmètre des données MCD-ST ;
- schéma MCD-ST v0.1 ;
- spécification du moteur de mapping ;
- roadmap ;
- décisions ouvertes.

Critère de sortie :

- le périmètre MVP est compréhensible sans relire le dossier initial.

## Étape 1 - Socle technique et web MVP

Objectif : créer un socle exécutable localement et pilotable depuis le web.

Livrables :

- structure de dépôt Python ;
- CLI `mcdst` pour automatisation ;
- application web minimale ;
- API locale ou service backend ;
- vue pipeline 30/70 ;
- lecture CSV et Excel ;
- génération de données synthétiques ;
- premiers exports Parquet ou SQL ;
- tests unitaires.

Critère de sortie :

- l'utilisateur peut générer ou charger un jeu synthétique, lancer le profilage et suivre les étapes dans le web.

## Étape 2 - Profilage et inventaire

Objectif : analyser les exports disponibles.

Livrables :

- inventaire des fichiers ;
- profilage des colonnes ;
- détection des types ;
- rapport JSON et HTML ;
- détection de candidats métier.

Critère de sortie :

- un utilisateur peut déposer des exports et obtenir une cartographie lisible.

## Étape 3 - Schéma et mapping

Objectif : transformer les exports vers MCD-ST v0.1.

Livrables :

- dictionnaire de données ;
- classification de sensibilité des champs ;
- moteur de mapping multi-exports ;
- graphe des sources et jointures candidates ;
- fichiers YAML de mapping ;
- file de revue humaine ;
- mapping de valeurs source vers concepts ;
- édition web des mappings YAML ;
- première vue d'administration des mappings ;
- moteur de transformation ;
- table `source_mcdst` ;
- table `anomalie_qualite`.

Critère de sortie :

- un lot synthétique multi-fichiers est transformé en tables MCD-ST validables, avec champs S4 exclus, revue humaine tracée et modification YAML possible dans le web.

## Étape 4 - Qualité

Objectif : rendre les limites des données visibles.

Livrables :

- règles de complétude ;
- règles d'unicité ;
- règles temporelles ;
- règles de nomenclature ;
- rapport qualité HTML/JSON ;
- indicateurs agrégés.
- administration des règles qualité.

Critère de sortie :

- chaque anomalie importante est classée avec une sévérité et une explication.

## Étape 5 - Cohorting et faisabilité

Objectif : permettre la création ou l'évaluation d'une cohorte.

Livrables :

- format YAML de cohorte ;
- moteur de filtrage ;
- séquences longitudinales simples entre événements datés ;
- comptage par étape ;
- diagnostics de faisabilité et rapport HTML ;
- diagramme de flux ;
- assistant de faisabilité ;
- exemple "travailleurs de plus de 45 ans avec IRDP élevé en Auvergne".

Critère de sortie :

- une question de cohorte produit une liste de données nécessaires et une exécution si les données existent.

## Étape 6 - IA assistive

Objectif : réduire l'effort humain de mapping et de normalisation.

Livrables :

- moteur de similarité entre colonnes et champs MCD-ST ;
- rapprochement entre valeurs sources et concepts ;
- scoring de confiance ;
- statut de revue humaine ;
- dataset synthétique annoté ;
- corpus de mappings validés ;
- export JSONL des mappings validés pour apprentissage supervisé ;
- premier baseline local TF-IDF/centroïdes pour le scoring de colonnes ;
- génération de suggestions auditables avec garde S4 depuis `profiles.json` ;
- métriques top-1 et top-3.

Critère de sortie :

- l'assistant propose des mappings traçables sans bloquer le pipeline classique.

## Étape 6 bis - Consolidation des domaines métier sensibles

Objectif : consolider les domaines métier sensibles intégrés en tranche minimale
dès v0.1.

Livrables :

- consolidation `risque_unite_travail` / DUERP ;
- consolidation `arret_travail` pour PDP et visites de reprise ;
- consolidation `examen_complementaire` / biométrie ;
- consolidation `vaccination` ;
- consolidation `pathologie_atmp` ;
- fixtures synthétiques dédiées ;
- règles de sensibilité, qualité et revue humaine par domaine.

Critère de sortie :

- chaque domaine sensible dispose d'une table minimale, d'un vocabulaire ou
  format de valeur, d'un mapping exemple et d'un cas de cohorte ou faisabilité.

## Étape 7 - Visualisation

Objectif : rendre le produit utilisable par plusieurs profils.

Livrables :

- interface web principale en découpage horizontal 30/70 ;
- pipeline ETL temps réel en zone haute ;
- espace de travail contextuel en zone basse ;
- vue direction SPSTi ;
- vue data quality ;
- vue administration ;
- vue cohorte ;
- vue faisabilité ;
- éditeur YAML complet ;
- journal d'audit ;
- gestion des sources, mappings, vocabulaires, règles et cohortes ;
- export de rapports.

Critère de sortie :

- un non-développeur peut piloter le pipeline, comprendre les données disponibles, modifier une configuration validée et explorer les cohortes possibles.

## Décisions ouvertes

- Choix du langage principal : Python probable pour data engineering et écosystème santé/data.
- Stockage local : DuckDB, SQLite, Parquet ou combinaison.
- Format du schéma : YAML, JSON Schema, Pydantic ou SQL migrations.
- Niveau exact de granularité géographique autorisé.
- Seuils d'agrégation pour éviter la réidentification dans les petites entreprises ou petites unités de travail.
- Définition métier et calcul de l'IRDP.
- Liste des nomenclatures de référence à intégrer en V0.1.
- Stratégie de packaging : application web locale, librairie Python, Docker, CLI technique.
- Gouvernance des mappings validés.
- Périmètre MVP de l'administration : mono-utilisateur local ou rôles applicatifs dès le départ.
- Conditions d'utilisation de données réelles pour entraîner le module IA.
- Profondeur exacte de normalisation des domaines sensibles : DUERP, arrêts,
  examens complémentaires, vaccinations, AT/MP.

## État actuel

Le prototype `prototypes/mapping_poc` valide le principe du mapping automatisé sans interface graphique :

- exports synthétiques multi-fichiers ;
- profilage ;
- détection S4 ;
- jointures candidates ;
- propositions de mapping ;
- mapping de valeurs ;
- file de revue ;
- génération `mapping_propose.yaml` puis `mapping_valide.yaml` ;
- dry-run MCD-ST et rapport qualité.

La décision durable est formalisée dans [MAPPING_ENGINE_SPEC.md](MAPPING_ENGINE_SPEC.md).

Une première tranche industrialisée existe dans `src/mcdst` :

- CLI `mcdst mapping propose` ;
- CLI `mcdst mapping review` ;
- CLI `mcdst mapping apply` ;
- CLI `mcdst cohort evaluate` ;
- CLI `mcdst learning dataset/train/evaluate/suggest/predict` ;
- option `mcdst mapping propose --learning-model` pour générer les suggestions avec le mapping ;
- modules de profilage, sensibilité, graphe source, mapping, revue, dry-run et qualité ;
- premier module de cohorte YAML avec comptages par étape, diagnostics, rapport HTML et séquences longitudinales v0.2 ;
- premier modèle local TF-IDF/centroïdes pour assister le mapping de colonnes ;
- tests d'acceptation sur un lot synthétique multi-fichiers ;
- garde-fou de test vérifiant que les identifiants directs synthétiques S4 ne sortent pas dans les tables MCD-ST standardisées ;
- CI GitHub exécutant la suite `pytest` sur Python 3.11 et 3.12.

## Priorité immédiate

La prochaine action concrète est de consolider ce moteur MVP :

1. stabiliser le contrat YAML de mapping proposé et validé ; premier verrou de test ajouté ;
2. ajouter des fixtures de tests versionnées hors dossier `_scratch` ; fait pour le scénario POC multi-fichiers ;
3. gérer les exports Excel et les erreurs d'encodage ; lecture XLSX multi-onglets et CSV `utf-8-sig`/`cp1252`/`latin-1` ajoutée ;
4. renforcer les jointures explicites entre sources ; `source_graph.json` et `join_rules.json` ajoutés avec cardinalité et revue ;
5. exposer ensuite la revue de mapping dans l'interface web ; première API locale et première UI web `propose/review/apply` ajoutées.
6. apprendre des validations humaines ; registre local `mapping_registry.yaml` ajouté pour réutiliser les mappings validés ;
7. produire un dataset puis un premier modèle local de suggestions ; `learning dataset/train/evaluate/suggest` ajoutés ;
8. brancher le modèle sur le flux de proposition ; option CLI/API/web ajoutée.
9. rendre la reproductibilité vérifiable en CI ; workflow GitHub Actions ajouté.
10. renforcer les garde-fous RGPD de fixtures ; test d'exclusion des identifiants directs S4 ajouté.
