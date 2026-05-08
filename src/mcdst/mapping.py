from __future__ import annotations

import difflib
from collections import defaultdict

from mcdst.schema import (
    AUTO_THRESHOLD,
    REQUIRED_FIELDS,
    REVIEW_THRESHOLD,
    TARGET_SCHEMA,
    VALUE_MAPPING_TRANSFORMS,
)
from mcdst.transforms import apply_transform, value_mapping_status
from mcdst.utils import normalize, utc_now

AUTO_MAPPING_STATUSES = {"auto_validable", "validated_by_registry"}


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
                        "reason": "direct identifier, sensitive free text or directly identifying company field",
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
                "justification": f"name={alias_score:.2f}, type={type_score:.2f}, values={value_score:.2f}",
            }
        )
    if not candidates:
        return None
    return max(candidates, key=lambda item: item["confidence_score"])


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
    if "naf" in field and any(value[:4].isdigit() and len(value) == 5 for value in examples):
        return 1.0
    if "flag" in field and set(examples).intersection({"oui", "non", "true", "false"}):
        return 0.9
    return 0.5


def propose_value_mappings(profiles: list[dict], proposals: list[dict]) -> list[dict]:
    profile_index = {
        (profile["file"], column["name"]): column
        for profile in profiles
        for column in profile["columns"]
    }
    value_mappings = []
    for proposal in proposals:
        if proposal["status"] not in AUTO_MAPPING_STATUSES:
            continue
        transform = proposal.get("transform")
        if transform not in VALUE_MAPPING_TRANSFORMS:
            continue
        column = profile_index[(proposal["source_file"], proposal["source_column"])]
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
        value_mappings.append(value_mapping_group(proposal, transform, mappings))
    return value_mappings


def value_mapping_group(proposal: dict, transform: str, mappings: list[dict]) -> dict:
    return {
        "source_file": proposal["source_file"],
        "source_column": proposal["source_column"],
        "entity": proposal["entity"],
        "target_field": proposal["target_field"],
        "transform": transform,
        "review_status": "a_revoir" if any(item["status"] == "a_revoir" for item in mappings) else "auto_draft",
        "mappings": mappings,
    }


def build_mapping_document(
    profiles: list[dict],
    proposals: list[dict],
    blocked: list[dict],
    join_candidates: list[dict],
    join_rules: list[dict],
    value_mappings: list[dict],
    *,
    source_system: str,
    schema_version: str,
    mapping_version: str = "0.1.0-draft",
) -> dict:
    entities = {}
    selected_groups, alternate_sources = select_entity_source_groups(proposals)
    for entity_name, group in selected_groups.items():
        entity = entities.setdefault(
            entity_name,
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
        "mapping_id": f"{source_system.lower()}_{schema_version}_draft".replace("-", "_"),
        "source_system": source_system,
        "schema_version": schema_version,
        "mapping_version": mapping_version,
        "review_status": "draft",
        "generated_at": utc_now(),
        "thresholds": {
            "auto_validable": AUTO_THRESHOLD,
            "a_revoir": REVIEW_THRESHOLD,
        },
        "source_files": [
            {
                "file": profile["file"],
                "row_count": profile["row_count"],
                "inferred_entities": profile["inferred_entities"],
                "format": profile.get("format", "csv"),
                "sheet": profile.get("sheet"),
            }
            for profile in profiles
        ],
        "join_candidates": join_candidates,
        "join_rules": join_rules,
        "alternate_entity_sources": alternate_sources,
        "entities": entities,
        "review_queue": [p for p in proposals if p["status"] == "a_revoir"],
        "value_mappings": value_mappings,
        "blocked_fields": blocked,
    }


def select_entity_source_groups(proposals: list[dict]) -> tuple[dict, list[dict]]:
    groups = defaultdict(list)
    for proposal in proposals:
        if proposal["status"] in AUTO_MAPPING_STATUSES:
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
            if transform not in VALUE_MAPPING_TRANSFORMS:
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
