from __future__ import annotations

import json
from shutil import copyfile

from mcdst.cli import main
from mcdst.cohort import evaluate_cohort_definition
from mcdst.engine import apply_mapping_file, apply_review_workdir, propose_mapping_workdir
from mcdst.joins import build_join_context, source_key_value
from mcdst.learning import build_column_suggestions, build_learning_dataset
from mcdst.profiling import profile_exports
from mcdst.registry import load_registry
from mcdst.utils import read_source_rows, write_yaml
from tests.support import (
    ARRET_REPRISE_COHORT_FIXTURE,
    CANONICAL_EXPORT_FILES,
    COHORT_FIXTURE,
    FIXTURE_EXPORTS,
    FIXTURE_REVIEW_DECISIONS,
    LONGITUDINAL_COHORT_FIXTURE,
    S4_SOURCE_COLUMNS,
    SEMICOLON_CSV_FIXTURE,
    SYNTHETIC_DIRECT_IDENTIFIER_VALUES,
    api_get,
    api_get_error,
    api_get_text,
    api_post,
    approve_all_column_decisions,
    approve_all_review_decisions,
    approve_no_review_decisions,
    assert_mapping_contract,
    copy_fixture_exports,
    find_join_rule,
    rewrite_structures_as_cp1252,
    running_api,
    write_excel_fixture,
)


def test_mapping_poc_fixture_directory_contains_only_canonical_exports():
    assert tuple(sorted(path.name for path in FIXTURE_EXPORTS.glob("*.csv"))) == CANONICAL_EXPORT_FILES


def test_mapping_poc_fixture_readme_declares_synthetic_data():
    readme = (FIXTURE_EXPORTS / "README.md").read_text(encoding="utf-8").lower()
    assert "synthetic" in readme
    assert "stable acceptance fixture" in readme


def test_mapping_engine_roundtrip(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )

    mapping = proposed["mapping"]
    assert len(mapping["entities"]) == 13
    assert len(mapping["blocked_fields"]) == 6
    assert len(mapping["join_candidates"]) == 31
    assert len(mapping["join_rules"]) == 31
    assert len(mapping["review_queue"]) == 2
    assert proposed["dry_run"]["quality"]["summary"]["generated_tables"]["travailleur"] == 4

    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_column_decisions(proposed["review_queue"]))

    validated = apply_review_workdir(workdir, decisions_path)
    assert len(validated["review_queue"]) == 0

    state = apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)
    summary = state["quality"]["summary"]
    assert summary["generated_tables"] == {
        "travailleur": 4,
        "entreprise": 3,
        "etablissement": 3,
        "unite_travail": 4,
        "episode_poste": 4,
        "visite_sante_travail": 4,
        "conclusion_medicale": 4,
        "exposition_professionnelle": 4,
        "examen_complementaire": 4,
        "pathologie_atmp": 4,
        "arret_travail": 4,
        "vaccination": 4,
        "risque_unite_travail": 4,
    }
    assert summary["blocked_fields_count"] == 6
    assert summary["review_queue_count"] == 0
    assert summary["join_candidates_count"] == 31
    assert summary["join_rules_count"] == 31
    assert summary["join_resolution"]["usable_rules_count"] == 11
    assert summary["join_resolution"]["resolved_count"] == 40
    assert summary["join_resolution"]["missed_count"] == 0
    assert summary["value_mapping_groups_count"] == 11

    pending_values = [
        rule for rule in state["quality"]["rules"]
        if rule["rule"] == "review_queue:pending_value_mappings"
    ][0]
    assert pending_values["status"] == "failed"
    assert "4 nomenclature values" in pending_values["message"]
    join_resolution = [
        rule for rule in state["quality"]["rules"]
        if rule["rule"] == "source_graph:join_resolution"
    ][0]
    assert join_resolution["status"] == "passed"
    assert "key values resolved through explicit join rules" in join_resolution["message"]


def test_mapping_engine_excludes_direct_identifiers_from_standardized_tables(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    blocked_columns = {field["column"] for field in proposed["mapping"]["blocked_fields"]}
    assert S4_SOURCE_COLUMNS <= blocked_columns

    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)
    apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)

    standardized_content = "\n".join(
        path.read_text(encoding="utf-8")
        for path in output.glob("*.csv")
        if path.name != "quality_report.json"
    )
    for column in S4_SOURCE_COLUMNS:
        assert column not in standardized_content
    for value in SYNTHETIC_DIRECT_IDENTIFIER_VALUES:
        assert value not in standardized_content


def test_mapping_engine_applies_value_review_decisions(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )

    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))

    validated = apply_review_workdir(workdir, decisions_path)
    assert len(validated["review_queue"]) == 0
    assert not [
        item
        for group in validated["value_mappings"]
        for item in group["mappings"]
        if item["status"] == "a_revoir"
    ]
    assert not [rule for rule in validated["join_rules"] if rule["status"] == "a_revoir"]

    write_yaml(decisions_path, approve_no_review_decisions())
    validated_again = apply_review_workdir(workdir, decisions_path)
    assert not [
        item
        for group in validated_again["value_mappings"]
        for item in group["mappings"]
        if item["status"] == "a_revoir"
    ]
    assert not [rule for rule in validated_again["join_rules"] if rule["status"] == "a_revoir"]

    state = apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)
    pending_values = [
        rule for rule in state["quality"]["rules"]
        if rule["rule"] == "review_queue:pending_value_mappings"
    ][0]
    join_rules = [
        rule for rule in state["quality"]["rules"]
        if rule["rule"] == "source_graph:explicit_join_rules"
    ][0]
    assert pending_values["status"] == "passed"
    assert join_rules["status"] == "passed"
    assert join_rules["message"] == "31 explicit join rules generated."
    assert state["quality"]["summary"]["review_queue_count"] == 0


def test_cohort_engine_evaluates_yaml_definition(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"
    report_path = tmp_path / "cohort_report.json"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)
    apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)

    result = evaluate_cohort_definition(output, COHORT_FIXTURE, report_path)

    assert result["cohort_name"] == "travailleurs_45_plus_manutention_auvergne"
    assert result["summary"]["feasibility_status"] == "feasible"
    assert result["summary"]["source_population_count"] == 4
    assert result["summary"]["included_count"] == 1
    assert [step["output_count"] for step in result["steps"]] == [4, 3, 3, 1]
    assert report_path.exists()


def test_cohort_engine_evaluates_longitudinal_yaml_definition(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"
    report_path = tmp_path / "cohort_report_v02.json"
    html_path = tmp_path / "cohort_report_v02.html"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)
    apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)

    result = evaluate_cohort_definition(output, LONGITUDINAL_COHORT_FIXTURE, report_path, html_path)

    assert result["cohort_name"] == "manutention_avant_restriction_2024"
    assert result["schema_version"] == "mcdst-cohort-v0.2"
    assert result["summary"]["feasibility_status"] == "feasible"
    assert result["feasibility"]["status"] == "feasible"
    assert result["feasibility"]["diagnostics"] == []
    assert result["summary"]["included_count"] == 1
    assert result["summary"]["longitudinal_sequences_count"] == 1
    assert result["summary"]["diagnostics_count"] == 0
    assert result["summary"]["required_tables"] == [
        "conclusion_medicale",
        "exposition_professionnelle",
        "travailleur",
        "visite_sante_travail",
    ]
    assert {event["id"]: event["records_count"] for event in result["longitudinal"]["events"]} == {
        "exposition_manutention": 1,
        "restriction_medicale": 2,
    }
    assert [step["output_count"] for step in result["steps"]] == [4, 3, 1]
    assert result["steps"][-1]["id"] == "longitudinal:exposition_before_restriction"
    assert result["steps"][-1]["matched_pairs_count"] == 1
    assert report_path.exists()
    assert "Rapport cohorte - manutention_avant_restriction_2024" in html_path.read_text(encoding="utf-8")


def test_cohort_engine_evaluates_work_stop_before_return_visit(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)
    apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)

    result = evaluate_cohort_definition(output, ARRET_REPRISE_COHORT_FIXTURE)

    assert result["cohort_name"] == "arret_avant_visite_reprise_2024"
    assert result["summary"]["feasibility_status"] == "feasible"
    assert result["summary"]["included_count"] == 1
    assert result["summary"]["required_tables"] == [
        "arret_travail",
        "travailleur",
        "visite_sante_travail",
    ]
    assert {event["id"]: event["records_count"] for event in result["longitudinal"]["events"]} == {
        "arret_atmp_termine": 2,
        "visite_reprise": 1,
    }
    assert [step["output_count"] for step in result["steps"]] == [4, 3, 1]
    assert result["longitudinal"]["sequences"][0]["matched_pairs_count"] == 1


def test_learning_dataset_export_from_reviewed_mapping(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    dataset_path = tmp_path / "training" / "mapping_dataset.jsonl"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)

    summary = build_learning_dataset(workdir, dataset_path)
    records = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
    ]

    assert summary["records_count"] == 105
    assert summary["by_task"] == {"column_mapping": 69, "value_mapping": 36}
    assert summary["by_label"] == {"blocked_s4": 6, "positive": 99}
    assert any(record["label"] == "blocked_s4" and record["source_column"] == "NomUsuel" for record in records)
    assert any(
        record["task"] == "value_mapping"
        and record["source_value"] == "Charge mentale"
        and record["target_value"] == "CHARGE_MENTALE"
        for record in records
    )


def test_source_graph_contains_explicit_join_rules(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    mapping = proposed["mapping"]
    join_rules = mapping["join_rules"]

    assert (workdir / "source_graph.json").exists()
    assert (workdir / "join_rules.json").exists()
    assert "&id" not in (workdir / "mapping_propose.yaml").read_text(encoding="utf-8")
    assert "*id" not in (workdir / "mapping_propose.yaml").read_text(encoding="utf-8")
    assert len(proposed["source_graph"]["nodes"]) == 9
    assert len(join_rules) == 31
    assert len([rule for rule in join_rules if rule["status"] == "auto_validable"]) == 12
    assert len([rule for rule in join_rules if rule["status"] == "a_revoir"]) == 19

    worker_rule = find_join_rule(
        join_rules,
        primary_file="export_01_individus.csv",
        foreign_file="export_03_actes.csv",
        column="ClePers",
    )
    assert worker_rule["key_role"] == "travailleur_id"
    assert worker_rule["join_type"] == "primary_foreign_key"
    assert worker_rule["cardinality"] == "one_to_one"

    company_rule = find_join_rule(
        join_rules,
        primary_file="export_02_structures.csv",
        foreign_file="export_01_individus.csv",
        column="CleAdh",
    )
    assert company_rule["key_role"] == "entreprise_id"
    assert company_rule["cardinality"] == "one_to_many"

    peer_rule = [
        rule for rule in join_rules
        if rule["left"]["source_file"] == "export_03_actes.csv"
        and rule["right"]["source_file"] == "export_04_risques.csv"
    ][0]
    assert peer_rule["join_type"] == "peer_key_overlap"
    assert peer_rule["primary"] is None
    assert peer_rule["foreign"] is None


def test_join_context_resolves_reference_keys_from_validated_rules(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    validated = apply_review_workdir(workdir, decisions_path)

    context = build_join_context(validated, exports)
    duerp_row = read_source_rows(exports, "export_09_duerp.csv")[0]
    visit_row = read_source_rows(exports, "export_03_actes.csv")[0]

    assert source_key_value(context, "export_09_duerp.csv", duerp_row, "etablissement_id", "Site") == "E10"
    assert source_key_value(context, "export_03_actes.csv", visit_row, "travailleur_id", "ClePers") == "S001"
    assert context["usage"]["resolved"] == 2
    assert context["usage"]["missed"] == 0


def test_mapping_yaml_contract_for_draft_and_reviewed_artifacts(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    assert_mapping_contract(proposed["mapping"], expected_status="draft")

    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_column_decisions(proposed["review_queue"]))
    validated = apply_review_workdir(workdir, decisions_path)

    assert_mapping_contract(validated, expected_status="reviewed")
    assert validated["review_queue"] == []
    assert validated["mapping_version"] == "0.1.0-draft-reviewed"
    assert validated["reviewed_at"]
    assert validated["review_decisions"]["column_mapping_decisions"]
    assert (
        validated["entities"]["conclusion_medicale"]["fields"]["restriction_flag"]["review_status"]
        == "validated_by_human_review"
    )
    assert (
        validated["entities"]["conclusion_medicale"]["fields"]["amenagement_flag"]["review_status"]
        == "validated_by_human_review"
    )


def test_mapping_registry_learns_from_human_review(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    registry_path = tmp_path / "mapping_registry.yaml"
    first_workdir = tmp_path / "first_work"
    second_workdir = tmp_path / "second_work"

    proposed = propose_mapping_workdir(
        exports,
        first_workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
        registry_path=registry_path,
    )
    assert len(proposed["review_queue"]["pending_column_mappings"]) == 2

    decisions_path = first_workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_column_decisions(proposed["review_queue"]))
    validated = apply_review_workdir(first_workdir, decisions_path, registry_path=registry_path)
    assert validated["learning_registry"]["column_mappings_count"] == 2

    registry = load_registry(registry_path)
    assert len(registry["column_mappings"]) == 2
    assert {
        (entry["source_column"], entry["entity"], entry["target_field"])
        for entry in registry["column_mappings"]
    } == {
        ("Adaptation", "conclusion_medicale", "amenagement_flag"),
        ("Reserve", "conclusion_medicale", "restriction_flag"),
    }

    learned = propose_mapping_workdir(
        exports,
        second_workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
        registry_path=registry_path,
    )
    assert learned["review_queue"]["pending_column_mappings"] == []
    assert len(learned["mapping"]["review_queue"]) == 0
    fields = learned["mapping"]["entities"]["conclusion_medicale"]["fields"]
    assert fields["restriction_flag"]["review_status"] == "validated_by_registry"
    assert fields["amenagement_flag"]["review_status"] == "validated_by_registry"
    assert fields["restriction_flag"]["confidence_score"] == 0.995
    assert fields["amenagement_flag"]["confidence_score"] == 0.995
    assert len(learned["review_queue"]["pending_value_mappings"]) == 4


def test_mapping_engine_reads_windows_encoded_csv(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    rewrite_structures_as_cp1252(exports / "export_02_structures.csv")
    workdir = tmp_path / "work"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_CP1252_EXPORT",
        schema_version="mcdst-v0.1",
    )

    structures = [
        profile for profile in proposed["profiles"]
        if profile["file"] == "export_02_structures.csv"
    ][0]
    region = [column for column in structures["columns"] if column["name"] == "Territoire"][0]

    assert structures["row_count"] == 3
    assert "Auvergne-Rhône-Alpes" in region["examples"]


def test_mapping_engine_detects_semicolon_csv_source(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    copyfile(
        SEMICOLON_CSV_FIXTURE,
        exports / "salaries_suivis_small.csv",
    )

    profiles = profile_exports(exports)
    assert len(profiles) == 1

    profile = profiles[0]
    column_names = [column["name"] for column in profile["columns"]]

    assert profile["row_count"] == 1
    assert len(column_names) > 20
    assert "Matricule personne" in column_names
    assert "Type suivi actuel" in column_names
    assert "Poste actuel" in column_names
    assert "travailleur" in profile["inferred_entities"]


def test_mapping_engine_reads_excel_workbook_sources(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    write_excel_fixture(exports / "logiciel_spsti.xlsx")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_EXCEL_EXPORT",
        schema_version="mcdst-v0.1",
    )
    mapping = proposed["mapping"]

    assert len(mapping["entities"]) == 13
    assert len(mapping["blocked_fields"]) == 6
    assert len(mapping["join_candidates"]) == 31
    assert len(mapping["join_rules"]) == 31
    assert all(source["format"] == "excel" for source in mapping["source_files"])
    assert {source["sheet"] for source in mapping["source_files"]} == {
        "export_01_individus",
        "export_02_structures",
        "export_03_actes",
        "export_04_risques",
        "export_05_biometrie",
        "export_06_pathologies_atmp",
        "export_07_arrets",
        "export_08_vaccinations",
        "export_09_duerp",
    }

    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_column_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)

    state = apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)
    assert state["quality"]["summary"]["generated_tables"]["travailleur"] == 4
    assert state["quality"]["summary"]["generated_tables"]["exposition_professionnelle"] == 4
    assert state["quality"]["summary"]["generated_tables"]["examen_complementaire"] == 4
    assert state["quality"]["summary"]["generated_tables"]["risque_unite_travail"] == 4


def test_mapping_cli_roundtrip(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"

    assert main(
        [
            "mapping",
            "propose",
            str(exports),
            "--out",
            str(workdir),
            "--source-system",
            "POC_SPSTI_MULTI_EXPORT",
        ]
    ) == 0

    decisions_path = workdir / "review_decisions.yaml"
    copyfile(FIXTURE_REVIEW_DECISIONS, decisions_path)

    assert main(["mapping", "review", str(decisions_path), "--workdir", str(workdir)]) == 0
    assert main(
        [
            "mapping",
            "apply",
            str(workdir / "mapping_valide.yaml"),
            "--exports",
            str(exports),
            "--out",
            str(output),
        ]
    ) == 0

    assert (workdir / "mapping_propose.yaml").exists()
    assert (workdir / "mapping_valide.yaml").exists()
    assert (output / "travailleur.csv").exists()
    assert (output / "quality_report.json").exists()


def test_cohort_cli_evaluate(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"
    report_path = tmp_path / "cohort_report.json"
    html_path = tmp_path / "cohort_report.html"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)
    apply_mapping_file(workdir / "mapping_valide.yaml", exports, output)

    assert main(
        [
            "cohort",
            "evaluate",
            str(COHORT_FIXTURE),
            "--tables",
            str(output),
            "--out",
            str(report_path),
            "--html-out",
            str(html_path),
        ]
    ) == 0
    assert report_path.exists()
    assert html_path.exists()


def test_learning_cli_dataset(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    dataset_path = tmp_path / "training" / "mapping_dataset.jsonl"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)

    assert main(["learning", "dataset", "--workdir", str(workdir), "--out", str(dataset_path)]) == 0
    assert dataset_path.exists()


def test_learning_cli_train_evaluate_and_predict(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    dataset_path = tmp_path / "training" / "mapping_dataset.jsonl"
    model_path = tmp_path / "training" / "column_model.json"
    suggestions_path = tmp_path / "training" / "mapping_suggestions.json"

    proposed = propose_mapping_workdir(
        exports,
        workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
    )
    decisions_path = workdir / "review_decisions.yaml"
    write_yaml(decisions_path, approve_all_review_decisions(proposed["review_queue"]))
    apply_review_workdir(workdir, decisions_path)
    build_learning_dataset(workdir, dataset_path)

    assert main(["learning", "train", "--dataset", str(dataset_path), "--out", str(model_path)]) == 0
    assert model_path.exists()

    model = json.loads(model_path.read_text(encoding="utf-8"))
    assert model["model_kind"] == "mcdst-column-centroid-v0.1"
    assert model["examples_count"] == 69
    assert model["label_counts"]["__BLOCKED_S4__"] == 6

    assert main(["learning", "evaluate", "--dataset", str(dataset_path), "--model", str(model_path)]) == 0
    suggested_workdir = tmp_path / "suggested_work"
    suggested = propose_mapping_workdir(
        exports,
        suggested_workdir,
        source_system="POC_SPSTI_MULTI_EXPORT",
        schema_version="mcdst-v0.1",
        learning_model_path=model_path,
    )
    assert suggested["learning_suggestions"]["suggestions_count"] >= 69
    assert (suggested_workdir / "mapping_suggestions.json").exists()

    suggestions = build_column_suggestions(workdir, model_path, suggestions_path, top_k=2)
    assert suggestions["blocked_s4_columns"] == 6
    assert suggestions["suggestions_count"] >= 69

    suggestion_payload = json.loads(suggestions_path.read_text(encoding="utf-8"))
    assert any(
        item["source_column"] == "TypeExamen"
        and item["target"] == "examen_complementaire.examen_type_concept_id"
        for item in suggestion_payload["suggestions"]
    )

    assert main(
        [
            "learning",
            "suggest",
            "--workdir",
            str(workdir),
            "--model",
            str(model_path),
            "--out",
            str(suggestions_path),
            "--top-k",
            "2",
        ]
    ) == 0
    assert main(
        [
            "learning",
            "predict",
            "--model",
            str(model_path),
            "--source-file",
            "export_05_biometrie.csv",
            "--source-column",
            "TypeExamen",
            "--source-type",
            "categorical",
            "--source-sensitivity",
            "S3",
            "--entity",
            "examen_complementaire",
            "--example",
            "IMC",
            "--top-k",
            "3",
        ]
    ) == 0


def test_mapping_api_roundtrip(tmp_path):
    exports = copy_fixture_exports(tmp_path / "exports")
    workdir = tmp_path / "work"
    output = tmp_path / "mcdst_tables"

    with running_api() as base_url:
        health = api_get(f"{base_url}/health")
        assert health["status"] == "ok"
        index_html = api_get_text(f"{base_url}/")
        app_js = api_get_text(f"{base_url}/web/app.js")
        assert "MCD-ST" in index_html
        assert "view-cohort" in index_html
        assert "view-joins" in index_html
        assert "cohort-picker" in index_html
        assert "cohort-yaml-editor" in index_html
        assert "quality-json-link" in index_html
        assert "join-json-link" in index_html
        assert "runPropose" in app_js
        assert "runCohort" in app_js
        assert "loadCohortCatalog" in app_js
        assert "saveCohortCopy" in app_js
        assert "failedRules" in app_js
        assert "renderJoins" in app_js
        assert "data-join-review-id" in app_js
        assert "join_rule_decisions" in app_js
        registry_path = tmp_path / "api_registry.yaml"
        cohort_catalog = api_get(f"{base_url}/api/cohorts")
        assert {cohort["name"] for cohort in cohort_catalog["cohorts"]} >= {
            "manutention_avant_restriction_2024",
            "arret_avant_visite_reprise_2024",
        }
        assert any(cohort["schema_version"] == "mcdst-cohort-v0.2" for cohort in cohort_catalog["cohorts"])

        proposed = api_post(
            f"{base_url}/api/mapping/propose",
            {
                "exports": str(exports),
                "workdir": str(workdir),
                "source_system": "POC_SPSTI_MULTI_EXPORT",
                "schema_version": "mcdst-v0.1",
                "registry_path": str(registry_path),
            },
        )
        assert proposed["status"] == "proposed"
        assert proposed["summary"]["entities"] == 13
        assert proposed["summary"]["join_rules"] == 31
        assert proposed["summary"]["review_joins"] == 19
        assert proposed["summary"]["review_columns"] == 2
        assert proposed["summary"]["review_values"] == 4
        assert proposed["summary"]["registry_column_mappings"] == 0
        assert proposed["summary"]["learning_suggestions"] == 0
        assert (workdir / "mapping_propose.yaml").exists()
        join_rules_raw = api_get_text(f"{base_url}/api/artifact/raw?path={workdir / 'join_rules.json'}")
        assert "primary_foreign_key" in join_rules_raw
        assert "a_revoir" in join_rules_raw

        artifact = api_get(f"{base_url}/api/artifact?path={workdir / 'mapping_propose.yaml'}")
        assert "mapping_id:" in artifact["content"]
        saved = api_post(
            f"{base_url}/api/artifact",
            {
                "path": str(workdir / "ui_note.yaml"),
                "content": "status: checked\n",
            },
        )
        assert saved["status"] == "saved"
        assert (workdir / "ui_note.yaml").read_text(encoding="utf-8") == "status: checked\n"

        review_queue = api_get(f"{base_url}/api/mapping/review-queue?workdir={workdir}")
        reviewed = api_post(
            f"{base_url}/api/mapping/review",
            {
                "workdir": str(workdir),
                "registry_path": str(registry_path),
                "decisions": approve_all_review_decisions(review_queue),
            },
        )
        assert reviewed["status"] == "reviewed"
        assert reviewed["summary"]["review_columns"] == 0
        assert reviewed["summary"]["review_values"] == 0
        assert reviewed["summary"]["review_joins"] == 0
        assert reviewed["summary"]["registry_column_mappings"] == 2
        assert (workdir / "mapping_valide.yaml").exists()
        assert registry_path.exists()
        reviewed_join_rules = json.loads(
            api_get_text(f"{base_url}/api/artifact/raw?path={workdir / 'join_rules.json'}")
        )
        assert len([rule for rule in reviewed_join_rules if rule["status"] == "a_revoir"]) == 0
        assert len([rule for rule in reviewed_join_rules if rule["status"] == "validated_by_human_review"]) == 19

        learned_workdir = tmp_path / "learned_work"
        learned = api_post(
            f"{base_url}/api/mapping/propose",
            {
                "exports": str(exports),
                "workdir": str(learned_workdir),
                "source_system": "POC_SPSTI_MULTI_EXPORT",
                "schema_version": "mcdst-v0.1",
                "registry_path": str(registry_path),
            },
        )
        assert learned["summary"]["review_columns"] == 0
        assert learned["summary"]["registry_column_mappings"] == 2

        applied = api_post(
            f"{base_url}/api/mapping/apply",
            {
                "mapping": str(workdir / "mapping_valide.yaml"),
                "exports": str(exports),
                "out": str(output),
            },
        )
        assert applied["status"] == "applied"
        assert applied["summary"]["generated_tables"]["travailleur"] == 4
        assert applied["summary"]["generated_tables"]["examen_complementaire"] == 4
        assert (output / "quality_report.json").exists()
        assert "required_mapping:travailleur" in api_get_text(
            f"{base_url}/api/artifact/raw?path={output / 'quality_report.json'}"
        )

        cohort_report = tmp_path / "cohort_report.json"
        cohort_report_html = tmp_path / "cohort_report.html"
        cohort = api_post(
            f"{base_url}/api/cohort/evaluate",
            {
                "tables": str(output),
                "definition": str(COHORT_FIXTURE),
                "out": str(cohort_report),
                "html_out": str(cohort_report_html),
            },
        )
        assert cohort["status"] == "evaluated"
        assert cohort["summary"]["included_count"] == 1
        assert cohort["summary"]["diagnostics_count"] == 0
        assert cohort["feasibility"]["status"] == "feasible"
        assert cohort["steps"][-1]["id"] == "criteria:exposure"
        assert cohort_report.exists()
        assert cohort_report_html.exists()
        assert cohort["artifacts"]["report_html"] == str(cohort_report_html)
        assert "Rapport cohorte" in api_get_text(f"{base_url}/api/artifact/raw?path={cohort_report_html}")

        missing = api_get_error(f"{base_url}/api/mapping/review-queue")
        assert missing["status"] == "error"
        assert "workdir" in missing["message"]
