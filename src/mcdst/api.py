from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from mcdst import __version__
from mcdst.cohort import evaluate_cohort_definition
from mcdst.engine import apply_mapping_file, apply_review_workdir, propose_mapping_workdir
from mcdst.registry import DEFAULT_REGISTRY_PATH
from mcdst.utils import read_yaml, write_yaml

WEB_DIR = Path(__file__).parent / "web"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), MCDSTRequestHandler)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = create_server(host, port)
    try:
        print(f"mcdst api listening on http://{host}:{server.server_port}")
        server.serve_forever()
    finally:
        server.server_close()


class MCDSTRequestHandler(BaseHTTPRequestHandler):
    server_version = "mcdst-api"

    def do_GET(self) -> None:
        route = urlparse(self.path)
        try:
            if route.path in {"/", "/web"}:
                self.send_static(WEB_DIR / "index.html")
                return
            if route.path.startswith("/web/"):
                self.send_static(WEB_DIR / route.path.removeprefix("/web/"))
                return
            if route.path == "/health":
                self.send_json({"status": "ok", "version": __version__})
                return
            if route.path == "/api/artifact":
                params = parse_qs(route.query)
                path = required_query_path(params, "path")
                self.send_json({"path": str(path), "content": path.read_text(encoding="utf-8")})
                return
            if route.path == "/api/mapping/review-queue":
                params = parse_qs(route.query)
                workdir = required_query_path(params, "workdir")
                self.send_json(read_yaml(workdir / "review_queue.yaml"))
                return
            self.send_error_json(HTTPStatus.NOT_FOUND, f"Unknown endpoint: {route.path}")
        except Exception as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self) -> None:
        route = urlparse(self.path)
        try:
            payload = self.read_json()
            if route.path == "/api/artifact":
                self.handle_artifact_save(payload)
                return
            if route.path == "/api/mapping/propose":
                self.handle_mapping_propose(payload)
                return
            if route.path == "/api/mapping/review":
                self.handle_mapping_review(payload)
                return
            if route.path == "/api/mapping/apply":
                self.handle_mapping_apply(payload)
                return
            if route.path == "/api/cohort/evaluate":
                self.handle_cohort_evaluate(payload)
                return
            self.send_error_json(HTTPStatus.NOT_FOUND, f"Unknown endpoint: {route.path}")
        except Exception as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def handle_mapping_propose(self, payload: dict[str, Any]) -> None:
        exports = required_path(payload, "exports")
        workdir = required_path(payload, "workdir")
        registry_path = optional_path(payload, "registry_path", DEFAULT_REGISTRY_PATH)
        learning_model_path = optional_path(payload, "learning_model_path")
        result = propose_mapping_workdir(
            exports,
            workdir,
            source_system=str(payload.get("source_system", "UNKNOWN_SOURCE")),
            schema_version=str(payload.get("schema_version", "mcdst-v0.1")),
            run_dry=bool(payload.get("run_dry", True)),
            registry_path=registry_path,
            learning_model_path=learning_model_path,
            learning_suggestions_top_k=int(payload.get("learning_suggestions_top_k", 3)),
            learning_suggestions_min_score=float(payload.get("learning_suggestions_min_score", 0.65)),
        )
        mapping = result["mapping"]
        dry_run = result["dry_run"]
        suggestions = result["learning_suggestions"] or {}
        self.send_json(
            {
                "status": "proposed",
                "summary": {
                    "entities": len(mapping["entities"]),
                    "blocked_s4": len(mapping["blocked_fields"]),
                    "join_candidates": len(mapping["join_candidates"]),
                    "join_rules": len(mapping.get("join_rules", [])),
                    "review_columns": len(mapping["review_queue"]),
                    "review_values": count_pending_value_mappings(result["review_queue"]["pending_value_mappings"]),
                    "registry_column_mappings": len(result["registry"].get("column_mappings", [])),
                    "learning_suggestions": suggestions.get("suggestions_count", 0),
                    "learning_blocked_s4": suggestions.get("blocked_s4_columns", 0),
                    "learning_strong_candidates": suggestions.get("strong_candidates", 0),
                    "draft_tables": dry_run["quality"]["summary"]["generated_tables"] if dry_run else {},
                },
                "artifacts": mapping_artifacts(workdir, registry_path),
            }
        )

    def handle_mapping_review(self, payload: dict[str, Any]) -> None:
        workdir = required_path(payload, "workdir")
        registry_path = optional_path(payload, "registry_path", DEFAULT_REGISTRY_PATH)
        if "decisions" in payload:
            decisions_path = workdir / "review_decisions.yaml"
            write_yaml(decisions_path, payload["decisions"])
        else:
            decisions_path = required_path(payload, "decisions_path")
        validated = apply_review_workdir(workdir, decisions_path, registry_path=registry_path)
        self.send_json(
            {
                "status": "reviewed",
                "summary": {
                    "review_status": validated["review_status"],
                    "review_columns": len(validated["review_queue"]),
                    "review_values": count_pending_value_mappings(validated["value_mappings"]),
                    "value_mapping_groups": len(validated["value_mappings"]),
                    "registry_column_mappings": validated.get("learning_registry", {}).get("column_mappings_count", 0),
                },
                "artifacts": {
                    "mapping_valide": str(workdir / "mapping_valide.yaml"),
                    "review_decisions": str(decisions_path),
                    "registry": str(registry_path),
                },
            }
        )

    def handle_mapping_apply(self, payload: dict[str, Any]) -> None:
        mapping_path = required_path(payload, "mapping")
        exports = required_path(payload, "exports")
        output = required_path(payload, "out")
        state = apply_mapping_file(mapping_path, exports, output)
        self.send_json(
            {
                "status": "applied",
                "summary": state["quality"]["summary"],
                "artifacts": {
                    "output": str(output),
                    "quality": str(output / "quality_report.json"),
                },
            }
        )

    def handle_cohort_evaluate(self, payload: dict[str, Any]) -> None:
        tables = required_path(payload, "tables")
        definition = required_path(payload, "definition")
        output = optional_path(payload, "out")
        result = evaluate_cohort_definition(tables, definition, output)
        self.send_json(
            {
                "status": "evaluated",
                "summary": result["summary"],
                "steps": result["steps"],
                "artifacts": {
                    "definition": str(definition),
                    "report": str(output) if output else None,
                },
            }
        )

    def handle_artifact_save(self, payload: dict[str, Any]) -> None:
        path = required_path(payload, "path")
        content = str(payload.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.send_json({"status": "saved", "path": str(path)})

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_static(self, path: Path) -> None:
        resolved = path.resolve()
        web_root = WEB_DIR.resolve()
        if not resolved.is_file() or web_root not in [resolved, *resolved.parents]:
            self.send_error_json(HTTPStatus.NOT_FOUND, "Static asset not found.")
            return
        body = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", CONTENT_TYPES.get(resolved.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: HTTPStatus, message: str) -> None:
        self.send_json({"status": "error", "message": message}, status=status)

    def log_message(self, format: str, *args: object) -> None:
        return


def mapping_artifacts(workdir: Path, registry_path: Path | None = None) -> dict[str, str]:
    return {
        "workdir": str(workdir),
        "profiles": str(workdir / "profiles.json"),
        "source_graph": str(workdir / "source_graph.json"),
        "join_candidates": str(workdir / "join_candidates.json"),
        "join_rules": str(workdir / "join_rules.json"),
        "mapping_propose": str(workdir / "mapping_propose.yaml"),
        "review_queue": str(workdir / "review_queue.yaml"),
        "mapping_suggestions": str(workdir / "mapping_suggestions.json"),
        "draft_tables": str(workdir / "mcdst_dry_run_draft"),
        "draft_quality": str(workdir / "quality_report_draft.json"),
        "registry": str(registry_path or DEFAULT_REGISTRY_PATH),
    }


def count_pending_value_mappings(groups: list[dict]) -> int:
    return sum(
        1
        for group in groups
        for item in group.get("mappings", [])
        if item.get("status") == "a_revoir"
    )


def required_path(payload: dict[str, Any], key: str) -> Path:
    value = payload.get(key)
    if not value:
        raise ValueError(f"Missing required field: {key}")
    return Path(str(value))


def optional_path(payload: dict[str, Any], key: str, default: Path | None = None) -> Path | None:
    value = payload.get(key)
    if value is None or value == "":
        return default
    return Path(str(value))


def required_query_path(params: dict[str, list[str]], key: str) -> Path:
    value = params.get(key, [""])[0]
    if not value:
        raise ValueError(f"Missing required query parameter: {key}")
    return Path(value)
