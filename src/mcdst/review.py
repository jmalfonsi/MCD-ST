from __future__ import annotations

import hashlib
import json

from mcdst.mapping import rebuild_value_mappings_for_mapping
from mcdst.utils import utc_now


def build_review_template(mapping: dict) -> dict:
    return {
        "review_version": "0.1.0",
        "generated_at": utc_now(),
        "instructions": "Validate, correct or reject the proposals with status a_revoir.",
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
            value_mapping_review_group(group)
            for group in mapping["value_mappings"]
            if group["review_status"] == "a_revoir"
        ],
        "pending_join_rules": [
            join_rule_review_item(rule)
            for rule in mapping.get("join_rules", [])
            if rule.get("status") == "a_revoir"
        ],
    }


def apply_review_decisions(mapping: dict, review_decisions: dict, profiles: list[dict]) -> dict:
    validated = json.loads(json.dumps(mapping))
    previous_value_mappings = mapping.get("value_mappings", [])
    approved_ids = {
        item["id"]: item
        for item in review_decisions.get("column_mapping_decisions", [])
        if item.get("action") == "approve"
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
            "review_reason": decision.get("reason", ""),
        }

    approved_review_ids = set(approved_ids.keys())
    validated["review_queue"] = [
        item for item in validated["review_queue"] if review_id(item) not in approved_review_ids
    ]
    validated["value_mappings"] = rebuild_value_mappings_for_mapping(validated, profiles)
    preserve_value_mapping_reviews(validated["value_mappings"], previous_value_mappings)
    apply_value_mapping_decisions(validated["value_mappings"], review_decisions)
    apply_join_rule_decisions(validated.get("join_rules", []), review_decisions)
    validated["review_decisions"] = review_decisions
    validated["mapping_version"] = next_reviewed_version(str(mapping.get("mapping_version", "0.1.0")))
    validated["review_status"] = "reviewed"
    validated["reviewed_at"] = utc_now()
    return validated


def join_rule_review_item(rule: dict) -> dict:
    primary = rule.get("primary") or {}
    foreign = rule.get("foreign") or {}
    left = rule.get("left") or {}
    right = rule.get("right") or {}
    return {
        "id": rule["id"],
        "key_role": rule.get("key_role", ""),
        "join_type": rule.get("join_type", ""),
        "cardinality": rule.get("cardinality", ""),
        "primary": {
            "source_file": primary.get("source_file", ""),
            "column": primary.get("column", ""),
        },
        "foreign": {
            "source_file": foreign.get("source_file", ""),
            "column": foreign.get("column", ""),
        },
        "left": {
            "source_file": left.get("source_file", ""),
            "column": left.get("column", ""),
        },
        "right": {
            "source_file": right.get("source_file", ""),
            "column": right.get("column", ""),
        },
        "confidence_score": rule.get("confidence_score", 0),
        "rationale": rule.get("rationale", ""),
        "suggested_action": "review",
    }


def value_mapping_review_group(group: dict) -> dict:
    reviewed = dict(group)
    reviewed["id"] = value_mapping_group_id(group)
    reviewed["mappings"] = [
        {
            **item,
            "id": value_mapping_id(group, item),
            "suggested_action": "review" if item["status"] == "a_revoir" else "none",
        }
        for item in group["mappings"]
    ]
    return reviewed


def apply_value_mapping_decisions(value_mappings: list[dict], review_decisions: dict) -> None:
    decisions = [
        item for item in review_decisions.get("value_mapping_decisions", [])
        if item.get("action") in {"approve", "correct", "reject"}
    ]
    by_id = {item["id"]: item for item in decisions if item.get("id")}
    by_key = {value_decision_key(item): item for item in decisions}

    for group in value_mappings:
        for item in group["mappings"]:
            decision = by_id.get(value_mapping_id(group, item)) or by_key.get(value_item_key(group, item))
            if not decision:
                continue
            action = decision.get("action")
            if action in {"approve", "correct"}:
                item["target_value"] = decision.get("target_value") or item["target_value"]
                item["status"] = "validated_by_human_review"
            elif action == "reject":
                item["status"] = "rejected"
            item["reviewer"] = decision.get("reviewer", "")
            item["review_reason"] = decision.get("reason", "")

        group["review_status"] = (
            "a_revoir"
            if any(item["status"] == "a_revoir" for item in group["mappings"])
            else "reviewed"
        )


def preserve_value_mapping_reviews(value_mappings: list[dict], previous_value_mappings: list[dict]) -> None:
    previous_by_key = {
        value_item_key(group, item): item
        for group in previous_value_mappings
        for item in group.get("mappings", [])
        if item.get("status") in {"validated_by_human_review", "rejected"}
    }
    for group in value_mappings:
        for item in group["mappings"]:
            previous = previous_by_key.get(value_item_key(group, item))
            if not previous:
                continue
            item["target_value"] = previous.get("target_value", item["target_value"])
            item["status"] = previous["status"]
            if previous.get("reviewer"):
                item["reviewer"] = previous["reviewer"]
            if previous.get("review_reason"):
                item["review_reason"] = previous["review_reason"]
        group["review_status"] = (
            "a_revoir"
            if any(item["status"] == "a_revoir" for item in group["mappings"])
            else "reviewed"
        )


def apply_join_rule_decisions(join_rules: list[dict], review_decisions: dict) -> None:
    decisions = {
        item["id"]: item
        for item in review_decisions.get("join_rule_decisions", [])
        if item.get("action") in {"approve", "reject"} and item.get("id")
    }
    for rule in join_rules:
        decision = decisions.get(rule.get("id"))
        if not decision:
            continue
        if decision["action"] == "approve":
            rule["status"] = "validated_by_human_review"
        elif decision["action"] == "reject":
            rule["status"] = "rejected"
        rule["reviewer"] = decision.get("reviewer", "")
        rule["review_reason"] = decision.get("reason", "")


def next_reviewed_version(version: str) -> str:
    return version if version.endswith("-reviewed") else f"{version}-reviewed"


def review_id(item: dict) -> str:
    raw = f"{item['source_file']}|{item['source_column']}|{item['entity']}|{item['target_field']}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def value_mapping_group_id(group: dict) -> str:
    raw = "|".join(
        [
            group["source_file"],
            group["source_column"],
            group["entity"],
            group["target_field"],
            group["transform"],
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def value_mapping_id(group: dict, item: dict) -> str:
    raw = "|".join(
        [
            group["source_file"],
            group["source_column"],
            group["entity"],
            group["target_field"],
            item["source_value"],
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def value_decision_key(decision: dict) -> tuple:
    return (
        decision.get("source_file", ""),
        decision.get("source_column", ""),
        decision.get("entity", ""),
        decision.get("target_field", ""),
        decision.get("source_value", ""),
    )


def value_item_key(group: dict, item: dict) -> tuple:
    return (
        group["source_file"],
        group["source_column"],
        group["entity"],
        group["target_field"],
        item["source_value"],
    )
