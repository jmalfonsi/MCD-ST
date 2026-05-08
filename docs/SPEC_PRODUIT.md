# Spécification produit MCD-ST

## Objectif

MCD-ST est une plateforme de réutilisation des données en santé au travail. Elle doit permettre à un directeur de SPSTi, un épidémiologiste, un data manager ou une équipe de recherche de transformer des exports hétérogènes en données standardisées, contrôlées et exploitables pour le pilotage, la prévention, la recherche ou la constitution de cohortes.

Le produit ne remplace pas les logiciels métiers SPSTi. Il se place après les exports, comme une couche d'analyse, de standardisation, de qualité et de documentation.

L'interface utilisateur principale est une application web. Les moteurs CLI et API sont des surfaces techniques pour l'automatisation, les tests et l'intégration, mais les usages métier doivent se faire dans le web.

## Utilisateurs cibles

### Direction de SPSTi

La direction cherche à comprendre la qualité et la valeur exploitable des données produites par le service.

Attendus :

- inventaire des exports ;
- indicateurs de complétude ;
- alertes sur les données manquantes ou incohérentes ;
- indicateurs agrégés de pilotage ;
- priorités d'amélioration de la qualité des données.

### Épidémiologiste ou biostatisticien

L'épidémiologiste cherche à construire une population source, des variables d'exposition, des critères temporels et des cohortes reproductibles.

Attendus :

- dictionnaire de données ;
- critères de cohorte versionnés ;
- diagramme de flux ;
- exports analytiques ;
- traçabilité des exclusions et des transformations.

### Service de recherche ou institution

L'équipe projet cherche à savoir si une question peut être traitée avec les données disponibles ou quelles données collecter pour la rendre faisable.

Attendus :

- matrice de faisabilité ;
- liste des variables nécessaires ;
- analyse des écarts entre besoin et données disponibles ;
- documentation pour protocole ou comité de pilotage.

## Parcours produit

### Parcours A - Analyser des exports

Entrée : un dossier contenant des fichiers CSV, Excel ou Parquet.

Sorties :

- inventaire des fichiers ;
- profilage des colonnes ;
- détection des objets métier probables ;
- proposition de mapping MCD-ST ;
- rapport qualité ;
- estimation des analyses et cohortes faisables.

Critères d'acceptation MVP :

- le système lit au moins CSV et Excel ;
- chaque fichier reçoit une fiche d'inventaire ;
- chaque colonne reçoit un type inféré et un taux de complétude ;
- les colonnes candidates au modèle MCD-ST sont signalées ;
- les mappings ambigus sont marqués comme nécessitant une revue humaine.

### Parcours B - Concevoir une cohorte

Entrée : une question formulée en langage métier ou un fichier YAML de cohorte.

Exemple :

```yaml
name: travailleurs_45_plus_irdp_auvergne
population:
  min_age: 45
  region: AUVERGNE_RHONE_ALPES
indicators:
  irdp:
    operator: ">="
    threshold: high
```

Sorties :

- variables minimales nécessaires ;
- variables recommandées ;
- tables MCD-ST concernées ;
- contraintes temporelles ;
- définition de cohorte exécutable ;
- points de vigilance qualité et RGPD.

Critères d'acceptation MVP :

- le système produit une liste de données nécessaires ;
- le système distingue données obligatoires, recommandées et optionnelles ;
- le système indique si les données chargées permettent ou non la cohorte ;
- le système produit une définition versionnable.

## Fonctionnalités MVP

### Profilage

- Lecture de fichiers sources.
- Détection de séparateurs, encodages et types.
- Statistiques de base : lignes, colonnes, valeurs manquantes, valeurs distinctes.
- Détection des dates, identifiants, codes, libellés et booléens.

### Mapping

- Mapping déclaratif YAML.
- Proposition semi-automatique par règles, dictionnaires et similarité sémantique.
- Revue humaine obligatoire pour les mappings incertains.
- Séparation entre revue de colonnes et revue des valeurs vers concepts.
- Blocage des champs S4 avant génération des tables MCD-ST standardisées.
- Génération d'un `mapping_propose.yaml`, d'une file de revue, puis d'un `mapping_valide.yaml` versionnable.
- Journalisation de la source, de la règle et de la version du mapping.

Le fonctionnement détaillé du moteur est décrit dans [MAPPING_ENGINE_SPEC.md](MAPPING_ENGINE_SPEC.md).

### Modèle commun

- Tables MCD-ST v0.1.
- Export Parquet et SQL.
- Dictionnaire de données versionné.
- Nomenclatures minimales.
- Classification de sensibilité des champs.
- Périmètre clair des données admises, optionnelles et exclues.

Le périmètre détaillé des données est décrit dans [PERIMETRE_DONNEES_MCD.md](PERIMETRE_DONNEES_MCD.md).

Les domaines métier sensibles intégrés en tranche minimale dès v0.1, notamment
examens complémentaires, AT/MP, arrêts de travail, vaccinations et DUERP
collectif, sont cadrés dans
[EXTENSIONS_MODELE_METIER.md](EXTENSIONS_MODELE_METIER.md).

### Qualité

- Contrôles de complétude.
- Contrôles d'unicité.
- Contrôles de cohérence temporelle.
- Contrôles de valeurs hors nomenclature.
- Table des anomalies avec niveaux `bloquant`, `alerte`, `info`.

### Cohorting

- Définition YAML.
- Exécution sur tables MCD-ST.
- Diagramme de flux.
- Comptages par étape.
- Export des métadonnées de cohorte.

### IA assistive

- Aide au mapping.
- Rapprochement entre libellés locaux et concepts standardisés.
- Détection des variables utiles pour une cohorte.
- Score de confiance et justification.
- Aucune décision médicale automatisée.

### Administration

- Gestion des mappings et de leurs versions.
- Gestion des sources, lots d'import et données synthétiques.
- Gestion des vocabulaires, concepts et synonymes.
- Gestion des règles qualité et définitions de cohortes.
- Journal d'audit des actions structurantes.
- Préparation à des rôles applicatifs distincts : administrateur, data manager, référent métier, épidémiologiste, lecteur.

## Non-objectifs MVP

- Pas de base nationale centralisée.
- Pas de publication de données réelles.
- Pas d'appariement SNDS.
- Pas de décision médicale automatisée.
- Pas d'interface complète de gestion métier SPSTi.
- Pas de modèle IA entraîné sur données réelles sans cadre juridique séparé.
- Pas de copie complète du dossier médical en santé au travail.
- Pas de base RH contenant identité civile, salaire, sanctions, coordonnées ou données sociales non nécessaires.

## Interfaces attendues

### Web

L'interface web est la surface principale de MCD-ST.

Principes :

- découpage horizontal 30/70 ;
- zone haute dédiée au pipeline ETL en temps réel ;
- zone basse dédiée à l'espace de travail contextuel ;
- design vivant, technique, dense et professionnel ;
- édition des fichiers YAML directement dans l'interface ;
- suivi des étapes, anomalies, mappings et cohortes sans quitter le web.

La zone haute schématise le pipeline :

```text
RAW -> Profilage -> Mapping -> MCD-ST -> Qualité -> Cohorting -> Exports / Viz
```

Chaque étape expose son statut, sa progression, ses compteurs, ses alertes et son dernier événement.

La zone basse affiche le détail opérationnel :

- inventaire des exports ;
- profilage des colonnes ;
- éditeur YAML ;
- administration des mappings, sources, vocabulaires et règles ;
- revue de mapping ;
- rapport qualité ;
- assistant de faisabilité ;
- constructeur de cohorte ;
- diagramme de flux ;
- exports.

La spécification détaillée de l'interface est décrite dans [SPEC_UI_WEB.md](SPEC_UI_WEB.md).

### CLI technique

Commandes cibles :

```bash
mcdst profile ./exports
mcdst map ./exports --mapping mapping.yaml
mcdst validate ./mcdst_tables
mcdst cohort ./mcdst_tables --definition cohort.yaml
mcdst report ./mcdst_tables
mcdst synth --output ./sample_data
```

La CLI doit rester disponible pour les développeurs, l'intégration continue, les démonstrations scriptées et les environnements où l'interface web n'est pas nécessaire.

### API locale

L'API locale sert de pont entre le moteur et l'interface web. Elle peut aussi servir une première interface statique locale pour les démonstrations et tests MVP.

Premiers endpoints MVP :

- `GET /health` ;
- `GET /` ;
- `GET /api/artifact?path=...` ;
- `POST /api/artifact` ;
- `POST /api/mapping/propose` ;
- `GET /api/mapping/review-queue?workdir=...` ;
- `POST /api/mapping/review` ;
- `POST /api/mapping/apply` ;
- `POST /api/cohort/evaluate`.

Cette API doit rester locale par défaut et ne pas exposer de données réelles hors de l'environnement du SPSTi.

### Mémoire locale des mappings

Les décisions humaines validées peuvent alimenter un registre local de mappings.

Principes MVP :

- apprentissage déterministe, explicable et désactivable ;
- stockage local dans un YAML versionnable ou archivable ;
- réutilisation limitée au même `source_system` ;
- aucune décision S4 ou médicale ne doit être apprise automatiquement ;
- le registre propose, mais le mapping validé reste l'artefact de vérité.

### Rapports

Formats cibles :

- HTML pour lecture humaine ;
- JSON pour automatisation ;
- CSV ou Parquet pour exports analytiques.

## Contraintes

- Fonctionnement local possible.
- Pipeline reproductible.
- Données sources conservées en zone RAW sans correction silencieuse.
- Transformations traçables.
- Données synthétiques disponibles pour tests publics.
- Composants IA désactivables.
