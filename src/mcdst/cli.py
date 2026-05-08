from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcdst import __version__
from mcdst.api import serve
from mcdst.cohort import evaluate_cohort_definition
from mcdst.engine import apply_mapping_file, apply_review_workdir, propose_mapping_workdir
from mcdst.learning import (
    build_column_suggestions,
    build_learning_dataset,
    evaluate_column_model,
    predict_column_mapping,
    train_column_model,
)
from mcdst.utils import read_json
from mcdst.registry import DEFAULT_REGISTRY_PATH


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcdst", description="MCD-ST command line tools")
    parser.add_argument("--version", action="version", version=f"mcdst {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the local MCD-ST HTTP API")
    serve_parser.add_argument("--host", default="127.0.0.1", help="API bind host")
    serve_parser.add_argument("--port", type=int, default=8765, help="API bind port")
    serve_parser.set_defaults(func=cmd_serve)

    mapping = subparsers.add_parser("mapping", help="Mapping engine commands")
    mapping_subparsers = mapping.add_subparsers(dest="mapping_command")

    propose = mapping_subparsers.add_parser("propose", help="Profile exports and propose a MCD-ST mapping")
    propose.add_argument("exports", type=Path, help="Directory containing source CSV exports")
    propose.add_argument("--out", type=Path, required=True, help="Work directory for generated artifacts")
    propose.add_argument("--schema", default="mcdst-v0.1", help="Target schema version")
    propose.add_argument("--source-system", default="UNKNOWN_SOURCE", help="Source system name")
    propose.add_argument("--registry", type=Path, help="Optional local mapping memory registry")
    propose.add_argument("--learning-model", type=Path, help="Optional local column mapping model JSON")
    propose.add_argument("--learning-top-k", type=int, default=3, help="Learning suggestions per column")
    propose.add_argument("--learning-min-score", type=float, default=0.65, help="Minimum learning suggestion score")
    propose.add_argument("--no-dry-run", action="store_true", help="Skip draft dry-run generation")
    propose.set_defaults(func=cmd_mapping_propose)

    review = mapping_subparsers.add_parser("review", help="Apply human review decisions to a proposed mapping")
    review.add_argument("decisions", type=Path, help="YAML decisions file")
    review.add_argument("--workdir", type=Path, required=True, help="Work directory created by mapping propose")
    review.add_argument("--registry", type=Path, help="Optional local mapping memory registry")
    review.set_defaults(func=cmd_mapping_review)

    apply = mapping_subparsers.add_parser("apply", help="Apply a validated mapping and generate MCD-ST tables")
    apply.add_argument("mapping", type=Path, help="Validated mapping YAML file")
    apply.add_argument("--exports", type=Path, required=True, help="Directory containing source CSV exports")
    apply.add_argument("--out", type=Path, required=True, help="Output directory for generated MCD-ST CSV tables")
    apply.set_defaults(func=cmd_mapping_apply)

    cohort = subparsers.add_parser("cohort", help="Cohort feasibility and execution commands")
    cohort_subparsers = cohort.add_subparsers(dest="cohort_command")

    evaluate = cohort_subparsers.add_parser("evaluate", help="Evaluate a cohort YAML definition on MCD-ST tables")
    evaluate.add_argument("definition", type=Path, help="Cohort YAML definition")
    evaluate.add_argument("--tables", type=Path, required=True, help="Directory containing MCD-ST CSV tables")
    evaluate.add_argument("--out", type=Path, help="Optional JSON report output path")
    evaluate.add_argument("--html-out", type=Path, help="Optional HTML report output path")
    evaluate.set_defaults(func=cmd_cohort_evaluate)

    learning = subparsers.add_parser("learning", help="Learning dataset and model commands")
    learning_subparsers = learning.add_subparsers(dest="learning_command")

    dataset = learning_subparsers.add_parser("dataset", help="Export a JSONL learning dataset from reviewed mapping artifacts")
    dataset.add_argument("--workdir", type=Path, required=True, help="Work directory containing profiles.json and mapping_valide.yaml")
    dataset.add_argument("--out", type=Path, required=True, help="Output JSONL dataset path")
    dataset.set_defaults(func=cmd_learning_dataset)

    train = learning_subparsers.add_parser("train", help="Train a local column mapping baseline model")
    train.add_argument("--dataset", type=Path, required=True, help="JSONL dataset created by learning dataset")
    train.add_argument("--out", type=Path, required=True, help="Output model JSON path")
    train.set_defaults(func=cmd_learning_train)

    evaluate_model = learning_subparsers.add_parser("evaluate", help="Evaluate a local column mapping model")
    evaluate_model.add_argument("--dataset", type=Path, required=True, help="JSONL dataset created by learning dataset")
    evaluate_model.add_argument("--model", type=Path, required=True, help="Model JSON path")
    evaluate_model.set_defaults(func=cmd_learning_evaluate)

    predict = learning_subparsers.add_parser("predict", help="Predict target mappings for one source column")
    predict.add_argument("--model", type=Path, required=True, help="Model JSON path")
    predict.add_argument("--source-file", required=True, help="Source file name")
    predict.add_argument("--source-column", required=True, help="Source column name")
    predict.add_argument("--source-type", default="", help="Inferred source type")
    predict.add_argument("--source-sensitivity", default="", help="Inferred source sensitivity")
    predict.add_argument("--entity", default="", help="Candidate target entity")
    predict.add_argument("--example", action="append", default=[], help="Example source value")
    predict.add_argument("--top-k", type=int, default=5, help="Number of predictions to show")
    predict.set_defaults(func=cmd_learning_predict)

    suggest = learning_subparsers.add_parser("suggest", help="Suggest mappings for all profiled source columns")
    suggest.add_argument("--workdir", type=Path, required=True, help="Work directory containing profiles.json")
    suggest.add_argument("--model", type=Path, required=True, help="Model JSON path")
    suggest.add_argument("--out", type=Path, required=True, help="Output suggestions JSON path")
    suggest.add_argument("--top-k", type=int, default=3, help="Suggestions to keep per column and candidate entity")
    suggest.add_argument("--min-score", type=float, default=0.65, help="Minimum model score to keep")
    suggest.set_defaults(func=cmd_learning_suggest)

    return parser


def cmd_serve(args: argparse.Namespace) -> int:
    serve(args.host, args.port)
    return 0


def cmd_mapping_propose(args: argparse.Namespace) -> int:
    result = propose_mapping_workdir(
        args.exports,
        args.out,
        source_system=args.source_system,
        schema_version=args.schema,
        run_dry=not args.no_dry_run,
        registry_path=args.registry,
        learning_model_path=args.learning_model,
        learning_suggestions_top_k=args.learning_top_k,
        learning_suggestions_min_score=args.learning_min_score,
    )
    mapping = result["mapping"]
    dry = result["dry_run"]
    print(f"mapping_propose: {args.out / 'mapping_propose.yaml'}")
    print(f"review_queue:    {args.out / 'review_queue.yaml'}")
    print(f"profiles:        {args.out / 'profiles.json'}")
    print(f"source_graph:    {args.out / 'source_graph.json'}")
    print(f"entities:        {len(mapping['entities'])}")
    print(f"blocked_s4:      {len(mapping['blocked_fields'])}")
    print(f"join_rules:      {len(mapping.get('join_rules', []))}")
    print(f"registry:        {args.registry if args.registry else 'disabled'}")
    if result["learning_suggestions"]:
        print(f"suggestions:     {args.out / 'mapping_suggestions.json'}")
        print(f"suggested_items: {result['learning_suggestions']['suggestions_count']}")
    print(f"review_columns:  {len(mapping['review_queue'])}")
    if dry:
        print(f"draft_tables:    {args.out / 'mcdst_dry_run_draft'}")
        print(f"draft_quality:   {args.out / 'quality_report_draft.json'}")
    return 0


def cmd_mapping_review(args: argparse.Namespace) -> int:
    validated = apply_review_workdir(args.workdir, args.decisions, registry_path=args.registry)
    print(f"mapping_valide:  {args.workdir / 'mapping_valide.yaml'}")
    print(f"review_status:   {validated['review_status']}")
    print(f"review_columns:  {len(validated['review_queue'])}")
    if args.registry:
        print(f"registry:        {args.registry}")
    return 0


def cmd_mapping_apply(args: argparse.Namespace) -> int:
    state = apply_mapping_file(args.mapping, args.exports, args.out)
    generated = state["quality"]["summary"]["generated_tables"]
    print(f"output:          {args.out}")
    print(f"quality:         {args.out / 'quality_report.json'}")
    print("tables:")
    for table, count in generated.items():
        print(f"  {table}: {count}")
    return 0


def cmd_cohort_evaluate(args: argparse.Namespace) -> int:
    result = evaluate_cohort_definition(args.tables, args.definition, args.out, args.html_out)
    summary = result["summary"]
    print(f"cohort:          {result['cohort_name']}")
    print(f"status:          {summary['feasibility_status']}")
    print(f"source:          {summary['source_population_count']}")
    print(f"included:        {summary['included_count']}")
    print(f"excluded:        {summary['excluded_count']}")
    print(f"diagnostics:     {summary['diagnostics_count']}")
    if summary["missing_tables"]:
        print(f"missing_tables:  {', '.join(summary['missing_tables'])}")
    if args.out:
        print(f"report:          {args.out}")
    if args.html_out:
        print(f"report_html:     {args.html_out}")
    return 0


def cmd_learning_dataset(args: argparse.Namespace) -> int:
    summary = build_learning_dataset(args.workdir, args.out)
    print(f"dataset:         {summary['output_path']}")
    print(f"records:         {summary['records_count']}")
    print("tasks:")
    for task, count in summary["by_task"].items():
        print(f"  {task}: {count}")
    print("labels:")
    for label, count in summary["by_label"].items():
        print(f"  {label}: {count}")
    return 0


def cmd_learning_train(args: argparse.Namespace) -> int:
    summary = train_column_model(args.dataset, args.out)
    print(f"model:           {summary['model_path']}")
    print(f"kind:            {summary['model_kind']}")
    print(f"examples:        {summary['examples_count']}")
    print(f"labels:          {summary['labels_count']}")
    print(f"blocked_s4:      {summary['blocked_s4_examples']}")
    return 0


def cmd_learning_evaluate(args: argparse.Namespace) -> int:
    metrics = evaluate_column_model(args.dataset, args.model)
    print(f"examples:        {metrics['examples_count']}")
    print(f"top1_accuracy:   {metrics['top1_accuracy']}")
    print(f"top3_accuracy:   {metrics['top3_accuracy']}")
    print(f"blocked_s4_recall: {metrics['blocked_s4_recall']}")
    return 0


def cmd_learning_predict(args: argparse.Namespace) -> int:
    model = read_json(args.model)
    record = {
        "source_file": args.source_file,
        "source_column": args.source_column,
        "source_column_normalized": "",
        "source_type": args.source_type,
        "source_sensitivity": args.source_sensitivity,
        "source_examples": args.example,
        "entity": args.entity,
    }
    predictions = predict_column_mapping(model, record, top_k=args.top_k)
    print(json.dumps(predictions, ensure_ascii=False, indent=2))
    return 0


def cmd_learning_suggest(args: argparse.Namespace) -> int:
    summary = build_column_suggestions(
        args.workdir,
        args.model,
        args.out,
        top_k=args.top_k,
        min_score=args.min_score,
    )
    print(f"suggestions:     {summary['suggestions_path']}")
    print(f"kind:            {summary['model_kind']}")
    print(f"files:           {summary['files_count']}")
    print(f"columns:         {summary['columns_count']}")
    print(f"items:           {summary['suggestions_count']}")
    print(f"blocked_s4:      {summary['blocked_s4_columns']}")
    print(f"strong:          {summary['strong_candidates']}")
    print(f"review:          {summary['review_candidates']}")
    print(f"low_confidence:  {summary['low_confidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
