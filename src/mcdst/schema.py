from __future__ import annotations


AUTO_THRESHOLD = 0.82
REVIEW_THRESHOLD = 0.50


TARGET_SCHEMA = {
    "travailleur": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "annee_naissance": {
            "aliases": ["annee_naissance", "annais", "annee naiss", "date_naissance", "anneen", "annee_n"],
            "type": "year",
            "sensitivity": "S2",
        },
        "sexe": {
            "aliases": ["sexe", "genre", "sexe_salarie", "civilitesexe"],
            "type": "categorical",
            "sensitivity": "S2",
            "transform": "normalize_sex",
        },
        "suivi_type_concept_id": {
            "aliases": ["type_suivi", "suivi", "suiv", "suivi medical", "suivi sante travail"],
            "type": "categorical",
            "sensitivity": "S3",
        },
    },
    "entreprise": {
        "entreprise_id": {
            "aliases": ["id_adh", "id_entreprise", "identifiant adherent", "adh", "cleadh", "cle_adh"],
            "type": "identifier",
            "sensitivity": "S1",
            "transform": "pseudonymize",
        },
        "secteur_naf": {
            "aliases": ["code_naf", "naf", "ape", "secteur_activite"],
            "type": "code",
            "sensitivity": "S1",
        },
        "taille_classe": {
            "aliases": ["effectif", "taille", "taille_entreprise", "nb_salaries", "nb"],
            "type": "numeric",
            "sensitivity": "S1",
            "transform": "classify_size",
        },
        "region": {
            "aliases": ["region", "territoire"],
            "type": "categorical",
            "sensitivity": "S1",
        },
    },
    "etablissement": {
        "etablissement_id": {
            "aliases": ["id_etab", "id_etablissement", "site_id", "id_site", "site"],
            "type": "identifier",
            "sensitivity": "S1",
            "transform": "pseudonymize",
        },
        "entreprise_id": {
            "aliases": ["id_adh", "id_entreprise", "adh", "cleadh", "cle_adh"],
            "type": "identifier",
            "sensitivity": "S1",
            "transform": "pseudonymize",
        },
        "secteur_naf": {
            "aliases": ["code_naf", "naf", "ape"],
            "type": "code",
            "sensitivity": "S1",
        },
        "taille_classe": {
            "aliases": ["effectif", "taille", "nb_salaries", "nb"],
            "type": "numeric",
            "sensitivity": "S1",
            "transform": "classify_size",
        },
        "region": {
            "aliases": ["region", "territoire"],
            "type": "categorical",
            "sensitivity": "S1",
        },
    },
    "unite_travail": {
        "unite_travail_id": {
            "aliases": ["service_ut", "unite_travail", "atelier", "service", "utlib", "ut_lib"],
            "type": "categorical",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "libelle_unite_source": {
            "aliases": ["service_ut", "unite_travail", "atelier", "service", "utlib", "ut_lib"],
            "type": "text",
            "sensitivity": "S2",
        },
        "etablissement_id": {
            "aliases": ["id_etab", "id_etablissement", "site_id", "site"],
            "type": "identifier",
            "sensitivity": "S1",
            "transform": "pseudonymize",
        },
    },
    "episode_poste": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "etablissement_id": {
            "aliases": ["id_etab", "id_etablissement", "site_id", "site"],
            "type": "identifier",
            "sensitivity": "S1",
            "transform": "pseudonymize",
        },
        "intitule_poste_source": {
            "aliases": ["poste", "intitule_poste", "emploi", "metier", "fonction", "libemploi", "lib_emploi"],
            "type": "text",
            "sensitivity": "S2",
        },
        "unite_travail_id": {
            "aliases": ["service_ut", "unite_travail", "atelier", "service", "utlib", "ut_lib"],
            "type": "categorical",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "date_debut": {
            "aliases": ["debut_poste", "date_debut_poste", "date_entree_poste", "datepriseposte", "deb"],
            "type": "date",
            "sensitivity": "S2",
        },
        "date_fin": {
            "aliases": ["fin_poste", "date_fin_poste", "date_sortie_poste", "datesortieposte", "fin"],
            "type": "date",
            "sensitivity": "S2",
        },
    },
    "visite_sante_travail": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "date_visite": {
            "aliases": ["datevisite", "date_visite", "dt_visite", "jour_visite", "jour"],
            "type": "date",
            "sensitivity": "S3",
        },
        "type_visite_concept_id": {
            "aliases": ["typevisite", "type_visite", "lib_type_visite", "nature_visite", "nature"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "normalize_visit_type",
        },
        "motif_visite_concept_id": {
            "aliases": ["motif", "motif_visite", "raison_visite", "raison"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "professionnel_role": {
            "aliases": ["pro", "professionnel", "role_professionnel", "acteur", "intervenant"],
            "type": "categorical",
            "sensitivity": "S2",
        },
    },
    "conclusion_medicale": {
        "conclusion_concept_id": {
            "aliases": ["avis", "conclusion", "conclusion_medicale", "decision"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "normalize_conclusion",
        },
        "restriction_flag": {
            "aliases": ["restriction", "restriction_txt", "restrictions", "reserve"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "to_flag",
        },
        "amenagement_flag": {
            "aliases": ["amenagement", "amenagement_poste", "adaptation"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "to_flag",
        },
    },
    "exposition_professionnelle": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "exposition_concept_id": {
            "aliases": ["nuisance", "exposition", "risque", "facteur_risque", "agent", "librisque", "lib_risque"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "normalize_exposure",
        },
        "categorie_exposition": {
            "aliases": ["nuisance", "exposition", "risque", "categorie", "librisque", "lib_risque"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "exposure_category",
        },
        "niveau_classe": {
            "aliases": ["niveau", "intensite", "frequence", "classe_niveau", "classe"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "date_debut": {
            "aliases": ["datedebutexpo", "debut_expo", "date_debut_exposition", "deb"],
            "type": "date",
            "sensitivity": "S3",
        },
        "date_fin": {
            "aliases": ["datefinexpo", "fin_expo", "date_fin_exposition", "fin"],
            "type": "date",
            "sensitivity": "S3",
        },
        "source_exposition_type": {
            "aliases": ["sourceinfo", "source_info", "source_exposition", "origine"],
            "type": "categorical",
            "sensitivity": "S3",
        },
    },
    "examen_complementaire": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "date_examen": {
            "aliases": ["dateexamen", "date_examen", "jour", "datevisite"],
            "type": "date",
            "sensitivity": "S3",
        },
        "examen_type_concept_id": {
            "aliases": ["typeexamen", "type_examen", "examen", "biometrie", "acte"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "resultat_valeur": {
            "aliases": ["resultat", "valeur", "mesure", "score"],
            "type": "numeric",
            "sensitivity": "S3",
        },
        "resultat_unite": {
            "aliases": ["unite", "unité", "unit", "unite_resultat"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "interpretation_concept_id": {
            "aliases": ["interpretation", "conclusion", "classe_resultat"],
            "type": "categorical",
            "sensitivity": "S3",
        },
    },
    "pathologie_atmp": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "date_evenement": {
            "aliases": ["dateevenement", "date_evenement", "date_at", "date_mp"],
            "type": "date",
            "sensitivity": "S3",
        },
        "type_evenement": {
            "aliases": ["typeevenement", "type_evenement", "type_atmp", "atmp"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "code_cim10": {
            "aliases": ["codecim10", "code_cim10", "cim10", "diagnostic_code"],
            "type": "code",
            "sensitivity": "S3",
        },
        "pathologie_concept_id": {
            "aliases": ["pathologie", "diagnostic", "libelle_diagnostic", "maladie"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "reconnaissance_statut": {
            "aliases": ["reconnu", "reconnaissance", "statut_reconnaissance"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "to_flag",
        },
    },
    "arret_travail": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "date_debut": {
            "aliases": ["datedebutarret", "date_debut_arret", "debut_arret", "date_debut"],
            "type": "date",
            "sensitivity": "S3",
        },
        "date_fin": {
            "aliases": ["datefinarret", "date_fin_arret", "fin_arret", "date_fin"],
            "type": "date",
            "sensitivity": "S3",
        },
        "type_arret": {
            "aliases": ["typearret", "type_arret", "motif_arret"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "lie_atmp_flag": {
            "aliases": ["lieatmp", "lie_atmp", "atmp", "lien_atmp"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "to_flag",
        },
    },
    "vaccination": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "clepers", "cle_personne"],
            "type": "identifier",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "vaccin_concept_id": {
            "aliases": ["vaccin", "vaccination", "valence"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "date_vaccination": {
            "aliases": ["datevaccination", "date_vaccination", "date_injection"],
            "type": "date",
            "sensitivity": "S3",
        },
        "statut_vaccinal": {
            "aliases": ["statutvaccinal", "statut_vaccinal", "statut"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "rappel_prevu": {
            "aliases": ["rappelprevu", "rappel_prevu", "date_rappel"],
            "type": "date",
            "sensitivity": "S3",
        },
    },
    "risque_unite_travail": {
        "etablissement_id": {
            "aliases": ["id_etab", "id_etablissement", "site_id", "site"],
            "type": "identifier",
            "sensitivity": "S1",
            "transform": "pseudonymize",
        },
        "unite_travail_id": {
            "aliases": ["service_ut", "unite_travail", "atelier", "service", "utlib", "ut_lib"],
            "type": "categorical",
            "sensitivity": "S2",
            "transform": "pseudonymize",
        },
        "risque_concept_id": {
            "aliases": ["risquecollectif", "risque_collectif", "risque", "librisque", "lib_risque"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "normalize_exposure",
        },
        "niveau_risque": {
            "aliases": ["niveaurisque", "niveau_risque", "niveau", "classe"],
            "type": "categorical",
            "sensitivity": "S3",
        },
        "mesure_prevention_source": {
            "aliases": ["mesureprevention", "mesure_prevention", "prevention", "mesures"],
            "type": "text",
            "sensitivity": "S3",
        },
        "date_evaluation": {
            "aliases": ["dateevaluation", "date_evaluation", "date_duerp"],
            "type": "date",
            "sensitivity": "S3",
        },
    },
}


FILE_ENTITY_HINTS = {
    "travailleur": ["salarie", "salaries", "travailleur"],
    "episode_poste": ["salarie", "poste", "emploi"],
    "unite_travail": ["salarie", "unite", "ut"],
    "entreprise": ["entreprise", "adherent", "etablissement"],
    "etablissement": ["entreprise", "etablissement", "site"],
    "visite_sante_travail": ["visite", "acte"],
    "conclusion_medicale": ["visite", "conclusion", "avis", "acte"],
    "exposition_professionnelle": ["exposition", "nuisance", "risque"],
    "examen_complementaire": ["biometrie", "examen", "audiogramme", "spirometrie"],
    "pathologie_atmp": ["pathologie", "atmp", "diagnostic"],
    "arret_travail": ["arret"],
    "vaccination": ["vaccin", "vaccination"],
    "risque_unite_travail": ["duerp", "risque collectif"],
}


FILENAME_ENTITY_SHORTCUTS = {
    "salaries": ["travailleur", "episode_poste", "unite_travail"],
    "salari": ["travailleur", "episode_poste", "unite_travail"],
    "individus": ["travailleur", "episode_poste", "unite_travail", "etablissement"],
    "individu": ["travailleur", "episode_poste", "unite_travail", "etablissement"],
    "entreprises": ["entreprise", "etablissement"],
    "entreprise": ["entreprise", "etablissement"],
    "structures": ["entreprise", "etablissement"],
    "structure": ["entreprise", "etablissement"],
    "etablissements": ["entreprise", "etablissement"],
    "visites": ["visite_sante_travail", "conclusion_medicale"],
    "visite": ["visite_sante_travail", "conclusion_medicale"],
    "actes": ["visite_sante_travail", "conclusion_medicale"],
    "acte": ["visite_sante_travail", "conclusion_medicale"],
    "expositions": ["exposition_professionnelle"],
    "exposition": ["exposition_professionnelle"],
    "risques": ["exposition_professionnelle"],
    "risque": ["exposition_professionnelle"],
    "biometrie": ["examen_complementaire"],
    "biometries": ["examen_complementaire"],
    "examens": ["examen_complementaire"],
    "examen": ["examen_complementaire"],
    "pathologies": ["pathologie_atmp"],
    "pathologie": ["pathologie_atmp"],
    "atmp": ["pathologie_atmp"],
    "arrets": ["arret_travail"],
    "arret": ["arret_travail"],
    "vaccinations": ["vaccination"],
    "vaccination": ["vaccination"],
    "duerp": ["risque_unite_travail"],
}


REQUIRED_FIELDS = {
    "travailleur": ["travailleur_id"],
    "entreprise": ["entreprise_id"],
    "etablissement": ["etablissement_id", "entreprise_id"],
    "unite_travail": ["unite_travail_id", "etablissement_id"],
    "episode_poste": ["travailleur_id", "intitule_poste_source"],
    "visite_sante_travail": ["travailleur_id", "date_visite", "type_visite_concept_id"],
    "conclusion_medicale": ["conclusion_concept_id"],
    "exposition_professionnelle": ["travailleur_id", "exposition_concept_id"],
    "examen_complementaire": ["travailleur_id", "date_examen", "examen_type_concept_id"],
    "pathologie_atmp": ["travailleur_id", "date_evenement", "type_evenement"],
    "arret_travail": ["travailleur_id", "date_debut"],
    "vaccination": ["travailleur_id", "vaccin_concept_id"],
    "risque_unite_travail": ["etablissement_id", "unite_travail_id", "risque_concept_id"],
}


VALUE_MAPPING_TRANSFORMS = {
    "normalize_sex",
    "normalize_visit_type",
    "normalize_conclusion",
    "normalize_exposure",
    "exposure_category",
    "to_flag",
    "classify_size",
}
