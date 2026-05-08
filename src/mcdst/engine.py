from __future__ import annotations

from pathlib import Path

from mcdst.dry_run import dry_run_transform
from mcdst.learning import build_column_suggestions
from mcdst.mapping import build_mapping_document, propose_mapping, propose_value_mappings
from mcdst.profiling import profile_exports
from mcdst.registry import apply_registry_to_proposals, learn_from_review, load_registry
from mcdst.review import apply_review_decisions, build_review_template
from mcdst.source_graph import build_source_graph
from mcdst.utils import read_json, read_yaml, write_json, write_yaml


def propose_mapping_workdir(
    exports_dir: Path,
    workdir: Path,
    *,
    source_system: str = "UNKNOWN_SOURCE",
    schema_version: str = "mcdst-v0.1",
    run_dry: bool = True,
    registry_path: Path | None = None,
    learning_model_path: Path | None = None,
    learning_suggestions_top_k: int = 3,
    learning_suggestions_min_score: float = 0.65,
) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    profiles = profile_exports(exports_dir)
    source_graph = build_source_graph(profiles)
    join_candidates = source_graph["join_candidates"]
    join_rules = source_graph["join_rules"]
    proposals, blocked = propose_mapping(profiles)
    registry = load_registry(registry_path)
    proposals = apply_registry_to_proposals(
        proposals,
        registry,
        source_system=source_system,
    )
    value_mappings = propose_value_mappings(profiles, proposals)
    mapping = build_mapping_document(
        profiles,
        proposals,
        blocked,
        join_candidates,
        join_rules,
        value_mappings,
        source_system=source_system,
        schema_version=schema_version,
    )
    review_queue = build_review_template(mapping)

    write_json(workdir / "profiles.json", profiles)
    learning_suggestions = None
    if learning_model_path:
        learning_suggestions = build_column_suggestions(
            workdir,
            learning_model_path,
            workdir / "mapping_suggestions.json",
            top_k=learning_suggestions_top_k,
            min_score=learning_suggestions_min_score,
        )

    write_json(workdir / "source_graph.json", source_graph)
    write_json(workdir / "join_candidates.json", join_candidates)
    write_json(workdir / "join_rules.json", join_rules)
    write_json(workdir / "mapping_proposals.json", proposals)
    write_json(workdir / "value_mappings.json", value_mappings)
    write_yaml(workdir / "mapping_propose.yaml", mapping)
    write_yaml(workdir / "review_queue.yaml", review_queue)

    state = None
    if run_dry:
        state = dry_run_transform(mapping, exports_dir, workdir / "mcdst_dry_run_draft")
        write_json(workdir / "quality_report_draft.json", state["quality"])

    return {
        "profiles": profiles,
        "source_graph": source_graph,
        "join_candidates": join_candidates,
        "join_rules": join_rules,
        "proposals": proposals,
        "registry": registry,
        "learning_suggestions": learning_suggestions,
        "mapping": mapping,
        "review_queue": review_queue,
        "dry_run": state,
    }


def apply_review_workdir(workdir: Path, decisions_path: Path, registry_path: Path | None = None) -> dict:
    mapping = review_base_mapping(workdir)
    profiles = read_json(workdir / "profiles.json")
    decisions = read_yaml(decisions_path)
    validated = apply_review_decisions(mapping, decisions, profiles)
    registry = learn_from_review(mapping, decisions, registry_path)
    if registry_path:
        validated["learning_registry"] = {
            "path": str(registry_path),
            "column_mappings_count": len(registry.get("column_mappings", [])),
        }
    write_yaml(workdir / "mapping_valide.yaml", validated)
    write_json(workdir / "join_rules.json", validated.get("join_rules", []))
    write_yaml(workdir / "review_queue.yaml", build_review_template(validated))
    return validated


def review_base_mapping(workdir: Path) -> dict:
    draft = read_yaml(workdir / "mapping_propose.yaml")
    validated_path = workdir / "mapping_valide.yaml"
    review_queue_path = workdir / "review_queue.yaml"
    if not validated_path.exists() or not review_queue_path.exists():
        return draft

    validated = read_yaml(validated_path)
    current_queue = read_yaml(review_queue_path)
    if review_queue_signature(current_queue) == review_queue_signature(build_review_template(validated)):
        return validated
    return draft


def review_queue_signature(review_queue: dict) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    value_ids = [
        item["id"]
        for group in review_queue.get("pending_value_mappings", [])
        for item in group.get("mappings", [])
        if item.get("suggested_action") == "review" or item.get("status") == "a_revoir"
    ]
    return (
        tuple(sorted(item["id"] for item in review_queue.get("pending_column_mappings", []))),
        tuple(sorted(value_ids)),
        tuple(sorted(item["id"] for item in review_queue.get("pending_join_rules", []))),
    )


def apply_mapping_file(mapping_path: Path, exports_dir: Path, output_dir: Path) -> dict:
    mapping = read_yaml(mapping_path)
    state = dry_run_transform(mapping, exports_dir, output_dir)
    write_json(output_dir / "quality_report.json", state["quality"])
    return state
