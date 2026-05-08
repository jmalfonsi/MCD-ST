# Spécification UI web MCD-ST

## Principe d'interface

L'expérience utilisateur principale de MCD-ST se fera par le web. La plateforme doit donner une impression à la fois vivante, technique et maîtrisée : l'utilisateur doit voir les données circuler, les étapes progresser, les anomalies apparaître, les mappings se construire et les cohortes se préciser.

La CLI et les scripts restent utiles pour les développeurs, l'intégration continue et l'automatisation, mais ils ne constituent pas l'interface principale pour les directions de SPSTi, épidémiologistes, data managers ou équipes de recherche.

## Structure 30/70

L'interface principale doit être découpée horizontalement :

- zone haute : 30 % de la hauteur utile ;
- zone basse : 70 % de la hauteur utile.

### Zone haute - Pipeline ETL temps réel

La zone haute est dédiée à la schématisation active du pipeline :

```text
RAW -> Profilage -> Mapping -> MCD-ST -> Qualité -> Cohorting -> Exports / Viz
```

Chaque étape doit afficher :

- statut : en attente, en cours, terminé, erreur, à revoir ;
- progression ;
- nombre de fichiers, lignes ou objets traités ;
- anomalies bloquantes ou alertes ;
- temps d'exécution ;
- dernier événement significatif ;
- accès rapide aux détails de l'étape.

Le pipeline doit être visuel et animé avec sobriété :

- flux de données entre étapes ;
- couleurs de statut ;
- pulsation ou mouvement léger pendant les traitements ;
- badges de qualité ;
- compteurs qui évoluent en temps réel ;
- possibilité de cliquer sur une étape pour filtrer la zone basse.

Cette zone est permanente : l'utilisateur doit toujours savoir où il se trouve dans le processus et ce qui bloque éventuellement la progression.

### Zone basse - Espace de travail contextuel

La zone basse change selon l'étape ou le profil utilisateur. Elle accueille les vues opérationnelles :

- inventaire des fichiers ;
- aperçu des tables sources ;
- profilage des colonnes ;
- éditeur de mapping YAML ;
- visualisation du modèle MCD-ST ;
- rapport qualité ;
- assistant de faisabilité ;
- constructeur de cohorte ;
- diagramme de flux ;
- exports et rapports.

La zone basse doit être dense, lisible et orientée travail. Elle doit privilégier les tableaux, panneaux latéraux, onglets, filtres, diff et contrôles de validation plutôt qu'une présentation marketing.

## Édition YAML intégrée

L'interface doit permettre de modifier les fichiers YAML directement dans le navigateur lorsque c'est nécessaire.

YAML concernés :

- mappings source vers MCD-ST ;
- définitions de cohortes ;
- règles qualité ;
- correspondances source vers concepts ;
- paramètres d'import.

Fonctions attendues :

- éditeur avec coloration syntaxique ;
- autocomplétion sur les tables et champs MCD-ST ;
- validation syntaxique immédiate ;
- validation métier : champ cible inexistant, type incompatible, concept inconnu ;
- aperçu des effets avant application ;
- comparaison avant/après ;
- historique des versions ;
- possibilité de revenir à une version précédente ;
- commentaire ou justification obligatoire pour valider un mapping sensible ;
- statut de revue : brouillon, à valider, validé, rejeté.

Le YAML reste le format de vérité pour la reproductibilité. L'interface web ne doit pas cacher cette couche ; elle doit au contraire la rendre éditable, compréhensible et sûre.

## Interface d'administration

MCD-ST doit intégrer une interface d'administration dédiée. Cette interface permet de gérer les éléments structurants de la plateforme sans modifier directement les fichiers du projet ou intervenir en base de données.

L'administration doit rester séparée des vues métier courantes. Elle s'adresse principalement aux administrateurs fonctionnels, data managers, référents métier, responsables projet et profils techniques autorisés.

### Objets administrables

L'interface d'administration doit permettre de gérer :

- mappings source vers MCD-ST ;
- fichiers YAML de configuration ;
- sources de données et lots d'import ;
- dictionnaires de données ;
- classification de sensibilité des champs ;
- vocabulaires et nomenclatures ;
- concepts, synonymes et relations conceptuelles ;
- règles qualité ;
- définitions de cohortes ;
- modèles de rapports ;
- paramètres du module IA assistive ;
- jeux de données synthétiques ;
- versions du schéma MCD-ST ;
- profils utilisateurs, rôles et permissions si l'application est multi-utilisateur.

### Administration des mappings

Les mappings sont un actif central du projet. L'interface doit permettre :

- création d'un mapping depuis un export profilé ;
- édition guidée champ source vers champ cible ;
- édition YAML avancée ;
- validation syntaxique et métier ;
- comparaison entre versions ;
- visualisation des impacts avant application ;
- statut de cycle de vie : brouillon, à revoir, validé, déprécié, archivé ;
- assignation à un réviseur métier ou data ;
- commentaire obligatoire lors d'une validation ou d'un rejet ;
- export et import de mappings ;
- duplication d'un mapping pour l'adapter à un autre SPSTi ou logiciel métier.

Chaque mapping validé doit être immuable. Toute modification d'un mapping validé doit créer une nouvelle version.

Le contrat moteur, les statuts de revue et les artefacts YAML sont décrits dans [MAPPING_ENGINE_SPEC.md](MAPPING_ENGINE_SPEC.md).

### Administration des données

L'interface doit permettre de gérer les données chargées ou générées :

- liste des lots d'import ;
- statut de traitement de chaque lot ;
- taille, volume, période couverte et source ;
- empreinte technique des fichiers ;
- tables MCD-ST générées ;
- anomalies associées ;
- niveaux de sensibilité détectés ou déclarés ;
- alertes sur les champs S3/S4 ;
- possibilité d'archiver ou supprimer un lot selon les règles locales ;
- séparation claire entre données réelles locales et données synthétiques ;
- impossibilité de publier ou exporter par erreur des données personnelles dans un livrable ouvert.

L'administration des données doit afficher les métadonnées et les états de traitement, mais ne doit pas encourager la consultation nominative ou individuelle lorsque ce n'est pas nécessaire.

Les lots contenant des données S3 ou des champs détectés comme S4 doivent être clairement signalés. Un champ S4 ne doit pas être mappable vers une table MCD-ST standardisée ; l'interface doit proposer son exclusion, sa suppression, son masquage ou son maintien strict en zone RAW locale selon les règles du SPSTi.

### Gouvernance et audit

Toute action structurante doit être tracée :

- création ou modification d'un mapping ;
- validation ou rejet ;
- import d'un lot ;
- exécution d'une cohorte ;
- changement d'une règle qualité ;
- modification d'un vocabulaire ;
- activation ou changement de version du module IA ;
- export de données ou de rapport.

Le journal d'audit doit inclure :

- utilisateur ou service ;
- date et heure ;
- objet modifié ;
- ancienne version ;
- nouvelle version ;
- justification si nécessaire ;
- impact estimé.

### Rôles applicatifs

Le MVP peut fonctionner en mono-utilisateur local, mais la conception doit prévoir plusieurs rôles :

- administrateur technique ;
- administrateur fonctionnel ;
- data manager ;
- référent métier santé-travail ;
- épidémiologiste ;
- lecteur ou observateur ;
- réviseur de mapping.

Les droits doivent pouvoir distinguer lecture, édition, validation, exécution et export.

## Vues principales

### Vue direction SPSTi

Objectif : comprendre rapidement la qualité et la valeur exploitable des données.

Composants :

- synthèse de qualité ;
- indicateurs agrégés ;
- couverture des domaines métier ;
- risques et priorités d'amélioration ;
- export rapport.

### Vue data manager

Objectif : contrôler les fichiers, les mappings et les anomalies.

Composants :

- inventaire des sources ;
- profilage colonnes ;
- éditeur YAML ;
- revue des mappings ;
- table des anomalies ;
- diff source-cible.

### Vue administration

Objectif : gérer les actifs structurants de la plateforme.

Composants :

- catalogue des sources ;
- gestion des mappings ;
- gestion des vocabulaires ;
- classification de sensibilité ;
- gestion des règles qualité ;
- gestion des cohortes ;
- journal d'audit ;
- rôles et permissions ;
- configuration du module IA.

### Vue épidémiologiste

Objectif : construire et documenter des cohortes reproductibles.

Composants :

- population source ;
- critères d'inclusion et exclusion ;
- diagramme de flux ;
- variables nécessaires ;
- exports analytiques ;
- métriques de complétude sur les variables de cohorte.

### Vue recherche ou institution

Objectif : évaluer la faisabilité d'une question ou d'une étude.

Composants :

- assistant de question ;
- données nécessaires ;
- données disponibles ;
- écarts et approximations ;
- recommandations de collecte ;
- génération d'une fiche de faisabilité.

## Interactions IA

L'IA assistive doit être visible comme une aide, pas comme une boîte noire.

Interactions attendues :

- suggestions de mapping ;
- score de confiance ;
- explication courte ;
- comparaison avec règles ou dictionnaires ;
- bouton de validation humaine ;
- rejet avec motif ;
- envoi en file de revue ;
- affichage de la version du modèle utilisée.

L'utilisateur doit pouvoir voir pourquoi une proposition est faite, l'accepter, la modifier ou la rejeter.

## États temps réel

Le web doit afficher les événements du pipeline au fil de l'eau :

- fichier détecté ;
- fichier lu ;
- colonne profilée ;
- mapping proposé ;
- mapping validé ;
- table générée ;
- règle qualité exécutée ;
- anomalie détectée ;
- cohorte exécutée ;
- rapport généré.

Ces événements doivent alimenter à la fois la zone haute du pipeline et un journal technique consultable dans la zone basse.

## Contraintes UX

- Interface web prioritaire.
- Design vivant, technique, dense et professionnel.
- Pas de page d'accueil marketing comme premier écran.
- Premier écran centré sur le pipeline et l'espace de travail.
- Les données, statuts et actions doivent rester visibles.
- Les erreurs doivent être actionnables.
- Les modifications de configuration doivent être traçables.
- Les composants sensibles doivent demander une validation explicite.
- Les fonctions d'administration doivent être séparées des vues d'analyse courantes.
- Les vues doivent s'adapter aux profils sans changer le socle technique.

## Critères d'acceptation MVP UI

- l'utilisateur voit le pipeline dans la zone haute ;
- les étapes changent de statut en temps réel ou quasi temps réel ;
- la zone basse affiche le détail de l'étape sélectionnée ;
- un fichier YAML de mapping peut être ouvert, modifié, validé et sauvegardé ;
- une erreur YAML est signalée avant exécution ;
- un mapping proposé par l'assistant peut être accepté, corrigé ou rejeté ;
- une définition de cohorte peut être visualisée en YAML et sous forme de critères ;
- un rapport qualité est consultable dans le web ;
- les mappings peuvent être gérés depuis une vue d'administration ;
- chaque modification structurante est versionnée ou journalisée ;
- l'interface reste utilisable par un profil non développeur.

## Première tranche locale

La première surface web servie par `mcdst serve` couvre :

- pipeline `RAW -> Profilage -> Mapping -> Revue -> Qualite` ;
- formulaire local des chemins d'exports, de travail et de sortie ;
- actions `propose`, `review` et `apply` via l'API locale ;
- lecture et sauvegarde du YAML de mapping ;
- revue des mappings de colonnes ;
- affichage et validation des valeurs de nomenclature en revue ;
- champ de registre local pour réutiliser les décisions humaines ;
- synthèse des tables générées.
