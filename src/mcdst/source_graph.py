from __future__ import annotations

import difflib
import hashlib


KEY_ENTITY_HINTS = {
    "travailleur_id": {
        "columns": {"clepers", "clepersonne", "idsalarie", "idsal", "matricule"},
        "anchor_entity": "travailleur",
    },
    "entreprise_id": {
        "columns": {"cleadh", "cleadhesion", "idadh", "identreprise", "adh"},
        "anchor_entity": "entreprise",
    },
    "etablissement_id": {
        "columns": {"site", "idsite", "idetab", "idetablissement"},
        "anchor_entity": "etablissement",
    },
}
REFERENCE_ENTITIES = {"travailleur", "entreprise", "etablissement", "unite_travail"}


def build_source_graph(profiles: list[dict]) -> dict:
    join_candidates = detect_join_candidates(profiles)
    return {
        "nodes": [
            {
                "source_file": profile["file"],
                "format": profile.get("format", "csv"),
                "sheet": profile.get("sheet"),
                "row_count": profile["row_count"],
                "inferred_entities": profile["inferred_entities"],
            }
            for profile in profiles
        ],
        "join_candidates": join_candidates,
        "join_rules": build_join_rules(join_candidates, profiles),
    }


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
                    name_score = difflib.SequenceMatcher(
                        None,
                        left_column["normalized"],
                        right_column["normalized"],
                    ).ratio()
                    type_bonus = 0.12 if left_column["inferred_type"] == right_column["inferred_type"] else 0.0
                    confidence = round(min((overlap_ratio * 0.78) + (name_score * 0.10) + type_bonus, 0.99), 3)
                    if confidence < 0.72:
                        continue
                    candidates.append(
                        {
                            "left_file": left_profile["file"],
                            "left_column": left_column["name"],
                            "left_distinct_count": left_column["distinct_count"],
                            "left_row_count": left_profile["row_count"],
                            "left_uniqueness_ratio": uniqueness_ratio(left_column, left_profile),
                            "right_file": right_profile["file"],
                            "right_column": right_column["name"],
                            "right_distinct_count": right_column["distinct_count"],
                            "right_row_count": right_profile["row_count"],
                            "right_uniqueness_ratio": uniqueness_ratio(right_column, right_profile),
                            "overlap_ratio": round(overlap_ratio, 3),
                            "overlap_values": sorted(overlap_values),
                            "confidence_score": confidence,
                            "status": "auto_validable" if confidence >= 0.85 else "a_revoir",
                        }
                    )
    return sorted(candidates, key=lambda item: (-item["confidence_score"], item["left_file"], item["right_file"]))


def build_join_rules(join_candidates: list[dict], profiles: list[dict]) -> list[dict]:
    profile_index = {profile["file"]: profile for profile in profiles}
    rules = []
    for candidate in join_candidates:
        left = join_side(candidate, "left", profile_index)
        right = join_side(candidate, "right", profile_index)
        key_role = shared_key_role(left["column"], right["column"])
        oriented = orient_join(left, right, key_role)

        if oriented:
            primary, foreign = oriented
            join_type = "primary_foreign_key"
            cardinality = infer_cardinality(primary, foreign)
            status = "auto_validable" if candidate["status"] == "auto_validable" else "a_revoir"
            rationale = "Primary side inferred from key role, entity context and uniqueness."
        else:
            primary = None
            foreign = None
            join_type = "peer_key_overlap"
            cardinality = "many_to_many"
            status = "a_revoir"
            rationale = "No unambiguous primary source detected; keep as review-only peer overlap."

        rules.append(
            {
                "id": join_rule_id(candidate),
                "key_role": key_role or "generic_key",
                "join_type": join_type,
                "cardinality": cardinality,
                "left": left,
                "right": right,
                "primary": primary,
                "foreign": foreign,
                "overlap_ratio": candidate["overlap_ratio"],
                "overlap_values": candidate["overlap_values"],
                "confidence_score": candidate["confidence_score"],
                "status": status,
                "rationale": rationale,
            }
        )
    return rules


def join_side(candidate: dict, side: str, profile_index: dict[str, dict]) -> dict:
    source_file = candidate[f"{side}_file"]
    profile = profile_index[source_file]
    return {
        "source_file": source_file,
        "column": candidate[f"{side}_column"],
        "row_count": candidate[f"{side}_row_count"],
        "distinct_count": candidate[f"{side}_distinct_count"],
        "uniqueness_ratio": candidate[f"{side}_uniqueness_ratio"],
        "inferred_entities": profile["inferred_entities"],
    }


def orient_join(left: dict, right: dict, key_role: str | None) -> tuple[dict, dict] | None:
    if key_role:
        anchor = KEY_ENTITY_HINTS[key_role]["anchor_entity"]
        left_anchor = anchor in left["inferred_entities"]
        right_anchor = anchor in right["inferred_entities"]
        if left_anchor and not right_anchor:
            return left, right
        if right_anchor and not left_anchor:
            return right, left
        if not left_anchor and not right_anchor:
            return None

    left_reference = bool(REFERENCE_ENTITIES.intersection(left["inferred_entities"]))
    right_reference = bool(REFERENCE_ENTITIES.intersection(right["inferred_entities"]))
    if left_reference and not right_reference:
        return left, right
    if right_reference and not left_reference:
        return right, left

    if left["uniqueness_ratio"] >= 0.98 and right["uniqueness_ratio"] < 0.98:
        return left, right
    if right["uniqueness_ratio"] >= 0.98 and left["uniqueness_ratio"] < 0.98:
        return right, left
    return None


def shared_key_role(left_column: str, right_column: str) -> str | None:
    left = normalize_key(left_column)
    right = normalize_key(right_column)
    for role, hints in KEY_ENTITY_HINTS.items():
        if left in hints["columns"] and right in hints["columns"]:
            return role
    return None


def infer_cardinality(primary: dict, foreign: dict) -> str:
    primary_unique = primary["uniqueness_ratio"] >= 0.98
    foreign_unique = foreign["uniqueness_ratio"] >= 0.98
    if primary_unique and foreign_unique:
        return "one_to_one"
    if primary_unique:
        return "one_to_many"
    return "many_to_many"


def uniqueness_ratio(column: dict, profile: dict) -> float:
    row_count = max(profile["row_count"], 1)
    return round(column["distinct_count"] / row_count, 3)


def normalize_key(column: str) -> str:
    return "".join(char for char in column.lower() if char.isalnum())


def join_rule_id(candidate: dict) -> str:
    raw = "|".join(
        [
            candidate["left_file"],
            candidate["left_column"],
            candidate["right_file"],
            candidate["right_column"],
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
