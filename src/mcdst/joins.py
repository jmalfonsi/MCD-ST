from __future__ import annotations

from pathlib import Path
from typing import Any

from mcdst.utils import read_source_rows

USABLE_JOIN_STATUSES = {"auto_validable", "validated_by_human_review"}
USABLE_CARDINALITIES = {"one_to_one", "one_to_many"}


def build_join_context(mapping: dict, exports_dir: Path) -> dict[str, Any]:
    rules = usable_join_rules(mapping.get("join_rules", []))
    source_refs = sorted(
        {
            side["source_file"]
            for rule in rules
            for side in [rule["primary"], rule["foreign"]]
            if side and side.get("source_file")
        }
    )
    rows_by_source = {source_ref: read_source_rows(exports_dir, source_ref) for source_ref in source_refs}
    primary_indexes = {}
    index_diagnostics = []
    rules_by_foreign: dict[tuple[str, str], list[dict]] = {}

    for rule in rules:
        primary = rule["primary"]
        foreign = rule["foreign"]
        index_key = (primary["source_file"], primary["column"])
        if index_key not in primary_indexes:
            index, duplicate_values = build_unique_index(
                rows_by_source.get(primary["source_file"], []),
                primary["column"],
            )
            primary_indexes[index_key] = index
            if duplicate_values:
                index_diagnostics.append(
                    {
                        "source_file": primary["source_file"],
                        "column": primary["column"],
                        "duplicate_values_count": len(duplicate_values),
                        "duplicate_values": duplicate_values[:5],
                    }
                )
        rules_by_foreign.setdefault((foreign["source_file"], rule["key_role"]), []).append(rule)

    for candidates in rules_by_foreign.values():
        candidates.sort(key=join_rule_sort_key)

    return {
        "rules": rules,
        "rows_by_source": rows_by_source,
        "primary_indexes": primary_indexes,
        "rules_by_foreign": rules_by_foreign,
        "index_diagnostics": index_diagnostics,
        "usage": {
            "attempted": 0,
            "resolved": 0,
            "missed": 0,
            "by_key_role": {},
        },
    }


def usable_join_rules(join_rules: list[dict]) -> list[dict]:
    return [
        rule
        for rule in join_rules
        if rule.get("status") in USABLE_JOIN_STATUSES
        and rule.get("join_type") == "primary_foreign_key"
        and rule.get("cardinality") in USABLE_CARDINALITIES
        and rule.get("primary")
        and rule.get("foreign")
    ]


def source_key_value(
    join_context: dict[str, Any],
    source_file: str,
    row: dict[str, str],
    key_role: str,
    fallback_column: str,
) -> str:
    resolved = resolve_primary_value(join_context, source_file, row, key_role)
    if resolved:
        return resolved
    return row.get(fallback_column, "") if fallback_column else ""


def resolve_primary_value(
    join_context: dict[str, Any],
    source_file: str,
    row: dict[str, str],
    key_role: str,
) -> str:
    candidates = join_context["rules_by_foreign"].get((source_file, key_role), [])
    if not candidates:
        return ""

    join_context["usage"]["attempted"] += 1
    increment_key_role_usage(join_context, key_role, "attempted")
    for rule in candidates:
        primary_row = resolve_primary_row(join_context, rule, row)
        if not primary_row:
            continue
        value = primary_row.get(rule["primary"]["column"], "")
        if value:
            join_context["usage"]["resolved"] += 1
            increment_key_role_usage(join_context, key_role, "resolved")
            return value

    join_context["usage"]["missed"] += 1
    increment_key_role_usage(join_context, key_role, "missed")
    return ""


def resolve_primary_row(join_context: dict[str, Any], rule: dict, foreign_row: dict[str, str]) -> dict[str, str] | None:
    primary = rule["primary"]
    foreign = rule["foreign"]
    foreign_value = foreign_row.get(foreign["column"], "")
    if not foreign_value:
        return None
    index = join_context["primary_indexes"].get((primary["source_file"], primary["column"]), {})
    return index.get(foreign_value)


def build_unique_index(rows: list[dict[str, str]], column: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    index: dict[str, dict[str, str]] = {}
    duplicate_values = set()
    for row in rows:
        value = row.get(column, "")
        if not value:
            continue
        if value in index:
            duplicate_values.add(value)
            continue
        index[value] = row
    for value in duplicate_values:
        index.pop(value, None)
    return index, sorted(duplicate_values)


def join_resolution_summary(join_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "usable_rules_count": len(join_context["rules"]),
        "attempted_count": join_context["usage"]["attempted"],
        "resolved_count": join_context["usage"]["resolved"],
        "missed_count": join_context["usage"]["missed"],
        "by_key_role": join_context["usage"]["by_key_role"],
        "index_diagnostics": join_context["index_diagnostics"],
    }


def increment_key_role_usage(join_context: dict[str, Any], key_role: str, counter: str) -> None:
    usage = join_context["usage"]["by_key_role"].setdefault(
        key_role,
        {
            "attempted": 0,
            "resolved": 0,
            "missed": 0,
        },
    )
    usage[counter] += 1


def join_rule_sort_key(rule: dict) -> tuple[float, float, str]:
    primary_uniqueness = float(rule.get("primary", {}).get("uniqueness_ratio") or 0)
    confidence = float(rule.get("confidence_score") or 0)
    return (-primary_uniqueness, -confidence, rule.get("id", ""))
