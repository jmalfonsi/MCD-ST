from __future__ import annotations

from datetime import UTC, date, datetime
from html import escape
from pathlib import Path
from typing import Any

from mcdst.utils import normalize, normalize_upper, read_csv, read_yaml, write_json


TABLE_FILES = {
    "travailleur": "travailleur.csv",
    "etablissement": "etablissement.csv",
    "episode_poste": "episode_poste.csv",
    "visite_sante_travail": "visite_sante_travail.csv",
    "conclusion_medicale": "conclusion_medicale.csv",
    "exposition_professionnelle": "exposition_professionnelle.csv",
    "examen_complementaire": "examen_complementaire.csv",
    "pathologie_atmp": "pathologie_atmp.csv",
    "arret_travail": "arret_travail.csv",
    "vaccination": "vaccination.csv",
    "risque_unite_travail": "risque_unite_travail.csv",
}

DEFAULT_EVENT_DATE_FIELDS = {
    "visite_sante_travail": "date_visite",
    "conclusion_medicale": "visite_sante_travail.date_visite",
    "exposition_professionnelle": "date_debut",
    "examen_complementaire": "date_examen",
    "pathologie_atmp": "date_evenement",
    "arret_travail": "date_debut",
    "vaccination": "date_vaccination",
}


def evaluate_cohort_definition(
    tables_dir: Path,
    definition_path: Path,
    output_path: Path | None = None,
    html_output_path: Path | None = None,
) -> dict:
    definition = read_yaml(definition_path) or {}
    result = evaluate_cohort(tables_dir, definition)
    result["definition_path"] = str(definition_path)
    if output_path:
        result["summary"]["output_path"] = str(output_path)
    if html_output_path:
        result["summary"]["html_output_path"] = str(html_output_path)
    if output_path:
        write_json(output_path, result)
    if html_output_path:
        write_cohort_html_report(html_output_path, result)
    return result


def evaluate_cohort(tables_dir: Path, definition: dict[str, Any]) -> dict:
    required_tables = required_tables_for_definition(definition)
    loaded = load_required_tables(tables_dir, required_tables)
    missing_tables = [table for table in required_tables if table not in loaded]
    diagnostics = build_missing_table_diagnostics(missing_tables)
    availability = [
        {
            "table": table,
            "status": "missing" if table in missing_tables else "available",
            "row_count": len(loaded.get(table, [])),
        }
        for table in required_tables
    ]

    travailleurs = loaded.get("travailleur", [])
    all_worker_ids = {row["travailleur_id"] for row in travailleurs if row.get("travailleur_id")}
    steps = [
        {
            "id": "source_population",
            "label": "Travailleurs source",
            "input_count": None,
            "output_count": len(all_worker_ids),
            "excluded_count": 0,
        }
    ]

    if missing_tables:
        return build_result(
            definition,
            required_tables,
            missing_tables,
            availability,
            steps,
            all_worker_ids,
            set(),
            diagnostics,
            empty_longitudinal_summary(),
        )

    diagnostics.extend(build_missing_field_diagnostics(definition, loaded))

    eligible = set(all_worker_ids)
    eligible = apply_population_filters(definition, loaded, eligible, steps)
    eligible = apply_criteria_filters(definition, loaded, eligible, steps)
    eligible, longitudinal = apply_longitudinal_filters(definition, loaded, eligible, steps)
    diagnostics.extend(build_longitudinal_diagnostics(longitudinal))
    return build_result(
        definition,
        required_tables,
        missing_tables,
        availability,
        steps,
        all_worker_ids,
        eligible,
        diagnostics,
        longitudinal,
    )


def required_tables_for_definition(definition: dict[str, Any]) -> list[str]:
    required = {"travailleur"}
    population = definition.get("population", {}) or {}
    criteria = definition.get("criteria", {}) or {}
    if has_value(population.get("region")):
        required.update({"etablissement", "episode_poste"})
    if extract_values(criteria, "exposure_concepts", "exposures"):
        required.add("exposition_professionnelle")
    if extract_values(criteria, "visit_types", "visits"):
        required.add("visite_sante_travail")
    if extract_values(criteria, "conclusion_concepts", "conclusions") or criteria.get("flags"):
        required.update({"visite_sante_travail", "conclusion_medicale"})
    required.update(required_tables_for_longitudinal(definition))
    return sorted(required)


def required_tables_for_longitudinal(definition: dict[str, Any]) -> set[str]:
    required = set()
    for event in longitudinal_event_definitions(definition).values():
        table = str(event.get("table") or "")
        if not table:
            continue
        required.add(table)
        date_field = str(event.get("date_field") or DEFAULT_EVENT_DATE_FIELDS.get(table, ""))
        if table == "conclusion_medicale" or date_field.startswith("visite_sante_travail."):
            required.add("visite_sante_travail")
    return required


def load_required_tables(tables_dir: Path, required_tables: list[str]) -> dict[str, list[dict[str, str]]]:
    tables = {}
    for table in required_tables:
        path = tables_dir / TABLE_FILES.get(table, f"{table}.csv")
        if path.exists():
            tables[table] = read_csv(path)
    return tables


def required_fields_for_definition(definition: dict[str, Any]) -> dict[str, set[str]]:
    required: dict[str, set[str]] = {"travailleur": {"travailleur_id"}}
    population = definition.get("population", {}) or {}
    criteria = definition.get("criteria", {}) or {}

    if population.get("min_age") is not None or population.get("max_age") is not None:
        add_required_fields(required, "travailleur", {"annee_naissance"})
    if has_value(population.get("sex")):
        add_required_fields(required, "travailleur", {"sexe"})
    if has_value(population.get("suivi_type")):
        add_required_fields(required, "travailleur", {"suivi_type_concept_id"})
    if has_value(population.get("region")):
        add_required_fields(required, "etablissement", {"etablissement_id", "region"})
        add_required_fields(required, "episode_poste", {"travailleur_id", "etablissement_id"})

    if extract_values(criteria, "exposure_concepts", "exposures"):
        add_required_fields(required, "exposition_professionnelle", {"travailleur_id", "exposition_concept_id"})
    if extract_values(criteria, "visit_types", "visits"):
        add_required_fields(required, "visite_sante_travail", {"travailleur_id", "type_visite_concept_id"})
    if extract_values(criteria, "conclusion_concepts", "conclusions") or criteria.get("flags"):
        add_required_fields(required, "visite_sante_travail", {"visite_id", "travailleur_id"})
        add_required_fields(required, "conclusion_medicale", {"visite_id"})
    if extract_values(criteria, "conclusion_concepts", "conclusions"):
        add_required_fields(required, "conclusion_medicale", {"conclusion_concept_id"})
    for field in (criteria.get("flags", {}) or {}):
        add_required_fields(required, "conclusion_medicale", {str(field)})

    for event in longitudinal_event_definitions(definition).values():
        table = str(event.get("table") or "")
        if not table:
            continue
        filters = event.get("filters", {}) or {}
        add_required_fields(required, table, set(filters.keys()))
        date_field = str(event.get("date_field") or DEFAULT_EVENT_DATE_FIELDS.get(table, "date"))
        worker_field = str(event.get("worker_field") or "travailleur_id")
        if table == "conclusion_medicale" or date_field.startswith("visite_sante_travail."):
            linked_date_field = date_field.split(".", 1)[1] if "." in date_field else date_field
            add_required_fields(required, table, {"visite_id"})
            add_required_fields(required, "visite_sante_travail", {"visite_id", "travailleur_id", linked_date_field})
        else:
            add_required_fields(required, table, {worker_field, date_field.split(".", 1)[-1]})

    return required


def add_required_fields(required: dict[str, set[str]], table: str, fields: set[str]) -> None:
    required.setdefault(table, set()).update(field for field in fields if field)


def build_missing_table_diagnostics(missing_tables: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "severity": "blocking",
            "code": "missing_table",
            "table": table,
            "message": f"Table MCD-ST requise absente: {table}",
        }
        for table in missing_tables
    ]


def build_missing_field_diagnostics(
    definition: dict[str, Any],
    tables: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    diagnostics = []
    for table, fields in sorted(required_fields_for_definition(definition).items()):
        if table not in tables:
            continue
        rows = tables[table]
        if not rows:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "empty_table",
                    "table": table,
                    "message": f"Table MCD-ST disponible mais vide: {table}",
                }
            )
            continue
        available = set().union(*(row.keys() for row in rows))
        missing_fields = sorted(field for field in fields if field not in available)
        for field in missing_fields:
            diagnostics.append(
                {
                    "severity": "blocking",
                    "code": "missing_field",
                    "table": table,
                    "field": field,
                    "message": f"Champ requis absent: {table}.{field}",
                }
            )
    return diagnostics


def build_longitudinal_diagnostics(longitudinal: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    diagnostics = []
    for event in longitudinal["events"]:
        if event["records_count"] == 0:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "empty_event",
                    "event": event["id"],
                    "table": event["table"],
                    "message": f"Aucun événement trouvé pour {event['id']}",
                }
            )
    for sequence in longitudinal["sequences"]:
        if sequence["matched_pairs_count"] == 0:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": "temporal_no_match",
                    "sequence": sequence["id"],
                    "message": f"Aucune paire temporelle ne valide la séquence {sequence['id']}",
                }
            )
    return diagnostics


def apply_population_filters(
    definition: dict[str, Any],
    tables: dict[str, list[dict[str, str]]],
    eligible: set[str],
    steps: list[dict],
) -> set[str]:
    population = definition.get("population", {}) or {}
    reference_year = int(definition.get("reference_year") or datetime.now(UTC).year)
    travailleurs = tables["travailleur"]

    if population.get("min_age") is not None:
        min_age = int(population["min_age"])
        allowed = {
            row["travailleur_id"]
            for row in travailleurs
            if row.get("travailleur_id")
            and age_at(row.get("annee_naissance", ""), reference_year) is not None
            and age_at(row.get("annee_naissance", ""), reference_year) >= min_age
        }
        eligible = apply_filter(steps, eligible, allowed, "population:min_age", f"Age >= {min_age}")

    if population.get("max_age") is not None:
        max_age = int(population["max_age"])
        allowed = {
            row["travailleur_id"]
            for row in travailleurs
            if row.get("travailleur_id")
            and age_at(row.get("annee_naissance", ""), reference_year) is not None
            and age_at(row.get("annee_naissance", ""), reference_year) <= max_age
        }
        eligible = apply_filter(steps, eligible, allowed, "population:max_age", f"Age <= {max_age}")

    if has_value(population.get("region")):
        regions = {normalize(value) for value in list_values(population["region"])}
        etablissement_ids = {
            row["etablissement_id"]
            for row in tables["etablissement"]
            if normalize(row.get("region", "")) in regions
        }
        allowed = {
            row["travailleur_id"]
            for row in tables["episode_poste"]
            if row.get("etablissement_id") in etablissement_ids
        }
        eligible = apply_filter(steps, eligible, allowed, "population:region", f"Region in {', '.join(sorted(regions))}")

    if has_value(population.get("sex")):
        sexes = {normalize_upper(value) for value in list_values(population["sex"])}
        allowed = {
            row["travailleur_id"]
            for row in travailleurs
            if normalize_upper(row.get("sexe", "")) in sexes
        }
        eligible = apply_filter(steps, eligible, allowed, "population:sex", f"Sexe in {', '.join(sorted(sexes))}")

    if has_value(population.get("suivi_type")):
        suivi_types = {normalize_upper(value) for value in list_values(population["suivi_type"])}
        allowed = {
            row["travailleur_id"]
            for row in travailleurs
            if normalize_upper(row.get("suivi_type_concept_id", "")) in suivi_types
        }
        eligible = apply_filter(steps, eligible, allowed, "population:suivi_type", "Type de suivi")

    return eligible


def apply_criteria_filters(
    definition: dict[str, Any],
    tables: dict[str, list[dict[str, str]]],
    eligible: set[str],
    steps: list[dict],
) -> set[str]:
    criteria = definition.get("criteria", {}) or {}

    exposure_concepts = {normalize_upper(value) for value in extract_values(criteria, "exposure_concepts", "exposures")}
    if exposure_concepts:
        allowed = {
            row["travailleur_id"]
            for row in tables["exposition_professionnelle"]
            if normalize_upper(row.get("exposition_concept_id", "")) in exposure_concepts
        }
        eligible = apply_filter(steps, eligible, allowed, "criteria:exposure", "Exposition professionnelle")

    visit_types = {normalize_upper(value) for value in extract_values(criteria, "visit_types", "visits")}
    if visit_types:
        allowed = {
            row["travailleur_id"]
            for row in tables["visite_sante_travail"]
            if normalize_upper(row.get("type_visite_concept_id", "")) in visit_types
        }
        eligible = apply_filter(steps, eligible, allowed, "criteria:visit_type", "Type de visite")

    conclusion_concepts = {normalize_upper(value) for value in extract_values(criteria, "conclusion_concepts", "conclusions")}
    if conclusion_concepts:
        visit_worker_index = visit_workers_by_id(tables["visite_sante_travail"])
        allowed = {
            visit_worker_index[row["visite_id"]]
            for row in tables["conclusion_medicale"]
            if row.get("visite_id") in visit_worker_index
            and normalize_upper(row.get("conclusion_concept_id", "")) in conclusion_concepts
        }
        eligible = apply_filter(steps, eligible, allowed, "criteria:conclusion", "Conclusion médicale")

    flags = criteria.get("flags", {}) or {}
    for field, expected in flags.items():
        visit_worker_index = visit_workers_by_id(tables["visite_sante_travail"])
        expected_value = boolean_text(expected)
        allowed = {
            visit_worker_index[row["visite_id"]]
            for row in tables["conclusion_medicale"]
            if row.get("visite_id") in visit_worker_index
            and boolean_text(row.get(field, "")) == expected_value
        }
        eligible = apply_filter(steps, eligible, allowed, f"criteria:{field}", field)

    return eligible


def apply_longitudinal_filters(
    definition: dict[str, Any],
    tables: dict[str, list[dict[str, str]]],
    eligible: set[str],
    steps: list[dict],
) -> tuple[set[str], dict[str, list[dict[str, Any]]]]:
    event_definitions = longitudinal_event_definitions(definition)
    sequences = longitudinal_sequences(definition)
    if not event_definitions or not sequences:
        return eligible, empty_longitudinal_summary()

    events_by_name = {
        name: build_event_records(name, event, tables)
        for name, event in event_definitions.items()
    }
    longitudinal = {
        "events": [
            summarize_event_records(name, event_definitions[name], events_by_name.get(name, []))
            for name in event_definitions
        ],
        "sequences": [],
    }

    for index, sequence in enumerate(sequences, start=1):
        first_name = str(sequence.get("first") or sequence.get("before") or "")
        then_name = str(sequence.get("then") or sequence.get("after") or "")
        sequence_id = str(sequence.get("id") or f"sequence_{index}")
        allowed, matched_pairs = workers_matching_temporal_sequence(
            events_by_name.get(first_name, []),
            events_by_name.get(then_name, []),
            eligible,
            sequence,
        )
        eligible = apply_filter(
            steps,
            eligible,
            allowed,
            f"longitudinal:{sequence_id}",
            str(sequence.get("label") or f"{first_name} avant {then_name}"),
        )
        steps[-1].update(
            {
                "first_event": first_name,
                "then_event": then_name,
                "relation": str(sequence.get("relation") or "before"),
                "min_days": optional_int(sequence.get("min_days")),
                "max_days": optional_int(sequence.get("max_days")),
                "matched_pairs_count": matched_pairs,
            }
        )
        longitudinal["sequences"].append(
            {
                "id": sequence_id,
                "label": str(sequence.get("label") or f"{first_name} avant {then_name}"),
                "first_event": first_name,
                "then_event": then_name,
                "relation": str(sequence.get("relation") or "before"),
                "min_days": optional_int(sequence.get("min_days")),
                "max_days": optional_int(sequence.get("max_days")),
                "matched_pairs_count": matched_pairs,
                "matched_workers_count": len(allowed.intersection(eligible)),
            }
        )

    return eligible, longitudinal


def longitudinal_event_definitions(definition: dict[str, Any]) -> dict[str, dict[str, Any]]:
    longitudinal = definition.get("longitudinal", {}) or {}
    events = longitudinal.get("events", {}) or {}
    return {
        str(name): event
        for name, event in events.items()
        if isinstance(event, dict)
    }


def longitudinal_sequences(definition: dict[str, Any]) -> list[dict[str, Any]]:
    longitudinal = definition.get("longitudinal", {}) or {}
    sequences = longitudinal.get("sequences", [])
    if isinstance(sequences, dict):
        return [
            {"id": str(name), **sequence}
            for name, sequence in sequences.items()
            if isinstance(sequence, dict)
        ]
    if isinstance(sequences, list):
        return [sequence for sequence in sequences if isinstance(sequence, dict)]
    return []


def build_event_records(
    name: str,
    event: dict[str, Any],
    tables: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    table = str(event.get("table") or "")
    rows = tables.get(table, [])
    filters = event.get("filters", {}) or {}
    records = []
    for row in rows:
        if not row_matches_filters(row, filters):
            continue
        worker_id, event_date = event_worker_and_date(table, row, event, tables)
        if worker_id and event_date:
            records.append(
                {
                    "name": name,
                    "table": table,
                    "travailleur_id": worker_id,
                    "date": event_date,
                }
            )
    return records


def summarize_event_records(
    name: str,
    event: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": name,
        "table": str(event.get("table") or ""),
        "date_field": str(event.get("date_field") or DEFAULT_EVENT_DATE_FIELDS.get(str(event.get("table") or ""), "")),
        "records_count": len(records),
        "workers_count": len({record["travailleur_id"] for record in records}),
    }


def empty_longitudinal_summary() -> dict[str, list[dict[str, Any]]]:
    return {"events": [], "sequences": []}


def event_worker_and_date(
    table: str,
    row: dict[str, str],
    event: dict[str, Any],
    tables: dict[str, list[dict[str, str]]],
) -> tuple[str, date | None]:
    date_field = str(event.get("date_field") or DEFAULT_EVENT_DATE_FIELDS.get(table, "date"))
    worker_field = str(event.get("worker_field") or "travailleur_id")

    if table == "conclusion_medicale" or date_field.startswith("visite_sante_travail."):
        visit = visit_index_by_id(tables.get("visite_sante_travail", [])).get(row.get("visite_id", ""), {})
        linked_date_field = date_field.split(".", 1)[1] if "." in date_field else date_field
        return visit.get("travailleur_id", ""), parse_date(visit.get(linked_date_field, ""))

    field = date_field.split(".", 1)[1] if "." in date_field else date_field
    return row.get(worker_field, ""), parse_date(row.get(field, ""))


def row_matches_filters(row: dict[str, str], filters: dict[str, Any]) -> bool:
    return all(value_matches_filter(row.get(field, ""), expected) for field, expected in filters.items())


def value_matches_filter(value: str, expected: Any) -> bool:
    if isinstance(expected, dict):
        if "any" in expected:
            return any(value_matches_filter(value, item) for item in list_values(expected["any"]))
        if "equals" in expected:
            return value_matches_filter(value, expected["equals"])
        if "not_any" in expected:
            return not any(value_matches_filter(value, item) for item in list_values(expected["not_any"]))
        return False
    if isinstance(expected, list):
        return any(value_matches_filter(value, item) for item in expected)
    return normalized_scalar(value) == normalized_scalar(expected)


def normalized_scalar(value: Any) -> str:
    boolean = boolean_text(value)
    if boolean in {"true", "false"}:
        return boolean
    return normalize_upper(str(value))


def workers_matching_temporal_sequence(
    first_events: list[dict[str, Any]],
    then_events: list[dict[str, Any]],
    eligible: set[str],
    sequence: dict[str, Any],
) -> tuple[set[str], int]:
    first_by_worker = events_by_worker(first_events)
    then_by_worker = events_by_worker(then_events)
    relation = normalize(str(sequence.get("relation") or "before"))
    min_days = optional_int(sequence.get("min_days"))
    max_days = optional_int(sequence.get("max_days"))
    allowed = set()
    matched_pairs = 0

    for worker_id in eligible:
        for first in first_by_worker.get(worker_id, []):
            for then in then_by_worker.get(worker_id, []):
                if temporal_relation_matches(first["date"], then["date"], relation, min_days, max_days):
                    allowed.add(worker_id)
                    matched_pairs += 1

    return allowed, matched_pairs


def events_by_worker(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        grouped.setdefault(event["travailleur_id"], []).append(event)
    return grouped


def temporal_relation_matches(
    first_date: date,
    then_date: date,
    relation: str,
    min_days: int | None,
    max_days: int | None,
) -> bool:
    if relation == "sameday":
        delta_days = abs((then_date - first_date).days)
    elif relation == "after":
        delta_days = (first_date - then_date).days
    else:
        delta_days = (then_date - first_date).days

    lower_bound = 0 if min_days is None else min_days
    if relation == "strictlybefore" and lower_bound == 0:
        lower_bound = 1
    if delta_days < lower_bound:
        return False
    return max_days is None or delta_days <= max_days


def apply_filter(steps: list[dict], eligible: set[str], allowed: set[str], step_id: str, label: str) -> set[str]:
    before = set(eligible)
    after = before.intersection(allowed)
    steps.append(
        {
            "id": step_id,
            "label": label,
            "input_count": len(before),
            "output_count": len(after),
            "excluded_count": len(before) - len(after),
        }
    )
    return after


def build_result(
    definition: dict[str, Any],
    required_tables: list[str],
    missing_tables: list[str],
    availability: list[dict],
    steps: list[dict],
    source_worker_ids: set[str],
    included_worker_ids: set[str],
    diagnostics: list[dict[str, Any]],
    longitudinal: dict[str, list[dict[str, Any]]],
) -> dict:
    included = sorted(included_worker_ids)
    sequences_count = len(longitudinal_sequences(definition))
    status = feasibility_status(diagnostics, source_worker_ids, included_worker_ids)
    return {
        "cohort_name": definition.get("name", "unnamed_cohort"),
        "schema_version": "mcdst-cohort-v0.2" if sequences_count else "mcdst-cohort-v0.1",
        "summary": {
            "feasibility_status": status,
            "source_population_count": len(source_worker_ids),
            "included_count": len(included),
            "excluded_count": max(len(source_worker_ids) - len(included), 0),
            "required_tables": required_tables,
            "missing_tables": missing_tables,
            "longitudinal_sequences_count": sequences_count,
            "diagnostics_count": len(diagnostics),
            "blocking_diagnostics_count": count_diagnostics(diagnostics, "blocking"),
            "warning_diagnostics_count": count_diagnostics(diagnostics, "warning"),
        },
        "feasibility": {
            "status": status,
            "diagnostics": diagnostics,
        },
        "data_availability": availability,
        "longitudinal": longitudinal,
        "steps": steps,
        "included_travailleurs": included,
    }


def feasibility_status(
    diagnostics: list[dict[str, Any]],
    source_worker_ids: set[str],
    included_worker_ids: set[str],
) -> str:
    if count_diagnostics(diagnostics, "blocking"):
        return "not_feasible"
    if source_worker_ids and not included_worker_ids:
        return "feasible_empty"
    return "feasible"


def count_diagnostics(diagnostics: list[dict[str, Any]], severity: str) -> int:
    return sum(1 for diagnostic in diagnostics if diagnostic.get("severity") == severity)


def write_cohort_html_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_cohort_report_html(result), encoding="utf-8")


def render_cohort_report_html(result: dict[str, Any]) -> str:
    summary = result["summary"]
    diagnostics = result.get("feasibility", {}).get("diagnostics", [])
    longitudinal = result.get("longitudinal", empty_longitudinal_summary())
    title = f"Rapport cohorte - {result['cohort_name']}"
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{html_text(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Arial, sans-serif; }}
    body {{ margin: 32px; color: #172026; background: #f7f8fa; }}
    main {{ max-width: 1120px; margin: 0 auto; }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 18px; margin-top: 28px; }}
    .muted {{ color: #66717a; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 18px 0; }}
    .metric {{ background: white; border: 1px solid #d8dee4; border-radius: 8px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8dee4; }}
    th, td {{ border-bottom: 1px solid #e6eaf0; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2f6; font-size: 13px; }}
    .status {{ display: inline-block; padding: 3px 8px; border-radius: 999px; background: #e8f5ed; color: #17663a; }}
    .status.not_feasible {{ background: #fdecec; color: #a32121; }}
    .status.feasible_empty {{ background: #fff4d6; color: #7a5200; }}
    .severity-blocking {{ color: #a32121; font-weight: 700; }}
    .severity-warning {{ color: #8a5a00; font-weight: 700; }}
  </style>
</head>
<body>
<main>
  <h1>{html_text(title)}</h1>
  <p class="muted">Définition: {html_text(result.get("definition_path", ""))}</p>
  <p>Statut: <span class="status {html_attr(summary["feasibility_status"])}">{html_text(summary["feasibility_status"])}</span></p>

  <section class="grid">
    {metric("Population source", summary["source_population_count"])}
    {metric("Inclus", summary["included_count"])}
    {metric("Exclus", summary["excluded_count"])}
    {metric("Diagnostics", summary["diagnostics_count"])}
    {metric("Séquences", summary["longitudinal_sequences_count"])}
  </section>

  <h2>Étapes de Cohorte</h2>
  {html_table(result["steps"], [
      ("id", "Étape"),
      ("label", "Libellé"),
      ("input_count", "Entrée"),
      ("output_count", "Sortie"),
      ("excluded_count", "Exclus"),
      ("matched_pairs_count", "Paires"),
  ])}

  <h2>Diagnostics de Faisabilité</h2>
  {html_table(diagnostics, [
      ("severity", "Sévérité"),
      ("code", "Code"),
      ("table", "Table"),
      ("field", "Champ"),
      ("event", "Événement"),
      ("sequence", "Séquence"),
      ("message", "Message"),
  ], severity_column=True)}

  <h2>Disponibilité des Données</h2>
  {html_table(result["data_availability"], [
      ("table", "Table"),
      ("status", "Statut"),
      ("row_count", "Lignes"),
  ])}

  <h2>Événements Longitudinaux</h2>
  {html_table(longitudinal["events"], [
      ("id", "Événement"),
      ("table", "Table"),
      ("date_field", "Date"),
      ("records_count", "Lignes"),
      ("workers_count", "Travailleurs"),
  ])}

  <h2>Séquences Longitudinales</h2>
  {html_table(longitudinal["sequences"], [
      ("id", "Séquence"),
      ("label", "Libellé"),
      ("first_event", "Premier"),
      ("then_event", "Puis"),
      ("relation", "Relation"),
      ("min_days", "Min jours"),
      ("max_days", "Max jours"),
      ("matched_pairs_count", "Paires"),
      ("matched_workers_count", "Travailleurs"),
  ])}

  <h2>Travailleurs Inclus</h2>
  {included_workers_html(result["included_travailleurs"])}
</main>
</body>
</html>
"""


def metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{html_text(label)}</span><strong>{html_text(value)}</strong></div>'


def html_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    *,
    severity_column: bool = False,
) -> str:
    if not rows:
        return '<p class="muted">Aucun élément.</p>'
    header = "".join(f"<th>{html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row.get(key, "")
            css_class = ""
            if severity_column and key == "severity" and value:
                css_class = f' class="severity-{html_attr(value)}"'
            cells.append(f"<td{css_class}>{html_text(value)}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def included_workers_html(worker_ids: list[str]) -> str:
    if not worker_ids:
        return '<p class="muted">Aucun travailleur inclus.</p>'
    rows = [{"travailleur_id": worker_id} for worker_id in worker_ids]
    return html_table(rows, [("travailleur_id", "Travailleur pseudonymisé")])


def html_text(value: Any) -> str:
    if value is None:
        return ""
    return escape(str(value))


def html_attr(value: Any) -> str:
    return normalize(str(value))


def extract_values(payload: dict[str, Any], direct_key: str, grouped_key: str) -> list[str]:
    direct = payload.get(direct_key)
    if direct:
        if isinstance(direct, dict):
            return list_values(direct.get("any", []))
        return list_values(direct)
    grouped = payload.get(grouped_key, {}) or {}
    return list_values(grouped.get("any", []))


def list_values(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def has_value(value: Any) -> bool:
    return bool(list_values(value))


def age_at(year: str, reference_year: int) -> int | None:
    try:
        return reference_year - int(year)
    except (TypeError, ValueError):
        return None


def parse_date(value: str) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def visit_workers_by_id(visites: list[dict[str, str]]) -> dict[str, str]:
    return {
        row["visite_id"]: row["travailleur_id"]
        for row in visites
        if row.get("visite_id") and row.get("travailleur_id")
    }


def visit_index_by_id(visites: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        row["visite_id"]: row
        for row in visites
        if row.get("visite_id")
    }


def optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def boolean_text(value: Any) -> str:
    normalized = normalize(str(value))
    if normalized in {"1", "true", "vrai", "yes", "oui"}:
        return "true"
    if normalized in {"0", "false", "faux", "no", "non"}:
        return "false"
    return normalized
