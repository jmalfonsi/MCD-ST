from __future__ import annotations

from datetime import UTC, date, datetime
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
) -> dict:
    definition = read_yaml(definition_path) or {}
    result = evaluate_cohort(tables_dir, definition)
    result["definition_path"] = str(definition_path)
    if output_path:
        result["summary"]["output_path"] = str(output_path)
        write_json(output_path, result)
    return result


def evaluate_cohort(tables_dir: Path, definition: dict[str, Any]) -> dict:
    required_tables = required_tables_for_definition(definition)
    loaded = load_required_tables(tables_dir, required_tables)
    missing_tables = [table for table in required_tables if table not in loaded]
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
        )

    eligible = set(all_worker_ids)
    eligible = apply_population_filters(definition, loaded, eligible, steps)
    eligible = apply_criteria_filters(definition, loaded, eligible, steps)
    eligible = apply_longitudinal_filters(definition, loaded, eligible, steps)
    return build_result(
        definition,
        required_tables,
        missing_tables,
        availability,
        steps,
        all_worker_ids,
        eligible,
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
) -> set[str]:
    event_definitions = longitudinal_event_definitions(definition)
    sequences = longitudinal_sequences(definition)
    if not event_definitions or not sequences:
        return eligible

    events_by_name = {
        name: build_event_records(name, event, tables)
        for name, event in event_definitions.items()
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

    return eligible


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
) -> dict:
    included = sorted(included_worker_ids)
    sequences_count = len(longitudinal_sequences(definition))
    return {
        "cohort_name": definition.get("name", "unnamed_cohort"),
        "schema_version": "mcdst-cohort-v0.2" if sequences_count else "mcdst-cohort-v0.1",
        "summary": {
            "feasibility_status": "not_feasible" if missing_tables else "feasible",
            "source_population_count": len(source_worker_ids),
            "included_count": len(included),
            "excluded_count": max(len(source_worker_ids) - len(included), 0),
            "required_tables": required_tables,
            "missing_tables": missing_tables,
            "longitudinal_sequences_count": sequences_count,
        },
        "data_availability": availability,
        "steps": steps,
        "included_travailleurs": included,
    }


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
