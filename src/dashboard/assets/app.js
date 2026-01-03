const state = {
  tasks: [],
  filtered: [],
  activeId: null,
  activeDetail: null,
  metrics: null,
  workflows: [],
  activeWorkflow: null,
};

const el = (id) => document.getElementById(id);

const statTotal = el("statTotal").querySelector(".stat-value");
const statSuccess = el("statSuccess").querySelector(".stat-value");
const statFailed = el("statFailed").querySelector(".stat-value");
const statToolCalls = el("statToolCalls").querySelector(".stat-value");
const taskList = el("taskList");
const taskCount = el("taskCount");
const detailTitle = el("detailTitle");
const taskDetail = el("taskDetail");
const searchInput = el("searchInput");
const statusFilter = el("statusFilter");
const sortFilter = el("sortFilter");
const refreshBtn = el("refreshBtn");
const exportDetailMdBtn = el("exportDetailMdBtn");
const exportDetailJsonBtn = el("exportDetailJsonBtn");
const trendSparkline = el("trendSparkline");
const trendSummary = el("trendSummary");
const trendBadge = el("trendBadge");
const toolMetricList = el("toolMetricList");
const workflowList = el("workflowList");
const workflowPreview = el("workflowPreview");
const workflowSearch = el("workflowSearch");
const openWorkflowBtn = el("openWorkflowBtn");
const refreshWorkflowBtn = el("refreshWorkflowBtn");

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatSize(size) {
  if (!size && size !== 0) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function updateStats() {
  const total = state.tasks.length;
  const success = state.tasks.filter((t) => t.success === true).length;
  const failed = state.tasks.filter((t) => t.success === false).length;
  statTotal.textContent = total;
  statSuccess.textContent = success;
  statFailed.textContent = failed;
  statToolCalls.textContent = state.metrics?.summary?.total_calls ?? 0;
}

function applyFilters() {
  const keyword = searchInput.value.trim().toLowerCase();
  const status = statusFilter.value;
  let filtered = [...state.tasks];
  if (keyword) {
    filtered = filtered.filter((task) => {
      const text = `${task.task_id} ${task.prompt || ""} ${JSON.stringify(task.metadata || {})}`.toLowerCase();
      return text.includes(keyword);
    });
  }
  if (status !== "all") {
    filtered = filtered.filter((task) => {
      return status === "success" ? task.success === true : task.success === false;
    });
  }
  const order = sortFilter.value;
  filtered.sort((a, b) => {
    const aTime = new Date(a.timestamp || 0).getTime();
    const bTime = new Date(b.timestamp || 0).getTime();
    return order === "asc" ? aTime - bTime : bTime - aTime;
  });
  state.filtered = filtered;
  renderList();
}

function renderList() {
  taskList.innerHTML = "";
  taskCount.textContent = `${state.filtered.length} items`;
  state.filtered.forEach((task, idx) => {
    const card = document.createElement("div");
    card.className = "task-card";
    if (task.task_id === state.activeId) {
      card.classList.add("active");
    }
    card.style.animationDelay = `${idx * 0.02}s`;
    const badgeClass = task.success === true ? "success" : task.success === false ? "fail" : "";
    const badgeLabel = task.success === true ? "SUCCESS" : task.success === false ? "FAILED" : "UNKNOWN";
    const promptPreview = escapeHtml((task.prompt || "").slice(0, 60));
    card.innerHTML = `
      <div class="task-meta">
        <span>${formatTime(task.timestamp)}</span>
        <span class="badge ${badgeClass}">${badgeLabel}</span>
      </div>
      <div class="task-title">${escapeHtml(task.task_id)}</div>
      <div class="task-meta">${promptPreview}</div>
    `;
    card.addEventListener("click", () => selectTask(task.task_id));
    taskList.appendChild(card);
  });
}

async function selectTask(taskId) {
  state.activeId = taskId;
  detailTitle.textContent = taskId;
  renderList();
  taskDetail.classList.remove("empty");
  taskDetail.innerHTML = "<div class='detail-block'>Loading...</div>";
  try {
    const data = await fetchJson(`/api/task/${taskId}`);
    state.activeDetail = data;
    renderDetail(data);
  } catch (err) {
    taskDetail.innerHTML = `<div class='detail-block'>Load failed: ${err.message}</div>`;
  }
}

function renderDetail(data) {
  const result = data.result || {};
  const context = data.context_snapshot || null;
  const toolMetrics = data.tool_metrics || null;
  const artifacts = data.artifacts || [];
  const statusLabel = result.success === true ? "Success" : result.success === false ? "Failed" : "Unknown";

  taskDetail.innerHTML = `
    <div class="detail-section">
      <h3>Overview</h3>
      <div class="detail-block">
        <div>Task ID: ${escapeHtml(data.task_id || "-")}</div>
        <div>Timestamp: ${formatTime(result.timestamp)}</div>
        <div>Version: ${escapeHtml(result.version_tag || "-")}</div>
        <div>Iterations: ${result.total_iterations ?? "-"}</div>
        <div>Execution: ${result.execution_time ?? "-"} s</div>
        <div>Status: ${statusLabel}</div>
      </div>
    </div>
    <div class="detail-section">
      <h3>Prompt</h3>
      <div class="detail-block">${escapeHtml(result.prompt || "")}</div>
    </div>
    <div class="detail-section">
      <h3>Final Response</h3>
      <div class="detail-block">${escapeHtml(result.final_answer || "")}</div>
    </div>
    <div class="detail-section">
      <h3>Tool Summary</h3>
      <div class="detail-block">${renderToolSummary(toolMetrics)}</div>
    </div>
    <div class="detail-section">
      <h3>Context Snapshot</h3>
      <div class="detail-block">${renderContextSummary(context)}</div>
    </div>
    <div class="detail-section">
      <h3>Artifacts</h3>
      <div class="artifact-list">${renderArtifacts(artifacts)}</div>
      <div id="artifactPreview" class="preview">Select an artifact to preview.</div>
    </div>
  `;

  document.querySelectorAll(".artifact-item").forEach((item) => {
    item.addEventListener("click", () => {
      const url = item.dataset.url;
      const mime = item.dataset.mime;
      previewArtifact(url, mime);
    });
  });
}

function renderToolSummary(metrics) {
  if (!metrics || !metrics.summary) return "No tool metrics yet.";
  const summary = metrics.summary;
  return `
    Total calls: ${summary.total_calls ?? 0}<br/>
    Success: ${summary.success ?? 0}<br/>
    Errors: ${summary.error ?? 0}<br/>
    Timeout: ${summary.timeout ?? 0}<br/>
    Total time: ${(summary.total_time ?? 0).toFixed(2)} s
  `;
}

function renderContextSummary(context) {
  if (!context) return "No context snapshot available.";
  const stats = context.stats || {};
  return `
    Messages: ${stats.message_count ?? 0}<br/>
    Files: ${stats.file_count ?? 0}<br/>
    Context length: ${stats.context_length ?? 0}
  `;
}

function renderArtifacts(artifacts) {
  if (!artifacts.length) return "<div class='detail-block'>No artifacts yet.</div>";
  return artifacts
    .map((item) => {
      return `
        <div class="artifact-item" data-url="${item.url}" data-mime="${item.mime}">
          <span>${escapeHtml(item.name)}</span>
          <span>${formatSize(item.size)}</span>
        </div>
      `;
    })
    .join("");
}

async function previewArtifact(url, mime) {
  const preview = el("artifactPreview");
  preview.textContent = "Loading...";
  if (!url) return;
  if (mime && mime.startsWith("image/")) {
    preview.innerHTML = `<img src="${url}" alt="preview"/>`;
    return;
  }
  if (mime && (mime.startsWith("text/") || mime === "application/json" || mime === "text/markdown")) {
    try {
      const res = await fetch(url);
      const text = await res.text();
      preview.textContent = text;
    } catch (err) {
      preview.textContent = `Read failed: ${err.message}`;
    }
    return;
  }
  preview.textContent = "Preview not supported for this file type.";
}

function buildSparkline(values, width = 240, height = 60) {
  const points = values.filter((value) => typeof value === "number" && !Number.isNaN(value));
  if (!points.length) {
    return "<div class='mini-item'>No duration data yet.</div>";
  }
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const step = width / Math.max(points.length - 1, 1);
  const path = points
    .map((value, idx) => {
      const x = Math.round(idx * step);
      const y = Math.round(height - ((value - min) / range) * height);
      return `${x},${y}`;
    })
    .join(" ");
  return `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <polyline points="${path}" fill="none" stroke="currentColor" stroke-width="2" />
    </svg>
  `;
}

function renderTrend() {
  if (!trendSparkline || !trendSummary) return;
  const recent = Array.isArray(state.metrics?.recent) ? state.metrics.recent : [];
  const times = recent.map((item) => Number(item.execution_time || 0)).filter((value) => value > 0);
  const successRate = recent.length
    ? Math.round((recent.filter((item) => item.success === true).length / recent.length) * 100)
    : 0;
  const avg = times.length ? times.reduce((sum, value) => sum + value, 0) / times.length : 0;
  const last = times.length ? times[times.length - 1] : 0;

  trendSparkline.innerHTML = buildSparkline(times);
  trendSummary.innerHTML = "";
  const items = [
    `Avg: ${avg ? avg.toFixed(2) : "--"} s`,
    `Last: ${last ? last.toFixed(2) : "--"} s`,
    `Success rate: ${recent.length ? `${successRate}%` : "--"}`,
  ];
  items.forEach((line) => {
    const row = document.createElement("div");
    row.className = "mini-item";
    row.textContent = line;
    trendSummary.appendChild(row);
  });
  if (trendBadge) {
    trendBadge.textContent = recent.length ? `${recent.length} runs` : "--";
  }
}

function renderToolMetrics() {
  if (!toolMetricList) return;
  toolMetricList.innerHTML = "";
  const tools = state.metrics?.tools || {};
  const entries = Object.entries(tools)
    .map(([name, item]) => ({
      name,
      total: item.total_calls ?? 0,
      success: item.success ?? 0,
      error: item.error ?? 0,
      avg: item.avg_time ?? 0,
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 8);

  if (!entries.length) {
    const row = document.createElement("div");
    row.className = "mini-item";
    row.textContent = "No tool metrics yet.";
    toolMetricList.appendChild(row);
    return;
  }
  entries.forEach((item) => {
    const row = document.createElement("div");
    row.className = "mini-item";
    row.textContent = `${item.name}: ${item.total} calls | ok ${item.success} | err ${item.error} | avg ${item.avg.toFixed(2)}s`;
    toolMetricList.appendChild(row);
  });
}

function renderWorkflowList() {
  if (!workflowList) return;
  workflowList.innerHTML = "";
  const keyword = (workflowSearch.value || "").trim().toLowerCase();
  const list = state.workflows.filter((item) => item.name.toLowerCase().includes(keyword));
  if (!list.length) {
    const empty = document.createElement("div");
    empty.className = "mini-item";
    empty.textContent = "No workflows found.";
    workflowList.appendChild(empty);
    return;
  }
  list.forEach((item) => {
    const card = document.createElement("div");
    card.className = "workflow-item";
    if (item.name === state.activeWorkflow) {
      card.classList.add("active");
    }
    const tags = [];
    if (item.files?.html) tags.push("<span class='workflow-tag'>HTML</span>");
    if (item.files?.mmd) tags.push("<span class='workflow-tag'>MMD</span>");
    card.innerHTML = `
      <div class="workflow-title">${escapeHtml(item.name)}</div>
      <div class="workflow-meta">${formatTime(item.updated_at)}</div>
      <div class="workflow-tags">${tags.join("")}</div>
    `;
    card.addEventListener("click", () => selectWorkflow(item.name));
    workflowList.appendChild(card);
  });
}

async function selectWorkflow(name) {
  state.activeWorkflow = name;
  renderWorkflowList();
  const entry = state.workflows.find((item) => item.name === name);
  await renderWorkflowPreview(entry);
}

async function renderWorkflowPreview(entry) {
  if (!workflowPreview) return;
  if (!entry) {
    workflowPreview.textContent = "Select a workflow to preview.";
    if (openWorkflowBtn) openWorkflowBtn.dataset.url = "";
    return;
  }
  const files = entry.files || {};
  const htmlUrl = files.html?.url || "";
  const mmdUrl = files.mmd?.url || "";
  if (openWorkflowBtn) {
    openWorkflowBtn.dataset.url = htmlUrl || mmdUrl || "";
  }
  if (htmlUrl) {
    workflowPreview.innerHTML = `<iframe src="${htmlUrl}" title="workflow preview"></iframe>`;
    return;
  }
  if (mmdUrl) {
    workflowPreview.textContent = "Loading...";
    try {
      const res = await fetch(mmdUrl);
      const text = await res.text();
      workflowPreview.textContent = text;
    } catch (err) {
      workflowPreview.textContent = `Load failed: ${err.message}`;
    }
    return;
  }
  workflowPreview.textContent = "No preview available.";
}

async function loadWorkflows() {
  try {
    const data = await fetchJson("/api/workflows");
    state.workflows = data.workflows || [];
    if (!state.activeWorkflow && state.workflows.length) {
      state.activeWorkflow = state.workflows[0].name;
    }
    renderWorkflowList();
    if (state.activeWorkflow) {
      const entry = state.workflows.find((item) => item.name === state.activeWorkflow);
      await renderWorkflowPreview(entry);
    }
  } catch (err) {
    if (workflowList) {
      workflowList.innerHTML = `<div class='mini-item'>Workflow load failed: ${err.message}</div>`;
    }
  }
}

function downloadText(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadJson(filename, payload) {
  const content = JSON.stringify(payload, null, 2);
  const blob = new Blob([content], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildTaskMarkdown(data) {
  const result = data.result || {};
  const context = data.context_snapshot || null;
  const artifacts = data.artifacts || [];
  const toolMetrics = data.tool_metrics || null;
  const summary = toolMetrics?.summary || {};
  const lines = [
    `# Task ${data.task_id || ""}`,
    "",
    "## Overview",
    `- Timestamp: ${formatTime(result.timestamp)}`,
    `- Version: ${result.version_tag || "-"}`,
    `- Iterations: ${result.total_iterations ?? "-"}`,
    `- Execution: ${result.execution_time ?? "-"} s`,
    `- Status: ${result.success === true ? "Success" : result.success === false ? "Failed" : "Unknown"}`,
    "",
    "## Prompt",
    "```",
    result.prompt || "",
    "```",
    "",
    "## Final Response",
    "```",
    result.final_answer || "",
    "```",
    "",
    "## Tool Metrics",
    `- Total calls: ${summary.total_calls ?? 0}`,
    `- Success: ${summary.success ?? 0}`,
    `- Errors: ${summary.error ?? 0}`,
    `- Timeout: ${summary.timeout ?? 0}`,
    `- Total time: ${(summary.total_time ?? 0).toFixed(2)} s`,
    "",
    "## Context Snapshot",
  ];
  if (context && context.stats) {
    lines.push(
      `- Messages: ${context.stats.message_count ?? 0}`,
      `- Files: ${context.stats.file_count ?? 0}`,
      `- Context length: ${context.stats.context_length ?? 0}`
    );
  } else {
    lines.push("- No snapshot available.");
  }
  lines.push("", "## Artifacts");
  if (!artifacts.length) {
    lines.push("- No artifacts.");
  } else {
    artifacts.forEach((item) => {
      lines.push(`- ${item.name} (${formatSize(item.size)})`);
    });
  }
  return lines.join("\n");
}

function exportDetail(type) {
  if (!state.activeDetail || !state.activeId) {
    return;
  }
  if (type === "json") {
    downloadJson(`task_${state.activeId}.json`, state.activeDetail);
    return;
  }
  downloadText(`task_${state.activeId}.md`, buildTaskMarkdown(state.activeDetail));
}

async function refresh() {
  try {
    const [indexData, metricsData] = await Promise.all([
      fetchJson("/api/index"),
      fetchJson("/api/metrics"),
    ]);
    state.tasks = indexData.tasks || [];
    state.metrics = metricsData || {};
    updateStats();
    applyFilters();
    renderTrend();
    renderToolMetrics();
    await loadWorkflows();
  } catch (err) {
    taskList.innerHTML = `<div class='detail-block'>Load failed: ${err.message}</div>`;
  }
}

searchInput.addEventListener("input", applyFilters);
statusFilter.addEventListener("change", applyFilters);
sortFilter.addEventListener("change", applyFilters);
refreshBtn.addEventListener("click", refresh);
if (workflowSearch) {
  workflowSearch.addEventListener("input", renderWorkflowList);
}
if (openWorkflowBtn) {
  openWorkflowBtn.addEventListener("click", () => {
    const url = openWorkflowBtn.dataset.url;
    if (url) {
      window.open(url, "_blank");
    }
  });
}
if (refreshWorkflowBtn) {
  refreshWorkflowBtn.addEventListener("click", loadWorkflows);
}
if (exportDetailMdBtn) {
  exportDetailMdBtn.addEventListener("click", () => exportDetail("md"));
}
if (exportDetailJsonBtn) {
  exportDetailJsonBtn.addEventListener("click", () => exportDetail("json"));
}

refresh();
