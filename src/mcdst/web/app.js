const state = {
  artifacts: {},
  reviewQueue: null,
  proposed: null,
  applied: null,
  cohort: null,
  joinRules: [],
};

const els = {
  health: document.querySelector("#health"),
  exportsPath: document.querySelector("#exports-path"),
  workdirPath: document.querySelector("#workdir-path"),
  outputPath: document.querySelector("#output-path"),
  sourceSystem: document.querySelector("#source-system"),
  registryPath: document.querySelector("#registry-path"),
  learningModelPath: document.querySelector("#learning-model-path"),
  cohortPicker: document.querySelector("#cohort-picker"),
  cohortDefinitionPath: document.querySelector("#cohort-definition-path"),
  cohortReportPath: document.querySelector("#cohort-report-path"),
  cohortHtmlPath: document.querySelector("#cohort-html-path"),
  cohortFrame: document.querySelector("#cohort-report-frame"),
  cohortYamlEditor: document.querySelector("#cohort-yaml-editor"),
  cohortYamlPath: document.querySelector("#cohort-yaml-path"),
  eventLog: document.querySelector("#event-log"),
  yamlEditor: document.querySelector("#yaml-editor"),
  yamlPath: document.querySelector("#yaml-path"),
};

document.querySelector("#run-propose").addEventListener("click", runPropose);
document.querySelector("#run-review").addEventListener("click", runReview);
document.querySelector("#run-apply").addEventListener("click", runApply);
document.querySelector("#run-cohort").addEventListener("click", runCohort);
document.querySelector("#load-yaml").addEventListener("click", loadYaml);
document.querySelector("#save-yaml").addEventListener("click", saveYaml);
document.querySelector("#load-cohort-yaml").addEventListener("click", loadCohortYaml);
document.querySelector("#save-cohort-copy").addEventListener("click", saveCohortCopy);
els.cohortPicker.addEventListener("change", () => selectCohortDefinition().catch((error) => log(error.message || String(error), "error")));
els.cohortYamlEditor.addEventListener("input", () => {
  state.cohortYamlDirty = true;
});

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => selectTab(button.dataset.tab));
});

boot();

async function boot() {
  try {
    const health = await getJson("/health");
    els.health.textContent = `API locale ${health.version}`;
    await loadCohortCatalog();
    log("API prete");
  } catch (error) {
    els.health.textContent = "API indisponible";
    els.health.className = "status-error";
  }
}

async function loadCohortCatalog() {
  const payload = await getJson("/api/cohorts");
  const cohorts = payload.cohorts || [];
  els.cohortPicker.innerHTML = cohorts.map((cohort) => `
    <option value="${escapeHtml(cohort.path)}">${escapeHtml(cohort.name)} (${escapeHtml(cohort.schema_version)})</option>
  `).join("");
  if (cohorts.length) {
    const selected = cohorts.find((cohort) => cohort.path === els.cohortDefinitionPath.value) || cohorts[0];
    els.cohortPicker.value = selected.path;
    setCohortDefinition(selected.path);
    await loadCohortYaml();
  }
}

async function selectCohortDefinition() {
  setCohortDefinition(els.cohortPicker.value);
  await loadCohortYaml();
}

function setCohortDefinition(path) {
  els.cohortDefinitionPath.value = path;
  const stem = path.split("/").pop().replace(/\.ya?ml$/i, "");
  els.cohortReportPath.value = `${els.workdirPath.value}/cohort_${stem}.json`;
  els.cohortHtmlPath.value = `${els.workdirPath.value}/cohort_${stem}.html`;
}

async function runPropose() {
  withBusy("#run-propose", async () => {
    log("Profilage et mapping");
    const payload = {
      exports: els.exportsPath.value,
      workdir: els.workdirPath.value,
      source_system: els.sourceSystem.value,
      schema_version: "mcdst-v0.1",
      registry_path: els.registryPath.value,
      learning_model_path: els.learningModelPath.value,
    };
    state.proposed = await postJson("/api/mapping/propose", payload);
    state.artifacts = state.proposed.artifacts;
    state.reviewQueue = await getJson(`/api/mapping/review-queue?workdir=${encodeURIComponent(els.workdirPath.value)}`);
    updateFromPropose();
    await loadArtifact(state.artifacts.mapping_propose);
    selectTab("review");
    log("Mapping propose");
  });
}

async function runReview() {
  withBusy("#run-review", async () => {
    if (!state.reviewQueue) {
      state.reviewQueue = await getJson(`/api/mapping/review-queue?workdir=${encodeURIComponent(els.workdirPath.value)}`);
    }
    const decisions = buildReviewDecisions();
    const reviewed = await postJson("/api/mapping/review", {
      workdir: els.workdirPath.value,
      registry_path: els.registryPath.value,
      decisions,
    });
    state.artifacts.mapping_valide = reviewed.artifacts.mapping_valide;
    state.artifacts.registry = reviewed.artifacts.registry;
    await loadArtifact(reviewed.artifacts.mapping_valide);
    await renderJoins();
    updateCounts({
      reviewColumns: reviewed.summary.review_columns,
      reviewValues: reviewed.summary.review_values,
      reviewJoins: reviewed.summary.review_joins,
    });
    selectTab("mapping");
    log(`Mapping valide, jointures a revoir ${reviewed.summary.review_joins}`);
  });
}

async function runApply() {
  withBusy("#run-apply", async () => {
    const mapping = state.artifacts.mapping_valide || `${els.workdirPath.value}/mapping_valide.yaml`;
    state.applied = await postJson("/api/mapping/apply", {
      mapping,
      exports: els.exportsPath.value,
      out: els.outputPath.value,
    });
    await renderQuality(state.applied);
    selectTab("quality");
    log("Tables generees");
  });
}

async function runCohort() {
  withBusy("#run-cohort", async () => {
    if (state.cohortYamlDirty) {
      await saveCohortCopy();
    }
    state.cohort = await postJson("/api/cohort/evaluate", {
      tables: els.outputPath.value,
      definition: els.cohortDefinitionPath.value,
      out: els.cohortReportPath.value,
      html_out: els.cohortHtmlPath.value,
    });
    await renderCohort();
    selectTab("cohort");
    log(`Cohorte ${state.cohort.summary.feasibility_status}`);
  });
}

async function loadCohortYaml() {
  const path = els.cohortDefinitionPath.value;
  const artifact = await getJson(`/api/artifact?path=${encodeURIComponent(path)}`);
  els.cohortYamlPath.textContent = artifact.path;
  els.cohortYamlEditor.value = artifact.content;
  state.cohortYamlDirty = false;
}

async function saveCohortCopy() {
  const current = els.cohortDefinitionPath.value.split("/").pop().replace(/\.ya?ml$/i, "");
  const original = current.endsWith("_edited") ? current.slice(0, -7) : current;
  const path = `${els.workdirPath.value}/${original}_edited.yaml`;
  await postJson("/api/artifact", { path, content: els.cohortYamlEditor.value });
  els.cohortDefinitionPath.value = path;
  els.cohortYamlPath.textContent = path;
  const stem = path.split("/").pop().replace(/\.ya?ml$/i, "");
  els.cohortReportPath.value = `${els.workdirPath.value}/cohort_${stem}.json`;
  els.cohortHtmlPath.value = `${els.workdirPath.value}/cohort_${stem}.html`;
  state.cohortYamlDirty = false;
  log("Copie cohorte sauvee");
}

async function loadYaml() {
  const path = state.artifacts.mapping_valide || state.artifacts.mapping_propose || `${els.workdirPath.value}/mapping_propose.yaml`;
  await loadArtifact(path);
}

async function saveYaml() {
  const path = els.yamlPath.textContent;
  await postJson("/api/artifact", { path, content: els.yamlEditor.value });
  log("YAML sauve");
}

async function loadArtifact(path) {
  const artifact = await getJson(`/api/artifact?path=${encodeURIComponent(path)}`);
  els.yamlPath.textContent = artifact.path;
  els.yamlEditor.value = artifact.content;
}

function updateFromPropose() {
  const summary = state.proposed.summary;
  updateCounts({
    sources: Object.keys(summary.draft_tables || {}).length,
    profiles: summary.entities,
    entities: summary.entities,
    reviewColumns: summary.review_columns,
    reviewValues: summary.review_values,
    reviewJoins: summary.review_joins,
    s4: summary.blocked_s4,
    joins: summary.join_rules,
    suggestions: summary.learning_suggestions,
  });
  renderSources();
  renderProfiles();
  renderJoins();
  renderSuggestions();
  renderReview();
}

async function renderSources() {
  const profiles = await getJson(`/api/artifact?path=${encodeURIComponent(state.artifacts.profiles)}`);
  const data = JSON.parse(profiles.content);
  document.querySelector("#source-rows").innerHTML = data.map((source) => `
    <tr>
      <td>${escapeHtml(source.file)}</td>
      <td>${source.row_count}</td>
      <td>${escapeHtml(source.format || "csv")}</td>
      <td>${escapeHtml((source.inferred_entities || []).join(", "))}</td>
    </tr>
  `).join("");
  document.querySelector("#count-sources").textContent = data.length;
}

async function renderProfiles() {
  const profiles = await getJson(`/api/artifact?path=${encodeURIComponent(state.artifacts.profiles)}`);
  const data = JSON.parse(profiles.content);
  const rows = data.flatMap((source) => (source.columns || []).map((column) => `
    <tr>
      <td>${escapeHtml(source.file)}</td>
      <td>${escapeHtml(column.name)}</td>
      <td>${escapeHtml(column.inferred_type)}</td>
      <td>${escapeHtml(column.sensitivity)}</td>
      <td>${column.completeness}</td>
    </tr>
  `));
  document.querySelector("#profile-rows").innerHTML = rows.join("");
  document.querySelector("#count-profiles").textContent = rows.length;
}

function renderReview() {
  const columns = state.reviewQueue.pending_column_mappings || [];
  document.querySelector("#review-columns").innerHTML = columns.map((item) => `
    <label class="review-item">
      <input type="checkbox" checked data-review-id="${escapeHtml(item.id)}">
      <span>${escapeHtml(item.source_file)} / ${escapeHtml(item.source_column)} -> ${escapeHtml(item.entity)}.${escapeHtml(item.target_field)}</span>
      <strong>${item.confidence_score}</strong>
    </label>
  `).join("");

  const values = state.reviewQueue.pending_value_mappings || [];
  document.querySelector("#review-values").innerHTML = values.flatMap((group) => {
    return group.mappings.filter((item) => item.status === "a_revoir").map((item) => `
      <tr>
        <td>${escapeHtml(group.source_file)}</td>
        <td>${escapeHtml(group.source_column)}</td>
        <td>${escapeHtml(group.entity)}.${escapeHtml(group.target_field)}</td>
        <td>
          <label class="value-review">
            <input
              type="checkbox"
              checked
              data-value-review-id="${escapeHtml(item.id)}"
              data-value-group-id="${escapeHtml(group.id)}"
            >
            <span>${escapeHtml(item.source_value)} -> ${escapeHtml(item.target_value)}</span>
          </label>
        </td>
      </tr>
    `);
  }).join("");
}

async function renderJoins() {
  if (!state.artifacts.join_rules) {
    document.querySelector("#join-rows").innerHTML = "";
    return;
  }
  const artifact = await getJson(`/api/artifact?path=${encodeURIComponent(state.artifacts.join_rules)}`);
  const rules = JSON.parse(artifact.content);
  state.joinRules = rules;
  const reviewRules = rules.filter((rule) => rule.status === "a_revoir");
  const autoRules = rules.filter((rule) => rule.status === "auto_validable");
  const avgConfidence = rules.length
    ? rules.reduce((total, rule) => total + Number(rule.confidence_score || 0), 0) / rules.length
    : 0;
  const rawUrl = `/api/artifact/raw?path=${encodeURIComponent(state.artifacts.join_rules)}`;

  document.querySelector("#join-total").textContent = rules.length;
  document.querySelector("#join-review").textContent = reviewRules.length;
  document.querySelector("#join-auto").textContent = autoRules.length;
  document.querySelector("#join-confidence").textContent = avgConfidence.toFixed(2);
  document.querySelector("#join-json-link").href = rawUrl;
  document.querySelector("#count-joins").textContent = rules.length;
  markStep("joins", reviewRules.length ? "warn" : "done");

  document.querySelector("#join-rows").innerHTML = rules.map((rule) => {
    const primary = rule.primary || rule.left || {};
    const foreign = rule.foreign || rule.right || {};
    return `
      <tr>
        <td>${joinReviewCell(rule)}</td>
        <td>${escapeHtml(rule.key_role || rule.join_type)}</td>
        <td>${escapeHtml(formatJoinSide(primary))}</td>
        <td>${escapeHtml(formatJoinSide(foreign))}</td>
        <td>${escapeHtml(rule.cardinality)}</td>
        <td class="${rule.status === "a_revoir" ? "status-warn" : "status-ok"}">${escapeHtml(rule.status)}</td>
        <td>${Number(rule.confidence_score || 0).toFixed(2)}</td>
        <td>${escapeHtml(rule.rationale)}</td>
      </tr>
    `;
  }).join("");
}

function joinReviewCell(rule) {
  if (rule.status !== "a_revoir") return "";
  return `
    <label class="value-review">
      <input type="checkbox" checked data-join-review-id="${escapeHtml(rule.id)}">
      <span>Valider</span>
    </label>
  `;
}

async function renderSuggestions() {
  const count = state.proposed?.summary?.learning_suggestions || 0;
  if (!count) {
    document.querySelector("#suggestion-rows").innerHTML = "";
    return;
  }
  const artifact = await getJson(`/api/artifact?path=${encodeURIComponent(state.artifacts.mapping_suggestions)}`);
  const payload = JSON.parse(artifact.content);
  const rows = (payload.suggestions || []).map((item) => `
    <tr>
      <td>${escapeHtml(item.source_file)}</td>
      <td>${escapeHtml(item.source_column)}</td>
      <td>${escapeHtml(item.target || "S4 bloque")}</td>
      <td>${Number(item.score).toFixed(3)}</td>
      <td>${escapeHtml(item.status)}</td>
    </tr>
  `);
  document.querySelector("#suggestion-rows").innerHTML = rows.join("");
}

async function renderQuality(applied) {
  const artifact = await getJson(`/api/artifact?path=${encodeURIComponent(applied.artifacts.quality)}`);
  const report = JSON.parse(artifact.content);
  const summary = report.summary || {};
  const rules = report.rules || [];
  const generated = summary.generated_tables || {};
  const failedRules = rules.filter((rule) => rule.status !== "passed");
  const rawUrl = `/api/artifact/raw?path=${encodeURIComponent(applied.artifacts.quality)}`;

  document.querySelector("#quality-generated").textContent = Object.keys(generated).length;
  document.querySelector("#quality-rules").textContent = rules.length;
  document.querySelector("#quality-failed").textContent = failedRules.length;
  document.querySelector("#quality-s4").textContent = summary.blocked_fields_count || 0;
  document.querySelector("#quality-json-link").href = rawUrl;

  document.querySelector("#quality-rows").innerHTML = rules.length ? rules.map((rule) => `
    <tr>
      <td>${escapeHtml(rule.rule)}</td>
      <td class="${rule.status === "passed" ? "status-ok" : "status-warn"}">${escapeHtml(rule.status)}</td>
      <td>${escapeHtml(rule.severity)}</td>
      <td>${escapeHtml(rule.message)}</td>
    </tr>
  `).join("") : Object.entries(generated).map(([table, count]) => `
    <tr>
      <td>${escapeHtml(table)}</td>
      <td class="status-ok">generated</td>
      <td>info</td>
      <td>${count} lignes</td>
    </tr>
  `).join("");
  document.querySelector("#count-quality").textContent = failedRules.length;
  markStep("quality", failedRules.length ? "warn" : "done");
}

async function renderCohort() {
  const summary = state.cohort.summary;
  const diagnostics = state.cohort.feasibility?.diagnostics || [];
  const events = state.cohort.longitudinal?.events || [];
  const steps = state.cohort.steps || [];
  const rawUrl = `/api/artifact/raw?path=${encodeURIComponent(state.cohort.artifacts.report_html)}`;

  document.querySelector("#cohort-status").textContent = summary.feasibility_status;
  document.querySelector("#cohort-source").textContent = summary.source_population_count;
  document.querySelector("#cohort-included").textContent = summary.included_count;
  document.querySelector("#cohort-diagnostics").textContent = summary.diagnostics_count;
  document.querySelector("#metric-cohort").textContent = summary.included_count;
  document.querySelector("#count-cohort").textContent = summary.included_count;
  document.querySelector("#cohort-html-link").href = rawUrl;

  document.querySelector("#cohort-step-rows").innerHTML = steps.map((step) => `
    <tr>
      <td>${escapeHtml(step.id)}</td>
      <td>${escapeHtml(step.label)}</td>
      <td>${escapeHtml(step.input_count ?? "")}</td>
      <td>${escapeHtml(step.output_count)}</td>
      <td>${escapeHtml(step.excluded_count)}</td>
      <td>${escapeHtml(step.matched_pairs_count ?? "")}</td>
    </tr>
  `).join("");

  document.querySelector("#cohort-diagnostic-rows").innerHTML = diagnostics.length ? diagnostics.map((item) => `
    <tr>
      <td>${escapeHtml(item.code)}</td>
      <td class="${item.severity === "blocking" ? "status-error" : "status-warn"}">${escapeHtml(item.severity)}</td>
      <td>${escapeHtml(item.message)}</td>
    </tr>
  `).join("") : `<tr><td colspan="3">Aucun diagnostic</td></tr>`;

  document.querySelector("#cohort-event-rows").innerHTML = events.length ? events.map((event) => `
    <tr>
      <td>${escapeHtml(event.id)}</td>
      <td>${escapeHtml(event.table)}</td>
      <td>${escapeHtml(event.records_count)}</td>
      <td>${escapeHtml(event.workers_count)}</td>
    </tr>
  `).join("") : `<tr><td colspan="4">Aucun evenement longitudinal</td></tr>`;

  const artifact = await getJson(`/api/artifact?path=${encodeURIComponent(state.cohort.artifacts.report_html)}`);
  els.cohortFrame.srcdoc = artifact.content;
  markStep("cohort", summary.feasibility_status === "not_feasible" ? "warn" : "done");
}

function buildReviewDecisions() {
  const approved = new Set([...document.querySelectorAll("[data-review-id]:checked")].map((input) => input.dataset.reviewId));
  const approvedValues = new Set(
    [...document.querySelectorAll("[data-value-review-id]:checked")].map((input) => input.dataset.valueReviewId)
  );
  const approvedJoins = new Set(
    [...document.querySelectorAll("[data-join-review-id]:checked")].map((input) => input.dataset.joinReviewId)
  );
  return {
    column_mapping_decisions: (state.reviewQueue.pending_column_mappings || [])
      .filter((item) => approved.has(item.id))
      .map((item) => ({
        id: item.id,
        action: "approve",
        source_file: item.source_file,
        source_column: item.source_column,
        entity: item.entity,
        target_field: item.target_field,
        transform: item.transform,
        reviewer: "web-local",
        reason: "Validated from local review UI.",
      })),
    value_mapping_decisions: (state.reviewQueue.pending_value_mappings || [])
      .flatMap((group) => group.mappings
        .filter((item) => approvedValues.has(item.id))
        .map((item) => ({
          id: item.id,
          action: "approve",
          source_file: group.source_file,
          source_column: group.source_column,
          entity: group.entity,
          target_field: group.target_field,
          source_value: item.source_value,
          target_value: item.target_value,
          reviewer: "web-local",
          reason: "Validated from local review UI.",
        }))),
    join_rule_decisions: (state.joinRules || [])
      .filter((rule) => rule.status === "a_revoir")
      .filter((rule) => approvedJoins.has(rule.id))
      .map((rule) => ({
        id: rule.id,
        action: "approve",
        key_role: rule.key_role,
        join_type: rule.join_type,
        reviewer: "web-local",
        reason: "Validated from local join review UI.",
      })),
  };
}

function formatJoinSide(side) {
  if (!side.source_file && !side.column) return "";
  return `${side.source_file || ""}::${side.column || ""}`;
}

function updateCounts({ sources, profiles, entities, reviewColumns, reviewValues, reviewJoins, s4, joins, suggestions }) {
  if (sources !== undefined) document.querySelector("#count-sources").textContent = sources;
  if (profiles !== undefined) document.querySelector("#count-profiles").textContent = profiles;
  if (entities !== undefined) {
    document.querySelector("#count-entities").textContent = entities;
    document.querySelector("#metric-entities").textContent = entities;
  }
  if (suggestions !== undefined) {
    document.querySelector("#count-suggestions").textContent = suggestions;
    document.querySelector("#metric-suggestions").textContent = suggestions;
    markStep("suggestions", suggestions ? "done" : "warn");
  }
  if (reviewColumns !== undefined || reviewValues !== undefined || reviewJoins !== undefined) {
    const total = (reviewColumns || 0) + (reviewValues || 0) + (reviewJoins || 0);
    document.querySelector("#count-review").textContent = total;
    document.querySelector("#metric-review").textContent = total;
    markStep("review", total ? "warn" : "done");
  }
  if (s4 !== undefined) document.querySelector("#metric-s4").textContent = s4;
  if (joins !== undefined) {
    document.querySelector("#metric-joins").textContent = joins;
    document.querySelector("#count-joins").textContent = joins;
  }
  markStep("sources", "done");
  markStep("profile", "done");
  markStep("mapping", "done");
}

function markStep(tab, status) {
  const step = document.querySelector(`.step[data-tab="${tab}"]`);
  step.classList.remove("done", "warn");
  step.classList.add(status);
}

function selectTab(tab) {
  document.querySelectorAll(".tab, .step").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tab);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `view-${tab}`);
  });
}

async function withBusy(selector, task) {
  const button = document.querySelector(selector);
  button.disabled = true;
  try {
    await task();
  } catch (error) {
    log(error.message || String(error), "error");
  } finally {
    button.disabled = false;
  }
}

async function getJson(url) {
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || response.statusText);
  return payload;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || response.statusText);
  return data;
}

function log(message, kind = "info") {
  const item = document.createElement("li");
  item.textContent = `${new Date().toLocaleTimeString()} ${message}`;
  if (kind === "error") item.className = "status-error";
  els.eventLog.prepend(item);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
