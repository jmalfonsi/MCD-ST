from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from mcdst.schema import FILE_ENTITY_HINTS, FILENAME_ENTITY_SHORTCUTS, TARGET_SCHEMA
from mcdst.sensitivity import infer_sensitivity
from mcdst.utils import (
    first_examples,
    is_date,
    is_number,
    is_year,
    list_tabular_sources,
    non_empty,
    normalize,
    read_source_rows,
)


def profile_exports(path: Path) -> list[dict]:
    profiles = []
    for source in list_tabular_sources(path):
        source_ref = str(source["source_ref"])
        rows = read_source_rows(path, source_ref)
        if not rows:
            profiles.append(
                {
                    "file": source_ref,
                    "row_count": 0,
                    "columns": [],
                    "inferred_entities": [],
                    "format": source["format"],
                    "sheet": source["sheet"],
                }
            )
            continue

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
                    "sensitivity": infer_sensitivity(column, source_ref),
                }
            )
        profiles.append(
            {
                "file": source_ref,
                "row_count": len(rows),
                "columns": columns,
                "inferred_entities": infer_entities(source_ref, columns),
                "format": source["format"],
                "sheet": source["sheet"],
            }
        )
    return profiles


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
