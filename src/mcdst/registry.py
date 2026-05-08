from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from mcdst.utils import normalize, read_yaml, utc_now, write_yaml

DEFAULT_REGISTRY_PATH = Path("work/mapping_registry.yaml")
REGISTRY_VERSION = "0.1.0"
REGISTRY_CONFIDENCE = 0.995
REGISTRY_STATUS = "validated_by_registry"


def load_registry(path: Path | None) -> dict:
    if not path or not path.exists():
        return empty_registry()
    registry = read_yaml(path) or {}
    registry.setdefault("registry_version", REGISTRY_VERSION)
    registry.setdefault("column_mappings", [])
    registry.setdefault("value_mappings", [])
    return registry


def empty_registry() -> dict:
    return {
        "registry_version": REGISTRY_VERSION,
        "updated_at": None,
        "column_mappings": [],
        "value_mappings": [],
    }


def save_registry(path: Path, registry: dict) -> None:
    registry["updated_at"] = utc_now()
    write_yaml(path, registry)


def learn_from_review(
    mapping: dict,
    review_decisions: dict,
    registry_path: Path | None,
) -> dict:
    registry = load_registry(registry_path)
    if not registry_path:
        return registry

    approved = {
        item["id"]: item
        for item in review_decisions.get("column_mapping_decisions", [])
        if item.get("action") == "approve"
    }
    learned = False
    for proposal in mapping.get("review_queue", []):
        decision = approved.get(review_id(proposal))
        if not decision:
            continue
        upsert_column_mapping(registry, mapping, proposal, decision)
        learned = True

    if learned:
        save_registry(registry_path, registry)
    return registry


def apply_registry_to_proposals(
    proposals: list[dict],
    registry: dict,
    *,
    source_system: str,
) -> list[dict]:
    memory = {
        registry_match_key(entry["source_column"], entry["entity"], entry["target_field"], entry.get("transform"))
        : entry
        for entry in registry.get("column_mappings", [])
        if entry.get("source_system") == source_system
    }
    output = []
    for proposal in proposals:
        entry = memory.get(
            registry_match_key(
                proposal["source_column"],
                proposal["entity"],
                proposal["target_field"],
                proposal.get("transform"),
            )
        )
        if not entry:
            output.append(proposal)
            continue
        learned = dict(proposal)
        learned["status"] = REGISTRY_STATUS
        learned["confidence_score"] = max(float(learned["confidence_score"]), REGISTRY_CONFIDENCE)
        learned["registry_entry_id"] = entry["id"]
        learned["justification"] = f"{learned['justification']}; registry={entry['id']}"
        output.append(learned)
    return output


def upsert_column_mapping(registry: dict, mapping: dict, proposal: dict, decision: dict[str, Any]) -> None:
    entry_id = registry_entry_id(
        mapping["source_system"],
        proposal["source_column"],
        proposal["entity"],
        proposal["target_field"],
        proposal.get("transform"),
    )
    now = utc_now()
    existing = next(
        (entry for entry in registry["column_mappings"] if entry["id"] == entry_id),
        None,
    )
    if existing:
        existing["decision_count"] += 1
        existing["last_learned_at"] = now
        existing["last_reviewer"] = decision.get("reviewer", "")
        existing["last_reason"] = decision.get("reason", "")
        return

    registry["column_mappings"].append(
        {
            "id": entry_id,
            "source_system": mapping["source_system"],
            "schema_version": mapping["schema_version"],
            "source_column": proposal["source_column"],
            "source_column_normalized": normalize(proposal["source_column"]),
            "source_type": proposal.get("source_type"),
            "source_sensitivity": proposal.get("source_sensitivity"),
            "entity": proposal["entity"],
            "target_field": proposal["target_field"],
            "target_sensitivity": proposal.get("target_sensitivity"),
            "transform": proposal.get("transform"),
            "status": "validated_by_human_review",
            "decision_count": 1,
            "first_learned_at": now,
            "last_learned_at": now,
            "last_reviewer": decision.get("reviewer", ""),
            "last_reason": decision.get("reason", ""),
        }
    )


def registry_match_key(source_column: str, entity: str, target_field: str, transform: str | None) -> tuple:
    return (normalize(source_column), entity, target_field, transform or "")


def registry_entry_id(
    source_system: str,
    source_column: str,
    entity: str,
    target_field: str,
    transform: str | None,
) -> str:
    raw = "|".join(
        [
            source_system,
            normalize(source_column),
            entity,
            target_field,
            transform or "",
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def review_id(item: dict) -> str:
    raw = f"{item['source_file']}|{item['source_column']}|{item['entity']}|{item['target_field']}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
