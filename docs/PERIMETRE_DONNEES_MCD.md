# Périmètre des données MCD-ST

## Objectif

Ce document précise les types de données qui peuvent entrer dans le modèle commun MCD-ST, en particulier pour les données relatives aux travailleurs/salariés et aux entreprises/établissements.

MCD-ST ne doit pas devenir une copie complète du dossier médical en santé au travail, ni une base RH. Le modèle commun doit contenir les données strictement nécessaires pour :

- standardiser les exports SPSTi ;
- évaluer la qualité et la complétude ;
- produire des indicateurs agrégés ;
- construire des cohortes reproductibles ;
- documenter les expositions, visites, conclusions, actions de prévention et événements PDP ;
- préparer des analyses épidémiologiques ou de pilotage dans un cadre maîtrisé.

Toute utilisation de données réelles doit être validée localement avec le DPO, le responsable de traitement et les référents métier. Les livrables ouverts du projet doivent utiliser uniquement des données synthétiques ou des données anonymisées au sens juridique strict.

## Principe directeur

Le MCD-ST standardisé doit contenir des données pseudonymisées, minimisées, structurées et traçables.

Il faut distinguer quatre espaces :

1. `RAW` : fichiers sources locaux, conservés sans correction silencieuse, pouvant contenir des données directement identifiantes si le SPSTi les a légalement exportées dans son environnement maîtrisé.
2. `MCD-ST` : tables standardisées pseudonymisées et minimisées, adaptées à l'analyse.
3. `DERIVED` : cohortes, scores, indicateurs et variables calculées.
4. `OPEN` : code, documentation, schémas, mappings génériques et données synthétiques uniquement.

Le MCD-ST ne doit pas propager les identifiants directs de la zone RAW vers les tables standardisées.

## Classification de sensibilité

Chaque champ du MCD doit recevoir un niveau de sensibilité.

| Niveau | Description | Exemple | Statut |
| --- | --- | --- | --- |
| S0 | Non personnel ou synthétique | vocabulaire, schéma, jeu synthétique | publiable si aucune donnée réelle |
| S1 | Donnée d'entreprise peu identifiante | secteur NAF, taille classe, région | admise |
| S2 | Donnée personnelle pseudonymisée professionnelle | identifiant travailleur pseudonymisé, épisode de poste | admise si utile |
| S3 | Donnée de santé, exposition ou conclusion sensible | restriction, inaptitude, exposition, événement PDP | admise avec minimisation stricte |
| S4 | Identifiant direct ou donnée trop sensible pour le MCD analytique | nom, prénom, INS/NIR, adresse, téléphone, compte rendu libre | exclue des tables MCD-ST |

## Données travailleur/salarié

### Admis dans le noyau MCD-ST

Ces données sont nécessaires pour construire une population source, relier les événements dans le temps et produire des analyses agrégées.

| Donnée | Exemple de champ | Sensibilité | Commentaire |
| --- | --- | --- | --- |
| Identifiant pseudonymisé | `travailleur_id` | S2 | Stable dans un même projet, non réversible sans secret local |
| Année de naissance ou classe d'âge | `annee_naissance`, `age_classe` | S2 | Préférer la classe d'âge si l'année exacte n'est pas nécessaire |
| Sexe si utile à l'analyse | `sexe` | S2 | À justifier selon les analyses et indicateurs |
| Statut de suivi | `statut_suivi` | S2 | Actif, sorti, inconnu |
| Période d'observation | `date_debut`, `date_fin` | S2 | Permet d'éviter les biais temporels |
| Type de suivi santé-travail | `suivi_type_concept_id` | S3 | Suivi simple, adapté, renforcé, selon nomenclature |

### Données professionnelles individuelles

Ces données décrivent la situation de travail et le contexte d'exposition.

| Donnée | Exemple de champ | Sensibilité | Commentaire |
| --- | --- | --- | --- |
| Épisode de poste | `episode_poste_id` | S2 | Relie travailleur, établissement, poste et période |
| Intitulé source de poste | `intitule_poste_source` | S2/S3 | À normaliser ; peut être rare et réidentifiant |
| Famille métier ou concept poste | `poste_concept_id` | S2 | À privilégier pour l'analyse |
| Code PCS ou métier si disponible | `pcs_code` | S2 | Optionnel, si qualité suffisante |
| Unité de travail | `unite_travail_id` | S2 | Utile pour risques et DUERP |
| Type d'horaire ou rythme | `rythme_travail_concept_id` | S3 | Travail de nuit, équipes alternantes, répétitif |
| Quotité ou temps de travail | `temps_travail_classe` | S2 | Optionnel et classé, pas besoin du détail RH fin |
| Type de contrat | `contrat_type_classe` | S2 | Optionnel, uniquement si nécessaire à une analyse |

### Visites et suivi santé-travail

| Donnée | Exemple de champ | Sensibilité | Commentaire |
| --- | --- | --- | --- |
| Date ou mois de visite | `date_visite`, `mois_visite` | S3 | Précision à minimiser selon besoin |
| Type de visite | `type_visite_concept_id` | S3 | VIP, périodique, reprise, pré-reprise, demande, mi-carrière, etc. |
| Professionnel ou rôle | `professionnel_role` | S2 | Rôle uniquement, pas nom nominatif du professionnel en V0.1 |
| Motif structuré | `motif_visite_concept_id` | S3 | Éviter les textes libres |
| Lien à épisode de poste | `episode_poste_id` | S2/S3 | Permet analyses longitudinales |

### Conclusions, restrictions et aménagements

Ces éléments sont au cœur de la santé au travail, mais fortement sensibles.

| Donnée | Exemple de champ | Sensibilité | Commentaire |
| --- | --- | --- | --- |
| Conclusion structurée | `conclusion_concept_id` | S3 | Apte, apte avec restriction, inapte, avis, attestation |
| Restriction | `restriction_flag`, `restriction_concept_id` | S3 | Préférer catégorie structurée plutôt que texte libre |
| Aménagement | `amenagement_flag`, `amenagement_concept_id` | S3 | Limiter au type d'aménagement |
| Orientation PDP | `orientation_pdp_flag` | S3 | Oui/non ou concept structuré |
| Inaptitude | `inaptitude_flag` | S3 | Très sensible, nécessaire seulement si finalité explicite |
| Texte court source | `texte_court_source` | S3/S4 | À éviter en MVP ; si conservé localement, non publiable et à revue stricte |

### Expositions professionnelles

Les expositions sont explicitement nécessaires au suivi santé-travail, à la prévention et à la recherche.

| Donnée | Exemple de champ | Sensibilité | Commentaire |
| --- | --- | --- | --- |
| Catégorie d'exposition | `categorie_exposition` | S3 | Biomécanique, chimique, bruit, horaires, psychosocial, etc. |
| Concept d'exposition | `exposition_concept_id` | S3 | Vocabulaire versionné |
| Agent ou nuisance | `agent_concept_id` | S3 | Poussières de bois, bruit, manutention, etc. |
| Période d'exposition | `date_debut`, `date_fin` | S3 | Peut être approximée |
| Niveau ou intensité | `niveau_classe` | S3 | Classe plutôt que valeur brute si possible |
| Source de l'information | `source_exposition_type` | S3 | DUERP, fiche entreprise, visite, étude de poste, déclaration |
| Mesures de prévention | `prevention_concept_id` | S3 | EPI, protection collective, adaptation poste |

### Événements santé et données médicales

Le MCD-ST ne doit pas importer largement les diagnostics, comptes rendus médicaux ou courriers.

Admis seulement si nécessaire, structuré et autorisé :

- existence d'une pathologie en lien possible avec une exposition, sous forme de concept ou indicateur très encadré ;
- événement de maintien en emploi ou PDP ;
- catégorie de visite ou de conclusion ;
- indicateurs agrégés ou dérivés.

À exclure du MCD-ST v0.1 :

- diagnostics détaillés non nécessaires ;
- comptes rendus libres ;
- courriers médicaux ;
- traitements médicamenteux ;
- antécédents familiaux ;
- données psychologiques détaillées ;
- documents PDF médicaux ;
- informations sur des tiers.

### Données salarié exclues du MCD-ST standardisé

Ces données peuvent exister dans les exports locaux ou le DMST, mais ne doivent pas être propagées dans le MCD analytique v0.1 :

- nom, prénom ;
- INS, NIR, numéro de sécurité sociale ;
- matricule RH directement identifiant ;
- adresse complète ;
- téléphone, email personnel ;
- coordonnées du médecin traitant ;
- photographie ;
- coordonnées bancaires ;
- salaire ;
- sanctions disciplinaires, évaluation RH, performance ;
- activité syndicale, opinions, religion, origine ethnique ;
- détails familiaux ;
- textes libres médicaux non nécessaires ;
- documents PDF, courriers et pièces jointes ;
- données de tiers non nécessaires au suivi.

## Données entreprise, établissement et environnement de travail

### Admis dans le noyau MCD-ST

| Donnée | Exemple de champ | Sensibilité | Commentaire |
| --- | --- | --- | --- |
| Identifiant entreprise pseudonymisé | `entreprise_id` | S1/S2 | Ne pas utiliser la raison sociale en sortie standard |
| Identifiant établissement pseudonymisé | `etablissement_id` | S1/S2 | Stable localement |
| Secteur d'activité | `secteur_naf`, `naf_classe` | S1 | Niveau exact à adapter selon risque de réidentification |
| Taille classe | `taille_classe` | S1 | Classe plutôt qu'effectif exact |
| Région | `region` | S1 | Géographie agrégée par défaut |
| Commune ou département | `commune_code`, `departement` | S1/S2 | Optionnel, selon taille et risque |
| Unité de travail | `unite_travail_id`, `unite_travail_libelle` | S1/S2 | Peut être réidentifiant dans petites structures |
| Activité ou métier dominant | `activite_concept_id` | S1 | Utile pour prévention |

### Données de prévention collective

| Donnée | Exemple de champ | Sensibilité | Commentaire |
| --- | --- | --- | --- |
| Fiche entreprise | `fiche_entreprise_id` | S1/S2 | Métadonnées structurées, pas document complet en MVP |
| Action en milieu de travail | `action_prevention_id` | S1/S2 | Type, date, thème, établissement |
| Étude de poste | `etude_poste_id` | S2/S3 | Métadonnées et conclusions structurées |
| Risques DUERP | `risque_concept_id` | S1/S3 | Agrégé par unité de travail |
| Mesure de prévention | `mesure_prevention_concept_id` | S1/S3 | Collective ou individuelle |
| Sensibilisation | `sensibilisation_concept_id` | S1 | Thème, population, date |

### Données entreprise à éviter ou exclure

À éviter dans le MCD standardisé :

- raison sociale en clair ;
- SIRET/SIREN en clair dans les exports analytiques ;
- adresse complète ;
- noms et coordonnées des interlocuteurs employeur ;
- organigramme nominatif ;
- commentaire libre sur la qualité managériale ou des personnes ;
- données commerciales ou financières non nécessaires ;
- documents complets non structurés.

Ces données peuvent rester en zone RAW ou dans un référentiel local autorisé, mais les tables MCD-ST doivent privilégier les identifiants pseudonymisés, les classes, les concepts et les niveaux agrégés.

## Données dérivées et indicateurs

MCD-ST doit pouvoir stocker des indicateurs calculés, mais jamais sans définition.

Exemples :

- score ou classe IRDP ;
- indicateur de risque de désinsertion professionnelle ;
- score de qualité d'un lot ;
- classe d'exposition cumulée ;
- indicateur de complétude d'une cohorte ;
- indicateur d'action de prévention.

Chaque indicateur doit inclure :

- code de l'indicateur ;
- entité concernée : travailleur, établissement, unité de travail, cohorte ;
- valeur numérique ou classe ;
- version de la définition ;
- date de calcul ;
- variables sources utilisées ;
- avertissement sur les limites ;
- niveau de sensibilité.

## Règles de minimisation par défaut

MCD-ST doit appliquer les règles suivantes :

- remplacer les identifiants directs par des identifiants pseudonymisés ;
- préférer année ou classe d'âge à date de naissance complète ;
- préférer région ou département à adresse complète ;
- préférer classe d'effectif à effectif exact ;
- préférer concept standardisé à texte libre ;
- préférer catégorie d'exposition à commentaire détaillé ;
- séparer données sources, données standardisées et données dérivées ;
- ne jamais publier de données réelles dans le dépôt open source ;
- rendre explicite toute donnée S3 utilisée dans une cohorte ou un indicateur.

## Impact sur le MCD v0.1

Le MCD v0.1 doit donc contenir en priorité :

- travailleur pseudonymisé ;
- période d'observation ;
- entreprise pseudonymisée ;
- établissement pseudonymisé ;
- unité de travail ;
- épisode de poste ;
- visite santé-travail ;
- conclusion structurée ;
- exposition professionnelle ;
- action de prévention ;
- événement PDP ;
- concepts, vocabulaires, synonymes et mappings ;
- sources, lots, anomalies qualité ;
- cohortes et indicateurs dérivés.

Le MCD v0.1 ne doit pas contenir :

- identité civile directe ;
- INS/NIR ;
- coordonnées personnelles ;
- données RH fines sans lien avec la finalité ;
- documents médicaux complets ;
- notes libres non maîtrisées ;
- données de tiers.

Les domaines clinique/biométrie, AT/MP, arrêts de travail, vaccinations et DUERP
collectif sont intégrés dès v0.1 sous forme minimale et structurée. Ils sont
cadrés dans [EXTENSIONS_MODELE_METIER.md](EXTENSIONS_MODELE_METIER.md), avec
minimisation, traçabilité et revue humaine renforcées.

## Références de cadrage

- Code du travail, article L4622-2 : missions des SPST, prévention, surveillance de l'état de santé, traçabilité des expositions et veille sanitaire.
- Code du travail, article L4624-8 : le DMST retrace l'état de santé, les expositions, les avis et propositions, dans le respect du secret médical.
- Code du travail, article R4624-45-4 : contenu du dossier médical en santé au travail.
- Code du travail, article L4161-1 : facteurs de risques professionnels.
- Code du travail, article L4121-3-1 : le DUERP répertorie les risques professionnels et assure la traçabilité collective des expositions.
- Guide CNIL SPST, décembre 2023 : données personnelles, confidentialité, risques de réidentification, DPO et conformité.
- CNIL, principes RGPD : finalité, minimisation, durées de conservation, sécurité.
