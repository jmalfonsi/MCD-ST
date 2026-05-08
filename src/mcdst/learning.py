from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from mcdst.schema import TARGET_SCHEMA
from mcdst.utils import normalize, read_json, read_yaml, utc_now, write_json


POSITIVE_VALUE_STATUSES = {"auto", "validated_by_human_review", "validated_by_registry"}
MODEL_KIND = "mcdst-column-centroid-v0.1"
BLOCKED_S4_LABEL = "__BLOCKED_S4__"


def build_learning_dataset(workdir: Path, output_path: Path) -> dict:
    profiles = read_json(workdir / "profiles.json")
    mapping = read_yaml(workdir / "mapping_valide.yaml")
    records = learning_records(mapping, profiles)
    write_jsonl(output_path, records)
    return dataset_summary(records, output_path)


def train_column_model(dataset_path: Path, output_path: Path) -> dict:
    records = [
        record for record in read_jsonl(dataset_path)
        if record.get("task") == "column_mapping"
    ]
    training = [
        {
            "label": column_model_label(record),
            "features": feature_counts(record),
        }
        for record in records
    ]
    document_frequency = Counter()
    for item in training:
        document_frequency.update(item["features"].keys())

    idf = {
        token: round(math.log((len(training) + 1) / (count + 1)) + 1.0, 6)
        for token, count in sorted(document_frequency.items())
    }
    label_vectors: dict[str, Counter] = defaultdict(Counter)
    label_counts = Counter()
    for item in training:
        label = item["label"]
        vector = tfidf_vector(item["features"], idf)
        label_vectors[label].update(vector)
        label_counts[label] += 1

    centroids = {
        label: normalize_vector({
            token: value / label_counts[label]
            for token, value in vector.items()
        })
        for label, vector in sorted(label_vectors.items())
    }
    model = {
        "model_kind": MODEL_KIND,
        "created_at": utc_now(),
        "dataset_path": str(dataset_path),
        "examples_count": len(training),
        "labels_count": len(centroids),
        "label_counts": dict(sorted(label_counts.items())),
        "idf": idf,
        "centroids": centroids,
    }
    write_json(output_path, model)
    return {
        "model_path": str(output_path),
        "model_kind": MODEL_KIND,
        "examples_count": len(training),
        "labels_count": len(centroids),
        "blocked_s4_examples": label_counts.get(BLOCKED_S4_LABEL, 0),
    }


def evaluate_column_model(dataset_path: Path, model_path: Path, top_k: int = 3) -> dict:
    model = read_json(model_path)
    records = [
        record for record in read_jsonl(dataset_path)
        if record.get("task") == "column_mapping"
    ]
    top1_hits = 0
    topk_hits = 0
    blocked_total = 0
    blocked_hits = 0
    for record in records:
        expected = column_model_label(record)
        predictions = predict_column_mapping(model, record, top_k=max(top_k, 1))
        predicted_labels = [item["label"] for item in predictions]
        if predicted_labels and predicted_labels[0] == expected:
            top1_hits += 1
        if expected in predicted_labels[:top_k]:
            topk_hits += 1
        if expected == BLOCKED_S4_LABEL:
            blocked_total += 1
            if predicted_labels and predicted_labels[0] == BLOCKED_S4_LABEL:
                blocked_hits += 1

    return {
        "dataset_path": str(dataset_path),
        "model_path": str(model_path),
        "examples_count": len(records),
        "top1_accuracy": round(top1_hits / max(len(records), 1), 4),
        "top3_accuracy": round(topk_hits / max(len(records), 1), 4),
        "blocked_s4_recall": round(blocked_hits / max(blocked_total, 1), 4),
        "blocked_s4_examples": blocked_total,
    }


def build_column_suggestions(
    workdir: Path,
    model_path: Path,
    output_path: Path,
    *,
    top_k: int = 3,
    min_score: float = 0.65,
) -> dict:
    profiles = read_json(workdir / "profiles.json")
    model = read_json(model_path)
    suggestions = suggest_column_mappings(profiles, model, top_k=top_k, min_score=min_score)
    payload = {
        "model_path": str(model_path),
        "model_kind": model.get("model_kind"),
        "profiles_path": str(workdir / "profiles.json"),
        "generated_at": utc_now(),
        "top_k": top_k,
        "min_score": min_score,
        "summary": suggestion_summary(profiles, suggestions),
        "suggestions": suggestions,
    }
    write_json(output_path, payload)
    return {
        "suggestions_path": str(output_path),
        "model_kind": model.get("model_kind"),
        **payload["summary"],
    }


def suggest_column_mappings(
    profiles: list[dict],
    model: dict,
    *,
    top_k: int = 3,
    min_score: float = 0.65,
) -> list[dict]:
    suggestions = []
    max_predictions = max(len(model.get("centroids", {})), top_k, 1)
    for profile in profiles:
        candidate_entities = profile.get("inferred_entities") or [None]
        for column in profile.get("columns", []):
            if column.get("sensitivity") == "S4":
                suggestions.append(blocked_s4_suggestion(profile, column))
                continue

            for entity in candidate_entities:
                record = column_prediction_record(profile, column, entity)
                predictions = predict_column_mapping(model, record, top_k=max_predictions)
                ranked = rank_entity_predictions(
                    predictions,
                    entity,
                    source_type=column.get("inferred_type"),
                    top_k=top_k,
                    min_score=min_score,
                )
                for rank, prediction in enumerate(ranked, start=1):
                    target_entity, target_field = split_target_label(prediction["label"])
                    target_type = target_field_type(target_entity, target_field)
                    suggestions.append(
                        {
                            "source_file": profile["file"],
                            "source_column": column["name"],
                            "source_type": column.get("inferred_type"),
                            "source_sensitivity": column.get("sensitivity"),
                            "candidate_entity": entity,
                            "rank": rank,
                            "target": prediction["target"],
                            "entity": target_entity,
                            "target_field": target_field,
                            "target_type": target_type,
                            "score": prediction["score"],
                            "status": suggestion_status(prediction["score"]),
                            "examples": column.get("examples", []),
                        }
                    )
    return sorted(
        suggestions,
        key=lambda item: (
            item["source_file"],
            item["source_column"],
            item.get("candidate_entity") or "",
            item.get("rank", 0),
            item.get("target") or "",
        ),
    )


def predict_column_mapping(model: dict, record: dict, top_k: int = 5) -> list[dict]:
    if record.get("source_sensitivity") == "S4":
        return [
            {
                "label": BLOCKED_S4_LABEL,
                "target": None,
                "score": 1.0,
                "reason": "S4 guard",
            }
        ]
    vector = tfidf_vector(feature_counts(record), model["idf"])
    scores = []
    for label, centroid in model["centroids"].items():
        score = dot(vector, centroid)
        scores.append(
            {
                "label": label,
                "target": None if label == BLOCKED_S4_LABEL else label,
                "score": round(score, 6),
            }
        )
    return sorted(scores, key=lambda item: (-item["score"], item["label"]))[:top_k]


def column_prediction_record(profile: dict, column: dict, entity: str | None) -> dict:
    return {
        "source_file": profile["file"],
        "source_column": column["name"],
        "source_column_normalized": column.get("normalized"),
        "source_type": column.get("inferred_type"),
        "source_sensitivity": column.get("sensitivity"),
        "source_examples": column.get("examples", []),
        "source_top_values": column.get("top_values", []),
        "entity": entity,
    }


def rank_entity_predictions(
    predictions: list[dict],
    entity: str | None,
    *,
    source_type: str | None,
    top_k: int,
    min_score: float,
) -> list[dict]:
    ranked = []
    for prediction in predictions:
        if prediction["label"] == BLOCKED_S4_LABEL:
            continue
        target_entity, target_field = split_target_label(prediction["label"])
        if entity and target_entity != entity:
            continue
        if not target_type_compatible(source_type, target_field_type(target_entity, target_field)):
            continue
        if prediction["score"] < min_score:
            continue
        ranked.append(prediction)
        if len(ranked) == top_k:
            break
    return ranked


def blocked_s4_suggestion(profile: dict, column: dict) -> dict:
    return {
        "source_file": profile["file"],
        "source_column": column["name"],
        "source_type": column.get("inferred_type"),
        "source_sensitivity": column.get("sensitivity"),
        "candidate_entity": None,
        "rank": 1,
        "target": None,
        "entity": None,
        "target_field": None,
        "target_type": None,
        "score": 1.0,
        "status": "blocked_s4",
        "reason": "S4 guard",
        "examples": column.get("examples", []),
    }


def split_target_label(label: str) -> tuple[str | None, str | None]:
    if not label or label == BLOCKED_S4_LABEL or "." not in label:
        return None, None
    entity, target_field = label.split(".", 1)
    return entity, target_field


def target_field_type(entity: str | None, target_field: str | None) -> str | None:
    if not entity or not target_field:
        return None
    return TARGET_SCHEMA.get(entity, {}).get(target_field, {}).get("type")


def target_type_compatible(source_type: str | None, target_type: str | None) -> bool:
    if not source_type or not target_type:
        return True
    if source_type == target_type:
        return True
    compatible = {
        ("identifier", "categorical"),
        ("categorical", "text"),
        ("text", "categorical"),
        ("year", "numeric"),
        ("numeric", "year"),
        ("code", "categorical"),
        ("categorical", "code"),
    }
    return (source_type, target_type) in compatible


def suggestion_status(score: float) -> str:
    if score >= 0.65:
        return "strong_candidate"
    if score >= 0.35:
        return "review_candidate"
    return "low_confidence"


def suggestion_summary(profiles: list[dict], suggestions: list[dict]) -> dict:
    return {
        "files_count": len(profiles),
        "columns_count": sum(len(profile.get("columns", [])) for profile in profiles),
        "suggestions_count": len(suggestions),
        "blocked_s4_columns": len([item for item in suggestions if item["status"] == "blocked_s4"]),
        "strong_candidates": len([item for item in suggestions if item["status"] == "strong_candidate"]),
        "review_candidates": len([item for item in suggestions if item["status"] == "review_candidate"]),
        "low_confidence": len([item for item in suggestions if item["status"] == "low_confidence"]),
    }


def learning_records(mapping: dict, profiles: list[dict]) -> list[dict]:
    profile_index = {
        (profile["file"], column["name"]): column
        for profile in profiles
        for column in profile["columns"]
    }
    records = []
    records.extend(column_mapping_records(mapping, profile_index))
    records.extend(blocked_field_records(mapping, profile_index))
    records.extend(value_mapping_records(mapping))
    return records


def column_mapping_records(mapping: dict, profile_index: dict[tuple[str, str], dict]) -> list[dict]:
    records = []
    for entity, payload in mapping["entities"].items():
        source_file = payload["source_file"]
        for target_field, spec in payload["fields"].items():
            column = profile_index.get((source_file, spec["source"]), {})
            records.append(
                {
                    "task": "column_mapping",
                    "label": "positive",
                    "source_system": mapping["source_system"],
                    "schema_version": mapping["schema_version"],
                    "mapping_version": mapping["mapping_version"],
                    "source_file": source_file,
                    "source_column": spec["source"],
                    "source_column_normalized": column.get("normalized"),
                    "source_type": column.get("inferred_type"),
                    "source_sensitivity": column.get("sensitivity"),
                    "source_examples": column.get("examples", []),
                    "source_top_values": column.get("top_values", []),
                    "entity": entity,
                    "target_field": target_field,
                    "target": f"{entity}.{target_field}",
                    "transform": spec.get("transform"),
                    "confidence_score": spec.get("confidence_score"),
                    "review_status": spec.get("review_status"),
                }
            )
    return records


def blocked_field_records(mapping: dict, profile_index: dict[tuple[str, str], dict]) -> list[dict]:
    records = []
    for blocked in mapping["blocked_fields"]:
        source_file = blocked["source_file"]
        source_column = blocked["column"]
        column = profile_index.get((source_file, source_column), {})
        records.append(
            {
                "task": "column_mapping",
                "label": "blocked_s4",
                "source_system": mapping["source_system"],
                "schema_version": mapping["schema_version"],
                "mapping_version": mapping["mapping_version"],
                "source_file": source_file,
                "source_column": source_column,
                "source_column_normalized": column.get("normalized"),
                "source_type": column.get("inferred_type"),
                "source_sensitivity": blocked["sensitivity"],
                "source_examples": column.get("examples", []),
                "source_top_values": column.get("top_values", []),
                "entity": None,
                "target_field": None,
                "target": None,
                "transform": None,
                "review_status": "blocked_s4",
                "blocked_reason": blocked.get("reason"),
                "recommended_action": blocked.get("recommended_action"),
            }
        )
    return records


def value_mapping_records(mapping: dict) -> list[dict]:
    records = []
    for group in mapping["value_mappings"]:
        for item in group["mappings"]:
            records.append(
                {
                    "task": "value_mapping",
                    "label": value_mapping_label(item.get("status", "")),
                    "source_system": mapping["source_system"],
                    "schema_version": mapping["schema_version"],
                    "mapping_version": mapping["mapping_version"],
                    "source_file": group["source_file"],
                    "source_column": group["source_column"],
                    "entity": group["entity"],
                    "target_field": group["target_field"],
                    "target": f"{group['entity']}.{group['target_field']}",
                    "transform": group["transform"],
                    "source_value": item["source_value"],
                    "target_value": item["target_value"],
                    "count": item.get("count"),
                    "review_status": item.get("status"),
                }
            )
    return records


def value_mapping_label(status: str) -> str:
    if status in POSITIVE_VALUE_STATUSES:
        return "positive"
    if status == "a_revoir":
        return "needs_review"
    if status == "rejected":
        return "rejected"
    return status or "unknown"


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            file.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dataset_summary(records: list[dict], output_path: Path) -> dict:
    by_task = Counter(record["task"] for record in records)
    by_label = Counter(record["label"] for record in records)
    return {
        "output_path": str(output_path),
        "records_count": len(records),
        "by_task": dict(sorted(by_task.items())),
        "by_label": dict(sorted(by_label.items())),
    }


def column_model_label(record: dict) -> str:
    if record.get("label") == "blocked_s4":
        return BLOCKED_S4_LABEL
    return str(record.get("target") or "")


def feature_counts(record: dict) -> Counter:
    tokens = []
    tokens.extend(weighted_tokens("file", normalize(Path(str(record.get("source_file", ""))).stem), 2))
    tokens.extend(weighted_tokens("column", str(record.get("source_column_normalized") or normalize(str(record.get("source_column", "")))), 5))
    tokens.extend(weighted_tokens("type", str(record.get("source_type") or ""), 3))
    tokens.extend(weighted_tokens("sensitivity", str(record.get("source_sensitivity") or ""), 3))
    tokens.extend(weighted_tokens("entity", str(record.get("entity") or ""), 4))
    tokens.extend(weighted_tokens("transform", str(record.get("transform") or ""), 2))
    for value in record.get("source_examples") or []:
        tokens.extend(weighted_tokens("example", normalize(str(value)), 1))
    for item in record.get("source_top_values") or []:
        if isinstance(item, list) and item:
            tokens.extend(weighted_tokens("value", normalize(str(item[0])), 1))
    return Counter(token for token in tokens if token)


def weighted_tokens(prefix: str, value: str, weight: int) -> list[str]:
    if not value:
        return []
    base = f"{prefix}:{value}"
    tokens = [base]
    tokens.extend(f"{prefix}:ngram:{ngram}" for ngram in char_ngrams(value))
    return tokens * max(weight, 1)


def char_ngrams(value: str, min_n: int = 3, max_n: int = 5) -> list[str]:
    compact = normalize(value)
    if len(compact) < min_n:
        return [compact] if compact else []
    output = []
    for size in range(min_n, min(max_n, len(compact)) + 1):
        output.extend(compact[index : index + size] for index in range(0, len(compact) - size + 1))
    return output


def tfidf_vector(features: Counter, idf: dict[str, float]) -> dict[str, float]:
    weighted = {
        token: count * idf[token]
        for token, count in features.items()
        if token in idf
    }
    return normalize_vector(weighted)


def normalize_vector(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm == 0:
        return {}
    return {
        token: round(value / norm, 8)
        for token, value in sorted(vector.items())
        if value
    }


def dot(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())
