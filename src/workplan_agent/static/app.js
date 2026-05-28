const API = "";

let currentSessionId = null;
let currentTab = "wbs";
let pendingRevisionAction = null;
let pollTimer = null;
let reviewPollTimer = null;
let reviewBusy = false;
let lastSessionData = null;

const $ = (id) => document.getElementById(id);

const panels = {
  create: $("createPanel"),
  progress: $("progressPanel"),
  results: $("resultsPanel"),
};

function showPanel(name) {
  Object.entries(panels).forEach(([key, el]) => {
    el.classList.toggle("hidden", key !== name);
  });
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

async function checkHealth() {
  const badge = $("healthBadge");
  try {
    const res = await fetch(`${API}/api/health`);
    if (!res.ok) throw new Error("unhealthy");
    badge.textContent = "API online";
    badge.classList.add("ok");
  } catch {
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

const DOWNLOAD_ARTIFACTS = { wbs: "WBS", raid: "RAID", brief: null };

function updateDownloadBar() {
  const bar = $("downloadBar");
  const artifact = DOWNLOAD_ARTIFACTS[currentTab];
  if (!currentSessionId || !artifact) {
    bar.classList.add("hidden");
    return;
  }
  bar.classList.remove("hidden");
  $("downloadArtifactLabel").textContent = artifact;
}

async function downloadArtifact(format) {
  const artifact = currentTab;
  if (artifact !== "wbs" && artifact !== "raid") return;
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

async function loadSampleBrief() {
  try {
    const res = await fetch(`${API}/assets/sample_brief.md`);
    if (!res.ok) throw new Error("Sample not found");
    $("briefText").value = await res.text();
  } catch {
    setError($("createError"), "Could not load sample brief.");
  }
}

function phaseLabel(phase, jobStatus, reviewInProgress) {
  if (reviewInProgress) {
    const labels = {
      revising: "Applying revision…",
      approving: "Approving workplan…",
    };
    return labels[phase] || "Review in progress…";
  }
  const labels = {
    queued: "Queued…",
    parsing: "Parsing client brief…",
    generating_wbs: "Generating WBS…",
    ready_for_review: "Ready for review",
    failed: "Generation failed",
  };
  if (jobStatus === "failed") return labels.failed;
  return labels[phase] || phase;
}

function progressPercent(phase, jobStatus) {
  if (jobStatus === "complete") return 100;
  if (jobStatus === "failed") return 100;
  const map = { queued: 10, parsing: 35, generating_wbs: 70, ready_for_review: 100 };
  return map[phase] ?? 20;
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
    ["Assumptions", summary.raid_assumptions],
    ["Issues", summary.raid_issues],
    ["Dependencies", summary.raid_dependencies],
  ];
  $("summaryCards").innerHTML = cards
    .map(
      ([label, value]) =>
        `<div class="card"><div class="value">${value}</div><div class="label">${label}</div></div>`
    )
    .join("");
}

function renderTabContent(data) {
  const el = $("tabContent");
  if (currentTab === "wbs") {
    el.textContent = data.wbs_markdown || "WBS not available yet.";
  } else if (currentTab === "raid") {
    el.textContent = data.raid_markdown || "RAID not available yet.";
  } else {
    el.textContent = JSON.stringify(data.parsed_brief, null, 2);
  }
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
  if (!diff || (!diff.wbs && !diff.raid)) {
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
  content.innerHTML = html;
  panel.classList.remove("hidden");
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function setReviewBusy(busy, message = "") {
  reviewBusy = busy;
  const statusEl = $("reviewStatus");
  const reviewButtons = document.querySelectorAll(
    ".review-actions .btn, #submitRevisionBtn, #cancelRevisionBtn"
  );

  reviewButtons.forEach((btn) => {
    btn.disabled = busy || lastSessionData?.status === "approved";
  });

  if (busy && message) {
    statusEl.classList.remove("hidden");
    statusEl.classList.add("busy");
    statusEl.textContent = message;
    statusEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } else if (!busy) {
    statusEl.classList.add("hidden");
    statusEl.classList.remove("busy");
    statusEl.textContent = "";
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
  const badge = $("statusBadge");
  badge.textContent = data.status || data.job_status;
  badge.classList.toggle("done", data.status === "approved");

  if (data.summary) {
    renderSummary(data.summary);
    const oq = $("openQuestions");
    if (data.summary.open_questions?.length) {
      oq.classList.remove("hidden");
      oq.innerHTML =
        "<strong>Open questions</strong> " +
        '<span class="hint">(from the brief — items the client has not decided yet)</span>' +
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

  const approved = data.status === "approved";
  const limitedOut = !data.unlimited_revisions && data.revisions_remaining === 0;
  $("reviewSection").classList.toggle("hidden", approved);

  if (limitedOut && !approved) {
    setError(
      $("reviewError"),
      "Revision limit reached. Set MAX_REVISIONS=0 in .env for unlimited revisions, then restart the server."
    );
  }

  if (data.review_in_progress) {
    setReviewBusy(
      true,
      phaseLabel(data.phase, data.job_status, true) + " Please wait."
    );
  } else if (!reviewBusy) {
    setReviewBusy(false);
    document
      .querySelectorAll(".review-actions .btn, #submitRevisionBtn, #cancelRevisionBtn")
      .forEach((btn) => {
        btn.disabled = approved || limitedOut;
      });
  }

  if (data.last_diff && !data.review_in_progress) {
    renderDiff(data.last_diff);
  }
  if (data.last_review_message && !data.review_in_progress && !reviewBusy) {
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

function startReviewPolling(initialMessage) {
  stopReviewPolling();
  setReviewBusy(true, initialMessage);

  const tick = async () => {
    try {
      const data = await pollSession(currentSessionId);
      updateResults(data);

      if (!data.review_in_progress) {
        stopReviewPolling();
        setReviewBusy(false);

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
        updateResults(data);
      }
    } catch (err) {
      stopReviewPolling();
      setReviewBusy(false);
      setError($("reviewError"), err.message);
    }
  };

  tick();
  reviewPollTimer = setInterval(tick, 400);
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
      $("phaseLabel").textContent = phaseLabel(
        data.phase,
        data.job_status,
        data.review_in_progress
      );
      $("progressBar").style.width = `${progressPercent(data.phase, data.job_status)}%`;

      if (data.job_status === "complete" && !data.review_in_progress) {
        clearInterval(pollTimer);
        showPanel("results");
        updateResults(data);
        return;
      }
      if (data.job_status === "failed") {
        clearInterval(pollTimer);
        setError($("progressError"), data.error || "Unknown error");
        return;
      }
    } catch (err) {
      clearInterval(pollTimer);
      setError($("progressError"), err.message);
    }
  };

  tick();
  pollTimer = setInterval(tick, 1200);
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

function showFeedbackForm(action) {
  if (reviewBusy) return;
  pendingRevisionAction = action;
  $("feedbackField").classList.remove("hidden");
  $("feedbackActions").classList.remove("hidden");
  $("feedbackHint").classList.remove("hidden");
  document.querySelectorAll(".review-actions .btn").forEach((b) => {
    b.disabled = true;
  });
  $("submitRevisionBtn").disabled = false;
  $("cancelRevisionBtn").disabled = false;
}

function cancelFeedbackForm() {
  pendingRevisionAction = null;
  $("feedbackText").value = "";
  $("feedbackField").classList.add("hidden");
  $("feedbackActions").classList.add("hidden");
  $("feedbackHint").classList.add("hidden");
  if (!reviewBusy && lastSessionData) {
    updateResults(lastSessionData);
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
  wbs: "Revising WBS… Please wait — do not click again.",
  raid: "Revising RAID log… Please wait — do not click again.",
  both: "Revising WBS and RAID… Please wait — do not click again.",
  approve: "Approving workplan…",
};

async function handleReviewAction(action) {
  if (reviewBusy) return;

  if (action === "approve") {
    setReviewBusy(true, REVISION_MESSAGES.approve);
    try {
      const { status, body } = await submitReview("approve");
      if (status === 200) {
        $("reviewMessage").classList.remove("hidden");
        $("reviewMessage").textContent = body.message;
      }
      const data = await pollSession(currentSessionId);
      updateResults(data);
    } catch (err) {
      setError($("reviewError"), err.message);
    } finally {
      setReviewBusy(false);
      if (lastSessionData) updateResults(lastSessionData);
    }
    return;
  }
  showFeedbackForm(action);
}

async function submitRevision() {
  if (!pendingRevisionAction || reviewBusy) return;

  const feedback = $("feedbackText").value.trim();
  if (!feedback) {
    setError($("reviewError"), "Feedback is required.");
    return;
  }

  const action = pendingRevisionAction;
  pendingRevisionAction = null;
  $("feedbackField").classList.add("hidden");
  $("feedbackActions").classList.add("hidden");
  $("feedbackHint").classList.add("hidden");

  try {
    const { status, body } = await submitReview(action, feedback);
    if (status === 202 || body.status === "accepted") {
      startReviewPolling(REVISION_MESSAGES[action] || "Applying revision…");
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
    setError($("reviewError"), err.message);
    setReviewBusy(false);
    if (lastSessionData) updateResults(lastSessionData);
  }
}

function resetUi() {
  clearInterval(pollTimer);
  stopReviewPolling();
  currentSessionId = null;
  pendingRevisionAction = null;
  lastSessionData = null;
  reviewBusy = false;
  cancelFeedbackForm();
  setError($("createError"), "");
  setError($("progressError"), "");
  setError($("reviewError"), "");
  $("reviewMessage").classList.add("hidden");
  $("diffPanel").classList.add("hidden");
  setReviewBusy(false);
  $("progressBar").style.width = "0%";
  setUploadStatus("");
  $("downloadBar").classList.add("hidden");
  showPanel("create");
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", async () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    currentTab = tab.dataset.tab;
    updateDownloadBar();
    if (currentSessionId) {
      const data = await pollSession(currentSessionId);
      renderTabContent(data);
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
$("loadSampleBtn").addEventListener("click", loadSampleBrief);
$("submitRevisionBtn").addEventListener("click", submitRevision);
$("cancelRevisionBtn").addEventListener("click", cancelFeedbackForm);
$("newSessionBtn").addEventListener("click", resetUi);

checkHealth();
