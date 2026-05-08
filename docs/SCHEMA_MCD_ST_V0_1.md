# Schéma MCD-ST v0.1

## Principes

Le schéma MCD-ST v0.1 doit représenter un socle minimal santé-travail sans chercher à tout modéliser dès la première version.

Principes de conception :

- un travailleur est pseudonymisé ;
- les événements sont rattachés à une période d'observation ;
- les postes, visites, expositions, conclusions et événements PDP sont datés ;
- les concepts métier sont reliés à des vocabulaires versionnés ;
- les transformations sont traçables ;
- les éléments dérivés, comme les cohortes et indicateurs qualité, sont séparés des données sources standardisées.
- chaque table et chaque champ sensible doivent pouvoir être classés selon le niveau de sensibilité décrit dans [PERIMETRE_DONNEES_MCD.md](PERIMETRE_DONNEES_MCD.md).

## Règle de périmètre

Le MCD-ST v0.1 n'est ni une copie complète du dossier médical en santé au travail, ni une base RH. Il contient uniquement des données pseudonymisées, minimisées et utiles à l'analyse santé-travail.

Les identifiants directs et les textes libres sensibles doivent rester hors des tables MCD-ST standardisées. Ils peuvent exister dans la zone RAW locale si le SPSTi dispose d'un cadre légal et technique adapté, mais ils ne doivent pas être propagés dans le modèle commun analytique.

## Tables noyau

### travailleur

Unité : travailleur ou salarié suivi par un SPSTi.

Champs minimaux :

- `travailleur_id` : identifiant pseudonymisé ;
- `annee_naissance` : année de naissance ou classe d'âge selon minimisation ;
- `age_classe` : classe d'âge si l'année de naissance n'est pas nécessaire ;
- `sexe` : sexe ou genre administratif si disponible ;
- `statut_suivi` : actif, sorti, inconnu ;
- `suivi_type_concept_id` : type de suivi santé-travail si utile et disponible ;
- `sensitivity_level` : niveau de sensibilité dominant de l'enregistrement ;
- `source_id` : référence de provenance.

Exclusions v0.1 :

- nom, prénom ;
- INS, NIR, numéro de sécurité sociale ;
- adresse complète ;
- téléphone, email personnel ;
- matricule RH directement identifiant ;
- coordonnées du médecin traitant ;
- données RH sans lien avec la finalité santé-travail.

### periode_observation

Unité : période pendant laquelle un travailleur est observable dans les exports.

Champs minimaux :

- `periode_observation_id` ;
- `travailleur_id` ;
- `date_debut` ;
- `date_fin` ;
- `motif_fin` ;
- `sensitivity_level` ;
- `source_id`.

### entreprise

Unité : entreprise.

Champs minimaux :

- `entreprise_id` ;
- `secteur_naf` ;
- `secteur_naf_niveau` : niveau de granularité retenu ;
- `taille_classe` ;
- `region` ;
- `sensitivity_level` ;
- `source_id`.

`entreprise_id` doit être un identifiant pseudonymisé dans les sorties analytiques. La raison sociale, le SIREN ou le SIRET en clair ne doivent pas être exportés dans le MCD standardisé sauf besoin local explicite et contrôlé.

### etablissement

Unité : établissement ou site.

Champs minimaux :

- `etablissement_id` ;
- `entreprise_id` ;
- `secteur_naf` ;
- `taille_classe` ;
- `commune_code` ou `region` selon minimisation ;
- `departement` si la granularité régionale est insuffisante et que le risque de réidentification reste maîtrisé ;
- `sensitivity_level` ;
- `source_id`.

### unite_travail

Unité : unité de travail, groupe homogène d'exposition ou regroupement opérationnel lié à l'évaluation des risques.

Champs minimaux :

- `unite_travail_id` ;
- `etablissement_id` ;
- `libelle_unite_source` ;
- `unite_travail_concept_id` ;
- `effectif_classe` ;
- `sensitivity_level` ;
- `source_id`.

L'unité de travail est utile pour relier DUERP, expositions, actions de prévention et cohortes. Son libellé peut être réidentifiant dans de petites structures ; il doit donc être normalisé ou agrégé dès que possible.

### episode_poste

Unité : période pendant laquelle un travailleur occupe un poste.

Champs minimaux :

- `episode_poste_id` ;
- `travailleur_id` ;
- `etablissement_id` ;
- `intitule_poste_source` ;
- `poste_concept_id` ;
- `pcs_code` si disponible et utile ;
- `contrat_type_classe` si nécessaire à la question analysée ;
- `temps_travail_classe` si nécessaire à la question analysée ;
- `rythme_travail_concept_id` si disponible ;
- `unite_travail_id` ;
- `date_debut` ;
- `date_fin` ;
- `sensitivity_level` ;
- `source_id`.

L'intitulé source du poste doit être conservé avec prudence, car il peut être rare et indirectement identifiant. Les analyses doivent privilégier `poste_concept_id`, `pcs_code` ou une famille métier.

### visite_sante_travail

Unité : visite ou contact santé-travail structuré.

Champs minimaux :

- `visite_id` ;
- `travailleur_id` ;
- `episode_poste_id` ;
- `date_visite` ;
- `mois_visite` si la date exacte n'est pas nécessaire ;
- `type_visite_concept_id` ;
- `motif_visite_concept_id` ;
- `professionnel_role` ;
- `sensitivity_level` ;
- `source_id`.

Le nom du professionnel de santé au travail n'est pas requis dans le MCD v0.1. Le rôle suffit pour les analyses : médecin du travail, infirmier santé travail, IPRP, équipe pluridisciplinaire, autre.

### conclusion_medicale

Unité : conclusion rattachée à une visite.

Champs minimaux :

- `conclusion_id` ;
- `visite_id` ;
- `conclusion_concept_id` ;
- `restriction_flag` ;
- `restriction_concept_id` ;
- `amenagement_flag` ;
- `amenagement_concept_id` ;
- `inaptitude_flag` ;
- `orientation_pdp_flag` ;
- `texte_court_source` ;
- `sensitivity_level` ;
- `source_id`.

`texte_court_source` est fortement sensible et doit rester optionnel. Le MVP doit privilégier les concepts structurés et les indicateurs booléens.

### exposition_professionnelle

Unité : exposition, nuisance ou facteur de risque professionnel.

Champs minimaux :

- `exposition_id` ;
- `travailleur_id` ;
- `episode_poste_id` ;
- `exposition_concept_id` ;
- `categorie_exposition` ;
- `agent_concept_id` ;
- `date_debut` ;
- `date_fin` ;
- `niveau_classe` ;
- `source_exposition_type` : visite, DUERP, fiche entreprise, étude de poste, déclaration, autre ;
- `mesure_prevention_concept_id` ;
- `sensitivity_level` ;
- `source_id`.

Les catégories minimales doivent couvrir au moins les contraintes biomécaniques, agents chimiques, bruit, vibrations, températures extrêmes, milieu hyperbare, travail de nuit, équipes alternantes, travail répétitif et autres expositions professionnelles pertinentes.

### action_prevention

Unité : action en milieu de travail ou action collective.

Champs minimaux :

- `action_prevention_id` ;
- `etablissement_id` ;
- `unite_travail_id` si l'action cible une unité de travail ;
- `type_action_concept_id` ;
- `date_action` ;
- `professionnel_role` ;
- `theme_action_concept_id` ;
- `population_cible_classe` ;
- `sensitivity_level` ;
- `source_id`.

### evenement_pdp

Unité : événement de prévention de la désinsertion professionnelle ou maintien en emploi.

Champs minimaux :

- `evenement_pdp_id` ;
- `travailleur_id` ;
- `visite_id` ;
- `type_evenement_concept_id` ;
- `date_evenement` ;
- `statut` ;
- `sensitivity_level` ;
- `source_id`.

Les événements PDP doivent être structurés. Les commentaires libres, courriers et pièces justificatives ne font pas partie du MCD v0.1.

## Tables sémantiques

### concept

Unité : concept standardisé.

Champs minimaux :

- `concept_id` ;
- `concept_code` ;
- `libelle` ;
- `domaine` ;
- `vocabulaire_id` ;
- `valid_start_date` ;
- `valid_end_date`.

### vocabulaire

Unité : vocabulaire ou nomenclature.

Champs minimaux :

- `vocabulaire_id` ;
- `nom` ;
- `version` ;
- `description`.

### synonyme_concept

Unité : synonyme ou libellé source rapproché d'un concept.

Champs minimaux :

- `synonyme_id` ;
- `concept_id` ;
- `libelle_source` ;
- `langue` ;
- `score_validation` ;
- `source_id`.

### source_vers_concept

Unité : mapping entre valeur source et concept cible.

Champs minimaux :

- `mapping_id` ;
- `source_system` ;
- `source_field` ;
- `source_value` ;
- `concept_id` ;
- `mapping_method` ;
- `confidence_score` ;
- `review_status` ;
- `source_id`.

## Tables de traçabilité et qualité

### source_mcdst

Unité : fichier, export, logiciel source ou lot de transformation.

Champs minimaux :

- `source_id` ;
- `source_system` ;
- `source_file` ;
- `source_hash` ;
- `source_kind` : réel local, synthétique, test, exemple ;
- `contains_personal_data` ;
- `contains_health_data` ;
- `mapping_version` ;
- `schema_version` ;
- `created_at`.

### anomalie_qualite

Unité : anomalie détectée par le moteur qualité.

Champs minimaux :

- `anomalie_id` ;
- `table_name` ;
- `field_name` ;
- `record_id` ;
- `rule_code` ;
- `severity` ;
- `message` ;
- `detected_at`.

## Tables dérivées

### cohorte

Unité : cohorte définie et exécutée.

Champs minimaux :

- `cohorte_id` ;
- `nom` ;
- `definition_version` ;
- `date_execution` ;
- `population_initiale_n` ;
- `population_finale_n`.

### attribut_cohorte

Unité : attribut ou variable dérivée pour une cohorte.

Champs minimaux :

- `attribut_id` ;
- `cohorte_id` ;
- `nom` ;
- `definition` ;
- `type` ;
- `source_fields`.

### indicateur_qualite

Unité : indicateur agrégé de qualité.

Champs minimaux :

- `indicateur_id` ;
- `scope` ;
- `metric_name` ;
- `metric_value` ;
- `computed_at` ;
- `source_id`.

### indicateur_derive

Unité : score, classe ou indicateur calculé pour un travailleur, un établissement, une unité de travail ou une cohorte.

Champs minimaux :

- `indicateur_derive_id` ;
- `entity_type` : travailleur, etablissement, unite_travail, cohorte ;
- `entity_id` ;
- `indicator_code` : par exemple `IRDP` ;
- `value_numeric` ;
- `value_class` ;
- `definition_version` ;
- `computed_at` ;
- `source_fields` ;
- `limitations` ;
- `sensitivity_level` ;
- `source_id`.

Un indicateur comme l'IRDP doit toujours être accompagné de sa définition versionnée, des variables sources utilisées et des limites connues. Il ne doit pas être stocké comme une donnée brute non expliquée.

## Données explicitement exclues des tables MCD-ST v0.1

Les éléments suivants doivent rester hors du MCD standardisé :

- identité civile directe du travailleur ;
- INS, NIR, numéro de sécurité sociale ;
- coordonnées personnelles ;
- coordonnées du médecin traitant ;
- salaire, coordonnées bancaires, sanctions ou évaluations RH ;
- opinions, activité syndicale, religion, origine ethnique ;
- documents médicaux complets, PDF, courriers et comptes rendus libres ;
- diagnostics détaillés non nécessaires à une finalité santé-travail explicitée ;
- données de tiers non nécessaires ;
- raison sociale, SIREN, SIRET, adresse complète et interlocuteurs nominatifs dans les exports analytiques ouverts ou partagés.

Ces données peuvent exister en source locale si le cadre du SPSTi l'autorise, mais elles ne doivent pas être incluses dans les tables MCD-ST standardisées destinées au cohorting, à la documentation et aux exemples ouverts.

## Domaines métier sensibles intégrés en v0.1

Plusieurs domaines métier sensibles sont intégrés dès v0.1 sous forme minimale,
structurée et sans texte libre :

- clinique, biométrie et examens complémentaires ;
- pathologies, accidents du travail et maladies professionnelles ;
- arrêts de travail ;
- vaccinations ;
- risques collectifs et DUERP.

Les tables minimales et limites d'intégration sont décrites dans
[EXTENSIONS_MODELE_METIER.md](EXTENSIONS_MODELE_METIER.md).
