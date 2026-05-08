from __future__ import annotations

from pathlib import Path

from mcdst.quality import (
    check_blocked_fields,
    check_join_candidates,
    check_join_coverage,
    check_join_rules,
    check_mapping_source_columns,
    check_required_mappings,
    check_review_queue,
    check_value_mapping_reviews,
)
from mcdst.transforms import (
    age_class,
    classify_size,
    exposure_category,
    normalize_conclusion,
    normalize_exposure,
    normalize_sex,
    normalize_visit_type,
    to_flag,
)
from mcdst.utils import hash_id, normalize, normalize_upper, read_source_rows, write_csv


def dry_run_transform(mapping: dict, exports_dir: Path, output_dir: Path) -> dict:
    entity_maps = {
        entity: {
            "source_file": payload["source_file"],
            "fields": {field: spec["source"] for field, spec in payload["fields"].items()},
        }
        for entity, payload in mapping["entities"].items()
    }
    tables = {}

    tables["travailleur"] = build_travailleurs(entity_maps, exports_dir)
    tables["entreprise"] = build_entreprises(entity_maps, exports_dir)
    tables["etablissement"] = build_etablissements(entity_maps, exports_dir)
    tables["unite_travail"] = build_unites_travail(entity_maps, exports_dir)
    tables["episode_poste"] = build_episodes_poste(entity_maps, exports_dir)
    tables["visite_sante_travail"] = build_visites(entity_maps, exports_dir)
    tables["conclusion_medicale"] = build_conclusions(entity_maps, exports_dir)
    tables["exposition_professionnelle"] = build_expositions(entity_maps, exports_dir)
    tables["examen_complementaire"] = build_examens_complementaires(entity_maps, exports_dir)
    tables["pathologie_atmp"] = build_pathologies_atmp(entity_maps, exports_dir)
    tables["arret_travail"] = build_arrets_travail(entity_maps, exports_dir)
    tables["vaccination"] = build_vaccinations(entity_maps, exports_dir)
    tables["risque_unite_travail"] = build_risques_unite_travail(entity_maps, exports_dir)

    for name, rows in tables.items():
        write_csv(output_dir / f"{name}.csv", rows)

    quality = {
        "rules": [],
        "summary": {
            "generated_tables": {name: len(rows) for name, rows in tables.items()},
            "blocked_fields_count": len(mapping["blocked_fields"]),
            "review_queue_count": len(mapping["review_queue"]),
            "join_candidates_count": len(mapping["join_candidates"]),
            "join_rules_count": len(mapping.get("join_rules", [])),
            "value_mapping_groups_count": len(mapping["value_mappings"]),
            "output_dir": str(output_dir),
        },
    }
    quality["rules"].extend(check_required_mappings(mapping))
    quality["rules"].extend(check_mapping_source_columns(mapping, exports_dir))
    quality["rules"].extend(check_review_queue(mapping))
    quality["rules"].extend(check_value_mapping_reviews(mapping))
    quality["rules"].extend(check_join_candidates(mapping))
    quality["rules"].extend(check_join_rules(mapping))
    quality["rules"].extend(check_join_coverage(tables))
    quality["rules"].extend(check_blocked_fields(mapping))
    return {"tables": tables, "quality": quality}


def build_travailleurs(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "travailleur", exports_dir)
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
            "source_id": "local_lot",
        }
    return list(out.values())


def build_entreprises(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "entreprise", exports_dir)
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
            "source_id": "local_lot",
        }
    return list(out.values())


def build_etablissements(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "etablissement", exports_dir)
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
            "source_id": "local_lot",
        }
    return list(out.values())


def build_unites_travail(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "unite_travail", exports_dir)
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
            "source_id": "local_lot",
        }
    return list(out.values())


def build_episodes_poste(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "episode_poste", exports_dir)
    fields = entity_maps.get("episode_poste", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        worker = row.get(fields.get("travailleur_id", ""), "")
        job = row.get(fields.get("intitule_poste_source", ""), "")
        if not worker or not job:
            continue
        et_source = row.get(fields.get("etablissement_id", ""), "")
        unit_source = row.get(fields.get("unite_travail_id", ""), "")
        out.append(
            {
                "episode_poste_id": hash_id("EP", f"{worker}|{job}|{index}"),
                "travailleur_id": hash_id("T", worker),
                "etablissement_id": hash_id("ET", et_source) if et_source else "",
                "unite_travail_id": hash_id("UT", f"{et_source}|{unit_source}") if unit_source else "",
                "intitule_poste_source": job,
                "poste_concept_id": normalize_upper(job),
                "date_debut": row.get(fields.get("date_debut", ""), ""),
                "date_fin": row.get(fields.get("date_fin", ""), ""),
                "sensitivity_level": "S2",
                "source_id": "local_lot",
            }
        )
    return out


def build_visites(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "visite_sante_travail", exports_dir)
    fields = entity_maps.get("visite_sante_travail", {}).get("fields", {})
    out = []
    for row in rows:
        worker = row.get(fields.get("travailleur_id", ""), "")
        visit_date = row.get(fields.get("date_visite", ""), "")
        visit_type = row.get(fields.get("type_visite_concept_id", ""), "")
        if not worker or not visit_date:
            continue
        out.append(
            {
                "visite_id": hash_id("V", f"{worker}|{visit_date}|{visit_type}"),
                "travailleur_id": hash_id("T", worker),
                "date_visite": visit_date,
                "type_visite_concept_id": normalize_visit_type(visit_type),
                "motif_visite_concept_id": normalize_upper(row.get(fields.get("motif_visite_concept_id", ""), "")),
                "professionnel_role": row.get(fields.get("professionnel_role", ""), ""),
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def build_conclusions(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "conclusion_medicale", exports_dir)
    visit_fields = entity_maps.get("visite_sante_travail", {}).get("fields", {})
    fields = entity_maps.get("conclusion_medicale", {}).get("fields", {})
    out = []
    for row in rows:
        worker = row.get(visit_fields.get("travailleur_id", ""), "")
        visit_date = row.get(visit_fields.get("date_visite", ""), "")
        visit_type = row.get(visit_fields.get("type_visite_concept_id", ""), "")
        if not worker or not visit_date:
            continue
        conclusion_raw = row.get(fields.get("conclusion_concept_id", ""), "")
        out.append(
            {
                "conclusion_id": hash_id("C", f"{worker}|{visit_date}|{conclusion_raw}"),
                "visite_id": hash_id("V", f"{worker}|{visit_date}|{visit_type}"),
                "conclusion_concept_id": normalize_conclusion(conclusion_raw),
                "restriction_flag": to_flag(row.get(fields.get("restriction_flag", ""), "")),
                "amenagement_flag": to_flag(row.get(fields.get("amenagement_flag", ""), "")),
                "inaptitude_flag": "false",
                "orientation_pdp_flag": "true" if "pdp" in normalize(conclusion_raw) else "false",
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def build_expositions(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "exposition_professionnelle", exports_dir)
    fields = entity_maps.get("exposition_professionnelle", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        worker = row.get(fields.get("travailleur_id", ""), "")
        exposure = row.get(fields.get("exposition_concept_id", ""), "")
        if not worker or not exposure:
            continue
        out.append(
            {
                "exposition_id": hash_id("X", f"{worker}|{exposure}|{index}"),
                "travailleur_id": hash_id("T", worker),
                "exposition_concept_id": normalize_exposure(exposure),
                "categorie_exposition": exposure_category(exposure),
                "niveau_classe": normalize_upper(row.get(fields.get("niveau_classe", ""), "")),
                "date_debut": row.get(fields.get("date_debut", ""), ""),
                "date_fin": row.get(fields.get("date_fin", ""), ""),
                "source_exposition_type": normalize_upper(row.get(fields.get("source_exposition_type", ""), "")),
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def build_examens_complementaires(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "examen_complementaire", exports_dir)
    fields = entity_maps.get("examen_complementaire", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        worker = row.get(fields.get("travailleur_id", ""), "")
        exam_date = row.get(fields.get("date_examen", ""), "")
        exam_type = row.get(fields.get("examen_type_concept_id", ""), "")
        if not worker or not exam_date or not exam_type:
            continue
        out.append(
            {
                "examen_id": hash_id("EX", f"{worker}|{exam_date}|{exam_type}|{index}"),
                "travailleur_id": hash_id("T", worker),
                "date_examen": exam_date,
                "examen_type_concept_id": normalize_upper(exam_type),
                "resultat_valeur": row.get(fields.get("resultat_valeur", ""), ""),
                "resultat_unite": row.get(fields.get("resultat_unite", ""), ""),
                "interpretation_concept_id": normalize_upper(row.get(fields.get("interpretation_concept_id", ""), "")),
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def build_pathologies_atmp(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "pathologie_atmp", exports_dir)
    fields = entity_maps.get("pathologie_atmp", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        worker = row.get(fields.get("travailleur_id", ""), "")
        event_date = row.get(fields.get("date_evenement", ""), "")
        event_type = row.get(fields.get("type_evenement", ""), "")
        if not worker or not event_date or not event_type:
            continue
        out.append(
            {
                "pathologie_atmp_id": hash_id("PA", f"{worker}|{event_date}|{event_type}|{index}"),
                "travailleur_id": hash_id("T", worker),
                "date_evenement": event_date,
                "type_evenement": normalize_upper(event_type),
                "code_cim10": normalize_upper(row.get(fields.get("code_cim10", ""), "")),
                "pathologie_concept_id": normalize_upper(row.get(fields.get("pathologie_concept_id", ""), "")),
                "reconnaissance_flag": to_flag(row.get(fields.get("reconnaissance_statut", ""), "")),
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def build_arrets_travail(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "arret_travail", exports_dir)
    fields = entity_maps.get("arret_travail", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        worker = row.get(fields.get("travailleur_id", ""), "")
        start_date = row.get(fields.get("date_debut", ""), "")
        if not worker or not start_date:
            continue
        out.append(
            {
                "arret_travail_id": hash_id("AR", f"{worker}|{start_date}|{index}"),
                "travailleur_id": hash_id("T", worker),
                "date_debut": start_date,
                "date_fin": row.get(fields.get("date_fin", ""), ""),
                "type_arret": normalize_upper(row.get(fields.get("type_arret", ""), "")),
                "lie_atmp_flag": to_flag(row.get(fields.get("lie_atmp_flag", ""), "")),
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def build_vaccinations(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "vaccination", exports_dir)
    fields = entity_maps.get("vaccination", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        worker = row.get(fields.get("travailleur_id", ""), "")
        vaccine = row.get(fields.get("vaccin_concept_id", ""), "")
        if not worker or not vaccine:
            continue
        out.append(
            {
                "vaccination_id": hash_id("VAC", f"{worker}|{vaccine}|{index}"),
                "travailleur_id": hash_id("T", worker),
                "vaccin_concept_id": normalize_upper(vaccine),
                "date_vaccination": row.get(fields.get("date_vaccination", ""), ""),
                "statut_vaccinal": normalize_upper(row.get(fields.get("statut_vaccinal", ""), "")),
                "rappel_prevu": row.get(fields.get("rappel_prevu", ""), ""),
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def build_risques_unite_travail(entity_maps: dict, exports_dir: Path) -> list[dict]:
    rows = read_entity_source(entity_maps, "risque_unite_travail", exports_dir)
    fields = entity_maps.get("risque_unite_travail", {}).get("fields", {})
    out = []
    for index, row in enumerate(rows, start=1):
        et_source = row.get(fields.get("etablissement_id", ""), "")
        unit_source = row.get(fields.get("unite_travail_id", ""), "")
        risk = row.get(fields.get("risque_concept_id", ""), "")
        if not et_source or not unit_source or not risk:
            continue
        out.append(
            {
                "risque_unite_travail_id": hash_id("RUT", f"{et_source}|{unit_source}|{risk}|{index}"),
                "etablissement_id": hash_id("ET", et_source),
                "unite_travail_id": hash_id("UT", f"{et_source}|{unit_source}"),
                "risque_concept_id": normalize_exposure(risk),
                "niveau_risque": normalize_upper(row.get(fields.get("niveau_risque", ""), "")),
                "mesure_prevention_source": row.get(fields.get("mesure_prevention_source", ""), ""),
                "date_evaluation": row.get(fields.get("date_evaluation", ""), ""),
                "sensitivity_level": "S3",
                "source_id": "local_lot",
            }
        )
    return out


def read_entity_source(entity_maps: dict, entity: str, exports_dir: Path) -> list[dict]:
    source_file = entity_maps.get(entity, {}).get("source_file")
    if not source_file:
        return []
    return read_source_rows(exports_dir, source_file)
