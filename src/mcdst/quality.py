from __future__ import annotations

from pathlib import Path

from mcdst.schema import REQUIRED_FIELDS
from mcdst.utils import read_source_rows


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
                "message": f"Missing required fields: {', '.join(missing)}" if missing else "All required fields are mapped.",
            }
        )
    return rules


def check_mapping_source_columns(mapping: dict, exports_dir: Path) -> list[dict]:
    rules = []
    for entity, payload in mapping["entities"].items():
        source_file = payload["source_file"]
        source_rows = read_source_rows(exports_dir, source_file)
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
                "message": f"Source columns missing in {source_file}: {', '.join(missing_sources)}"
                if missing_sources
                else f"All mapped columns exist in {source_file}.",
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
            "message": f"{queue_count} mapping proposals require human review."
            if queue_count
            else "No column mapping proposal is pending review.",
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
            "message": f"{len(pending)} nomenclature values require domain review: {', '.join(pending[:5])}"
            if pending
            else "No nomenclature value is pending domain review.",
        }
    ]


def check_join_candidates(mapping: dict) -> list[dict]:
    join_count = len(mapping["join_candidates"])
    return [
        {
            "rule": "source_graph:join_candidates",
            "severity": "alerte" if join_count == 0 else "info",
            "status": "failed" if join_count == 0 else "passed",
            "message": f"{join_count} join candidates detected between exports."
            if join_count
            else "No join candidate detected between exports.",
        }
    ]


def check_join_rules(mapping: dict) -> list[dict]:
    join_rules = mapping.get("join_rules", [])
    pending = [rule for rule in join_rules if rule["status"] == "a_revoir"]
    return [
        {
            "rule": "source_graph:explicit_join_rules",
            "severity": "alerte" if pending else "info",
            "status": "failed" if pending else "passed",
            "message": f"{len(join_rules)} explicit join rules generated; {len(pending)} require review."
            if pending
            else f"{len(join_rules)} explicit join rules generated.",
        }
    ]


def check_join_coverage(tables: dict) -> list[dict]:
    travailleur_ids = {row["travailleur_id"] for row in tables.get("travailleur", [])}
    rules = []
    for table_name in ["visite_sante_travail", "exposition_professionnelle", "episode_poste"]:
        unknown = [
            row.get("travailleur_id")
            for row in tables.get(table_name, [])
            if row.get("travailleur_id") not in travailleur_ids
        ]
        rules.append(
            {
                "rule": f"join_coverage:{table_name}.travailleur_id",
                "severity": "alerte" if unknown else "info",
                "status": "failed" if unknown else "passed",
                "message": f"{len(unknown)} worker ids are missing from table travailleur."
                if unknown
                else "All referenced workers exist.",
            }
        )
    return rules


def check_blocked_fields(mapping: dict) -> list[dict]:
    return [
        {
            "rule": "sensitivity:S4_blocked",
            "severity": "info",
            "status": "passed",
            "message": f"{len(mapping['blocked_fields'])} S4 fields excluded from standardized MCD-ST tables.",
        }
    ]
