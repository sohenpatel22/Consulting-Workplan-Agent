const API = "";

let currentSessionId = null;
let currentTab = "wbs";
let pollTimer = null;
let reviewPollTimer = null;
let lastSessionData = null;
let pendingConfirmationQuestions = [];

const REVISION_TABS = new Set(["wbs", "raid", "stakeholder", "status"]);
const feedbackDrafts = { wbs: "", raid: "", stakeholder: "", status: "" };
/** Artifacts submitted locally before the next poll confirms them. */
const pendingRevisionTabs = new Set();

const ARTIFACT_LABELS = {
  wbs: "WBS",
  raid: "RAID",
  stakeholder: "Stakeholder Map",
  status: "Status Report",
  quality_gates: "Quality Gates",
};

const $ = (id) => document.getElementById(id);

const panels = {
  create: $("createPanel"),
  progress: $("progressPanel"),
  confirm: $("confirmPanel"),
  results: $("resultsPanel"),
};

function showPanel(name) {
  Object.entries(panels).forEach(([key, el]) => {
    el.classList.toggle("hidden", key !== name);
  });
  $("appLayout")?.classList.toggle("layout-wide", name === "results");
}

function setError(el, message) {
  if (!message) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.classList.remove("hidden");
  el.textContent = message;
}

function parseApiError(body) {
  if (!body || !body.detail) return "Request failed";
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((d) => d.msg || String(d)).join("; ");
  }
  return String(body.detail);
}

let backendLlm = null;

function formatModelBadge({ model, provider, ready, configured_model }) {
  if (!ready || !model) {
    return {
      text: configured_model
        ? `No API keys (MODEL=${configured_model})`
        : "No API keys configured",
      title: "Set OPENAI_API_KEY or ANTHROPIC_API_KEY for live generation",
      warn: true,
    };
  }
  const vendor = provider === "anthropic" ? "Anthropic" : "OpenAI";
  const title =
    model !== configured_model
      ? `Configured MODEL=${configured_model}; using ${model} based on available API keys`
      : `Backend LLM (${vendor})`;
  return { text: `${vendor} · ${model}`, title, warn: false };
}

function refreshModelBadge() {
  const el = $("modelBadge");
  if (!el || !backendLlm) return;
  const { text, title, warn } = formatModelBadge(backendLlm);
  const mock = $("mockMode")?.checked;
  el.textContent = mock ? `Mock mode · ${text}` : text;
  el.title = mock
    ? "Mock mode is on — revisions are simulated; this is the configured backend model for live runs"
    : title;
  el.classList.toggle("warn", warn);
  el.classList.toggle("ok", !warn);
}

async function checkHealth() {
  const badge = $("healthBadge");
  const modelBadge = $("modelBadge");
  try {
    const res = await fetch(`${API}/api/health`);
    if (!res.ok) throw new Error("unhealthy");
    const data = await res.json();
    backendLlm = {
      model: data.model,
      provider: data.provider,
      ready: data.ready,
      configured_model: data.configured_model,
    };
    refreshModelBadge();
    badge.textContent = "API online";
    badge.classList.add("ok");
  } catch {
    if (modelBadge) {
      modelBadge.textContent = "Model unknown";
      modelBadge.classList.add("warn");
    }
    badge.textContent = "API offline";
    badge.classList.add("warn");
  }
}

function setUploadStatus(message, kind = "") {
  const el = $("uploadStatus");
  el.textContent = message || "";
  el.classList.remove("ok", "error");
  if (kind) el.classList.add(kind);
}

async function uploadBriefFile(file) {
  if (!file) return;
  setUploadStatus("Extracting text…");
  setError($("createError"), "");

  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch(`${API}/api/brief/upload`, {
      method: "POST",
      body: form,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(parseApiError(body));
    }
    $("briefText").value = body.text;
    setUploadStatus(`Loaded ${body.filename} (${body.char_count} chars)`, "ok");
  } catch (err) {
    setUploadStatus(err.message, "error");
  } finally {
    $("briefFileInput").value = "";
  }
}

const DOWNLOAD_ARTIFACTS = {
  wbs: "WBS",
  raid: "RAID",
  stakeholder: "Stakeholder Map",
  status: "Status Report",
  quality_gates: "Quality Gates Checklist",
  brief: null,
};

function updateDownloadBar() {
  const bar = $("downloadBar");
  const artifact = DOWNLOAD_ARTIFACTS[currentTab];
  const xlsxBtn = $("downloadXlsxBtn");
  if (
    !currentSessionId ||
    !artifact ||
    (lastSessionData && isArtifactGenerationRunning(lastSessionData))
  ) {
    bar.classList.add("hidden");
    return;
  }
  bar.classList.remove("hidden");
  $("downloadArtifactLabel").textContent = artifact;
  if (xlsxBtn) {
    xlsxBtn.classList.toggle("hidden", currentTab !== "raid");
  }
}

async function downloadArtifact(format) {
  const artifact = currentTab;
  if (
    artifact !== "wbs" &&
    artifact !== "raid" &&
    artifact !== "stakeholder" &&
    artifact !== "status" &&
    artifact !== "quality_gates"
  )
    return;
  if (!currentSessionId) return;

  const url = `${API}/api/sessions/${currentSessionId}/download/${artifact}/${format}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(parseApiError(body));
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : `${artifact}.${format}`;
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  } catch (err) {
    setError($("reviewError"), `Download failed: ${err.message}`);
  }
}

function isRevisionTab(tab = currentTab) {
  return REVISION_TABS.has(tab);
}

function saveFeedbackDraft() {
  if (isRevisionTab()) {
    feedbackDrafts[currentTab] = $("feedbackText").value;
  }
}

function loadFeedbackDraft() {
  if (isRevisionTab()) {
    $("feedbackText").value = feedbackDrafts[currentTab] || "";
  } else {
    $("feedbackText").value = "";
  }
}

function getRevisionsInProgress(data = lastSessionData) {
  const serverList = data?.revisions_in_progress ?? [];
  return [...new Set([...serverList, ...pendingRevisionTabs])];
}

function isTabRevising(tab = currentTab) {
  return getRevisionsInProgress().includes(tab);
}

function hasActiveRevisions(data = lastSessionData) {
  return getRevisionsInProgress(data).length > 0;
}

function syncPendingRevisions(data) {
  const server = new Set(data?.revisions_in_progress ?? []);
  if (!data?.review_in_progress && server.size === 0) {
    pendingRevisionTabs.clear();
    return;
  }
  for (const tab of pendingRevisionTabs) {
    if (server.has(tab)) continue;
    if (server.size > 0) {
      pendingRevisionTabs.delete(tab);
    }
  }
}

function formatStaleMessage(artifact, upstreamKeys, data) {
  const versions = data.artifact_versions || {};
  const basedOn = data.artifact_based_on?.[artifact] || {};
  const parts = upstreamKeys.map((dep) => {
    const label = ARTIFACT_LABELS[dep] || dep;
    return `${label} v${basedOn[dep] ?? "?"} (current v${versions[dep] ?? "?"})`;
  });
  const label = ARTIFACT_LABELS[artifact] || artifact;
  return `${label} may be outdated — upstream revised since last update (${parts.join(", ")}). Consider revising this document.`;
}

function updateTabIndicators(data) {
  const inProgress = getRevisionsInProgress(data);
  document.querySelectorAll(".tab[data-tab]").forEach((tab) => {
    const key = tab.dataset.tab;
    const stale = data.stale_artifacts?.[key];
    tab.classList.toggle("tab-stale", Boolean(stale?.length));
    tab.classList.toggle("tab-revising", inProgress.includes(key));
  });
}

function renderStaleNotice(data) {
  const el = $("staleNotice");
  if (!el) return;
  const tabStale = data.stale_artifacts?.[currentTab];
  if (!isRevisionTab() || !tabStale?.length) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.classList.remove("hidden");
  el.textContent = formatStaleMessage(currentTab, tabStale, data);
}

function renderQualityGatesStaleBanner(data) {
  const el = $("qualityGatesStaleBanner");
  if (!el) return;
  const staleKeys = data.stale_artifacts?.quality_gates || [];
  if (!data.quality_gates_stale && !staleKeys.length) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.classList.remove("hidden");
  if (staleKeys.length) {
    el.textContent = formatStaleMessage("quality_gates", staleKeys, data);
  } else {
    el.textContent =
      "Quality checks may be outdated — run a quality check after your revisions.";
  }
}

function updateFeedbackPane(data) {
  const showFeedback = isRevisionTab();
  $("artifactFeedbackColumn").classList.toggle("hidden", !showFeedback);
  $("resultsPanel").classList.toggle("artifact-review-mode", showFeedback);

  if (showFeedback) {
    const label = ARTIFACT_LABELS[currentTab] || currentTab;
    $("feedbackFieldLabel").textContent = `Feedback for ${label}`;
    const inProgress = getRevisionsInProgress(data);
    if (isTabRevising()) {
      $("revisionTargetHint").textContent = `${label} revision in progress…`;
    } else if (inProgress.length) {
      $("revisionTargetHint").textContent =
        `Submitting revises ${label} only. Other tabs can be revised in parallel.`;
    } else {
      $("revisionTargetHint").textContent = `Submitting revises the ${label} only.`;
    }
  }

  const approved = data?.status === "approved";
  const limitedOut = data && !data.unlimited_revisions && data.revisions_remaining === 0;
  const revisingThisTab = isTabRevising();
  const canSubmit = showFeedback && !revisingThisTab && !approved && !limitedOut;
  $("submitRevisionBtn").disabled = !canSubmit;
  $("clearFeedbackBtn").disabled = !showFeedback || revisingThisTab;
}

async function loadSampleBrief() {
  try {
    const res = await fetch(`${API}/assets/sample_brief.md`);
    if (!res.ok) throw new Error("Sample not found");
    $("briefText").value = await res.text();
  } catch {
    setError($("createError"), "Could not load sample brief.");
  }
}

function phaseLabel(phase, jobStatus, revisionsInProgress) {
  if (revisionsInProgress?.length) {
    const labels = {
      revising: "Applying revision…",
      approving: "Approving workplan…",
    };
    return labels[phase] || "Review in progress…";
  }
  const labels = {
    queued: "Queued…",
    parsing: "Parsing client brief…",
    awaiting_confirmation: "Awaiting your answers…",
    generating_wbs: "Generating WBS…",
    generating_raid: "Generating RAID log…",
    generating_stakeholder: "Generating Stakeholder Map…",
    generating_status: "Generating Status Report…",
    ready_for_review: "Ready for review",
    failed: "Generation failed",
  };
  if (jobStatus === "failed") return labels.failed;
  return labels[phase] || phase;
}

function progressPercent(phase, jobStatus) {
  if (jobStatus === "complete") return 100;
  if (jobStatus === "failed") return 100;
  const map = {
    queued: 10,
    parsing: 25,
    awaiting_confirmation: 40,
    generating_wbs: 55,
    generating_raid: 70,
    generating_stakeholder: 85,
    generating_status: 95,
    ready_for_review: 100,
  };
  return map[phase] ?? 20;
}

function hasViewableArtifacts(data) {
  return Boolean(
    data?.wbs_html ||
      data?.raid_html ||
      data?.stakeholder_html ||
      data?.status_html
  );
}

function isArtifactGenerationRunning(data) {
  return (
    data?.job_status === "running" &&
    !data?.awaiting_confirmation &&
    data?.phase !== "awaiting_confirmation" &&
    data?.phase !== "parsing" &&
    data?.phase !== "queued"
  );
}

function updateGenerationBanner(data) {
  const banner = $("generationBanner");
  if (!banner) return;
  const inProgress = isArtifactGenerationRunning(data);
  banner.classList.toggle("hidden", !inProgress);
  if (!inProgress) return;
  const label = phaseLabel(data.phase, data.job_status, data.revisions_in_progress);
  $("generationPhaseLabel").textContent = `${label} — completed reports are shown below as they finish.`;
  $("generationProgressBar").style.width = `${progressPercent(data.phase, data.job_status)}%`;
}

function updateProgressPanel(data) {
  $("phaseLabel").textContent = phaseLabel(
    data.phase,
    data.job_status,
    data.revisions_in_progress
  );
  $("progressBar").style.width = `${progressPercent(data.phase, data.job_status)}%`;
}

function handleGenerationPoll(data) {
  updateProgressPanel(data);

  if (data.awaiting_confirmation || data.phase === "awaiting_confirmation") {
    clearInterval(pollTimer);
    showConfirmationPanel(data);
    return true;
  }

  if (hasViewableArtifacts(data) && isArtifactGenerationRunning(data)) {
    showPanel("results");
    updateResults(data);
    updateGenerationBanner(data);
  }

  if (data.job_status === "complete" && !data.review_in_progress) {
    clearInterval(pollTimer);
    showPanel("results");
    updateResults(data);
    updateGenerationBanner(data);
    return true;
  }

  if (data.job_status === "failed") {
    clearInterval(pollTimer);
    if (hasViewableArtifacts(data)) {
      showPanel("results");
      updateResults(data);
      updateGenerationBanner(data);
      setError($("reviewError"), data.error || "Generation failed before completion.");
    } else {
      setError($("progressError"), data.error || "Unknown error");
    }
    return true;
  }

  return false;
}

async function pollSession(sessionId) {
  const res = await fetch(`${API}/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to load session");
  return res.json();
}

function renderSummary(summary) {
  const cards = [
    ["Objectives", summary.objectives_count],
    ["WBS items", summary.wbs_items],
    ["Risks", summary.raid_risks],
    ["Actions", summary.raid_actions ?? summary.raid_assumptions],
    ["Issues", summary.raid_issues],
    ["Decisions", summary.raid_decisions ?? summary.raid_dependencies],
    ["Stakeholders", summary.stakeholders_count || 0],
    ["Milestones", summary.status_milestones_count || 0],
  ];
  if (summary.quality_gates_total) {
    cards.push([`Quality Gates`, `${summary.quality_gates_passed}/${summary.quality_gates_total}`]);
  }
  $("summaryCards").innerHTML = cards
    .map(
      ([label, value]) =>
        `<div class="card"><div class="value">${value}</div><div class="label">${label}</div></div>`
    )
    .join("");
}

function renderTabContent(data) {
  const artifactView = $("artifactView");
  const briefView = $("briefTabContent");
  const qualityGatesView = $("qualityGatesTabContent");

  if (currentTab === "brief") {
    artifactView.classList.add("hidden");
    briefView.classList.remove("hidden");
    qualityGatesView.classList.add("hidden");
    briefView.textContent = JSON.stringify(data.parsed_brief, null, 2);
    updateFeedbackPane(data);
    return;
  }

  if (currentTab === "quality_gates") {
    artifactView.classList.add("hidden");
    briefView.classList.add("hidden");
    qualityGatesView.classList.remove("hidden");
    renderQualityGatesList(data.quality_gates);
    renderQualityGatesStaleBanner(data);
    updateFeedbackPane(data);
    return;
  }

  artifactView.classList.remove("hidden");
  briefView.classList.add("hidden");
  qualityGatesView.classList.add("hidden");

  const preview = $("artifactPreview");

  if (currentTab === "wbs") {
    preview.innerHTML = data.wbs_html || "<p class='empty-preview'>WBS not available yet.</p>";
  } else if (currentTab === "raid") {
    preview.innerHTML = data.raid_html || "<p class='empty-preview'>RAID not available yet.</p>";
  } else if (currentTab === "stakeholder") {
    preview.innerHTML =
      data.stakeholder_html || "<p class='empty-preview'>Stakeholder Map not available yet.</p>";
  } else if (currentTab === "status") {
    preview.innerHTML =
      data.status_html || "<p class='empty-preview'>Status Report not available yet.</p>";
  }

  renderStaleNotice(data);
  updateFeedbackPane(data);
}

function renderQualityGatesList(qualityGates) {
  const container = $("qualityGatesList");
  if (!qualityGates || !qualityGates.items || !qualityGates.items.length) {
    container.innerHTML = "<p class='empty-preview'>No Quality Gates checklists generated yet.</p>";
    return;
  }
  
  const groups = {};
  qualityGates.items.forEach(item => {
    if (!groups[item.category]) {
      groups[item.category] = [];
    }
    groups[item.category].push(item);
  });
  
  let html = "";
  for (const [category, items] of Object.entries(groups)) {
    html += `
      <div class="gate-category-group">
        <h3 class="gate-category-title">${escapeHtml(category)} Checklists</h3>
        <div class="gate-items">
    `;
    
    items.forEach(item => {
      let statusClass = "review";
      let badgeText = "Requires Review";
      let isChecked = "";
      let isDisabled = "";
      
      if (item.passed) {
        statusClass = "passed";
        badgeText = "Passed";
        isChecked = "checked";
        if (!item.manual) isDisabled = "disabled";
      } else if (!item.passed && !item.manual) {
        statusClass = "failed";
        badgeText = "Failed Check";
      }
      
      const badgeHtml = `<span class="badge ${statusClass}">${badgeText}</span>`;
      const feedbackHtml = item.message ? `<div class="gate-feedback ${statusClass}">${escapeHtml(item.message)}</div>` : "";
      
      html += `
        <div class="gate-item ${statusClass}">
          <input type="checkbox" class="gate-checkbox" ${isChecked} ${isDisabled} />
          <div class="gate-details">
            <div class="gate-title-row">
              <span class="gate-item-title">${escapeHtml(item.title)}</span>
              ${badgeHtml}
            </div>
            <span class="gate-desc">${escapeHtml(item.description)}</span>
            ${feedbackHtml}
          </div>
        </div>
      `;
    });
    
    html += `
        </div>
      </div>
    `;
  }
  
  container.innerHTML = html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatDiffLine(line) {
  if (line.startsWith("+++") || line.startsWith("---")) {
    return `<span class="diff-hunk">${escapeHtml(line)}</span>`;
  }
  if (line.startsWith("@@")) {
    return `<span class="diff-hunk">${escapeHtml(line)}</span>`;
  }
  if (line.startsWith("+")) {
    return `<span class="diff-add">${escapeHtml(line)}</span>`;
  }
  if (line.startsWith("-")) {
    return `<span class="diff-del">${escapeHtml(line)}</span>`;
  }
  return `<span class="diff-ctx">${escapeHtml(line)}</span>`;
}

function formatDiffBlock(text) {
  return text.split("\n").map(formatDiffLine).join("\n");
}

function renderDiff(diff) {
  const panel = $("diffPanel");
  const content = $("diffContent");
  if (!diff || (!diff.wbs && !diff.raid && !diff.stakeholder_map && !diff.status_report)) {
    panel.classList.add("hidden");
    content.innerHTML = "";
    return;
  }

  let html = "";
  if (diff.wbs) {
    html += `<h4>WBS</h4><pre class="diff-body">${formatDiffBlock(diff.wbs)}</pre>`;
  }
  if (diff.raid) {
    html += `<h4>RAID</h4><pre class="diff-body">${formatDiffBlock(diff.raid)}</pre>`;
  }
  if (diff.stakeholder_map) {
    html += `<h4>Stakeholder Map</h4><pre class="diff-body">${formatDiffBlock(diff.stakeholder_map)}</pre>`;
  }
  if (diff.status_report) {
    html += `<h4>Weekly Status Report</h4><pre class="diff-body">${formatDiffBlock(diff.status_report)}</pre>`;
  }
  content.innerHTML = html;
  panel.classList.remove("hidden");
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function setReviewStatus(message = "") {
  const statusEl = $("reviewStatus");
  if (message) {
    statusEl.classList.remove("hidden");
    statusEl.classList.add("busy");
    statusEl.textContent = message;
  } else if (!hasActiveRevisions()) {
    statusEl.classList.add("hidden");
    statusEl.classList.remove("busy");
    statusEl.textContent = "";
  }
}

function updateReviewControls(data) {
  const approved = data.status === "approved";
  const generating = isArtifactGenerationRunning(data);
  const limitedOut = !data.unlimited_revisions && data.revisions_remaining === 0;
  const qualityBusy = false;

  document.querySelectorAll(".review-actions .btn").forEach((btn) => {
    const action = btn.dataset.action;
    if (action === "approve") {
      btn.disabled = approved || generating;
    } else if (action === "quality_check") {
      btn.disabled = approved || qualityBusy || generating;
    }
  });

  updateFeedbackPane(data);

  if (hasActiveRevisions(data)) {
    const active = getRevisionsInProgress(data)
      .map((key) => ARTIFACT_LABELS[key] || key)
      .join(", ");
    setReviewStatus(`Revising ${active}…`);
  } else {
    setReviewStatus("");
  }
}

function updateRevisionHint(data) {
  $("revisionCount").textContent = String(data.revision_count ?? 0);
  const label = $("revisionCountLabel");
  if (data.unlimited_revisions) {
    label.textContent = "Revisions applied (unlimited):";
  } else {
    label.textContent = `Revisions applied (${data.revisions_remaining ?? 0} remaining):`;
  }
}

function updateResults(data) {
  lastSessionData = data;
  syncPendingRevisions(data);
  const badge = $("statusBadge");
  badge.textContent = data.status || data.job_status;
  badge.classList.toggle("done", data.status === "approved");

  if (data.summary) {
    renderSummary(data.summary);
    const oq = $("openQuestions");
    const resolved =
      data.parsed_brief?.resolved_open_questions?.filter(
        (item) => item?.question && item?.answer
      ) ?? [];
    if (resolved.length) {
      oq.classList.remove("hidden");
      oq.innerHTML =
        "<strong>Confirmed before build</strong> " +
        '<span class="hint">(planner sign-off on open questions)</span>' +
        "<ul>" +
        resolved
          .map(
            (item) =>
              `<li><strong>${escapeHtml(item.question)}</strong><br />${escapeHtml(item.answer)}</li>`
          )
          .join("") +
        "</ul>";
    } else if (data.summary.open_questions?.length) {
      oq.classList.remove("hidden");
      oq.innerHTML =
        "<strong>Open questions</strong> " +
        '<span class="hint">(from the brief — not yet resolved)</span>' +
        "<ul>" +
        data.summary.open_questions.map((q) => `<li>${escapeHtml(q)}</li>`).join("") +
        "</ul>";
    } else {
      oq.classList.add("hidden");
    }
  }

  renderTabContent(data);
  updateDownloadBar();
  updateRevisionHint(data);
  updateTabIndicators(data);

  const approved = data.status === "approved";
  const generating = isArtifactGenerationRunning(data);
  const limitedOut = !data.unlimited_revisions && data.revisions_remaining === 0;
  $("reviewSection").classList.toggle("hidden", approved || generating);
  updateGenerationBanner(data);

  if (limitedOut && !approved) {
    setError(
      $("reviewError"),
      "Revision limit reached. Set MAX_REVISIONS=0 in .env for unlimited revisions, then restart the server."
    );
  }

  updateReviewControls(data);

  if (data.last_diff && !hasActiveRevisions(data)) {
    renderDiff(data.last_diff);
  }
  if (data.last_review_message && !hasActiveRevisions(data)) {
    $("reviewMessage").classList.remove("hidden");
    $("reviewMessage").textContent = data.last_review_message;
  }
}

function stopReviewPolling() {
  if (reviewPollTimer) {
    clearInterval(reviewPollTimer);
    reviewPollTimer = null;
  }
}

function startReviewPolling() {
  stopReviewPolling();

  const tick = async () => {
    try {
      const data = await pollSession(currentSessionId);
      updateResults(data);

      if (!hasActiveRevisions(data)) {
        stopReviewPolling();

        if (data.review_error) {
          setError($("reviewError"), data.review_error);
          return;
        }

        if (data.last_diff) {
          renderDiff(data.last_diff);
        }
        if (data.last_review_message) {
          $("reviewMessage").classList.remove("hidden");
          $("reviewMessage").textContent = data.last_review_message;
        }
      }
    } catch (err) {
      stopReviewPolling();
      setError($("reviewError"), err.message);
    }
  };

  tick();
  reviewPollTimer = setInterval(tick, 400);
}

function renderParsePreview(preview) {
  const el = $("parsePreview");
  if (!preview) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  el.classList.remove("hidden");
  el.innerHTML = `
    <div class="parse-preview-grid">
      <div><span class="label">Client</span><strong>${escapeHtml(preview.client || "—")}</strong></div>
      <div><span class="label">Project</span><strong>${escapeHtml(preview.project || "—")}</strong></div>
      <div><span class="label">Objectives</span><strong>${preview.objectives_count ?? 0}</strong></div>
      <div><span class="label">In-scope items</span><strong>${preview.scope_in_count ?? 0}</strong></div>
    </div>`;
}

function normalizeConfirmationQuestion(item) {
  if (typeof item === "string") {
    return { question: item, suggested_answers: [] };
  }
  return {
    question: item?.question || "",
    suggested_answers: Array.isArray(item?.suggested_answers)
      ? item.suggested_answers
      : [],
  };
}

function renderConfirmationForm(questions) {
  const form = $("confirmQuestionsForm");
  form.innerHTML = questions
    .map((item, index) => {
      const { question, suggested_answers: choices } = normalizeConfirmationQuestion(item);
      const choicesHtml =
        choices.length > 0
          ? `<div class="confirm-choices" role="group" aria-label="Suggested answers">
          <span class="confirm-choices-label">Tentative options (click to prefill — edit as needed)</span>
          <div class="confirm-choice-list">
            ${choices
              .map(
                (choice, choiceIndex) => `
            <button
              type="button"
              class="confirm-choice-chip"
              data-question-index="${index}"
              data-choice-index="${choiceIndex}"
            >${escapeHtml(choice)}</button>`
              )
              .join("")}
          </div>
        </div>`
          : "";
      return `
    <div class="field confirm-question">
      <label class="confirm-q-label" for="confirm-answer-${index}">
        ${index + 1}. ${escapeHtml(question)}
      </label>
      ${choicesHtml}
      <textarea
        id="confirm-answer-${index}"
        class="confirm-answer"
        data-question-index="${index}"
        rows="3"
        required
        placeholder="Your decision or assumption for the workplan…"
      ></textarea>
    </div>`;
    })
    .join("");

  form.querySelectorAll(".confirm-choice-chip").forEach((button) => {
    button.addEventListener("click", () => {
      const index = button.dataset.questionIndex;
      const choiceIndex = Number(button.dataset.choiceIndex);
      const normalized = normalizeConfirmationQuestion(questions[index]);
      const choice = normalized.suggested_answers[choiceIndex];
      const textarea = form.querySelector(`.confirm-answer[data-question-index="${index}"]`);
      if (textarea && choice) {
        textarea.value = choice;
        textarea.focus();
      }
      form.querySelectorAll(`.confirm-choice-chip[data-question-index="${index}"]`).forEach((chip) => {
        chip.classList.toggle("selected", chip === button);
      });
    });
  });
}

function warmBuildPromptCache(sessionId) {
  fetch(`${API}/api/sessions/${sessionId}/warm-build-cache`, {
    method: "POST",
  }).catch(() => {});
}

function showConfirmationPanel(data) {
  pendingConfirmationQuestions = data.confirmation_questions || [];
  $("confirmSessionIdLabel").textContent = data.session_id;
  renderParsePreview(data.parse_preview);
  renderConfirmationForm(pendingConfirmationQuestions);
  setError($("confirmError"), "");
  $("confirmBuildBtn").disabled = false;
  showPanel("confirm");
  warmBuildPromptCache(data.session_id);
}

function resumePollingAfterConfirm(sessionId) {
  showPanel("progress");
  $("sessionIdLabel").textContent = sessionId;
  setError($("progressError"), "");
  setError($("reviewError"), "");

  const tick = async () => {
    try {
      const data = await pollSession(sessionId);
      if (handleGenerationPoll(data)) return;
    } catch (err) {
      clearInterval(pollTimer);
      setError($("progressError"), err.message);
    }
  };

  tick();
  pollTimer = setInterval(tick, 800);
}

async function submitConfirmation() {
  if (!currentSessionId) return;

  const fields = document.querySelectorAll(".confirm-answer");
  const answers = [];
  for (const field of fields) {
    const index = Number(field.dataset.questionIndex);
    const question =
      normalizeConfirmationQuestion(pendingConfirmationQuestions[index]).question || "";
    const answer = field.value.trim();
    if (!answer) {
      setError($("confirmError"), "Please answer every open question before continuing.");
      field.focus();
      return;
    }
    answers.push({ question, answer });
  }

  $("confirmBuildBtn").disabled = true;
  setError($("confirmError"), "");

  try {
    const res = await fetch(`${API}/api/sessions/${currentSessionId}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(parseApiError(body));
    }
    resumePollingAfterConfirm(currentSessionId);
  } catch (err) {
    setError($("confirmError"), err.message);
    $("confirmBuildBtn").disabled = false;
  }
}

function startPolling(sessionId) {
  currentSessionId = sessionId;
  $("sessionIdLabel").textContent = sessionId;
  showPanel("progress");
  setError($("progressError"), "");
  setError($("createError"), "");

  const tick = async () => {
    try {
      const data = await pollSession(sessionId);
      if (data.phase === "parsing" || data.phase === "queued" || !hasViewableArtifacts(data)) {
        showPanel("progress");
      }
      if (handleGenerationPoll(data)) return;
    } catch (err) {
      clearInterval(pollTimer);
      setError($("progressError"), err.message);
    }
  };

  tick();
  pollTimer = setInterval(tick, 800);
}

async function createSession() {
  const briefText = $("briefText").value.trim();
  if (briefText.length < 10) {
    setError($("createError"), "Brief must be at least 10 characters.");
    return;
  }

  $("generateBtn").disabled = true;
  setError($("createError"), "");

  try {
    const res = await fetch(`${API}/api/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        brief_text: briefText,
        user_prompt: $("userPrompt").value.trim(),
        mock: $("mockMode").checked,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(parseApiError(body));
    }
    const data = await res.json();
    $("diffPanel").classList.add("hidden");
    startPolling(data.session_id);
  } catch (err) {
    setError($("createError"), err.message);
  } finally {
    $("generateBtn").disabled = false;
  }
}

async function submitReview(action, feedback = "") {
  setError($("reviewError"), "");
  $("reviewMessage").classList.add("hidden");

  const res = await fetch(`${API}/api/sessions/${currentSessionId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, feedback }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(parseApiError(body));
  }
  return { status: res.status, body };
}

const REVISION_MESSAGES = {
  wbs: "Revising WBS…",
  raid: "Revising RAID log…",
  stakeholder: "Revising Stakeholder Map…",
  status: "Revising Status Report…",
};

async function handleReviewAction(action) {
  if (action === "approve") {
    const stale =
      lastSessionData?.quality_gates_stale ||
      Object.keys(lastSessionData?.stale_artifacts || {}).length > 0;
    if (stale) {
      const proceed = window.confirm(
        "Some documents or quality checks may be outdated. Approve anyway?"
      );
      if (!proceed) return;
    }

    setReviewStatus("Approving workplan…");
    try {
      const { body } = await submitReview("approve");
      $("reviewMessage").classList.remove("hidden");
      $("reviewMessage").textContent = body.message;
      const data = await pollSession(currentSessionId);
      updateResults(data);
    } catch (err) {
      setError($("reviewError"), err.message);
    } finally {
      setReviewStatus("");
      if (lastSessionData) updateResults(lastSessionData);
    }
    return;
  }

  if (action === "quality_check") {
    setReviewStatus("Running quality check…");
    try {
      const { body } = await submitReview("quality_check");
      $("reviewMessage").classList.remove("hidden");
      $("reviewMessage").textContent = body.message;
      const data = await pollSession(currentSessionId);
      updateResults(data);
    } catch (err) {
      setError($("reviewError"), err.message);
    } finally {
      setReviewStatus("");
    }
    return;
  }
}

async function submitRevision() {
  if (!isRevisionTab()) return;
  if (isTabRevising()) {
    setError(
      $("reviewError"),
      `${ARTIFACT_LABELS[currentTab] || currentTab} is still being revised. Wait or switch to another tab.`
    );
    return;
  }

  const feedback = $("feedbackText").value.trim();
  if (!feedback) {
    setError($("reviewError"), "Feedback is required.");
    return;
  }

  const action = currentTab;
  saveFeedbackDraft();
  setError($("reviewError"), "");
  $("submitRevisionBtn").disabled = true;

  try {
    const { status, body } = await submitReview(action, feedback);
    if (status === 202 || body.status === "accepted") {
      feedbackDrafts[action] = "";
      $("feedbackText").value = "";
      pendingRevisionTabs.add(action);
      if (lastSessionData) {
        updateReviewControls({
          ...lastSessionData,
          review_in_progress: true,
          revisions_in_progress: getRevisionsInProgress(lastSessionData),
        });
      }
      const data = await pollSession(currentSessionId);
      updateResults(data);
      startReviewPolling();
      return;
    }
    if (body.diff) {
      renderDiff(body.diff);
    }
    $("reviewMessage").classList.remove("hidden");
    $("reviewMessage").textContent = body.message;
    const data = await pollSession(currentSessionId);
    updateResults(data);
  } catch (err) {
    pendingRevisionTabs.delete(action);
    setError($("reviewError"), err.message);
    if (lastSessionData) updateResults(lastSessionData);
  }
}

function clearFeedback() {
  if (!isRevisionTab()) return;
  feedbackDrafts[currentTab] = "";
  $("feedbackText").value = "";
}

function resetUi() {
  clearInterval(pollTimer);
  stopReviewPolling();
  currentSessionId = null;
  currentTab = "wbs";
  lastSessionData = null;
  pendingConfirmationQuestions = [];
  pendingRevisionTabs.clear();
  Object.keys(feedbackDrafts).forEach((key) => {
    feedbackDrafts[key] = "";
  });
  $("feedbackText").value = "";
  $("artifactView").classList.add("hidden");
  $("briefTabContent").classList.add("hidden");
  $("qualityGatesTabContent").classList.add("hidden");
  setError($("createError"), "");
  setError($("progressError"), "");
  setError($("reviewError"), "");
  $("reviewMessage").classList.add("hidden");
  $("diffPanel").classList.add("hidden");
  setReviewStatus("");
  $("progressBar").style.width = "0%";
  setUploadStatus("");
  $("userPrompt").value = "";
  $("confirmQuestionsForm").innerHTML = "";
  $("parsePreview").classList.add("hidden");
  setError($("confirmError"), "");
  $("downloadBar").classList.add("hidden");
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelector(".tab[data-tab='wbs']").classList.add("active");
  showPanel("create");
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", async () => {
    saveFeedbackDraft();
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    currentTab = tab.dataset.tab;
    updateDownloadBar();
    if (currentSessionId && lastSessionData) {
      renderTabContent(lastSessionData);
      updateTabIndicators(lastSessionData);
      updateReviewControls(lastSessionData);
      loadFeedbackDraft();
    } else if (currentSessionId) {
      const data = await pollSession(currentSessionId);
      lastSessionData = data;
      updateResults(data);
    }
  });
});

document.querySelectorAll("[data-format]").forEach((btn) => {
  btn.addEventListener("click", () => downloadArtifact(btn.dataset.format));
});

$("briefFileInput").addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) uploadBriefFile(file);
});

document.querySelectorAll("[data-action]").forEach((btn) => {
  btn.addEventListener("click", () => handleReviewAction(btn.dataset.action));
});

$("generateBtn").addEventListener("click", createSession);
$("confirmBuildBtn").addEventListener("click", submitConfirmation);
$("loadSampleBtn").addEventListener("click", loadSampleBrief);
$("submitRevisionBtn").addEventListener("click", submitRevision);
$("clearFeedbackBtn").addEventListener("click", clearFeedback);
$("feedbackText").addEventListener("input", saveFeedbackDraft);
$("newSessionBtn").addEventListener("click", resetUi);
$("mockMode")?.addEventListener("change", refreshModelBadge);

checkHealth();
