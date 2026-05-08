#!/usr/bin/env python3
"""
PROTOTYPE JETABLE - POC de mapping automatisé MCD-ST.

Objectif : valider le principe profilage -> inférence -> mapping scoré ->
YAML -> dry-run vers quelques tables MCD-ST, sans interface graphique.
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRATCH = ROOT / "_scratch_PROTOTYPE_WIPE_ME"
EXPORTS = SCRATCH / "exports_sources"
OUT = SCRATCH / "mcdst_dry_run"
DRAFT_OUT = SCRATCH / "mcdst_dry_run_draft"
VALIDATED_OUT = SCRATCH / "mcdst_dry_run_validated"

AUTO_THRESHOLD = 0.82
REVIEW_THRESHOLD = 0.50


TARGET_SCHEMA = {
    "travailleur": {
        "travailleur_id": {
            "aliases": ["id_salarie", "idsal", "id_sal", "matricule", "identifiant salarié", "clepers", "cle_personne"],
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
            "aliases": ["sexe", "genre", "sexe_salarie"],
            "type": "categorical",
            "sensitivity": "S2",
            "transform": "normalize_sex",
        },
        "suivi_type_concept_id": {
            "aliases": ["type_suivi", "suivi", "suivi medical", "suivi santé travail"],
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
            "aliases": ["region", "région", "territoire"],
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
            "aliases": ["region", "région"],
            "type": "categorical",
            "sensitivity": "S1",
        },
    },
    "unite_travail": {
        "unite_travail_id": {
            "aliases": ["service_ut", "unite_travail", "unité de travail", "atelier", "service", "utlib", "ut_lib"],
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
            "aliases": ["debut_poste", "date_debut_poste", "date_entree_poste", "datepriseposte"],
            "type": "date",
            "sensitivity": "S2",
        },
        "date_fin": {
            "aliases": ["fin_poste", "date_fin_poste", "date_sortie_poste", "datesortieposte"],
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
            "aliases": ["restriction", "restriction_txt", "restrictions", "reserve", "réserve"],
            "type": "categorical",
            "sensitivity": "S3",
            "transform": "to_flag",
        },
        "amenagement_flag": {
            "aliases": ["amenagement", "aménagement", "amenagement_poste", "adaptation"],
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
}

FILE_ENTITY_HINTS = {
    "travailleur": ["salarie", "salaries", "travailleur"],
    "episode_poste": ["salarie", "poste", "emploi"],
    "unite_travail": ["salarie", "unite", "ut"],
    "entreprise": ["entreprise", "adherent", "etablissement"],
    "etablissement": ["entreprise", "etablissement", "site"],
    "visite_sante_travail": ["visite"],
    "conclusion_medicale": ["visite", "conclusion", "avis"],
    "exposition_professionnelle": ["exposition", "nuisance", "risque"],
}

FILENAME_ENTITY_SHORTCUTS = {
    "salaries": ["travailleur", "episode_poste", "unite_travail"],
    "salari": ["travailleur", "episode_poste", "unite_travail"],
    "entreprises": ["entreprise", "etablissement"],
    "entreprise": ["entreprise", "etablissement"],
    "etablissements": ["entreprise", "etablissement"],
    "visites": ["visite_sante_travail", "conclusion_medicale"],
    "visite": ["visite_sante_travail", "conclusion_medicale"],
    "actes": ["visite_sante_travail", "conclusion_medicale"],
    "acte": ["visite_sante_travail", "conclusion_medicale"],
    "expositions": ["exposition_professionnelle"],
    "exposition": ["exposition_professionnelle"],
    "risques": ["exposition_professionnelle"],
    "risque": ["exposition_professionnelle"],
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
}


def main() -> None:
    reset_scratch()
    generate_synthetic_exports()

    profiles = profile_exports(EXPORTS)
    join_candidates = detect_join_candidates(profiles)
    proposals, blocked = propose_mapping(profiles)
    value_mappings = propose_value_mappings(profiles, proposals)
    mapping = build_mapping_document(profiles, proposals, blocked, join_candidates, value_mappings)
    write_text(SCRATCH / "mapping_propose.yaml", to_yaml(mapping))
    write_json(SCRATCH / "profiles.json", profiles)
    write_json(SCRATCH / "mapping_proposals.json", proposals)
    write_json(SCRATCH / "join_candidates.json", join_candidates)
    write_json(SCRATCH / "value_mappings.json", value_mappings)

    review_template = build_review_template(mapping)
    review_decisions = simulate_review_decisions(review_template)
    write_text(SCRATCH / "review_queue.yaml", to_yaml(review_template))
    write_text(SCRATCH / "review_decisions.yaml", to_yaml(review_decisions))

    draft_state = dry_run_transform(mapping, DRAFT_OUT)
    validated_mapping = apply_review_decisions(mapping, review_decisions, profiles)
    write_text(SCRATCH / "mapping_valide.yaml", to_yaml(validated_mapping))
    validated_state = dry_run_transform(validated_mapping, VALIDATED_OUT)

    write_json(SCRATCH / "quality_report_draft.json", draft_state["quality"])
    write_json(SCRATCH / "quality_report_validated.json", validated_state["quality"])

    print_state(profiles, mapping, draft_state, validated_mapping, validated_state)


def reset_scratch() -> None:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    EXPORTS.mkdir(parents=True)
    DRAFT_OUT.mkdir(parents=True)
    VALIDATED_OUT.mkdir(parents=True)


def generate_synthetic_exports() -> None:
    write_csv(
        EXPORTS / "export_01_individus.csv",
        [
            {
                "ClePers": "S001",
                "NomUsuel": "Martin",
                "Prenom": "Aline",
                "AnneeN": "1974",
                "CiviliteSexe": "Femme",
                "CleAdh": "A100",
                "Site": "E10",
                "LibEmploi": "Aide soignante",
                "UT_Lib": "EHPAD - Unité Alzheimer",
                "DatePrisePoste": "2018-04-01",
                "DateSortiePoste": "",
                "Suiv": "SIA",
                "TelPortable": "0600000001",
            },
            {
                "ClePers": "S002",
                "NomUsuel": "Bernard",
                "Prenom": "Karim",
                "AnneeN": "1982",
                "CiviliteSexe": "M",
                "CleAdh": "A101",
                "Site": "E11",
                "LibEmploi": "Menuisier poseur",
                "UT_Lib": "Atelier bois",
                "DatePrisePoste": "2020-01-15",
                "DateSortiePoste": "",
                "Suiv": "SIR",
                "TelPortable": "0600000002",
            },
            {
                "ClePers": "S003",
                "NomUsuel": "Dubois",
                "Prenom": "Nadia",
                "AnneeN": "1968",
                "CiviliteSexe": "F",
                "CleAdh": "A100",
                "Site": "E10",
                "LibEmploi": "ASH",
                "UT_Lib": "Bionettoyage",
                "DatePrisePoste": "2016-09-10",
                "DateSortiePoste": "",
                "Suiv": "SIA",
                "TelPortable": "0600000003",
            },
            {
                "ClePers": "S004",
                "NomUsuel": "Leroy",
                "Prenom": "Marc",
                "AnneeN": "1971",
                "CiviliteSexe": "H",
                "CleAdh": "A102",
                "Site": "E12",
                "LibEmploi": "Agent logistique",
                "UT_Lib": "Quai livraison",
                "DatePrisePoste": "2019-11-20",
                "DateSortiePoste": "",
                "Suiv": "SIR",
                "TelPortable": "0600000004",
            },
        ],
    )
    write_csv(
        EXPORTS / "export_02_structures.csv",
        [
            {
                "CleAdh": "A100",
                "Site": "E10",
                "Adherent": "Clinique du Centre",
                "Siret": "12345678900011",
                "APE": "8610Z",
                "Nb": "180",
                "Territoire": "Auvergne-Rhône-Alpes",
            },
            {
                "CleAdh": "A101",
                "Site": "E11",
                "Adherent": "Bois & Pose SARL",
                "Siret": "98765432100022",
                "APE": "4332A",
                "Nb": "22",
                "Territoire": "Auvergne-Rhône-Alpes",
            },
            {
                "CleAdh": "A102",
                "Site": "E12",
                "Adherent": "Logistique Sud",
                "Siret": "11122233300044",
                "APE": "5229B",
                "Nb": "8",
                "Territoire": "Auvergne-Rhône-Alpes",
            },
        ],
    )
    write_csv(
        EXPORTS / "export_03_actes.csv",
        [
            {
                "ClePers": "S001",
                "Jour": "2024-02-12",
                "Nature": "VR",
                "Raison": "AT > 30 jours",
                "Decision": "apte avec restrictions",
                "Reserve": "Port de charges <= 5 kg",
                "Adaptation": "poste aménagé",
                "Intervenant": "Médecin du travail",
                "CR": "Douleurs lombaires persistantes",
            },
            {
                "ClePers": "S002",
                "Jour": "2024-03-18",
                "Nature": "VIP",
                "Raison": "périodique",
                "Decision": "apte",
                "Reserve": "",
                "Adaptation": "non",
                "Intervenant": "Infirmier santé travail",
                "CR": "",
            },
            {
                "ClePers": "S003",
                "Jour": "2024-05-02",
                "Nature": "pre reprise",
                "Raison": "arrêt long",
                "Decision": "orientation PDP",
                "Reserve": "",
                "Adaptation": "aménagement horaire",
                "Intervenant": "Médecin du travail",
                "CR": "Situation à revoir en cellule PDP",
            },
            {
                "ClePers": "S004",
                "Jour": "2024-06-14",
                "Nature": "occasionnelle",
                "Raison": "demande salarié",
                "Decision": "avis complémentaire",
                "Reserve": "Pas de conduite prolongée",
                "Adaptation": "à étudier",
                "Intervenant": "Médecin du travail",
                "CR": "Demande liée à fatigue persistante",
            },
        ],
    )
    write_csv(
        EXPORTS / "export_04_risques.csv",
        [
            {
                "ClePers": "S001",
                "LibRisque": "Manutention patients",
                "Classe": "élevé",
                "Deb": "2018-04-01",
                "Fin": "",
                "Origine": "étude de poste",
            },
            {
                "ClePers": "S002",
                "LibRisque": "Poussières de bois",
                "Classe": "moyen",
                "Deb": "2020-01-15",
                "Fin": "",
                "Origine": "fiche entreprise",
            },
            {
                "ClePers": "S003",
                "LibRisque": "Gestes répétitifs",
                "Classe": "élevé",
                "Deb": "2016-09-10",
                "Fin": "",
                "Origine": "visite",
            },
            {
                "ClePers": "S004",
                "LibRisque": "Charge mentale",
                "Classe": "à qualifier",
                "Deb": "2019-11-20",
                "Fin": "",
                "Origine": "déclaration salarié",
            },
        ],
    )


def profile_exports(path: Path) -> list[dict]:
    profiles = []
    for file_path in sorted(path.glob("*.csv")):
        rows = read_csv(file_path)
        columns = []
        for column in rows[0].keys():
            values = [row[column] for row in rows]
            present_values = [value for value in values if value != ""]
            columns.append(
                {
                    "name": column,
                    "normalized": normalize(column),
                    "inferred_type": infer_type(column, values),
                    "completeness": round(non_empty(values) / max(len(values), 1), 3),
                    "distinct_count": len(set(present_values)),
                    "examples": first_examples(values),
                    "top_values": Counter(present_values).most_common(8),
                    "value_sample": sorted(set(present_values))[:20],
                    "sensitivity": infer_sensitivity(column, file_path.name),
                }
            )
        profiles.append(
            {
                "file": file_path.name,
                "row_count": len(rows),
                "columns": columns,
                "inferred_entities": infer_entities(file_path.name, columns),
            }
        )
    return profiles


def detect_join_candidates(profiles: list[dict]) -> list[dict]:
    candidates = []
    for left_index, left_profile in enumerate(profiles):
        for right_profile in profiles[left_index + 1 :]:
            for left_column in left_profile["columns"]:
                for right_column in right_profile["columns"]:
                    if left_column["sensitivity"] == "S4" or right_column["sensitivity"] == "S4":
                        continue
                    if left_column["inferred_type"] not in {"identifier", "code", "categorical"}:
                        continue
                    if right_column["inferred_type"] not in {"identifier", "code", "categorical"}:
                        continue
                    left_values = set(left_column["value_sample"])
                    right_values = set(right_column["value_sample"])
                    if not left_values or not right_values:
                        continue
                    overlap_values = left_values.intersection(right_values)
                    overlap_ratio = len(overlap_values) / min(len(left_values), len(right_values))
                    name_score = difflib.SequenceMatcher(None, left_column["normalized"], right_column["normalized"]).ratio()
                    type_bonus = 0.12 if left_column["inferred_type"] == right_column["inferred_type"] else 0.0
                    confidence = round(min((overlap_ratio * 0.78) + (name_score * 0.10) + type_bonus, 0.99), 3)
                    if confidence < 0.72:
                        continue
                    candidates.append(
                        {
                            "left_file": left_profile["file"],
                            "left_column": left_column["name"],
                            "right_file": right_profile["file"],
                            "right_column": right_column["name"],
                            "overlap_ratio": round(overlap_ratio, 3),
                            "overlap_values": sorted(overlap_values),
                            "confidence_score": confidence,
                            "status": "auto_validable" if confidence >= 0.85 else "a_revoir",
                        }
                    )
    return sorted(candidates, key=lambda item: (-item["confidence_score"], item["left_file"], item["right_file"]))


def propose_mapping(profiles: list[dict]) -> tuple[list[dict], list[dict]]:
    proposals = []
    blocked = []
    for profile in profiles:
        entities = profile["inferred_entities"]
        for column in profile["columns"]:
            if column["sensitivity"] == "S4":
                blocked.append(
                    {
                        "source_file": profile["file"],
                        "column": column["name"],
                        "sensitivity": "S4",
                        "reason": "identifiant direct, donnée libre sensible ou donnée entreprise directement identifiante",
                        "recommended_action": "exclude_from_mcd",
                    }
                )
                continue

            for entity in entities:
                best = best_field_for_column(column, entity)
                if not best:
                    continue
                status = "ignored"
                if best["confidence_score"] >= AUTO_THRESHOLD:
                    status = "auto_validable"
                elif best["confidence_score"] >= REVIEW_THRESHOLD:
                    status = "a_revoir"
                if status == "auto_validable" and requires_human_review(column, best):
                    status = "a_revoir"
                if status == "ignored":
                    continue
                proposals.append(
                    {
                        "source_file": profile["file"],
                        "source_column": column["name"],
                        "source_type": column["inferred_type"],
                        "source_sensitivity": column["sensitivity"],
                        "entity": entity,
                        "target_field": best["target_field"],
                        "target_sensitivity": best["target_sensitivity"],
                        "transform": best.get("transform"),
                        "confidence_score": best["confidence_score"],
                        "status": status,
                        "justification": best["justification"],
                        "examples": column["examples"],
                    }
                )
    return dedupe_proposals(proposals), blocked


def requires_human_review(column: dict, best: dict) -> bool:
    target_field = best["target_field"]
    if target_field in {"restriction_flag", "amenagement_flag"}:
        values = [value for value, _count in column["top_values"]]
        return not values_are_boolean_like(values)
    return False


def values_are_boolean_like(values: list[str]) -> bool:
    if not values:
        return True
    allowed = {"oui", "non", "true", "false", "0", "1", "y", "n", "yes", "no"}
    return all(normalize(value) in allowed for value in values if value)


def propose_value_mappings(profiles: list[dict], proposals: list[dict]) -> list[dict]:
    profile_index = {
        (profile["file"], column["name"]): column
        for profile in profiles
        for column in profile["columns"]
    }
    value_mappings = []
    for proposal in proposals:
        if proposal["status"] != "auto_validable":
            continue
        transform = proposal.get("transform")
        if transform not in {
            "normalize_sex",
            "normalize_visit_type",
            "normalize_conclusion",
            "normalize_exposure",
            "exposure_category",
            "to_flag",
            "classify_size",
        }:
            continue
        column = profile_index[(proposal["source_file"], proposal["source_column"])]
        mappings = []
        for source_value, count in column["top_values"]:
            target_value = apply_transform(transform, source_value)
            status = value_mapping_status(transform, source_value, target_value)
            mappings.append(
                {
                    "source_value": source_value,
                    "target_value": target_value,
                    "count": count,
                    "status": status,
                }
            )
        value_mappings.append(
            {
                "source_file": proposal["source_file"],
                "source_column": proposal["source_column"],
                "entity": proposal["entity"],
                "target_field": proposal["target_field"],
                "transform": transform,
                "review_status": "a_revoir"
                if any(item["status"] == "a_revoir" for item in mappings)
                else "auto_draft",
                "mappings": mappings,
            }
        )
    return value_mappings


def best_field_for_column(column: dict, entity: str) -> dict | None:
    candidates = []
    for field, spec in TARGET_SCHEMA[entity].items():
        alias_score = best_alias_score(column["name"], spec["aliases"])
        type_score = 1.0 if column["inferred_type"] == spec["type"] else compatible_type_score(column["inferred_type"], spec["type"])
        value_score = value_evidence(column, field)
        confidence = round((alias_score * 0.68) + (type_score * 0.20) + (value_score * 0.12), 3)
        if confidence <= 0.35:
            continue
        candidates.append(
            {
                "target_field": field,
                "target_sensitivity": spec["sensitivity"],
                "transform": spec.get("transform"),
                "confidence_score": min(confidence, 0.99),
                "justification": f"nom={alias_score:.2f}, type={type_score:.2f}, valeurs={value_score:.2f}",
            }
        )
    if not candidates:
        return None
    return max(candidates, key=lambda item: item["confidence_score"])


def build_mapping_document(
    profiles: list[dict],
    proposals: list[dict],
    blocked: list[dict],
    join_candidates: list[dict],
    value_mappings: list[dict],
) -> dict:
    entities = {}
    selected_groups, alternate_sources = select_entity_source_groups(proposals)
    for entity, group in selected_groups.items():
        entity = entities.setdefault(
            entity,
            {
                "source_file": group["source_file"],
                "review_status": "auto_draft",
                "fields": {},
            },
        )
        for proposal in group["proposals"]:
            entity["fields"][proposal["target_field"]] = {
                "source": proposal["source_column"],
                "confidence_score": proposal["confidence_score"],
                "sensitivity": proposal["target_sensitivity"],
                "transform": proposal["transform"],
                "review_status": proposal["status"],
            }

    return {
        "prototype": True,
        "source_system": "POC_SPSTI_MULTI_EXPORT",
        "mapping_version": "0.0.1-prototype",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "thresholds": {
            "auto_validable": AUTO_THRESHOLD,
            "a_revoir": REVIEW_THRESHOLD,
        },
        "source_files": [
            {
                "file": profile["file"],
                "row_count": profile["row_count"],
                "inferred_entities": profile["inferred_entities"],
            }
            for profile in profiles
        ],
        "join_candidates": join_candidates,
        "alternate_entity_sources": alternate_sources,
        "entities": entities,
        "review_queue": [p for p in proposals if p["status"] == "a_revoir"],
        "value_mappings": value_mappings,
        "blocked_fields": blocked,
    }


def select_entity_source_groups(proposals: list[dict]) -> tuple[dict, list[dict]]:
    groups = defaultdict(list)
    for proposal in proposals:
        if proposal["status"] == "auto_validable":
            groups[(proposal["entity"], proposal["source_file"])].append(proposal)

    scored_groups = defaultdict(list)
    for (entity, source_file), items in groups.items():
        fields = {item["target_field"] for item in items}
        required = set(REQUIRED_FIELDS.get(entity, []))
        required_count = len(fields.intersection(required))
        score = round((required_count * 5.0) + len(fields) + sum(item["confidence_score"] for item in items), 3)
        scored_groups[entity].append(
            {
                "entity": entity,
                "source_file": source_file,
                "score": score,
                "required_count": required_count,
                "field_count": len(fields),
                "proposals": sorted(items, key=lambda item: item["target_field"]),
            }
        )

    selected = {}
    alternates = []
    for entity, options in scored_groups.items():
        ranked = sorted(options, key=lambda item: (-item["score"], item["source_file"]))
        selected[entity] = ranked[0]
        for alternate in ranked[1:]:
            alternates.append(
                {
                    "entity": alternate["entity"],
                    "source_file": alternate["source_file"],
                    "score": alternate["score"],
                    "field_count": alternate["field_count"],
                    "required_count": alternate["required_count"],
                    "status": "not_selected",
                }
            )
    return selected, alternates


def build_review_template(mapping: dict) -> dict:
    return {
        "prototype": True,
        "review_version": "0.0.1-prototype",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "instructions": "Valider, corriger ou rejeter les propositions a_revoir. Les décisions ci-dessous sont simulées dans le POC.",
        "pending_column_mappings": [
            {
                "id": review_id(item),
                "source_file": item["source_file"],
                "source_column": item["source_column"],
                "entity": item["entity"],
                "target_field": item["target_field"],
                "transform": item["transform"],
                "confidence_score": item["confidence_score"],
                "examples": item["examples"],
                "suggested_action": "review",
            }
            for item in mapping["review_queue"]
        ],
        "pending_value_mappings": [
            group
            for group in mapping["value_mappings"]
            if group["review_status"] == "a_revoir"
        ],
    }


def simulate_review_decisions(review_template: dict) -> dict:
    decisions = []
    for item in review_template["pending_column_mappings"]:
        action = "reject"
        reason = "Proposition non validée par défaut dans le POC."
        if item["entity"] == "conclusion_medicale" and item["target_field"] == "restriction_flag":
            action = "approve"
            reason = "Réserve textuelle interprétée comme présence d'une restriction ; validation métier requise."
        if item["entity"] == "conclusion_medicale" and item["target_field"] == "amenagement_flag":
            action = "approve"
            reason = "Adaptation de poste interprétée comme présence d'un aménagement ; validation métier requise."
        decisions.append(
            {
                "id": item["id"],
                "action": action,
                "source_file": item["source_file"],
                "source_column": item["source_column"],
                "entity": item["entity"],
                "target_field": item["target_field"],
                "transform": item["transform"],
                "reviewer": "prototype_reviewer",
                "reason": reason,
            }
        )

    value_decisions = []
    for group in review_template["pending_value_mappings"]:
        reviewed_items = []
        for item in group["mappings"]:
            reviewed_items.append(
                {
                    "source_value": item["source_value"],
                    "target_value": item["target_value"],
                    "action": "approve" if item["status"] == "auto" else "needs_domain_review",
                    "reason": "Valeur reconnue automatiquement."
                    if item["status"] == "auto"
                    else "Valeur inconnue ou trop spécifique pour validation automatique.",
                }
            )
        value_decisions.append(
            {
                "source_file": group["source_file"],
                "source_column": group["source_column"],
                "entity": group["entity"],
                "target_field": group["target_field"],
                "transform": group["transform"],
                "decisions": reviewed_items,
            }
        )

    return {
        "prototype": True,
        "reviewed_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "column_mapping_decisions": decisions,
        "value_mapping_decisions": value_decisions,
    }


def apply_review_decisions(mapping: dict, review_decisions: dict, profiles: list[dict]) -> dict:
    validated = json.loads(json.dumps(mapping))
    approved_ids = {
        item["id"]: item
        for item in review_decisions["column_mapping_decisions"]
        if item["action"] == "approve"
    }

    for item in mapping["review_queue"]:
        decision = approved_ids.get(review_id(item))
        if not decision:
            continue
        entity_payload = validated["entities"].setdefault(
            item["entity"],
            {
                "source_file": item["source_file"],
                "review_status": "reviewed",
                "fields": {},
            },
        )
        if entity_payload["source_file"] != item["source_file"]:
            continue
        entity_payload["fields"][item["target_field"]] = {
            "source": item["source_column"],
            "confidence_score": item["confidence_score"],
            "sensitivity": item["target_sensitivity"],
            "transform": item["transform"],
            "review_status": "validated_by_human_review",
            "review_reason": decision["reason"],
        }

    approved_review_ids = set(approved_ids.keys())
    validated["review_queue"] = [
        item for item in validated["review_queue"] if review_id(item) not in approved_review_ids
    ]
    validated["review_decisions"] = review_decisions
    validated["value_mappings"] = rebuild_value_mappings_for_mapping(validated, profiles)
    validated["mapping_version"] = "0.0.1-prototype-reviewed"
    validated["review_status"] = "reviewed"
    return validated


def rebuild_value_mappings_for_mapping(mapping: dict, profiles: list[dict]) -> list[dict]:
    profile_index = {
        (profile["file"], column["name"]): column
        for profile in profiles
        for column in profile["columns"]
    }
    groups = []
    for entity, payload in mapping["entities"].items():
        source_file = payload["source_file"]
        for target_field, spec in payload["fields"].items():
            transform = spec.get("transform")
            if transform not in {
                "normalize_sex",
                "normalize_visit_type",
                "normalize_conclusion",
                "normalize_exposure",
                "exposure_category",
                "to_flag",
                "classify_size",
            }:
                continue
            column = profile_index.get((source_file, spec["source"]))
            if not column:
                continue
            mappings = []
            for source_value, count in column["top_values"]:
                target_value = apply_transform(transform, source_value)
                mappings.append(
                    {
                        "source_value": source_value,
                        "target_value": target_value,
                        "count": count,
                        "status": value_mapping_status(transform, source_value, target_value),
                    }
                )
            groups.append(
                {
                    "source_file": source_file,
                    "source_column": spec["source"],
                    "entity": entity,
                    "target_field": target_field,
                    "transform": transform,
                    "review_status": "a_revoir"
                    if any(item["status"] == "a_revoir" for item in mappings)
                    else "auto_draft",
                    "mappings": mappings,
                }
            )
    return groups


def review_id(item: dict) -> str:
    raw = f"{item['source_file']}|{item['source_column']}|{item['entity']}|{item['target_field']}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def dry_run_transform(mapping: dict, output_dir: Path) -> dict:
    entity_maps = {
        entity: {
            "source_file": payload["source_file"],
            "fields": {field: spec["source"] for field, spec in payload["fields"].items()},
        }
        for entity, payload in mapping["entities"].items()
    }
    tables = {}
    quality = {"rules": [], "summary": {}}

    tables["travailleur"] = build_travailleurs(entity_maps)
    tables["entreprise"] = build_entreprises(entity_maps)
    tables["etablissement"] = build_etablissements(entity_maps)
    tables["unite_travail"] = build_unites_travail(entity_maps)
    tables["episode_poste"] = build_episodes_poste(entity_maps)
    tables["visite_sante_travail"] = build_visites(entity_maps)
    tables["conclusion_medicale"] = build_conclusions(entity_maps)
    tables["exposition_professionnelle"] = build_expositions(entity_maps)

    for name, rows in tables.items():
        write_csv(output_dir / f"{name}.csv", rows)

    quality["rules"].extend(check_required_mappings(mapping))
    quality["rules"].extend(check_mapping_source_columns(mapping))
    quality["rules"].extend(check_review_queue(mapping))
    quality["rules"].extend(check_value_mapping_reviews(mapping))
    quality["rules"].extend(check_join_candidates(mapping))
    quality["rules"].extend(check_join_coverage(tables))
    quality["rules"].extend(check_blocked_fields(mapping))
    quality["summary"] = {
        "generated_tables": {name: len(rows) for name, rows in tables.items()},
        "blocked_fields_count": len(mapping["blocked_fields"]),
        "review_queue_count": len(mapping["review_queue"]),
        "join_candidates_count": len(mapping["join_candidates"]),
        "value_mapping_groups_count": len(mapping["value_mappings"]),
        "output_dir": str(output_dir.relative_to(ROOT)),
    }
    return {"tables": tables, "quality": quality}


def build_travailleurs(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "travailleur")
    fields = entity_maps.get("travailleur", {}).get("fields", {})
    out = {}
    for row in rows:
        source_id = row.get(fields.get("travailleur_id", ""), "")
        if not source_id:
            continue
        tid = hash_id("T", source_id)
        out[tid] = {
            "travailleur_id": tid,
            "annee_naissance": row.get(fields.get("annee_naissance", ""), ""),
            "age_classe": age_class(row.get(fields.get("annee_naissance", ""), "")),
            "sexe": normalize_sex(row.get(fields.get("sexe", ""), "")),
            "suivi_type_concept_id": normalize_upper(row.get(fields.get("suivi_type_concept_id", ""), "")),
            "sensitivity_level": "S3",
            "source_id": "poc_lot_001",
        }
    return list(out.values())


def build_entreprises(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "entreprise")
    fields = entity_maps.get("entreprise", {}).get("fields", {})
    out = {}
    for row in rows:
        source_id = row.get(fields.get("entreprise_id", ""), "")
        if not source_id:
            continue
        eid = hash_id("E", source_id)
        out[eid] = {
            "entreprise_id": eid,
            "secteur_naf": row.get(fields.get("secteur_naf", ""), ""),
            "taille_classe": classify_size(row.get(fields.get("taille_classe", ""), "")),
            "region": row.get(fields.get("region", ""), ""),
            "sensitivity_level": "S1",
            "source_id": "poc_lot_001",
        }
    return list(out.values())


def build_etablissements(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "etablissement")
    fields = entity_maps.get("etablissement", {}).get("fields", {})
    out = {}
    for row in rows:
        source_id = row.get(fields.get("etablissement_id", ""), "")
        if not source_id:
            continue
        etid = hash_id("ET", source_id)
        entreprise_source = row.get(fields.get("entreprise_id", ""), "")
        out[etid] = {
            "etablissement_id": etid,
            "entreprise_id": hash_id("E", entreprise_source) if entreprise_source else "",
            "secteur_naf": row.get(fields.get("secteur_naf", ""), ""),
            "taille_classe": classify_size(row.get(fields.get("taille_classe", ""), "")),
            "region": row.get(fields.get("region", ""), ""),
            "sensitivity_level": "S1",
            "source_id": "poc_lot_001",
        }
    return list(out.values())


def build_unites_travail(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "unite_travail")
    fields = entity_maps.get("unite_travail", {}).get("fields", {})
    out = {}
    for row in rows:
        unit_source = row.get(fields.get("unite_travail_id", ""), "")
        et_source = row.get(fields.get("etablissement_id", ""), "")
        if not unit_source:
            continue
        uid = hash_id("UT", f"{et_source}|{unit_source}")
        out[uid] = {
            "unite_travail_id": uid,
            "etablissement_id": hash_id("ET", et_source) if et_source else "",
            "libelle_unite_source": row.get(fields.get("libelle_unite_source", ""), unit_source),
            "unite_travail_concept_id": normalize_upper(unit_source),
            "sensitivity_level": "S2",
            "source_id": "poc_lot_001",
        }
    return list(out.values())


def build_episodes_poste(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "episode_poste")
    fields = entity_maps.get("episode_poste", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        sal = row.get(fields.get("travailleur_id", ""), "")
        poste = row.get(fields.get("intitule_poste_source", ""), "")
        if not sal or not poste:
            continue
        et_source = row.get(fields.get("etablissement_id", ""), "")
        unit_source = row.get(fields.get("unite_travail_id", ""), "")
        out.append(
            {
                "episode_poste_id": hash_id("EP", f"{sal}|{poste}|{index}"),
                "travailleur_id": hash_id("T", sal),
                "etablissement_id": hash_id("ET", et_source) if et_source else "",
                "unite_travail_id": hash_id("UT", f"{et_source}|{unit_source}") if unit_source else "",
                "intitule_poste_source": poste,
                "poste_concept_id": normalize_upper(poste),
                "date_debut": row.get(fields.get("date_debut", ""), ""),
                "date_fin": row.get(fields.get("date_fin", ""), ""),
                "sensitivity_level": "S2",
                "source_id": "poc_lot_001",
            }
        )
    return out


def build_visites(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "visite_sante_travail")
    fields = entity_maps.get("visite_sante_travail", {}).get("fields", {})
    out = []
    for row in rows:
        sal = row.get(fields.get("travailleur_id", ""), "")
        date_visite = row.get(fields.get("date_visite", ""), "")
        visit_type = row.get(fields.get("type_visite_concept_id", ""), "")
        if not sal or not date_visite:
            continue
        out.append(
            {
                "visite_id": hash_id("V", f"{sal}|{date_visite}|{visit_type}"),
                "travailleur_id": hash_id("T", sal),
                "date_visite": date_visite,
                "type_visite_concept_id": normalize_visit_type(visit_type),
                "motif_visite_concept_id": normalize_upper(row.get(fields.get("motif_visite_concept_id", ""), "")),
                "professionnel_role": row.get(fields.get("professionnel_role", ""), ""),
                "sensitivity_level": "S3",
                "source_id": "poc_lot_001",
            }
        )
    return out


def build_conclusions(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "conclusion_medicale")
    visit_fields = entity_maps.get("visite_sante_travail", {}).get("fields", {})
    fields = entity_maps.get("conclusion_medicale", {}).get("fields", {})
    out = []
    for row in rows:
        sal = row.get(visit_fields.get("travailleur_id", ""), "")
        date_visite = row.get(visit_fields.get("date_visite", ""), "")
        visit_type = row.get(visit_fields.get("type_visite_concept_id", ""), "")
        if not sal or not date_visite:
            continue
        conclusion_raw = row.get(fields.get("conclusion_concept_id", ""), "")
        out.append(
            {
                "conclusion_id": hash_id("C", f"{sal}|{date_visite}|{conclusion_raw}"),
                "visite_id": hash_id("V", f"{sal}|{date_visite}|{visit_type}"),
                "conclusion_concept_id": normalize_conclusion(conclusion_raw),
                "restriction_flag": to_flag(row.get(fields.get("restriction_flag", ""), "")),
                "amenagement_flag": to_flag(row.get(fields.get("amenagement_flag", ""), "")),
                "inaptitude_flag": "false",
                "orientation_pdp_flag": "true" if "pdp" in normalize(conclusion_raw) else "false",
                "sensitivity_level": "S3",
                "source_id": "poc_lot_001",
            }
        )
    return out


def build_expositions(entity_maps: dict) -> list[dict]:
    rows = read_entity_source(entity_maps, "exposition_professionnelle")
    fields = entity_maps.get("exposition_professionnelle", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        sal = row.get(fields.get("travailleur_id", ""), "")
        exposure = row.get(fields.get("exposition_concept_id", ""), "")
        if not sal or not exposure:
            continue
        out.append(
            {
                "exposition_id": hash_id("X", f"{sal}|{exposure}|{index}"),
                "travailleur_id": hash_id("T", sal),
                "exposition_concept_id": normalize_exposure(exposure),
                "categorie_exposition": exposure_category(exposure),
                "niveau_classe": normalize_upper(row.get(fields.get("niveau_classe", ""), "")),
                "date_debut": row.get(fields.get("date_debut", ""), ""),
                "date_fin": row.get(fields.get("date_fin", ""), ""),
                "source_exposition_type": normalize_upper(row.get(fields.get("source_exposition_type", ""), "")),
                "sensitivity_level": "S3",
                "source_id": "poc_lot_001",
            }
        )
    return out


def check_required_mappings(mapping: dict) -> list[dict]:
    rules = []
    entities = mapping["entities"]
    for entity, required_fields in REQUIRED_FIELDS.items():
        mapped_fields = set(entities.get(entity, {}).get("fields", {}).keys())
        missing = [field for field in required_fields if field not in mapped_fields]
        rules.append(
            {
                "rule": f"required_mapping:{entity}",
                "severity": "bloquant" if missing else "info",
                "status": "failed" if missing else "passed",
                "message": f"Champs requis manquants: {', '.join(missing)}" if missing else "Tous les champs requis sont mappés.",
            }
        )
    return rules


def check_mapping_source_columns(mapping: dict) -> list[dict]:
    rules = []
    for entity, payload in mapping["entities"].items():
        source_file = payload["source_file"]
        source_rows = read_csv(EXPORTS / source_file)
        available_columns = set(source_rows[0].keys()) if source_rows else set()
        missing_sources = [
            spec["source"]
            for spec in payload["fields"].values()
            if spec["source"] not in available_columns
        ]
        rules.append(
            {
                "rule": f"mapping_source_columns:{entity}",
                "severity": "bloquant" if missing_sources else "info",
                "status": "failed" if missing_sources else "passed",
                "message": f"Colonnes sources absentes de {source_file}: {', '.join(missing_sources)}"
                if missing_sources
                else f"Toutes les colonnes mappées existent dans {source_file}.",
            }
        )
    return rules


def check_review_queue(mapping: dict) -> list[dict]:
    queue_count = len(mapping["review_queue"])
    return [
        {
            "rule": "review_queue:pending_mapping_proposals",
            "severity": "alerte" if queue_count else "info",
            "status": "failed" if queue_count else "passed",
            "message": f"{queue_count} propositions de mapping nécessitent une revue humaine."
            if queue_count
            else "Aucune proposition de mapping en attente de revue.",
        }
    ]


def check_value_mapping_reviews(mapping: dict) -> list[dict]:
    pending = []
    for group in mapping["value_mappings"]:
        for item in group["mappings"]:
            if item["status"] == "a_revoir":
                pending.append(
                    f"{group['source_file']}::{group['source_column']} "
                    f"{item['source_value']}->{item['target_value']}"
                )
    return [
        {
            "rule": "review_queue:pending_value_mappings",
            "severity": "alerte" if pending else "info",
            "status": "failed" if pending else "passed",
            "message": f"{len(pending)} valeurs de nomenclature nécessitent une revue métier: {', '.join(pending[:5])}"
            if pending
            else "Aucune valeur de nomenclature en attente de revue métier.",
        }
    ]


def check_join_candidates(mapping: dict) -> list[dict]:
    join_count = len(mapping["join_candidates"])
    return [
        {
            "rule": "source_graph:join_candidates",
            "severity": "alerte" if join_count == 0 else "info",
            "status": "failed" if join_count == 0 else "passed",
            "message": f"{join_count} jointures candidates détectées entre exports."
            if join_count
            else "Aucune jointure candidate détectée entre exports.",
        }
    ]


def check_join_coverage(tables: dict) -> list[dict]:
    travailleur_ids = {row["travailleur_id"] for row in tables.get("travailleur", [])}
    rules = []
    for table_name in ["visite_sante_travail", "exposition_professionnelle", "episode_poste"]:
        unknown = [row.get("travailleur_id") for row in tables.get(table_name, []) if row.get("travailleur_id") not in travailleur_ids]
        rules.append(
            {
                "rule": f"join_coverage:{table_name}.travailleur_id",
                "severity": "alerte" if unknown else "info",
                "status": "failed" if unknown else "passed",
                "message": f"{len(unknown)} identifiants travailleurs absents de la table travailleur." if unknown else "Tous les travailleurs référencés existent.",
            }
        )
    return rules


def check_blocked_fields(mapping: dict) -> list[dict]:
    return [
        {
            "rule": "sensitivity:S4_blocked",
            "severity": "info",
            "status": "passed",
            "message": f"{len(mapping['blocked_fields'])} champs S4 exclus du MCD standardisé.",
        }
    ]


def print_state(
    profiles: list[dict],
    mapping: dict,
    draft_state: dict,
    validated_mapping: dict,
    validated_state: dict,
) -> None:
    print("\n=== POC MAPPING MCD-ST ===")
    print("Prototype jetable : profilage -> mapping -> YAML -> dry-run MCD-ST")
    print(f"Dossier généré : {SCRATCH.relative_to(ROOT)}")

    print("\n--- 1. Profilage des exports ---")
    for profile in profiles:
        print(f"{profile['file']} | {profile['row_count']} lignes | entités: {', '.join(profile['inferred_entities'])}")
        for column in profile["columns"]:
            print(
                f"  - {column['name']:<22} type={column['inferred_type']:<11} "
                f"compl={column['completeness']:<4} sens={column['sensitivity']} exemples={column['examples']}"
            )

    print("\n--- 2. Champs bloqués S4 ---")
    for item in mapping["blocked_fields"]:
        print(f"  - {item['source_file']}::{item['column']} -> {item['recommended_action']} ({item['reason']})")

    print("\n--- 3. Graphe source : jointures candidates ---")
    if not mapping["join_candidates"]:
        print("  Aucune jointure candidate.")
    for join in mapping["join_candidates"]:
        print(
            f"  {join['left_file']}::{join['left_column']} <-> "
            f"{join['right_file']}::{join['right_column']} "
            f"score={join['confidence_score']} overlap={join['overlap_ratio']} status={join['status']}"
        )

    print("\n--- 4. Mapping auto-validable ---")
    for entity, payload in mapping["entities"].items():
        print(f"[{entity}] depuis {payload['source_file']}")
        for field, spec in payload["fields"].items():
            print(
                f"  {field:<28} <- {spec['source']:<18} "
                f"score={spec['confidence_score']} sens={spec['sensitivity']} transform={spec['transform']}"
            )

    print("\n--- 5. Mapping de valeurs proposé ---")
    for group in mapping["value_mappings"]:
        print(
            f"  {group['source_file']}::{group['source_column']} -> "
            f"{group['entity']}.{group['target_field']} ({group['transform']}) status={group['review_status']}"
        )
        for item in group["mappings"]:
            print(f"    - {item['source_value']} -> {item['target_value']} [{item['status']}] n={item['count']}")

    print("\n--- 6. File de revue humaine simulée ---")
    if not mapping["review_queue"]:
        print("  Aucune proposition intermédiaire.")
    for item in mapping["review_queue"]:
        print(
            f"  {item['source_file']}::{item['source_column']} -> "
            f"{item['entity']}.{item['target_field']} score={item['confidence_score']} "
            f"justif={item['justification']}"
        )

    print("\n--- 7. Revue simulée appliquée ---")
    approved = [
        item for item in validated_mapping.get("review_decisions", {}).get("column_mapping_decisions", [])
        if item["action"] == "approve"
    ]
    remaining = len(validated_mapping["review_queue"])
    for item in approved:
        print(f"  + {item['source_file']}::{item['source_column']} -> {item['entity']}.{item['target_field']} ({item['reason']})")
    print(f"  Restent en revue colonne : {remaining}")

    print("\n--- 8. Dry-run MCD-ST brouillon ---")
    for table, rows in draft_state["tables"].items():
        print(f"  {table:<28} {len(rows)} lignes -> {DRAFT_OUT.relative_to(ROOT) / (table + '.csv')}")

    print("\n--- 9. Dry-run MCD-ST validé ---")
    for table, rows in validated_state["tables"].items():
        print(f"  {table:<28} {len(rows)} lignes -> {VALIDATED_OUT.relative_to(ROOT) / (table + '.csv')}")

    print("\n--- 10. Qualité brouillon ---")
    for rule in draft_state["quality"]["rules"]:
        print(f"  [{rule['severity']}] {rule['rule']} : {rule['status']} - {rule['message']}")

    print("\n--- 11. Qualité validée ---")
    for rule in validated_state["quality"]["rules"]:
        print(f"  [{rule['severity']}] {rule['rule']} : {rule['status']} - {rule['message']}")

    print("\n--- Fichiers utiles ---")
    print(f"  Mapping YAML       : {SCRATCH.relative_to(ROOT) / 'mapping_propose.yaml'}")
    print(f"  Revue YAML         : {SCRATCH.relative_to(ROOT) / 'review_queue.yaml'}")
    print(f"  Décisions YAML     : {SCRATCH.relative_to(ROOT) / 'review_decisions.yaml'}")
    print(f"  Mapping validé     : {SCRATCH.relative_to(ROOT) / 'mapping_valide.yaml'}")
    print(f"  Profilage JSON     : {SCRATCH.relative_to(ROOT) / 'profiles.json'}")
    print(f"  Propositions JSON  : {SCRATCH.relative_to(ROOT) / 'mapping_proposals.json'}")
    print(f"  Jointures JSON     : {SCRATCH.relative_to(ROOT) / 'join_candidates.json'}")
    print(f"  Valeurs JSON       : {SCRATCH.relative_to(ROOT) / 'value_mappings.json'}")
    print(f"  Qualité brouillon  : {SCRATCH.relative_to(ROOT) / 'quality_report_draft.json'}")
    print(f"  Qualité validée    : {SCRATCH.relative_to(ROOT) / 'quality_report_validated.json'}")


def infer_entities(filename: str, columns: list[dict]) -> list[str]:
    normalized_filename = normalize(filename)
    for hint, entities in FILENAME_ENTITY_SHORTCUTS.items():
        if hint in normalized_filename:
            return entities

    scores = Counter()
    for entity, hints in FILE_ENTITY_HINTS.items():
        for hint in hints:
            if normalize(hint) in normalized_filename:
                scores[entity] += 3
    column_names = " ".join(column["normalized"] for column in columns)
    for entity, fields in TARGET_SCHEMA.items():
        for spec in fields.values():
            if any(normalize(alias) in column_names for alias in spec["aliases"]):
                scores[entity] += 1
    selected = [entity for entity, score in scores.items() if score >= 2]
    return sorted(selected, key=lambda entity: (-scores[entity], entity))


def infer_type(name: str, values: list[str]) -> str:
    present = [value.strip() for value in values if value.strip()]
    normalized_name = normalize(name)
    if normalized_name in {"clepers", "cleadh", "site"}:
        return "identifier"
    if normalized_name.startswith("cle") and len(set(present)) >= max(1, int(len(present) * 0.6)):
        return "identifier"
    if any(token in normalized_name for token in ["date", "debut", "fin"]):
        return "date"
    if "id" in normalized_name and len(set(present)) >= max(1, int(len(present) * 0.7)):
        return "identifier"
    if present and all(is_year(value) for value in present):
        return "year"
    if present and all(is_date(value) for value in present):
        return "date"
    if present and all(is_number(value) for value in present):
        return "numeric"
    if present and all(re.match(r"^[0-9]{2,4}[a-zA-Z]?$", value) for value in present):
        return "code"
    if len(set(normalize(value) for value in present)) <= max(8, int(len(present) * 0.6)):
        return "categorical"
    return "text"


def infer_sensitivity(name: str, filename: str) -> str:
    column_name = normalize(name)
    n = normalize(f"{filename} {name}")
    s4 = [
        "nom",
        "prenom",
        "mail",
        "email",
        "telephone",
        "tel",
        "adresse",
        "nir",
        "ins",
        "siret",
        "siren",
        "raisonsociale",
        "commentairemedical",
        "commentaire",
        "adherent",
        "nomusuel",
        "courrier",
        "pdf",
        "note",
        "cr",
    ]
    if any(token in column_name for token in s4):
        return "S4"
    if any(token in column_name for token in ["idsal", "idtravailleur", "idsalarie", "matricule", "clepers"]):
        return "S2"
    if any(token in column_name for token in ["anneen", "civilitesexe", "libemploi", "utlib"]):
        return "S2"
    s3 = [
        "visite",
        "avis",
        "conclusion",
        "restriction",
        "amenagement",
        "adaptation",
        "reserve",
        "decision",
        "nature",
        "raison",
        "inaptitude",
        "nuisance",
        "risque",
        "exposition",
        "motif",
        "pdp",
        "sante",
        "niveau",
        "classe",
        "origine",
    ]
    if any(token in n for token in s3):
        return "S3"
    s2 = ["sal", "salarie", "travailleur", "poste", "service", "ut", "suivi", "sexe", "naiss"]
    if any(token in n for token in s2):
        return "S2"
    return "S1"


def dedupe_proposals(proposals: list[dict]) -> list[dict]:
    best_by_target = {}
    for proposal in proposals:
        key = (proposal["source_file"], proposal["entity"], proposal["target_field"])
        current = best_by_target.get(key)
        if not current or proposal["confidence_score"] > current["confidence_score"]:
            best_by_target[key] = proposal
    return sorted(best_by_target.values(), key=lambda p: (p["source_file"], p["entity"], p["target_field"]))


def best_alias_score(name: str, aliases: list[str]) -> float:
    n = normalize(name)
    scores = []
    for alias in aliases:
        a = normalize(alias)
        if n == a:
            scores.append(1.0)
        elif n in a or a in n:
            scores.append(0.92)
        else:
            scores.append(difflib.SequenceMatcher(None, n, a).ratio())
    return max(scores)


def compatible_type_score(source_type: str, target_type: str) -> float:
    compatible = {
        ("identifier", "categorical"),
        ("categorical", "text"),
        ("text", "categorical"),
        ("year", "numeric"),
        ("numeric", "year"),
        ("code", "categorical"),
        ("categorical", "code"),
    }
    return 0.65 if (source_type, target_type) in compatible else 0.25


def value_evidence(column: dict, field: str) -> float:
    examples = [normalize(value) for value in column["examples"]]
    if field == "sexe" and set(examples).intersection({"f", "m", "femme", "homme"}):
        return 1.0
    if "date" in field and column["inferred_type"] == "date":
        return 1.0
    if "annee" in field and column["inferred_type"] == "year":
        return 1.0
    if "region" in field and any("auvergne" in value or "rhone" in value for value in examples):
        return 1.0
    if "naf" in field and any(re.match(r"^[0-9]{4}[a-z]$", value) for value in examples):
        return 1.0
    if "flag" in field and set(examples).intersection({"oui", "non", "true", "false"}):
        return 0.9
    return 0.5


def read_entity_source(entity_maps: dict, entity: str) -> list[dict]:
    source_file = entity_maps.get(entity, {}).get("source_file")
    if not source_file:
        return []
    return read_csv(EXPORTS / source_file)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def to_yaml(value: object, indent: int = 0) -> str:
    spaces = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{spaces}{key}:")
                lines.append(to_yaml(item, indent + 2))
            else:
                lines.append(f"{spaces}{key}: {yaml_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{spaces}[]"
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{spaces}-")
                lines.append(to_yaml(item, indent + 2))
            elif isinstance(item, list):
                lines.append(f"{spaces}-")
                lines.append(to_yaml(item, indent + 2))
            else:
                lines.append(f"{spaces}- {yaml_scalar(item)}")
        return "\n".join(lines)
    return f"{spaces}{yaml_scalar(value)}"


def yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(char in text for char in [":", "#", "{", "}", "[", "]", ","]) or text.lower() in {"true", "false", "null"}:
        return json.dumps(text, ensure_ascii=False)
    return text


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value))
    ascii_only = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", ascii_only.lower())


def normalize_upper(value: str) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text.upper()


def hash_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(f"mcdst-poc|{value}".encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def non_empty(values: list[str]) -> int:
    return sum(1 for value in values if value.strip())


def first_examples(values: list[str]) -> list[str]:
    seen = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
        if len(seen) == 3:
            break
    return seen


def is_year(value: str) -> bool:
    return bool(re.match(r"^(19|20)[0-9]{2}$", value))


def is_date(value: str) -> bool:
    if not value:
        return False
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            pass
    return False


def is_number(value: str) -> bool:
    try:
        float(value.replace(",", "."))
        return True
    except ValueError:
        return False


def normalize_sex(value: str) -> str:
    n = normalize(value)
    if n in {"f", "femme"}:
        return "F"
    if n in {"m", "h", "homme"}:
        return "M"
    return "INCONNU" if value else ""


def classify_size(value: str) -> str:
    if not is_number(value):
        return ""
    number = int(float(value.replace(",", ".")))
    if number < 11:
        return "TPE_1_10"
    if number < 50:
        return "PME_11_49"
    if number < 250:
        return "ETI_50_249"
    return "GE_250_PLUS"


def apply_transform(transform: str, value: str) -> str:
    if transform == "normalize_sex":
        return normalize_sex(value)
    if transform == "normalize_visit_type":
        return normalize_visit_type(value)
    if transform == "normalize_conclusion":
        return normalize_conclusion(value)
    if transform == "normalize_exposure":
        return normalize_exposure(value)
    if transform == "exposure_category":
        return exposure_category(value)
    if transform == "to_flag":
        return to_flag(value)
    if transform == "classify_size":
        return classify_size(value)
    return value


def value_mapping_status(transform: str, source_value: str, target_value: str) -> str:
    if not source_value:
        return "ignore_empty"
    if transform == "normalize_visit_type" and target_value not in {"REPRISE", "PRE_REPRISE", "VIP_PERIODIQUE"}:
        return "a_revoir"
    if transform == "normalize_conclusion" and target_value not in {
        "APTE",
        "APTE_AVEC_RESTRICTION",
        "INAPTE",
        "ORIENTATION_PDP",
    }:
        return "a_revoir"
    known_exposures = {"POUSSIERES_BOIS", "MANUTENTION_MANUELLE", "GESTES_REPETITIFS"}
    if transform == "normalize_exposure" and target_value not in known_exposures:
        return "a_revoir"
    if transform == "exposure_category" and target_value == "AUTRE":
        return "a_revoir"
    if transform == "normalize_sex" and target_value == "INCONNU":
        return "a_revoir"
    if transform == "classify_size" and not target_value:
        return "a_revoir"
    return "auto"


def age_class(year: str) -> str:
    if not is_year(year):
        return ""
    age = datetime.now(UTC).year - int(year)
    if age < 30:
        return "AGE_18_29"
    if age < 45:
        return "AGE_30_44"
    if age < 55:
        return "AGE_45_54"
    return "AGE_55_PLUS"


def normalize_visit_type(value: str) -> str:
    n = normalize(value)
    if n in {"vr", "visitereprise"}:
        return "REPRISE"
    if "prereprise" in n or "pre" in n and "reprise" in n:
        return "PRE_REPRISE"
    if "reprise" in n:
        return "REPRISE"
    if "period" in n or "vip" in n:
        return "VIP_PERIODIQUE"
    return normalize_upper(value)


def normalize_conclusion(value: str) -> str:
    n = normalize(value)
    if "pdp" in n:
        return "ORIENTATION_PDP"
    if "restriction" in n:
        return "APTE_AVEC_RESTRICTION"
    if "inapte" in n:
        return "INAPTE"
    if "apte" in n:
        return "APTE"
    return normalize_upper(value)


def to_flag(value: str) -> str:
    n = normalize(value)
    if not n or n in {"non", "false", "0", "aucun", "aucune"}:
        return "false"
    return "true"


def normalize_exposure(value: str) -> str:
    n = normalize(value)
    if "bois" in n or "chim" in n or "poussiere" in n:
        return "POUSSIERES_BOIS"
    if "manutention" in n:
        return "MANUTENTION_MANUELLE"
    if "repetitif" in n or "gestes" in n:
        return "GESTES_REPETITIFS"
    return normalize_upper(value)


def exposure_category(value: str) -> str:
    n = normalize(value)
    if "bois" in n or "chim" in n or "poussiere" in n:
        return "CHIMIQUE"
    if "manutention" in n or "repetitif" in n or "gestes" in n:
        return "BIOMECANIQUE"
    if "bruit" in n:
        return "BRUIT"
    return "AUTRE"


if __name__ == "__main__":
    main()
