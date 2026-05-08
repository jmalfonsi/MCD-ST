# MCD-ST - Cadrage produit

## Positionnement

MCD-ST doit être conçu comme une plateforme complète de réutilisation des données en santé au travail, et non comme un simple outil ETL. Le framework doit pouvoir s'adapter à plusieurs profils d'utilisateurs et à plusieurs intentions d'usage :

- comprendre l'essence d'exports SPSTi hétérogènes ;
- standardiser les données disponibles ;
- évaluer leur qualité et leurs limites ;
- construire ou préparer des cohortes reproductibles ;
- identifier les données nécessaires pour répondre à une question métier, scientifique ou de pilotage.

Le périmètre des données doit rester strict : MCD-ST standardise des données utiles, pseudonymisées et minimisées ; il ne doit devenir ni une copie complète du dossier médical en santé au travail, ni une base RH.

Le produit doit donc fonctionner dans deux directions complémentaires :

1. partir des données disponibles pour en extraire une lecture structurée ;
2. partir d'une question ou d'une cohorte cible pour déterminer les données nécessaires.

## Profils utilisateurs

### Directeur ou direction de SPSTi

Objectif principal : piloter, comprendre, prioriser et rendre exploitables les données produites par le service.

Besoins typiques :

- savoir ce que les exports contiennent réellement ;
- mesurer la complétude, la cohérence et la qualité des données ;
- produire des indicateurs agrégés utiles au pilotage ;
- identifier les zones de fragilité : champs manquants, nomenclatures locales, données non exploitables ;
- préparer un dialogue avec les équipes métier, le DPO, les éditeurs logiciels et les partenaires institutionnels ;
- valoriser les données sans exposer de données individuelles.

Expérience attendue :

- tableaux de bord lisibles ;
- rapports qualité interprétables ;
- cartographie des données disponibles ;
- recommandations sur les priorités d'amélioration ;
- export d'indicateurs agrégés.

### Épidémiologiste ou biostatisticien

Objectif principal : transformer des données santé-travail en matériau d'analyse fiable.

Besoins typiques :

- comprendre la structure longitudinale des données ;
- vérifier les périodes d'observation ;
- définir une population source ;
- construire des cohortes reproductibles ;
- documenter les critères d'inclusion et d'exclusion ;
- évaluer les biais liés aux données manquantes ou aux mappings incertains ;
- exporter des tables analytiques.

Expérience attendue :

- définitions de cohortes versionnées ;
- diagrammes de flux ;
- dictionnaire de données complet ;
- requêtes reproductibles ;
- métriques qualité par variable et par étape de cohorte ;
- exports Parquet, SQL ou CSV documentés.

### Service de recherche, institution ou équipe projet

Objectif principal : cadrer une étude, une évaluation ou un projet multicentrique à partir de données SPSTi.

Besoins typiques :

- savoir si une question de recherche est faisable avec les données disponibles ;
- comparer les structures de données entre plusieurs SPSTi ;
- harmoniser les définitions ;
- préparer un protocole de réutilisation ;
- produire une documentation transparente ;
- anticiper les démarches RGPD, sécurité et gouvernance.

Expérience attendue :

- matrice de faisabilité ;
- cartographie des variables nécessaires ;
- analyse des écarts entre données requises et données disponibles ;
- documentation exportable pour protocole ou comité de pilotage ;
- traçabilité des mappings et transformations.

## Deux modes fondamentaux

### Mode 1 - Analyse d'exports disponibles

Question utilisateur type :

> "Voici les exports de mon SPSTi. Que peut-on en tirer ? Quelle est leur essence exploitable ?"

Le système doit :

- scanner les fichiers sources ;
- détecter les tables, champs, types, formats et volumes ;
- inférer les objets métier probables : travailleur, visite, poste, exposition, conclusion, action, PDP ;
- proposer un mapping vers le modèle MCD-ST ;
- signaler les ambiguïtés ;
- mesurer la qualité des champs ;
- produire une cartographie des données disponibles ;
- indiquer les usages possibles : indicateurs, cohortes, études faisables ;
- distinguer ce qui est exploitable immédiatement, exploitable après correction, ou non exploitable.

Sorties attendues :

- rapport d'inventaire ;
- rapport qualité ;
- proposition de mapping YAML ;
- dictionnaire source ;
- matrice "données disponibles -> usages possibles" ;
- recommandations de standardisation.

### Mode 2 - Conception inverse d'une cohorte ou d'une étude

Question utilisateur type :

> "Je veux créer une cohorte de travailleurs de plus de 45 ans, avec un indice IRDP élevé, en région Auvergne. De quelles données ai-je besoin ?"

Le système doit :

- traduire la demande en critères formels ;
- identifier les concepts nécessaires ;
- produire la liste des variables requises, recommandées et optionnelles ;
- préciser les tables MCD-ST nécessaires ;
- indiquer les contraintes temporelles ;
- vérifier si les exports disponibles permettent de répondre à la demande ;
- produire une définition de cohorte versionnable ;
- signaler les données manquantes ou les approximations nécessaires.

Exemple de décomposition :

- Population : travailleurs suivis, âge calculable, période d'observation connue.
- Âge : année de naissance ou date de naissance minimisée.
- Territoire : région de l'établissement, du lieu de travail ou du SPSTi selon la définition retenue.
- IRDP : variable source existante ou règle de calcul documentée.
- Niveau IRDP élevé : seuil explicite, versionné et justifié.
- Temporalité : année d'index, date de suivi, validité du poste, date de visite ou période d'exposition.
- Données minimales : travailleur pseudonymisé, période d'observation, établissement ou lieu, épisode de poste, indicateur IRDP.
- Données recommandées : sexe, secteur NAF, taille d'entreprise, type de contrat si disponible, exposition professionnelle, type de visite, conclusion médicale, évènements PDP.

Sorties attendues :

- fiche de faisabilité ;
- liste des données nécessaires ;
- définition YAML de cohorte ;
- diagramme de flux prévisionnel ;
- plan de mapping ;
- points de vigilance RGPD et qualité.

## Conséquences sur l'architecture

MCD-ST doit séparer clairement cinq couches produit :

1. Couche ingestion : lecture et profilage des exports.
2. Couche sémantique : modèle commun, vocabulaires, concepts, mappings.
3. Couche IA assistive : aide au mapping, rapprochement sémantique, extraction de concepts et faisabilité.
4. Couche analytique : qualité, cohorting, indicateurs, exports analytiques.
5. Couche expérience utilisateur : rapports, assistants, tableaux de bord et génération de documentation.

Cette séparation est importante pour permettre aux différents profils d'utiliser le même socle sans imposer la même interface.

## Module IA de domaine

MCD-ST pourra intégrer un petit modèle de deep learning spécialisé dans les données de santé au travail. Ce modèle ne doit pas être présenté comme un système de décision médicale, mais comme un assistant sémantique destiné à accélérer le mapping, la normalisation et la préparation des analyses.

### Finalité

Le modèle doit aider à répondre à des tâches concrètes :

- proposer des correspondances entre champs sources et champs MCD-ST ;
- rapprocher des intitulés locaux de postes, expositions, visites, conclusions ou actions de prévention avec les concepts standardisés ;
- détecter qu'un champ source ressemble à une date de visite, un identifiant travailleur, une conclusion médicale ou une exposition professionnelle ;
- suggérer les tables MCD-ST nécessaires pour répondre à une question de cohorte ;
- identifier les variables manquantes pour une cohorte cible ;
- produire des explications courtes sur la raison d'un mapping proposé ;
- classer les mappings selon un score de confiance ;
- signaler les cas qui doivent être relus par un expert humain.

### Données d'entraînement

Le modèle doit être entraîné prioritairement sur des connaissances maîtrisées et non sensibles :

- dictionnaire de données MCD-ST ;
- nomenclatures santé-travail ;
- tables de concepts, synonymes et relations conceptuelles ;
- mappings validés entre exports sources et modèle MCD-ST ;
- documentation métier sur les visites, expositions, conclusions, restrictions, aménagements, actions de prévention et événements PDP ;
- exemples synthétiques d'exports SPSTi ;
- jeux annotés par des experts métier-data ;
- règles de cohortes versionnées.

L'utilisation de données réelles de santé au travail pour entraîner ou ajuster le modèle doit rester une étape séparée, encadrée juridiquement, documentée et validée avec le DPO. Les exemples publics et les tests ouverts doivent reposer sur des données synthétiques ou anonymisées au sens juridique strict.

### Approche technique

Le premier niveau utile n'est pas forcément un grand modèle génératif. Une approche progressive est préférable :

1. moteur de règles et dictionnaires ;
2. embeddings sémantiques pour rapprocher noms de colonnes, libellés et concepts ;
3. classifieur supervisé pour les mappings fréquents ;
4. reranker pour classer les propositions ;
5. petit modèle de domaine entraîné ou ajusté sur les mappings validés ;
6. assistant génératif uniquement pour expliquer, documenter et proposer, jamais pour valider seul.

Cette approche permet de livrer rapidement une aide utile, tout en conservant une architecture contrôlable et évaluable.

### Sorties attendues

Chaque proposition du modèle doit être accompagnée de métadonnées :

- champ source ;
- champ cible MCD-ST proposé ;
- concept standardisé proposé ;
- méthode utilisée : règle, dictionnaire, embedding, classifieur, modèle génératif ;
- score de confiance ;
- justification courte ;
- statut de revue : à valider, validé, rejeté, corrigé ;
- version du modèle ;
- version du dictionnaire de données ;
- trace vers les exemples ou règles ayant motivé la proposition.

### Garde-fous

Le modèle IA ne doit pas :

- produire une décision médicale ;
- déterminer seul l'inclusion finale d'un travailleur dans une cohorte ;
- masquer les incertitudes ;
- écraser un mapping humain validé sans revue ;
- utiliser des données réelles non autorisées pour l'entraînement ;
- publier des exemples contenant des données personnelles ou indirectement réidentifiantes.

Le modèle doit toujours rester désactivable. Le pipeline MCD-ST doit fonctionner sans IA, avec des mappings YAML et des règles explicites.

### Évaluation

Le module IA doit être évalué comme un composant logiciel mesurable :

- précision top-1 et top-3 des mappings proposés ;
- rappel des champs importants détectés ;
- taux de mappings nécessitant revue humaine ;
- taux d'erreurs critiques ;
- stabilité entre versions ;
- performance par type d'objet métier : travailleur, poste, visite, exposition, conclusion, PDP ;
- comparaison à une méthode simple par dictionnaire ou règles.

L'objectif n'est pas d'automatiser 100 % du mapping, mais de réduire l'effort humain tout en améliorant la traçabilité.

## Fonctionnalités structurantes

### Assistant d'inventaire

Analyse des exports bruts et production d'une cartographie des données disponibles.

### Assistant de mapping

Proposition semi-automatique de correspondances entre champs sources et modèle MCD-ST, avec revue humaine obligatoire pour les mappings ambigus.

La logique stable du moteur de mapping est décrite dans [docs/MAPPING_ENGINE_SPEC.md](docs/MAPPING_ENGINE_SPEC.md).

### Assistant de faisabilité

À partir d'une question ou d'une cohorte cible, identification des données nécessaires, des tables concernées et des manques.

### Moteur de cohorting

Transformation d'une définition métier en critères versionnés, exécutables et documentés.

### Moteur qualité

Contrôles techniques, temporels, sémantiques et analytiques, avec niveaux de sévérité.

### MCD-ST Viz

Interface de visualisation adaptée aux profils :

- vue pilotage pour direction SPSTi ;
- vue qualité et données pour data manager ;
- vue cohorte pour épidémiologiste ;
- vue faisabilité pour recherche et institution.

## Principe directeur

Le produit doit toujours répondre à l'une de ces deux questions :

- "Avec les données que j'ai, que puis-je comprendre, standardiser et analyser ?"
- "Pour répondre à la question que je pose, de quelles données ai-je besoin et sont-elles disponibles ?"

Ce principe doit guider la spécification du MVP, les exemples, les tests, les écrans, la documentation et les démonstrations.
