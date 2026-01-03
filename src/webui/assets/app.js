const state = {
  sessionId: null,
  activeSlot: "alpha",
  slots: {},
  transcripts: {},
  pins: [],
  errors: [],
  templates: [],
  filters: {
    role: "all",
    query: "",
    pinnedOnly: false,
  },
  renderLimit: 120,
  renderStep: 80,
  clientId: null,
  busy: false,
  stats: {
    total: 0,
    success: 0,
  },
  lastReply: "",
  lastAssistantMessageId: null,
  replyTarget: null,
  lastPreset: "",
  dashboardUrl: "",
  artifactPreviewUrl: null,
  selectedArtifacts: [],
  artifactDiffBundle: null,
  streamEnabled: true,
  maxIterations: null,
  loadingOlder: false,
  runLog: [],
  media: {
    items: [],
    sources: [],
    alerts: [],
    briefs: [],
    stats: {},
  },
  webhooks: {
    logs: [],
  },
  taskBoard: {
    items: [],
    stats: {},
    selectedId: null,
  },
  bookmarks: {
    items: [],
    selectedId: null,
  },
  reminders: {
    items: [],
    logs: [],
    selectedId: null,
  },
  focus: {
    items: [],
    active: null,
    timer: null,
  },
  knowledgeMap: {
    folders: [],
    recent: [],
  },
  workflowTemplates: {
    items: [],
    selectedId: null,
    runs: [],
  },
  artifactTags: {
    items: {},
  },
  systemMetrics: {},
  logsCenter: [],
  triggers: [],
  todo: {
    tasks: [],
    view: { type: "project", id: "Inbox" },
    selectedTaskId: null,
    projects: [],
    smartLists: [],
    filters: {
      query: "",
      tags: [],
    },
    drag: {
      taskId: null,
      sourceSection: "",
    },
  },
  mainView: "chat",
};

const COLLAPSE_LIMIT = 800;

const storeKey = "sama_pixel_session";
const slotKey = "sama_session_slots";
const transcriptKey = "sama_session_transcripts";
const themeKey = "sama_theme";
const templateKey = "sama_templates";
const errorKey = "sama_errors";
const clientKey = "sama_client_id";
const streamKey = "sama_stream_enabled";
const presetKey = "sama_last_preset";
const draftKey = "sama_message_draft";
const todoProjectsKey = "sama_todo_projects";
const todoFiltersKey = "sama_todo_filters";
const todoCollapseKey = "sama_todo_collapse";

const STREAM_RETRY_DELAYS = [1000, 2000, 4000];
const STREAM_STALL_MS = 20000;

const el = (id) => document.getElementById(id);

const chatLog = el("chatLog");
const messageInput = el("messageInput");
const sendBtn = el("sendBtn");
const stopBtn = el("stopBtn");
const continueBtn = el("continueBtn");
const newSessionBtn = el("newSessionBtn");
const resetBtn = el("resetBtn");
const clearBtn = el("clearBtn");
const copyBtn = el("copyBtn");
const syncBtn = el("syncBtn");
const dashboardBtn = el("dashboardBtn");
const dashboardStatus = el("dashboardStatus");
const dashboardOpenBtn = el("dashboardOpenBtn");
const dashboardCopyBtn = el("dashboardCopyBtn");
const linkBtn = el("linkBtn");
const streamBtn = el("streamBtn");
const searchInput = el("searchInput");
const searchClearBtn = el("searchClearBtn");
const loadOlderBtn = el("loadOlderBtn");
const refreshPinsBtn = el("refreshPinsBtn");
const exportMdBtn = el("exportMdBtn");
const exportJsonBtn = el("exportJsonBtn");
const exportDocxBtn = el("exportDocxBtn");
const exportPdfBtn = el("exportPdfBtn");
const templateNameInput = el("templateName");
const templateSelect = el("templateSelect");
const saveTemplateBtn = el("saveTemplateBtn");
const insertTemplateBtn = el("insertTemplateBtn");
const suggestionsEl = el("suggestions");
const replyBanner = el("replyBanner");
const replyLabel = el("replyLabel");
const replyClearBtn = el("replyClearBtn");
const commandBtn = el("commandBtn");
const artifactSearchInput = el("artifactSearchInput");
const artifactSearchBtn = el("artifactSearchBtn");
const artifactSuccessFilter = el("artifactSuccessFilter");
const artifactSourceFilter = el("artifactSourceFilter");
const artifactTagFilter = el("artifactTagFilter");
const artifactFilterBtn = el("artifactFilterBtn");
const artifactPreview = el("artifactPreview");
const artifactMeta = el("artifactMeta");
const artifactFiles = el("artifactFiles");
const artifactLeft = el("artifactLeft");
const artifactRight = el("artifactRight");
const artifactDiffBtn = el("artifactDiffBtn");
const artifactDiffAllBtn = el("artifactDiffAllBtn");
const artifactDiffList = el("artifactDiffList");
const archiveSelectedBtn = el("archiveSelectedBtn");
const clearSelectedBtn = el("clearSelectedBtn");
const cleanupKeepRecent = el("cleanupKeepRecent");
const cleanupMaxDays = el("cleanupMaxDays");
const cleanupKeepFailed = el("cleanupKeepFailed");
const cleanupBtn = el("cleanupBtn");
const artifactDiff = el("artifactDiff");
const pluginList = el("pluginList");
const reloadPluginsBtn = el("reloadPluginsBtn");
const statUser = el("statUser");
const statAssistant = el("statAssistant");
const statSystem = el("statSystem");
const statTopics = el("statTopics");
const summaryCard = el("summaryCard");
const metricsSummary = el("metricsSummary");
const metricsSparkline = el("metricsSparkline");
const refreshMetricsBtn = el("refreshMetricsBtn");
const presetStatus = el("presetStatus");
const presetButtons = Array.from(document.querySelectorAll(".preset-btn"));

const statusIndicator = el("statusIndicator");
const statusHint = el("statusHint");
const queueHint = el("queueHint");
const collabCount = el("collabCount");
const sessionIdEl = el("sessionId");
const modelNameEl = el("modelName");
const baseUrlEl = el("baseUrl");
const profileNameEl = el("profileName");
const iterationCountEl = el("iterationCount");
const elapsedTimeEl = el("elapsedTime");
const successRateEl = el("successRate");
const sessionBadge = el("sessionBadge");
const modelBadge = el("modelBadge");
const latencyBadge = el("latencyBadge");
const slotItems = Array.from(document.querySelectorAll(".session-item"));
const railButtons = Array.from(document.querySelectorAll(".rail-btn"));
const themeButtons = Array.from(document.querySelectorAll(".theme-btn"));
const filterButtons = Array.from(document.querySelectorAll(".filter-btn"));
const pinList = el("pinList");
const errorList = el("errorList");
const clearErrorsBtn = el("clearErrorsBtn");
const auditLimitInput = el("auditLimit");
const auditScopeSelect = el("auditScope");
const auditTypeInput = el("auditType");
const refreshAuditBtn = el("refreshAuditBtn");
const exportAuditBtn = el("exportAuditBtn");
const auditList = el("auditList");
const runLogList = el("runLogList");
const clearRunLogBtn = el("clearRunLogBtn");
const projectNotesEl = el("projectNotes");
const longNotesEl = el("longNotes");
const noteTitleInput = el("noteTitle");
const noteContentInput = el("noteContent");
const addProjectNoteBtn = el("addProjectNoteBtn");
const addLongNoteBtn = el("addLongNoteBtn");
const contextSummary = el("contextSummary");
const dedupStats = el("dedupStats");
const refreshContextBtn = el("refreshContextBtn");
const scheduleMode = el("scheduleMode");
const scheduleValue = el("scheduleValue");
const schedulePrompt = el("schedulePrompt");
const addScheduleBtn = el("addScheduleBtn");
const refreshScheduleBtn = el("refreshScheduleBtn");
const scheduleList = el("scheduleList");
const newsTopicInput = el("newsTopicInput");
const newsTimeInput = el("newsTimeInput");
const newsEnabled = el("newsEnabled");
const newsObsidianEnabled = el("newsObsidianEnabled");
const newsObsidianDir = el("newsObsidianDir");
const newsObsidianFile = el("newsObsidianFile");
const saveNewsConfigBtn = el("saveNewsConfigBtn");
const refreshNewsBtn = el("refreshNewsBtn");
const loadNewsBtn = el("loadNewsBtn");
const newsList = el("newsList");
const newsPreview = el("newsPreview");
const mediaAlertInput = el("mediaAlertInput");
const mediaTimeInput = el("mediaTimeInput");
const mediaEnabled = el("mediaEnabled");
const mediaObsidianEnabled = el("mediaObsidianEnabled");
const mediaObsidianDir = el("mediaObsidianDir");
const mediaObsidianFile = el("mediaObsidianFile");
const saveMediaConfigBtn = el("saveMediaConfigBtn");
const refreshMediaBtn = el("refreshMediaBtn");
const loadMediaBtn = el("loadMediaBtn");
const loadMediaSourcesBtn = el("loadMediaSourcesBtn");
const mediaSourcesList = el("mediaSourcesList");
const mediaSourceName = el("mediaSourceName");
const mediaSourcePlatform = el("mediaSourcePlatform");
const mediaSourceType = el("mediaSourceType");
const mediaSourceUrl = el("mediaSourceUrl");
const mediaSourceEnabled = el("mediaSourceEnabled");
const addMediaSourceBtn = el("addMediaSourceBtn");
const mediaSearchInput = el("mediaSearchInput");
const mediaFilterSelect = el("mediaFilterSelect");
const mediaSearchBtn = el("mediaSearchBtn");
const mediaItemTitle = el("mediaItemTitle");
const mediaItemLink = el("mediaItemLink");
const mediaItemSource = el("mediaItemSource");
const addMediaItemBtn = el("addMediaItemBtn");
const mediaAlertList = el("mediaAlertList");
const mediaTrends = el("mediaTrends");
const mediaSavedList = el("mediaSavedList");
const mediaItemList = el("mediaItemList");
const mediaBriefList = el("mediaBriefList");
const mediaBriefPreview = el("mediaBriefPreview");
const refreshMediaBriefsBtn = el("refreshMediaBriefsBtn");
const webhookUrlInput = el("webhookUrlInput");
const webhookHeadersInput = el("webhookHeadersInput");
const webhookPayloadInput = el("webhookPayloadInput");
const sendWebhookBtn = el("sendWebhookBtn");
const webhookLimitInput = el("webhookLimitInput");
const refreshWebhookBtn = el("refreshWebhookBtn");
const clearWebhookBtn = el("clearWebhookBtn");
const webhookLogList = el("webhookLogList");
const artifactList = el("artifactList");
const refreshArtifactsBtn = el("refreshArtifactsBtn");
const configIterations = el("configIterations");
const configMemory = el("configMemory");
const configTemp = el("configTemp");
const configContext = el("configContext");
const applyConfigBtn = el("applyConfigBtn");
const modeFastBtn = el("modeFastBtn");
const modeBalancedBtn = el("modeBalancedBtn");
const modeQualityBtn = el("modeQualityBtn");
const progressFill = el("progressFill");
const progressLabel = el("progressLabel");
const tokenUsage = el("tokenUsage");
const tokenCount = el("tokenCount");
const snapshotLabelInput = el("snapshotLabel");
const createSnapshotBtn = el("createSnapshotBtn");
const refreshSnapshotsBtn = el("refreshSnapshotsBtn");
const snapshotList = el("snapshotList");
const archiveNowBtn = el("archiveNowBtn");
const refreshArchivesBtn = el("refreshArchivesBtn");
const archiveList = el("archiveList");
const kbStatus = el("kbStatus");
const kbPathInput = el("kbPathInput");
const kbIndexBtn = el("kbIndexBtn");
const kbRebuildBtn = el("kbRebuildBtn");
const kbClearBtn = el("kbClearBtn");
const kbSearchInput = el("kbSearchInput");
const kbSearchBtn = el("kbSearchBtn");
const kbResults = el("kbResults");
const kbPreview = el("kbPreview");
const kbAliases = el("kbAliases");
const configModelName = el("configModelName");
const configBaseUrl = el("configBaseUrl");
const configSystemRatio = el("configSystemRatio");
const configHistoryRatio = el("configHistoryRatio");
const configFileRatio = el("configFileRatio");
const configFileChunk = el("configFileChunk");
const configFileMaxChunks = el("configFileMaxChunks");
const configFileMinScore = el("configFileMinScore");
const configFileQueryMessages = el("configFileQueryMessages");
const configHistoryRetrieval = el("configHistoryRetrieval");
const configRetrievalRatio = el("configRetrievalRatio");
const configRetrievalMaxMessages = el("configRetrievalMaxMessages");
const configRetrievalMinScore = el("configRetrievalMinScore");
const configRetrievalQueryMessages = el("configRetrievalQueryMessages");
const configRetrievalRoles = el("configRetrievalRoles");
const configNotesMaxTokens = el("configNotesMaxTokens");
const profileSelect = el("profileSelect");
const applyProfileBtn = el("applyProfileBtn");
const moduleToggleBtn = el("moduleToggleBtn");
const moduleCloseBtn = el("moduleCloseBtn");
const moduleFilter = el("moduleFilter");
const moduleBackdrop = el("moduleBackdrop");
const taskTitleInput = el("taskTitleInput");
const taskStatusInput = el("taskStatusInput");
const taskPriorityInput = el("taskPriorityInput");
const taskTagsInput = el("taskTagsInput");
const taskDueInput = el("taskDueInput");
const taskLinksInput = el("taskLinksInput");
const taskNotesInput = el("taskNotesInput");
const addTaskBtn = el("addTaskBtn");
const refreshTasksBtn = el("refreshTasksBtn");
const taskStats = el("taskStats");
const taskList = el("taskList");
const bookmarkTitleInput = el("bookmarkTitleInput");
const bookmarkUrlInput = el("bookmarkUrlInput");
const bookmarkTagsInput = el("bookmarkTagsInput");
const bookmarkSourceInput = el("bookmarkSourceInput");
const bookmarkNotesInput = el("bookmarkNotesInput");
const addBookmarkBtn = el("addBookmarkBtn");
const refreshBookmarksBtn = el("refreshBookmarksBtn");
const bookmarkList = el("bookmarkList");
const reminderTitleInput = el("reminderTitleInput");
const reminderDueInput = el("reminderDueInput");
const reminderNotesInput = el("reminderNotesInput");
const addReminderBtn = el("addReminderBtn");
const refreshRemindersBtn = el("refreshRemindersBtn");
const reminderLogLimit = el("reminderLogLimit");
const refreshReminderLogsBtn = el("refreshReminderLogsBtn");
const reminderList = el("reminderList");
const reminderLogList = el("reminderLogList");
const focusLabelInput = el("focusLabelInput");
const focusDurationInput = el("focusDurationInput");
const focusNotesInput = el("focusNotesInput");
const startFocusBtn = el("startFocusBtn");
const stopFocusBtn = el("stopFocusBtn");
const focusTimer = el("focusTimer");
const focusList = el("focusList");
const refreshKbMapBtn = el("refreshKbMapBtn");
const kbFolderList = el("kbFolderList");
const kbRecentList = el("kbRecentList");
const workflowTitleInput = el("workflowTitleInput");
const workflowTagsInput = el("workflowTagsInput");
const workflowSpecInput = el("workflowSpecInput");
const addWorkflowBtn = el("addWorkflowBtn");
const updateWorkflowBtn = el("updateWorkflowBtn");
const runWorkflowBtn = el("runWorkflowBtn");
const exportWorkflowBtn = el("exportWorkflowBtn");
const refreshWorkflowBtn = el("refreshWorkflowBtn");
const workflowList = el("workflowList");
const workflowRunLog = el("workflowRunLog");
const artifactTagTaskInput = el("artifactTagTaskInput");
const artifactTagInput = el("artifactTagInput");
const artifactTagNotesInput = el("artifactTagNotesInput");
const saveArtifactTagsBtn = el("saveArtifactTagsBtn");
const removeArtifactTagsBtn = el("removeArtifactTagsBtn");
const refreshArtifactTagsBtn = el("refreshArtifactTagsBtn");
const artifactTagList = el("artifactTagList");
const systemMetrics = el("systemMetrics");
const refreshSystemMetricsBtn = el("refreshSystemMetricsBtn");
const reviewPathInput = el("reviewPathInput");
const reviewTextInput = el("reviewTextInput");
const reviewPathsBtn = el("reviewPathsBtn");
const reviewTextBtn = el("reviewTextBtn");
const reviewList = el("reviewList");
const reviewSummary = el("reviewSummary");
const dataPathInput = el("dataPathInput");
const dataLimitInput = el("dataLimitInput");
const dataCsvInput = el("dataCsvInput");
const dataOpsInput = el("dataOpsInput");
const previewDataBtn = el("previewDataBtn");
const transformDataBtn = el("transformDataBtn");
const dataPreview = el("dataPreview");
const logsLimitInput = el("logsLimitInput");
const refreshLogsBtn = el("refreshLogsBtn");
const logsList = el("logsList");
const refreshTriggerBtn = el("refreshTriggerBtn");
const triggerList = el("triggerList");
const todoPanel = el("todoPanel");
const todoProjectBadge = el("todoProjectBadge");
const todoCountBadge = el("todoCountBadge");
const todoProjectList = el("todoProjectList");
const todoProjectInput = el("todoProjectInput");
const addTodoProjectBtn = el("addTodoProjectBtn");
const todoSmartList = el("todoSmartList");
const todoQuickInput = el("todoQuickInput");
const todoQuickPriority = el("todoQuickPriority");
const todoQuickDue = el("todoQuickDue");
const todoAddBtn = el("todoAddBtn");
const todoTodayList = el("todoTodayList");
const todoUpcomingList = el("todoUpcomingList");
const todoBacklogList = el("todoBacklogList");
const todoBlockedList = el("todoBlockedList");
const todoDoneList = el("todoDoneList");
const todoDetailTitle = el("todoDetailTitle");
const todoDetailStatus = el("todoDetailStatus");
const todoDetailPriority = el("todoDetailPriority");
const todoDetailProject = el("todoDetailProject");
const todoDetailDue = el("todoDetailDue");
const todoDetailTags = el("todoDetailTags");
const todoDetailLinks = el("todoDetailLinks");
const todoDetailNotes = el("todoDetailNotes");
const todoSaveBtn = el("todoSaveBtn");
const todoArchiveBtn = el("todoArchiveBtn");
const todoDeleteBtn = el("todoDeleteBtn");
const todoSearchInput = el("todoSearchInput");
const todoTagFilterInput = el("todoTagFilterInput");
const todoFilterClearBtn = el("todoFilterClearBtn");
const todoCollapseToggles = Array.from(document.querySelectorAll(".todo-collapse-toggle"));
const todoSections = {
  today: todoTodayList,
  upcoming: todoUpcomingList,
  backlog: todoBacklogList,
  blocked: todoBlockedList,
  done: todoDoneList,
};

const pad = (value, size = 2) => String(value).padStart(size, "0");

let historyObserver = null;
let todoDropSlot = null;
const markdownObserver = window.IntersectionObserver
  ? new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const body = entry.target;
      markdownObserver.unobserve(body);
      const raw = body.dataset.raw || "";
      applyMarkdownToBody(body, raw);
    });
  }, { root: chatLog, threshold: 0.15 })
  : null;

function formatTime() {
  const now = new Date();
  return `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}

function shortId(value) {
  if (!value) return "--";
  return value.slice(0, 6) + "..." + value.slice(-4);
}

function truncate(text, limit) {
  if (!text) return "";
  if (text.length <= limit) return text;
  return text.slice(0, Math.max(0, limit - 3)) + "...";
}

function formatListPreview(items, limit = 6) {
  if (!Array.isArray(items) || !items.length) return "--";
  const slice = items.slice(0, limit);
  const suffix = items.length > limit ? " ..." : "";
  return slice.join(", ") + suffix;
}

function parseCsvList(value) {
  if (!value) return [];
  return value
    .split(/[,\\|]+/)
    .map((item) => item.trim())
    .filter((item) => item.length);
}

function parseLines(value) {
  if (!value) return [];
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter((item) => item.length);
}

function formatBytes(value) {
  const num = Number(value);
  if (!Number.isFinite(num) || num <= 0) return "--";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let idx = 0;
  let size = num;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(size >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function formatLocalIso(date, includeSeconds = true) {
  const dt = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(dt.getTime())) return "";
  const base = `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
  if (!includeSeconds) return base;
  return `${base}:${pad(dt.getSeconds())}`;
}

const MODULE_GROUP_MAP = {
  "RUN LOG": "ops",
  "DASHBOARD": "system",
  "PRESETS": "system",
  "CONTEXT SNAPSHOT": "memory",
  "QUICK TIPS": "memory",
  "PIN BOARD": "memory",
  "ERROR LOG": "ops",
  "AUDIT LOG": "ops",
  "MEMORY NOTES": "memory",
  "MEMORY CONTROL": "memory",
  "SCHEDULE": "automation",
  "NEWS DIGEST": "media",
  "MEDIA HUB": "media",
  "MEDIA FEED": "media",
  "MEDIA BRIEFS": "media",
  "WEBHOOK CENTER": "ops",
  "ARTIFACTS": "ops",
  "ANALYTICS": "insights",
  "PLUGINS": "system",
  "CONFIG PANEL": "system",
  "KNOWLEDGE BASE": "knowledge",
  "TASK BOARD": "automation",
  "BOOKMARK VAULT": "personal",
  "REMINDER CENTER": "automation",
  "FOCUS SESSIONS": "personal",
  "KNOWLEDGE MAP": "knowledge",
  "WORKFLOW TEMPLATES": "automation",
  "ARTIFACT TAGS": "ops",
  "SYSTEM MONITOR": "ops",
  "CODE REVIEW": "labs",
  "DATA LAB": "labs",
  "LOGS CENTER": "ops",
  "TRIGGER WATCH": "automation",
};

let moduleCards = [];

function initModuleDock() {
  const cards = Array.from(document.querySelectorAll(".side-panel .panel-card"));
  moduleCards = cards.filter((card) => card.dataset.module !== "primary" && card.dataset.module !== "dock");
  moduleCards.forEach((card) => {
    card.classList.add("module-section");
    const title = (card.querySelector("h3")?.textContent || "").trim().toUpperCase();
    card.dataset.group = MODULE_GROUP_MAP[title] || "misc";
  });
  applyModuleFilter();
}

function setModulesOpen(open) {
  document.body.classList.toggle("modules-open", open);
  if (open && moduleFilter && !moduleFilter.value) {
    moduleFilter.value = "all";
  }
  if (open) {
    applyModuleFilter();
  }
}

function applyModuleFilter() {
  if (!moduleFilter || !moduleCards.length) return;
  const filter = moduleFilter.value || "all";
  moduleCards.forEach((card) => {
    const groupRaw = card.dataset.group || "misc";
    const groups = groupRaw.split(",").map((item) => item.trim());
    const show = filter === "all" || groups.includes(filter);
    card.style.display = show ? "" : "none";
  });
}

function setRailActive(action) {
  railButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.action === action);
  });
}

function setMainView(view) {
  state.mainView = view;
  document.body.classList.toggle("view-todo", view === "todo");
  if (view === "todo") {
    loadTasks();
  }
}

function safeParseJson(value) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch (err) {
    return null;
  }
}

function createClientId() {
  if (window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `client_${Math.random().toString(16).slice(2)}_${Date.now()}`;
}

function initClientId() {
  const stored = localStorage.getItem(clientKey);
  state.clientId = stored || createClientId();
  localStorage.setItem(clientKey, state.clientId);
}

function loadTemplates() {
  try {
    state.templates = JSON.parse(localStorage.getItem(templateKey) || "[]");
  } catch (err) {
    state.templates = [];
  }
  renderTemplateSelect();
}

function saveTemplates() {
  localStorage.setItem(templateKey, JSON.stringify(state.templates));
}

function renderTemplateSelect() {
  if (!templateSelect) return;
  templateSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select template";
  templateSelect.appendChild(placeholder);
  state.templates.forEach((tpl) => {
    const option = document.createElement("option");
    option.value = tpl.name;
    option.textContent = tpl.name;
    templateSelect.appendChild(option);
  });
}

function loadErrors() {
  try {
    state.errors = JSON.parse(localStorage.getItem(errorKey) || "[]");
  } catch (err) {
    state.errors = [];
  }
  renderErrors();
}

function saveErrors() {
  localStorage.setItem(errorKey, JSON.stringify(state.errors));
}

function setStatus(text, tone = "ready") {
  statusIndicator.textContent = text;
  statusIndicator.dataset.tone = tone;
  if (tone === "busy") {
    statusHint.textContent = "Agent engaged";
    queueHint.textContent = "Queue locked";
  } else {
    statusHint.textContent = "Signal stable";
    queueHint.textContent = "Queue normal";
  }
}

function addError(message) {
  if (!message) return;
  state.errors.unshift({ message, time: formatTime() });
  if (state.errors.length > 30) {
    state.errors = state.errors.slice(0, 30);
  }
  saveErrors();
  renderErrors();
}

function clearErrors() {
  state.errors = [];
  saveErrors();
  renderErrors();
}

function renderErrors() {
  if (!errorList) return;
  errorList.innerHTML = "";
  if (!state.errors.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No errors yet.";
    errorList.appendChild(empty);
    return;
  }
  state.errors.forEach((entry) => {
    const item = document.createElement("div");
    item.className = "list-item error";
    item.innerHTML = `<strong>${entry.time}</strong> ${entry.message}`;
    errorList.appendChild(item);
  });
}

function loadPresetState() {
  state.lastPreset = localStorage.getItem(presetKey) || "";
  updatePresetStatus();
}

function updatePresetStatus() {
  if (presetStatus) {
    presetStatus.textContent = state.lastPreset
      ? `Active preset: ${state.lastPreset.toUpperCase()}`
      : "No preset applied.";
  }
  presetButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.preset === state.lastPreset);
  });
}

async function applyPreset(name) {
  const preset = (name || "").trim().toLowerCase();
  if (!preset) return;
  try {
    await postJson("/api/preset", { name: preset });
    state.lastPreset = preset;
    localStorage.setItem(presetKey, preset);
    updatePresetStatus();
    renderMessage("system", `Preset applied: ${preset.toUpperCase()}.`, { skipStore: true });
    await loadConfig();
    await loadInfo();
  } catch (err) {
    addError(`Preset apply failed: ${err.message}`);
  }
}

function setDashboardStatus(url, running) {
  state.dashboardUrl = url || "";
  if (!dashboardStatus) return;
  if (!url) {
    dashboardStatus.textContent = "Not running.";
    return;
  }
  const label = running ? "RUNNING" : "READY";
  const safeUrl = escapeHtml(url);
  dashboardStatus.innerHTML = `${label}: <a href="${safeUrl}" target="_blank" rel="noopener">${safeUrl}</a>`;
}

async function loadDashboardStatus() {
  if (!dashboardStatus) return;
  try {
    const data = await fetchJson("/api/dashboard?start=0");
    setDashboardStatus(data.url, data.running);
  } catch (err) {
    setDashboardStatus("", false);
  }
}

async function copyDashboardLink() {
  if (!state.dashboardUrl) {
    renderMessage("system", "No dashboard link yet.", { skipStore: true });
    return;
  }
  const ok = await copyToClipboard(state.dashboardUrl);
  if (ok) {
    renderMessage("system", "Dashboard link copied.", { skipStore: true });
  } else {
    addError("Dashboard copy failed.");
  }
}

function formatAuditTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function buildAuditSummary(entry) {
  if (!entry || typeof entry !== "object") return "--";
  const parts = [];
  if (entry.session_id) parts.push(`SESSION ${shortId(entry.session_id)}`);
  if (entry.task_id) parts.push(`TASK ${entry.task_id}`);
  if (entry.schedule_id) parts.push(`SCHEDULE ${entry.schedule_id}`);
  if (entry.preset) parts.push(`PRESET ${entry.preset}`);
  if (entry.command) parts.push(`CMD ${entry.command}`);
  if (entry.success === true) parts.push("OK");
  if (entry.success === false) parts.push("FAIL");
  if (entry.cancelled) parts.push("CANCELLED");
  if (entry.error) parts.push(`ERROR ${truncate(entry.error, 120)}`);
  if (entry.message) parts.push(truncate(entry.message, 120));
  if (Array.isArray(entry.args) && entry.args.length) {
    parts.push(`ARGS ${truncate(entry.args.join(" "), 120)}`);
  }
  if (!parts.length) return "--";
  return parts.map((part) => escapeHtml(String(part))).join(" | ");
}

function renderAuditLogs(entries, emptyMessage) {
  if (!auditList) return;
  auditList.innerHTML = "";
  if (!Array.isArray(entries) || !entries.length) {
    const empty = document.createElement("div");
    empty.className = "list-item audit-item";
    empty.textContent = emptyMessage || "No audit entries.";
    auditList.appendChild(empty);
    return;
  }
  entries.forEach((entry) => {
    const item = document.createElement("div");
    item.className = "list-item audit-item";
    if (entry && entry.raw) {
      item.textContent = entry.raw;
      auditList.appendChild(item);
      return;
    }
    const type = String(entry.type || "event").toUpperCase();
    const stamp = formatAuditTime(entry.timestamp);
    const summary = buildAuditSummary(entry);
    item.innerHTML = `<strong>${escapeHtml(type)}</strong> <span class="audit-meta">${escapeHtml(stamp)}</span><br>${summary}`;
    auditList.appendChild(item);
  });
}

async function loadAuditLogs() {
  if (!auditList) return;
  const limitRaw = auditLimitInput ? auditLimitInput.value : "";
  const parsed = parseInt(limitRaw || "50", 10);
  const limit = Number.isNaN(parsed) ? 50 : Math.max(1, parsed);
  const scope = auditScopeSelect ? auditScopeSelect.value : "session";
  const typeFilter = auditTypeInput ? auditTypeInput.value.trim().toLowerCase() : "";
  if (scope === "session" && !state.sessionId) {
    renderAuditLogs([], "No session selected.");
    return;
  }
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (scope === "session" && state.sessionId) {
    params.set("session_id", state.sessionId);
  }
  try {
    const data = await fetchJson(`/api/audit?${params.toString()}`);
    let entries = data.entries || [];
    if (typeFilter) {
      entries = entries.filter((entry) => String(entry.type || "").toLowerCase().includes(typeFilter));
    }
    renderAuditLogs(entries);
  } catch (err) {
    renderAuditLogs([], "Audit load failed.");
    addError(`Audit load failed: ${err.message}`);
  }
}

function exportAuditLogs() {
  if (!auditList) return;
  const items = Array.from(auditList.querySelectorAll(".list-item")).map((item) => item.textContent || "");
  const payload = items.join("\n");
  downloadText(payload, `sama_audit_${Date.now()}.txt`);
}

function getDraftKey() {
  if (state.sessionId) {
    return `${draftKey}_${state.sessionId}`;
  }
  return draftKey;
}

function loadDraft() {
  if (!messageInput) return;
  const stored = localStorage.getItem(getDraftKey()) || "";
  if (!messageInput.value) {
    messageInput.value = stored;
  }
}

function saveDraft(value) {
  localStorage.setItem(getDraftKey(), value || "");
}

function clearDraft() {
  localStorage.removeItem(getDraftKey());
}

function addRunLog(label, detail) {
  const item = {
    time: formatTime(),
    label: label || "EVENT",
    detail: detail || "",
  };
  state.runLog.unshift(item);
  if (state.runLog.length > 40) {
    state.runLog = state.runLog.slice(0, 40);
  }
  renderRunLog();
}

function renderRunLog() {
  if (!runLogList) return;
  runLogList.innerHTML = "";
  if (!state.runLog.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No run events yet.";
    runLogList.appendChild(empty);
    return;
  }
  state.runLog.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${entry.time}</strong> ${escapeHtml(entry.label)}<br>${escapeHtml(entry.detail)}`;
    runLogList.appendChild(row);
  });
}

function clearRunLog() {
  state.runLog = [];
  renderRunLog();
}

function buildSparkline(values, width = 240, height = 48) {
  const points = values.filter((value) => typeof value === "number" && !Number.isNaN(value));
  if (!points.length) {
    return `<div class="sparkline-empty">No data</div>`;
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
    <svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <polyline points="${path}" fill="none" stroke="currentColor" stroke-width="2" />
    </svg>
  `;
}

function renderMetrics(data) {
  if (metricsSummary) {
    const summary = (data && data.summary) || {};
    const lines = [
      `Total calls: ${summary.total_calls ?? 0}`,
      `Success: ${summary.success ?? 0}`,
      `Errors: ${summary.error ?? 0}`,
      `Timeout: ${summary.timeout ?? 0}`,
      `Avg time: ${(summary.avg_time ?? 0).toFixed(2)}s`,
      `Error rate: ${((summary.error_rate ?? 0) * 100).toFixed(1)}%`,
    ];
    metricsSummary.innerHTML = lines.map((line) => `<div class="list-item">${line}</div>`).join("");
  }
}

async function loadMetrics() {
  if (!metricsSummary || !metricsSparkline) return;
  try {
    const data = await fetchJson("/api/metrics");
    renderMetrics(data.metrics || {});
    const recent = (data.recent || []).map((item) => Number(item.execution_time || 0)).filter((value) => value > 0);
    metricsSparkline.innerHTML = buildSparkline(recent);
  } catch (err) {
    if (metricsSummary) {
      metricsSummary.innerHTML = `<div class="list-item">Metrics unavailable.</div>`;
    }
    if (metricsSparkline) {
      metricsSparkline.innerHTML = `<div class="sparkline-empty">No data</div>`;
    }
    addError(`Metrics load failed: ${err.message}`);
  }
}

function setBusy(isBusy) {
  state.busy = isBusy;
  sendBtn.disabled = isBusy;
  messageInput.disabled = isBusy;
  if (stopBtn) stopBtn.disabled = !isBusy;
  if (continueBtn) continueBtn.disabled = isBusy;
  setStatus(isBusy ? "BUSY" : "READY", isBusy ? "busy" : "ready");
}

async function copyToClipboard(text) {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    return false;
  }
}

function updateReplyBanner() {
  if (!replyBanner || !replyLabel) return;
  if (!state.replyTarget) {
    replyBanner.classList.remove("active");
    replyLabel.textContent = "Replying to --";
    return;
  }
  replyBanner.classList.add("active");
  replyLabel.textContent = formatReplyLabel(state.replyTarget);
}

function formatReplyLabel(reply) {
  if (!reply) return "Replying to --";
  const role = reply.role ? reply.role.toUpperCase() : "MESSAGE";
  const summary = truncate(reply.content || "", 120);
  return `Replying to ${role}: ${summary || "--"}`;
}

function setReplyTarget(target) {
  if (!target) return;
  state.replyTarget = {
    role: target.role || "message",
    content: target.content || "",
    time: target.time || "",
    messageId: target.messageId || null,
  };
  updateReplyBanner();
}

function clearReplyTarget() {
  state.replyTarget = null;
  updateReplyBanner();
}

function buildReplyContext(reply, text) {
  if (!reply) return text;
  const role = reply.role ? reply.role.toUpperCase() : "MESSAGE";
  const stamp = reply.time || "--";
  const snippet = truncate(reply.content || "", 240);
  return `Reply context [${role} ${stamp}]: ${snippet}\n\n${text}`;
}

function jumpToMessage(messageId) {
  if (!messageId) return;
  const target = chatLog.querySelector(`[data-message-id="${messageId}"]`);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
}

function setMessageRating(messageId, rating) {
  if (!state.sessionId || !messageId) return;
  const items = getTranscriptItems(state.sessionId);
  const target = items.find((item) => item.messageId === messageId);
  if (!target) return;
  target.rating = rating;
  saveTranscripts();
}

function applyRatingState(wrapper, rating) {
  if (!wrapper) return;
  const up = wrapper.querySelector("[data-rating='up']");
  const down = wrapper.querySelector("[data-rating='down']");
  if (up) up.classList.toggle("active", rating === 1);
  if (down) down.classList.toggle("active", rating === -1);
}

function ensurePinButton(wrapper, messageId) {
  if (!wrapper || !messageId) return;
  if (wrapper.querySelector(".message-pin")) return;
  const pinBtn = document.createElement("button");
  pinBtn.className = "message-pin";
  pinBtn.textContent = state.pins.includes(messageId) ? "UNPIN" : "PIN";
  pinBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    togglePin(messageId, wrapper);
  });
  wrapper.appendChild(pinBtn);
}

function ensureRatingButtons(wrapper, messageId) {
  if (!wrapper || !messageId) return;
  const actions = wrapper.querySelector(".message-actions");
  if (!actions) return;
  if (actions.querySelector("[data-rating='up']")) return;
  const upBtn = document.createElement("button");
  upBtn.textContent = "UP";
  upBtn.dataset.rating = "up";
  upBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleRating(messageId, 1, wrapper);
  });
  const downBtn = document.createElement("button");
  downBtn.textContent = "DOWN";
  downBtn.dataset.rating = "down";
  downBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleRating(messageId, -1, wrapper);
  });
  actions.appendChild(upBtn);
  actions.appendChild(downBtn);
  applyRatingState(wrapper, 0);
}

function toggleRating(messageId, value, wrapper) {
  if (!messageId) return;
  const items = getTranscriptItems(state.sessionId);
  const target = items.find((item) => item.messageId === messageId);
  const current = target ? target.rating || 0 : 0;
  const next = current === value ? 0 : value;
  setMessageRating(messageId, next);
  applyRatingState(wrapper, next);
}

function buildPreviewContent(content, limit = COLLAPSE_LIMIT) {
  if (!content) return "";
  if (content.length <= limit) return content;
  return content.slice(0, limit) + "\n\n...(truncated)";
}

function applyMarkdownToBody(body, content) {
  if (!body) return;
  body.classList.add("markdown");
  body.innerHTML = renderMarkdown(autoSegmentText(content || ""));
  renderMath(body);
  enhanceCodeBlocks(body);
  body.dataset.markdownPending = "false";
}

function observeMarkdown(body, content) {
  if (!body) return;
  body.dataset.raw = content || "";
  body.dataset.markdownPending = "true";
  if (!markdownObserver) {
    applyMarkdownToBody(body, content);
    return;
  }
  markdownObserver.observe(body);
}

function renderMessageBody(body, content, useMarkdown, options = {}) {
  if (!body) return;
  if (useMarkdown) {
    if (options.deferMarkdown) {
      body.textContent = content || "";
      observeMarkdown(body, content || "");
    } else {
      applyMarkdownToBody(body, content || "");
    }
  } else {
    body.textContent = content || "";
  }
}

function attachCollapseControl(wrapper, content, useMarkdown, limit = COLLAPSE_LIMIT, deferMarkdown = false) {
  if (!wrapper || !useMarkdown || !content || content.length <= limit) return;
  if (wrapper.dataset.hasAttachments === "true") return;
  const actions = wrapper.querySelector(".message-actions");
  const body = wrapper.querySelector(".message-body");
  if (!actions || !body) return;
  if (actions.querySelector(".message-collapse")) return;
  const preview = buildPreviewContent(content, limit);
  wrapper.dataset.fullContent = content;
  wrapper.dataset.previewContent = preview;
  wrapper.dataset.collapsed = "true";
  renderMessageBody(body, preview, useMarkdown, { deferMarkdown });
  const toggleBtn = document.createElement("button");
  toggleBtn.className = "message-collapse";
  toggleBtn.textContent = "EXPAND";
  toggleBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    const collapsed = wrapper.dataset.collapsed === "true";
    const nextContent = collapsed ? wrapper.dataset.fullContent : wrapper.dataset.previewContent;
    renderMessageBody(body, nextContent, useMarkdown, { deferMarkdown: false });
    wrapper.dataset.collapsed = collapsed ? "false" : "true";
    toggleBtn.textContent = collapsed ? "COLLAPSE" : "EXPAND";
  });
  actions.appendChild(toggleBtn);
}

function renderMessage(role, content, options = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  wrapper.dataset.role = role;
  const stamp = options.time || formatTime();
  const messageId = options.messageId || null;
  if (messageId) {
    wrapper.dataset.messageId = messageId;
  }
  wrapper.dataset.time = stamp;
  if (options.typing) {
    wrapper.classList.add("typing");
    wrapper.dataset.typing = "true";
  }
  if (options.pinned) {
    wrapper.classList.add("pinned");
  }
  if (Array.isArray(options.attachments) && options.attachments.length > 0) {
    wrapper.dataset.hasAttachments = "true";
  }

  const meta = document.createElement("div");
  meta.className = "message-meta";
  const label = role === "user" ? "USER" : role === "assistant" ? "SAMA" : "SYSTEM";
  meta.innerHTML = `<span>${label}</span><span>${stamp}</span>`;

  const body = document.createElement("div");
  body.className = "message-body";
  const useMarkdown = role === "assistant" && options.markdown !== false;
  renderMessageBody(body, content, useMarkdown, { deferMarkdown: options.deferMarkdown === true });

  wrapper.appendChild(meta);
  if (options.reply) {
    const reply = document.createElement("div");
    reply.className = "message-reply";
    reply.textContent = formatReplyLabel(options.reply);
    if (options.reply.messageId) {
      reply.addEventListener("click", () => jumpToMessage(options.reply.messageId));
    }
    wrapper.appendChild(reply);
  }
  wrapper.appendChild(body);
  if (options.attachments) {
    renderAttachments(wrapper, options.attachments);
  }
  if (role === "assistant" && messageId) {
    const pinBtn = document.createElement("button");
    pinBtn.className = "message-pin";
    pinBtn.textContent = options.pinned ? "UNPIN" : "PIN";
    pinBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      togglePin(messageId, wrapper);
    });
    wrapper.appendChild(pinBtn);
  }
  if (role !== "system") {
    const actions = document.createElement("div");
    actions.className = "message-actions";
    const replyBtn = document.createElement("button");
    replyBtn.textContent = "REPLY";
    replyBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      setReplyTarget({ role, content, time: stamp, messageId });
      messageInput.focus();
    });
    const copyAction = document.createElement("button");
    copyAction.textContent = "COPY";
    copyAction.addEventListener("click", async (event) => {
      event.stopPropagation();
      const ok = await copyToClipboard(content || "");
      if (ok) {
        renderMessage("system", "Message copied.", { skipStore: true });
      } else {
        addError("Copy failed.");
      }
    });
    actions.appendChild(replyBtn);
    actions.appendChild(copyAction);
    if (role === "assistant" && messageId) {
      const upBtn = document.createElement("button");
      upBtn.textContent = "UP";
      upBtn.dataset.rating = "up";
      upBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleRating(messageId, 1, wrapper);
      });
      const downBtn = document.createElement("button");
      downBtn.textContent = "DOWN";
      downBtn.dataset.rating = "down";
      downBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleRating(messageId, -1, wrapper);
      });
      actions.appendChild(upBtn);
      actions.appendChild(downBtn);
    }
    wrapper.appendChild(actions);
    if (role === "assistant" && messageId) {
      applyRatingState(wrapper, options.rating || 0);
    }
  }
  if (role === "assistant") {
    attachCollapseControl(wrapper, content || "", useMarkdown, COLLAPSE_LIMIT, options.deferMarkdown === true);
  }
  const target = options.container || chatLog;
  if (target) {
    target.appendChild(wrapper);
  }
  if (!options.noScroll && target === chatLog) {
    chatLog.scrollTop = chatLog.scrollHeight;
  }
  if (!options.skipStore) {
    storeMessage(role, content, stamp, messageId, options.pinned, options.reply, options.rating, options.attachments);
  }
  return wrapper;
}

function renderMarkdown(raw) {
  if (!raw) return "";
  let text = raw.replace(/\r\n/g, "\n");
  const codeBlocks = [];

  text = text.replace(/```([\w-]+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    const token = `@@CODEBLOCK${codeBlocks.length}@@`;
    codeBlocks.push({ lang: (lang || "").trim(), code });
    return token;
  });

  text = escapeHtml(text);

  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  text = text.replace(/(^|[^*])\*([^*]+)\*([^*]|$)/g, "$1<em>$2</em>$3");
  text = text.replace(/(^|[^_])_([^_]+)_([^_]|$)/g, "$1<em>$2</em>$3");
  text = text.replace(/~~([^~]+)~~/g, "<del>$1</del>");
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, url) => {
    const safeUrl = sanitizeUrl(url);
    return `<a href="${safeUrl}" target="_blank" rel="noopener">${label}</a>`;
  });

  const lines = text.split("\n");
  const blocks = [];
  let listType = null;
  let inQuote = false;

  const closeList = () => {
    if (listType) {
      blocks.push(listType === "ol" ? "</ol>" : "</ul>");
      listType = null;
    }
  };

  const closeQuote = () => {
    if (inQuote) {
      blocks.push("</blockquote>");
      inQuote = false;
    }
  };

  const isTableRow = (line) => line.includes("|");
  const parseTableRow = (line) => {
    return line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell) => cell.trim());
  };
  const isTableSeparator = (line) => {
    const trimmed = line.trim();
    if (!trimmed.includes("-")) {
      return false;
    }
    const parts = trimmed
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell) => cell.trim());
    if (parts.length < 2) {
      return false;
    }
    return parts.every((cell) => /^:?-{3,}:?$/.test(cell));
  };
  const parseAlignment = (line, size) => {
    const parts = line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell) => cell.trim());
    const alignments = [];
    for (let i = 0; i < size; i += 1) {
      const cell = parts[i] || "";
      if (cell.startsWith(":") && cell.endsWith(":")) {
        alignments.push("center");
      } else if (cell.endsWith(":")) {
        alignments.push("right");
      } else if (cell.startsWith(":")) {
        alignments.push("left");
      } else {
        alignments.push("left");
      }
    }
    return alignments;
  };
  const buildTable = (headers, alignments, rows) => {
    const columnCount = Math.max(
      headers.length,
      ...rows.map((row) => row.length),
      1
    );
    const padRow = (row) => {
      const padded = row.slice(0, columnCount);
      while (padded.length < columnCount) {
        padded.push("");
      }
      return padded;
    };
    const headerCells = padRow(headers);
    const bodyRows = rows.map(padRow);
    let html = "<table><thead><tr>";
    headerCells.forEach((cell, idx) => {
      const alignClass = alignments[idx] ? ` class="align-${alignments[idx]}"` : "";
      html += `<th${alignClass}>${cell}</th>`;
    });
    html += "</tr></thead>";
    if (bodyRows.length) {
      html += "<tbody>";
      bodyRows.forEach((row) => {
        html += "<tr>";
        row.forEach((cell, idx) => {
          const alignClass = alignments[idx] ? ` class="align-${alignments[idx]}"` : "";
          html += `<td${alignClass}>${cell}</td>`;
        });
        html += "</tr>";
      });
      html += "</tbody>";
    }
    html += "</table>";
    return html;
  };

  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      closeQuote();
      index += 1;
      continue;
    }

    if (/^@@CODEBLOCK\d+@@$/.test(trimmed)) {
      closeList();
      closeQuote();
      blocks.push(trimmed);
      index += 1;
      continue;
    }

    if (isTableRow(trimmed) && index + 1 < lines.length && isTableSeparator(lines[index + 1])) {
      const headers = parseTableRow(trimmed);
      if (headers.length > 1) {
        closeList();
        closeQuote();
        const alignments = parseAlignment(lines[index + 1], headers.length);
        const rows = [];
        index += 2;
        while (index < lines.length) {
          const nextLine = lines[index];
          const nextTrim = nextLine.trim();
          if (!nextTrim) {
            break;
          }
          if (/^@@CODEBLOCK\d+@@$/.test(nextTrim)) {
            break;
          }
          if (!isTableRow(nextTrim)) {
            break;
          }
          rows.push(parseTableRow(nextLine));
          index += 1;
        }
        blocks.push(buildTable(headers, alignments, rows));
        continue;
      }
    }

    if (/^#{1,6}\s+/.test(trimmed)) {
      closeList();
      closeQuote();
      const level = trimmed.match(/^#{1,6}/)[0].length;
      const content = trimmed.replace(/^#{1,6}\s+/, "");
      blocks.push(`<h${level}>${content}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^>\s+/.test(trimmed)) {
      if (!inQuote) {
        closeList();
        blocks.push("<blockquote>");
        inQuote = true;
      }
      blocks.push(`<p>${trimmed.replace(/^>\s+/, "")}</p>`);
      index += 1;
      continue;
    }

    const ulMatch = trimmed.match(/^[-*]\s+/);
    const olMatch = trimmed.match(/^\d+\.\s+/);
    if (ulMatch || olMatch) {
      const itemText = trimmed.replace(/^([-*]|\d+\.)\s+/, "");
      const taskMatch = itemText.match(/^\[( |x|X)\]\s+(.*)/);
      const nextType = taskMatch ? "task" : (olMatch ? "ol" : "ul");
      if (listType && listType !== nextType) {
        closeList();
      }
      if (!listType) {
        if (nextType === "ol") {
          blocks.push("<ol>");
        } else if (nextType === "task") {
          blocks.push('<ul class="task-list">');
        } else {
          blocks.push("<ul>");
        }
        listType = nextType;
      }
      if (taskMatch) {
        const checked = taskMatch[1].toLowerCase() === "x";
        const label = taskMatch[2];
        const checkbox = `<input type="checkbox" ${checked ? "checked" : ""} disabled />`;
        blocks.push(`<li class="task-item">${checkbox}<span>${label}</span></li>`);
      } else {
        blocks.push(`<li>${itemText}</li>`);
      }
      index += 1;
      continue;
    }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      closeList();
      closeQuote();
      blocks.push("<hr />");
      index += 1;
      continue;
    }

    closeList();
    closeQuote();
    blocks.push(`<p>${trimmed}</p>`);
    index += 1;
  }

  closeList();
  closeQuote();

  let html = blocks.join("\n");
  codeBlocks.forEach((block, idx) => {
    const token = `@@CODEBLOCK${idx}@@`;
    const langClass = block.lang ? ` class="language-${escapeHtml(block.lang)}"` : "";
    const safeCode = escapeHtml(block.code);
    const codeHtml = `<pre><code${langClass}>${safeCode}</code></pre>`;
    html = html.replace(token, codeHtml);
  });

  return html;
}

function autoSegmentText(text) {
  if (!text) return "";
  if (text.includes("```")) return text;
  if (text.includes("\n\n")) return text;
  if (text.length < 280) return text;
  const parts = text.split(/(?<=[.!?。！？])\s+/);
  if (parts.length <= 1) {
    return text;
  }
  return parts.join("\n\n");
}

function renderMath(container) {
  if (typeof window.renderMathInElement !== "function") {
    return;
  }
  window.renderMathInElement(container, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false },
    ],
    throwOnError: false,
    ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"],
  });
}

function enhanceCodeBlocks(container) {
  if (!container) return;
  const blocks = Array.from(container.querySelectorAll("pre"));
  blocks.forEach((pre) => {
    const parent = pre.parentElement;
    if (parent && parent.classList.contains("code-block")) {
      return;
    }
    const code = pre.querySelector("code");
    if (code && window.hljs && !code.dataset.highlighted) {
      const highlight = () => {
        window.hljs.highlightElement(code);
        code.dataset.highlighted = "true";
      };
      if (window.requestIdleCallback) {
        window.requestIdleCallback(highlight);
      } else {
        setTimeout(highlight, 0);
      }
    }
    const wrapper = document.createElement("div");
    wrapper.className = "code-block";
    const header = document.createElement("div");
    header.className = "code-block-header";
    const label = document.createElement("span");
    label.className = "code-block-label";
    let lang = "";
    if (code && code.className) {
      const match = code.className.match(/language-([a-z0-9_-]+)/i);
      if (match) {
        lang = match[1].toUpperCase();
      }
    }
    label.textContent = lang ? `CODE: ${lang}` : "CODE";
    const actionGroup = document.createElement("div");
    actionGroup.className = "code-block-actions";
    const copyBtn = document.createElement("button");
    copyBtn.className = "mini ghost";
    copyBtn.textContent = "COPY";
    copyBtn.addEventListener("click", async (event) => {
      event.stopPropagation();
      const text = code ? code.textContent || "" : pre.textContent || "";
      const ok = await copyToClipboard(text.trim());
      if (!ok) {
        addError("Code copy failed.");
      }
    });
    const foldBtn = document.createElement("button");
    foldBtn.className = "mini ghost";
    foldBtn.textContent = "FOLD";
    foldBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      wrapper.classList.toggle("collapsed");
      foldBtn.textContent = wrapper.classList.contains("collapsed") ? "EXPAND" : "FOLD";
    });
    actionGroup.appendChild(copyBtn);
    actionGroup.appendChild(foldBtn);
    header.appendChild(label);
    header.appendChild(actionGroup);
    if (pre.parentElement) {
      pre.parentElement.insertBefore(wrapper, pre);
      wrapper.appendChild(header);
      wrapper.appendChild(pre);
    }
  });
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sanitizeUrl(value) {
  const trimmed = (value || "").trim();
  if (!trimmed) {
    return "#";
  }
  if (trimmed.startsWith("#")) {
    return trimmed;
  }
  try {
    const parsed = new URL(trimmed, window.location.href);
    if (["http:", "https:", "mailto:"].includes(parsed.protocol)) {
      return parsed.href;
    }
  } catch (err) {
    return "#";
  }
  return "#";
}

function detectLanguageFromFile(name) {
  const ext = (name || "").split(".").pop().toLowerCase();
  const map = {
    js: "javascript",
    ts: "typescript",
    py: "python",
    json: "json",
    md: "markdown",
    yaml: "yaml",
    yml: "yaml",
    html: "html",
    css: "css",
    sh: "bash",
    txt: "plaintext",
  };
  return map[ext] || "";
}

const commandHints = [
  { label: "/help", insert: "/help" },
  { label: "/reset", insert: "/reset" },
  { label: "/new", insert: "/new" },
  { label: "/pin", insert: "/pin" },
  { label: "/unpin all", insert: "/unpin all" },
  { label: "/search <query>", insert: "/search " },
  { label: "/note project <title> :: <content>", insert: "/note project " },
  { label: "/note long <title> :: <content>", insert: "/note long " },
  { label: "/docx <title> :: <content>", insert: "/docx " },
  { label: "/pdf <title> :: <content>", insert: "/pdf " },
  { label: "/kb search <query>", insert: "/kb search " },
  { label: "/workflow <path>", insert: "/workflow " },
  { label: "/schedule list", insert: "/schedule list" },
  { label: "/mode fast", insert: "/mode fast" },
  { label: "/mode balanced", insert: "/mode balanced" },
  { label: "/mode quality", insert: "/mode quality" },
  { label: "/snapshot <label>", insert: "/snapshot " },
  { label: "/rollback <snapshot_id>", insert: "/rollback " },
  { label: "/plugins", insert: "/plugins" },
  { label: "/reload", insert: "/reload" },
  { label: "/config", insert: "/config" },
  { label: "/dashboard", insert: "/dashboard" },
];

const topicStopWords = new Set([
  "the", "and", "for", "with", "that", "this", "from", "have", "will", "would",
  "there", "their", "about", "your", "you", "are", "was", "were", "what", "when",
  "where", "which", "who", "why", "how", "can", "could", "should", "into", "over",
  "after", "before", "than", "then", "them", "they", "she", "him", "her", "his",
  "our", "out", "not", "but", "use", "using", "make", "made", "more", "most",
  "just", "like", "also", "only", "each", "per", "etc"
]);

function updateSuggestions() {
  if (!suggestionsEl) return;
  const value = messageInput.value.trim();
  if (!value.startsWith("/")) {
    suggestionsEl.classList.remove("active");
    suggestionsEl.innerHTML = "";
    return;
  }
  const keyword = value.slice(1).toLowerCase();
  const matches = commandHints.filter((item) => item.label.toLowerCase().includes(keyword));
  suggestionsEl.innerHTML = "";
  if (!matches.length) {
    suggestionsEl.classList.remove("active");
    return;
  }
  matches.slice(0, 6).forEach((item) => {
    const row = document.createElement("div");
    row.className = "suggestions-item";
    row.innerHTML = `<strong>${item.label}</strong>`;
    row.addEventListener("click", () => {
      messageInput.value = item.insert + " ";
      messageInput.focus();
      suggestionsEl.classList.remove("active");
      suggestionsEl.innerHTML = "";
    });
    suggestionsEl.appendChild(row);
  });
  suggestionsEl.classList.add("active");
}

function openCommandPalette() {
  if (!messageInput || !suggestionsEl) return;
  const current = messageInput.value.trim();
  if (suggestionsEl.classList.contains("active") && current.startsWith("/")) {
    suggestionsEl.classList.remove("active");
    suggestionsEl.innerHTML = "";
    return;
  }
  if (!current.startsWith("/")) {
    messageInput.value = "/";
  }
  messageInput.focus();
  updateSuggestions();
}

function removeTyping() {
  const typing = chatLog.querySelector(".message.typing");
  if (typing) {
    typing.remove();
  }
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}

async function postJson(url, body) {
  return fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

async function loadInfo() {
  try {
    const data = await fetchJson("/api/info");
    modelNameEl.textContent = data.model_name || "--";
    baseUrlEl.textContent = data.base_url || "--";
    profileNameEl.textContent = data.profile || "default";
    modelBadge.textContent = `MODEL: ${data.model_name || "--"}`;
  } catch (err) {
    renderMessage("system", `Failed to load info: ${err.message}`);
    addError(`Info load failed: ${err.message}`);
  }
}

async function ensureSession() {
  const fromUrl = getSessionFromUrl();
  if (fromUrl) {
    const ok = await checkSession(fromUrl);
    if (ok) {
      activateSession(fromUrl, state.activeSlot, true);
      return;
    }
  }
  const stored = localStorage.getItem(storeKey);
  if (stored) {
    const ok = await checkSession(stored);
    if (ok) {
      activateSession(stored, state.activeSlot, true);
      return;
    }
  }
  await createSession(state.activeSlot);
}

async function checkSession(sessionId) {
  try {
    await fetchJson(`/api/status?session_id=${encodeURIComponent(sessionId)}`);
    return true;
  } catch (err) {
    return false;
  }
}

async function createSession() {
  const data = await postJson("/api/session", {});
  return data.session_id;
}

function updateSessionView() {
  sessionIdEl.textContent = state.sessionId || "--";
  sessionBadge.textContent = `SESSION: ${shortId(state.sessionId)}`;
}

function updateShareLink() {
  if (!state.sessionId) return;
  const url = new URL(window.location.href);
  url.searchParams.set("session", state.sessionId);
  window.history.replaceState({}, "", url);
}

function getSessionFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("session");
}

function loadSlots() {
  const defaults = {
    alpha: { label: "Session Alpha" },
    delta: { label: "Session Delta" },
    echo: { label: "Session Echo" },
  };
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(slotKey) || "{}");
  } catch (err) {
    stored = {};
  }
  state.slots = {};
  Object.keys(defaults).forEach((key) => {
    const base = defaults[key];
    const saved = (stored.slots && stored.slots[key]) || {};
    state.slots[key] = {
      label: base.label,
      sessionId: saved.sessionId || null,
      lastUsed: saved.lastUsed || null,
    };
  });
  state.activeSlot = stored.activeSlot && state.slots[stored.activeSlot] ? stored.activeSlot : "alpha";
}

function saveSlots() {
  localStorage.setItem(slotKey, JSON.stringify({ activeSlot: state.activeSlot, slots: state.slots }));
}

function loadTranscripts() {
  try {
    state.transcripts = JSON.parse(localStorage.getItem(transcriptKey) || "{}");
  } catch (err) {
    state.transcripts = {};
  }
}

function saveTranscripts() {
  localStorage.setItem(transcriptKey, JSON.stringify(state.transcripts));
}

function storeMessage(role, content, time, messageId, pinned, reply, rating, attachments) {
  if (!state.sessionId) return;
  if (!state.transcripts[state.sessionId]) {
    state.transcripts[state.sessionId] = [];
  }
  let replyPayload = null;
  if (reply && (reply.content || reply.messageId)) {
    replyPayload = {
      role: reply.role || "message",
      content: reply.content || "",
      time: reply.time || "",
      messageId: reply.messageId || null,
    };
  }
  state.transcripts[state.sessionId].push({
    role,
    content,
    time,
    messageId: messageId || null,
    pinned: Boolean(pinned),
    reply: replyPayload,
    rating: typeof rating === "number" ? rating : 0,
    attachments: Array.isArray(attachments) ? attachments : [],
  });
  if (role === "assistant" && messageId) {
    state.lastAssistantMessageId = messageId;
  }
  if (role === "assistant" && (!Array.isArray(attachments) || attachments.length === 0)) {
    updateLastReply(content || "");
  }
  saveTranscripts();
}

function clearTranscriptCache(sessionId) {
  if (!sessionId) return;
  if (!state.transcripts[sessionId]) return;
  state.transcripts[sessionId] = [];
  saveTranscripts();
  renderTranscript(sessionId);
}

function getTranscriptItems(sessionId) {
  return state.transcripts[sessionId] || [];
}

function isMeaningfulContent(value) {
  const text = (value || "").trim();
  if (!text) return false;
  return text.toLowerCase() !== "(empty response)";
}

function getLatestTranscriptContent(items, preferRole) {
  if (!Array.isArray(items) || !items.length) return "";
  const findLatest = (role) => {
    for (let i = items.length - 1; i >= 0; i -= 1) {
      const item = items[i];
      if (item.role !== role) continue;
      if (isMeaningfulContent(item.content)) return item.content;
    }
    return "";
  };
  if (preferRole) {
    const hit = findLatest(preferRole);
    if (hit) return hit;
  }
  for (let i = items.length - 1; i >= 0; i -= 1) {
    if (isMeaningfulContent(items[i].content)) return items[i].content;
  }
  return "";
}

function buildTranscriptExport(items, limit = 8) {
  if (!Array.isArray(items) || !items.length) return "";
  const trimmed = items.filter((item) => item.role !== "system" && isMeaningfulContent(item.content));
  if (!trimmed.length) return "";
  const slice = trimmed.slice(-Math.max(1, limit));
  return slice
    .map((item) => `[${String(item.role || "message").toUpperCase()}] ${item.content}`)
    .join("\n\n");
}

function syncLastAssistantFromTranscript(sessionId) {
  if (!sessionId) return;
  const items = getTranscriptItems(sessionId);
  if (!items.length) return;
  let lastAssistantId = null;
  let lastAssistantContent = "";
  for (let i = items.length - 1; i >= 0; i -= 1) {
    const item = items[i];
    if (item.role !== "assistant") continue;
    if (!lastAssistantId && item.messageId) {
      lastAssistantId = item.messageId;
    }
    if (!lastAssistantContent) {
      const content = (item.content || "").trim();
      if (content) {
        lastAssistantContent = item.content;
      }
    }
    if (lastAssistantId && lastAssistantContent) break;
  }
  if (lastAssistantId) {
    state.lastAssistantMessageId = lastAssistantId;
  }
  if (lastAssistantContent) {
    state.lastReply = lastAssistantContent;
  }
}

function updateLastReply(content) {
  if (typeof content !== "string") return;
  if (isMeaningfulContent(content)) {
    state.lastReply = content;
  }
}

function applyFilters(items) {
  let filtered = items.slice();
  const query = state.filters.query.trim().toLowerCase();
  if (query) {
    filtered = filtered.filter((item) => (item.content || "").toLowerCase().includes(query));
  }
  if (state.filters.pinnedOnly) {
    filtered = filtered.filter((item) => item.pinned);
  } else if (state.filters.role !== "all") {
    filtered = filtered.filter((item) => item.role === state.filters.role);
  }
  return filtered;
}

function setFilterRole(role) {
  if (role === "pinned") {
    state.filters.pinnedOnly = !state.filters.pinnedOnly;
    if (state.filters.pinnedOnly) {
      state.filters.role = "all";
    }
  } else {
    state.filters.role = role;
    state.filters.pinnedOnly = false;
  }
  updateFilterButtons();
  if (state.sessionId) {
    renderTranscript(state.sessionId);
  }
}

function updateFilterButtons() {
  filterButtons.forEach((btn) => {
    const role = btn.dataset.role;
    if (role === "pinned") {
      btn.classList.toggle("active", state.filters.pinnedOnly);
    } else {
      btn.classList.toggle("active", state.filters.role === role && !state.filters.pinnedOnly);
    }
  });
}

function observeHistorySentinel(node) {
  if (!node || !window.IntersectionObserver) return;
  if (historyObserver) {
    historyObserver.disconnect();
  }
  historyObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      loadOlderMessages();
    });
  }, { root: chatLog, threshold: 0.2 });
  historyObserver.observe(node);
}

function renderTranscript(sessionId, options = {}) {
  const preserveScroll = options.preserveScroll === true;
  const prevHeight = preserveScroll ? chatLog.scrollHeight : 0;
  const prevTop = preserveScroll ? chatLog.scrollTop : 0;
  chatLog.innerHTML = "";
  const items = applyFilters(getTranscriptItems(sessionId));
  const limit = Math.max(10, state.renderLimit);
  const slice = items.length > limit ? items.slice(items.length - limit) : items;
  let sentinel = null;
  if (items.length > slice.length) {
    sentinel = document.createElement("div");
    sentinel.className = "history-sentinel";
    chatLog.appendChild(sentinel);
  }
  const fragment = document.createDocumentFragment();
  slice.forEach((item) => {
    const hasAttachments = Array.isArray(item.attachments) && item.attachments.length > 0;
    renderMessage(item.role, item.content, {
      time: item.time,
      skipStore: true,
      noScroll: true,
      messageId: item.messageId,
      pinned: item.pinned,
      reply: item.reply,
      rating: item.rating,
      attachments: item.attachments,
      markdown: hasAttachments ? false : undefined,
      container: fragment,
      deferMarkdown: item.role === "assistant" && !hasAttachments,
    });
  });
  chatLog.appendChild(fragment);
  if (sentinel) {
    observeHistorySentinel(sentinel);
  }
  if (loadOlderBtn) {
    loadOlderBtn.style.display = items.length > slice.length ? "inline-flex" : "none";
  }
  if (preserveScroll) {
    chatLog.scrollTop = chatLog.scrollHeight - prevHeight + prevTop;
  } else {
    chatLog.scrollTop = chatLog.scrollHeight;
  }
  syncLastAssistantFromTranscript(sessionId);
  updateAnalytics();
}

function loadOlderMessages() {
  if (!state.sessionId || state.loadingOlder) return;
  const items = getTranscriptItems(state.sessionId);
  if (state.renderLimit >= items.length) return;
  state.loadingOlder = true;
  state.renderLimit += state.renderStep;
  renderTranscript(state.sessionId, { preserveScroll: true });
  state.loadingOlder = false;
}

function syncTranscriptPins() {
  if (!state.sessionId) return;
  const items = getTranscriptItems(state.sessionId);
  const pinnedSet = new Set(state.pins);
  items.forEach((item) => {
    if (!item.messageId) return;
    item.pinned = pinnedSet.has(item.messageId);
  });
  saveTranscripts();
}

function renderPinList() {
  if (!pinList) return;
  pinList.innerHTML = "";
  if (!state.pins.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No pinned messages.";
    pinList.appendChild(empty);
    return;
  }
  const items = getTranscriptItems(state.sessionId);
  state.pins.forEach((pinId) => {
    const match = items.find((item) => item.messageId === pinId);
    const item = document.createElement("div");
    item.className = "list-item";
    if (match) {
      item.innerHTML = `<strong>${pinId}</strong> ${truncate(match.content, 80)}`;
    } else {
      item.innerHTML = `<strong>${pinId}</strong> (not in cache)`;
    }
    pinList.appendChild(item);
  });
}

function updateAnalytics() {
  if (!state.sessionId) return;
  const items = getTranscriptItems(state.sessionId);
  let userCount = 0;
  let assistantCount = 0;
  let systemCount = 0;
  const freq = {};
  items.forEach((item) => {
    if (item.role === "user") userCount += 1;
    if (item.role === "assistant") assistantCount += 1;
    if (item.role === "system") systemCount += 1;
    if (item.role === "system") return;
    const text = (item.content || "").toLowerCase();
    const words = text.match(/[a-z0-9]{3,}/g) || [];
    words.forEach((word) => {
      if (topicStopWords.has(word)) return;
      freq[word] = (freq[word] || 0) + 1;
    });
  });
  if (statUser) statUser.textContent = String(userCount);
  if (statAssistant) statAssistant.textContent = String(assistantCount);
  if (statSystem) statSystem.textContent = String(systemCount);
  const topics = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map((entry) => entry[0]);
  if (statTopics) {
    statTopics.textContent = topics.length ? topics.join(", ") : "--";
  }
  if (summaryCard) {
    const lastAssistant = [...items].reverse().find((item) => item.role === "assistant");
    summaryCard.textContent = lastAssistant ? truncate(lastAssistant.content || "", 160) : "No summary yet.";
  }
}

async function refreshPins() {
  if (!state.sessionId) return;
  try {
    const data = await fetchJson(`/api/pins?session_id=${encodeURIComponent(state.sessionId)}`);
    const pins = data.pins || [];
    state.pins = pins.map((item) => item.message_id).filter(Boolean);
    syncTranscriptPins();
    renderPinList();
    renderTranscript(state.sessionId);
  } catch (err) {
    addError(`Pin sync failed: ${err.message}`);
  }
}

async function togglePin(messageId, wrapper) {
  if (!state.sessionId || !messageId) return;
  const isPinned = state.pins.includes(messageId);
  try {
    if (isPinned) {
      await postJson("/api/unpin", { session_id: state.sessionId, message_id: messageId });
    } else {
      await postJson("/api/pin", { session_id: state.sessionId, message_id: messageId });
    }
    await refreshPins();
    if (wrapper) {
      wrapper.classList.toggle("pinned", !isPinned);
      const button = wrapper.querySelector(".message-pin");
      if (button) {
        button.textContent = isPinned ? "PIN" : "UNPIN";
      }
    }
  } catch (err) {
    addError(`Pin update failed: ${err.message}`);
  }
}

function renderNotes(project, longTerm) {
  if (projectNotesEl) {
    projectNotesEl.innerHTML = "";
    if (!project.length) {
      const empty = document.createElement("div");
      empty.className = "list-item";
      empty.textContent = "No project notes.";
      projectNotesEl.appendChild(empty);
    } else {
      project.forEach((note) => {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `<strong>${note.title}</strong> ${truncate(note.content, 120)}`;
        projectNotesEl.appendChild(item);
      });
    }
  }
  if (longNotesEl) {
    longNotesEl.innerHTML = "";
    if (!longTerm.length) {
      const empty = document.createElement("div");
      empty.className = "list-item";
      empty.textContent = "No long-term notes.";
      longNotesEl.appendChild(empty);
    } else {
      longTerm.forEach((note) => {
        const item = document.createElement("div");
        item.className = "list-item";
        item.innerHTML = `<strong>${note.title}</strong> ${truncate(note.content, 120)}`;
        longNotesEl.appendChild(item);
      });
    }
  }
}

async function loadNotes() {
  if (!state.sessionId) return;
  try {
    const data = await fetchJson(`/api/notes?session_id=${encodeURIComponent(state.sessionId)}`);
    renderNotes(data.project || [], data.long_term || []);
  } catch (err) {
    addError(`Note sync failed: ${err.message}`);
  }
}

function renderContextReport(report) {
  if (!contextSummary) return;
  contextSummary.innerHTML = "";
  if (!report || !report.tokens) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No context report yet.";
    contextSummary.appendChild(empty);
    return;
  }
  const items = [
    `Total tokens: ${report.tokens.total || "--"}`,
    `History used: ${report.history ? report.history.count : 0}`,
    `Retrieval used: ${report.retrieval ? report.retrieval.count : 0}`,
    `File context: ${report.file_context ? report.file_context.count : 0}`,
    `Summary: ${report.summary_included ? "YES" : "NO"}`,
    `Notes: ${report.notes_included ? "YES" : "NO"}`,
  ];
  if (report.budgets && report.budgets.total) {
    items.push(
      `Budgets (S/R/F/H): ${report.budgets.system || 0}/${report.budgets.retrieval || 0}/${report.budgets.file || 0}/${report.budgets.history || 0}`
    );
  }
  items.forEach((text) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.textContent = text;
    contextSummary.appendChild(row);
  });
  const historyIds = report.history && report.history.message_ids ? report.history.message_ids : [];
  const retrievalIds = report.retrieval && report.retrieval.message_ids ? report.retrieval.message_ids : [];
  const filePaths = report.file_context && report.file_context.paths ? report.file_context.paths : [];
  const detail = [
    { label: "History IDs", values: historyIds },
    { label: "Retrieval IDs", values: retrievalIds },
    { label: "Files", values: filePaths },
  ];
  detail.forEach((entry) => {
    if (!entry.values.length) return;
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${entry.label}</strong><br>${formatListPreview(entry.values, 6)}`;
    contextSummary.appendChild(row);
  });
}

function renderDedupStats(stats) {
  if (!dedupStats) return;
  dedupStats.innerHTML = "";
  if (!stats) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No stats.";
    dedupStats.appendChild(empty);
    return;
  }
  const rows = [
    `Messages checked: ${stats.total || 0}`,
    `Duplicates blocked: ${stats.hits || 0}`,
    `Hit rate: ${stats.hit_rate !== undefined ? stats.hit_rate : "--"}`,
  ];
  rows.forEach((text) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.textContent = text;
    dedupStats.appendChild(item);
  });
}

async function loadContextReport() {
  if (!state.sessionId) return;
  try {
    const data = await fetchJson(`/api/context?session_id=${encodeURIComponent(state.sessionId)}`);
    renderContextReport(data.context || {});
  } catch (err) {
    addError(`Context report failed: ${err.message}`);
  }
}

async function loadMemoryStats() {
  if (!state.sessionId) return;
  try {
    const data = await fetchJson(`/api/memory/stats?session_id=${encodeURIComponent(state.sessionId)}`);
    renderDedupStats(data.dedup || {});
  } catch (err) {
    addError(`Memory stats failed: ${err.message}`);
  }
}

async function addNote(type) {
  if (!state.sessionId) return;
  const title = (noteTitleInput && noteTitleInput.value || "").trim();
  const content = (noteContentInput && noteContentInput.value || "").trim();
  if (!content) {
    addError("Note content is required.");
    return;
  }
  try {
    await postJson("/api/notes", {
      session_id: state.sessionId,
      type,
      title,
      content,
    });
    if (noteTitleInput) noteTitleInput.value = "";
    if (noteContentInput) noteContentInput.value = "";
    await loadNotes();
  } catch (err) {
    addError(`Note add failed: ${err.message}`);
  }
}

function renderSnapshots(items) {
  if (!snapshotList) return;
  snapshotList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No snapshots.";
    snapshotList.appendChild(empty);
    return;
  }
  items.slice().reverse().forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const label = item.label ? ` ${item.label}` : "";
    row.innerHTML = `<strong>${item.snapshot_id}</strong>${label}<br>${item.timestamp || ""}`;
    const btn = document.createElement("button");
    btn.className = "mini ghost";
    btn.textContent = "RESTORE";
    btn.addEventListener("click", () => restoreSnapshot(item.snapshot_id));
    row.appendChild(btn);
    snapshotList.appendChild(row);
  });
}

async function loadSnapshots() {
  if (!state.sessionId) return;
  try {
    const data = await fetchJson(`/api/memory/snapshots?session_id=${encodeURIComponent(state.sessionId)}`);
    renderSnapshots(data.snapshots || []);
  } catch (err) {
    addError(`Snapshot load failed: ${err.message}`);
  }
}

async function createSnapshot() {
  if (!state.sessionId) return;
  const label = (snapshotLabelInput && snapshotLabelInput.value || "").trim();
  try {
    await postJson("/api/memory/snapshot", { session_id: state.sessionId, label });
    if (snapshotLabelInput) snapshotLabelInput.value = "";
    await loadSnapshots();
  } catch (err) {
    addError(`Snapshot create failed: ${err.message}`);
  }
}

async function restoreSnapshot(snapshotId) {
  if (!state.sessionId || !snapshotId) return;
  try {
    await postJson("/api/memory/rollback", { session_id: state.sessionId, snapshot_id: snapshotId });
    renderMessage("system", "Snapshot restored.", { skipStore: true });
    clearTranscriptCache(state.sessionId);
    await refreshPins();
    await loadNotes();
    await loadSnapshots();
  } catch (err) {
    addError(`Snapshot restore failed: ${err.message}`);
  }
}

function renderArchives(items) {
  if (!archiveList) return;
  archiveList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No archives.";
    archiveList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${item.name}</strong><br>${item.timestamp || ""}`;
    const btn = document.createElement("button");
    btn.className = "mini ghost";
    btn.textContent = "RESTORE";
    btn.addEventListener("click", () => restoreArchive(item.name));
    row.appendChild(btn);
    archiveList.appendChild(row);
  });
}

async function loadArchives() {
  try {
    const data = await fetchJson("/api/memory/archives");
    renderArchives(data.archives || []);
  } catch (err) {
    addError(`Archive load failed: ${err.message}`);
  }
}

async function createArchiveNow() {
  if (!state.sessionId) return;
  try {
    await postJson("/api/memory/archive", { session_id: state.sessionId });
    await loadArchives();
  } catch (err) {
    addError(`Archive failed: ${err.message}`);
  }
}

async function restoreArchive(name) {
  if (!state.sessionId || !name) return;
  try {
    await postJson("/api/memory/archive/restore", { session_id: state.sessionId, name });
    renderMessage("system", "Archive restored.", { skipStore: true });
    clearTranscriptCache(state.sessionId);
    await refreshPins();
    await loadNotes();
    await loadSnapshots();
  } catch (err) {
    addError(`Archive restore failed: ${err.message}`);
  }
}

function renderSchedules(items) {
  if (!scheduleList) return;
  scheduleList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No schedules.";
    scheduleList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${item.schedule_id}</strong> ${item.next_run || "--"}<br>${truncate(item.prompt, 120)}`;
    scheduleList.appendChild(row);
  });
}

async function loadSchedules() {
  try {
    const data = await fetchJson("/api/schedules");
    renderSchedules(data.schedules || []);
  } catch (err) {
    if (String(err.message || "").includes("scheduler_disabled")) {
      return;
    }
    addError(`Schedule sync failed: ${err.message}`);
  }
}

async function addSchedule() {
  const mode = scheduleMode ? scheduleMode.value : "in";
  const value = scheduleValue ? scheduleValue.value.trim() : "";
  const prompt = schedulePrompt ? schedulePrompt.value.trim() : "";
  if (!value || !prompt) {
    addError("Schedule value and prompt are required.");
    return;
  }
  const payload = {
    action: "add",
    prompt,
    session_id: state.sessionId,
  };
  if (mode === "in") {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds <= 0) {
      addError("Invalid seconds.");
      return;
    }
    payload.interval_seconds = Math.floor(seconds);
  } else {
    payload.run_at = value;
  }
  try {
    await postJson("/api/schedules", payload);
    if (scheduleValue) scheduleValue.value = "";
    if (schedulePrompt) schedulePrompt.value = "";
    await loadSchedules();
  } catch (err) {
    addError(`Schedule add failed: ${err.message}`);
  }
}

function buildNewsMarkdown(data) {
  if (!data) return "";
  const dateKey = data.date || "";
  const topics = Array.isArray(data.topics) ? data.topics : [];
  const items = Array.isArray(data.items) ? data.items : [];
  const lines = [
    `# Daily News Digest (${dateKey})`,
    "",
    `Generated: ${data.generated_at || ""}`,
    `Topics: ${topics.length ? topics.join(", ") : "--"}`,
    `Total items: ${data.total_items ?? items.length}`,
    "",
  ];
  if (!items.length) {
    lines.push("No news items found.");
    return lines.join("\n");
  }
  const grouped = {};
  items.forEach((item) => {
    const key = item.topic || "Other";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(item);
  });
  Object.keys(grouped).forEach((topic) => {
    lines.push(`## ${topic}`);
    grouped[topic].forEach((entry) => {
      const title = entry.title || "Untitled";
      const link = entry.link || "";
      const source = entry.source || "";
      const published = entry.published || "";
      const summary = entry.summary || "";
      lines.push(`- [${title}](${link})`);
      const meta = [source, published].filter(Boolean).join(" | ");
      if (meta) {
        lines.push(`  - ${meta}`);
      }
      if (summary) {
        lines.push(`  - ${summary}`);
      }
    });
    lines.push("");
  });
  return lines.join("\n");
}

function renderNewsPreview(data, message) {
  if (!newsPreview) return;
  if (!data && message) {
    newsPreview.textContent = message;
    return;
  }
  const markdown = buildNewsMarkdown(data);
  if (!markdown) {
    newsPreview.textContent = message || "No news selected.";
    return;
  }
  const meta = [];
  if (data && data.obsidian_path) {
    meta.push(`Saved to: ${escapeHtml(String(data.obsidian_path))}`);
  }
  const metaHtml = meta.length ? `<div class="news-meta">${meta.join("<br>")}</div>` : "";
  newsPreview.innerHTML = metaHtml + renderMarkdown(markdown);
}

function renderNewsList(items) {
  if (!newsList) return;
  newsList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No news yet.";
    newsList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const date = item.date || "--";
    const count = item.total_items ?? 0;
    const hasError = Array.isArray(item.errors) && item.errors.length > 0;
    row.innerHTML = `<strong>${date}</strong> ${count} items${hasError ? " | ERR" : ""}`;
    row.addEventListener("click", () => {
      loadNewsDigest(date);
    });
    newsList.appendChild(row);
  });
}

async function loadNewsList() {
  if (!newsList) return;
  try {
    const data = await fetchJson("/api/news");
    const items = data.items || [];
    renderNewsList(items);
    if (newsPreview && items.length && !newsPreview.dataset.loaded) {
      newsPreview.dataset.loaded = "true";
      loadNewsDigest(items[0].date);
    }
  } catch (err) {
    addError(`News load failed: ${err.message}`);
  }
}

async function loadNewsDigest(dateKey) {
  if (!newsPreview || !dateKey) return;
  newsPreview.textContent = "Loading...";
  try {
    const data = await fetchJson(`/api/news?date=${encodeURIComponent(dateKey)}`);
    if (data && !data.error) {
      renderNewsPreview(data);
      return;
    }
    renderNewsPreview(null, "News not found.");
  } catch (err) {
    renderNewsPreview(null, "News load failed.");
    addError(`News load failed: ${err.message}`);
  }
}

async function refreshNews() {
  if (!refreshNewsBtn) return;
  try {
    const data = await postJson("/api/news/refresh", {});
    await loadNewsList();
    if (data && data.date) {
      loadNewsDigest(data.date);
    }
    addRunLog("NEWS", "Digest refreshed.");
  } catch (err) {
    addError(`News refresh failed: ${err.message}`);
  }
}

async function applyNewsConfig() {
  if (!newsTopicInput || !newsTimeInput || !newsEnabled) return;
  const topics = parseCsvList(newsTopicInput.value);
  const scheduleTime = newsTimeInput.value || "12:00";
  const enabled = newsEnabled.value === "true";
  const obsidianEnabled = newsObsidianEnabled ? newsObsidianEnabled.value === "true" : false;
  const obsidianDir = newsObsidianDir ? newsObsidianDir.value.trim() : "";
  const obsidianFile = newsObsidianFile ? newsObsidianFile.value.trim() : "";
  const overrides = {
    news_digest: {
      enabled,
      schedule_time: scheduleTime,
      topics,
      obsidian_enabled: obsidianEnabled,
      obsidian_dir: obsidianDir,
      obsidian_filename: obsidianFile || "news_{date}.md",
    },
  };
  try {
    await postJson("/api/config", { overrides });
    renderMessage("system", "News settings saved.", { skipStore: true });
    await loadConfig();
  } catch (err) {
    addError(`News settings failed: ${err.message}`);
  }
}

function buildMediaBriefMarkdown(data) {
  if (!data) return "";
  const dateKey = data.date || "";
  const items = Array.isArray(data.items) ? data.items : [];
  const lines = [
    `# Media Brief (${dateKey})`,
    "",
    `Generated: ${data.generated_at || ""}`,
    `Total items: ${data.total_items ?? items.length}`,
    `New items: ${data.new_items ?? 0}`,
    "",
  ];
  const alertHits = Array.isArray(data.alert_hits) ? data.alert_hits : [];
  if (alertHits.length) {
    lines.push("## Alerts");
    alertHits.forEach((entry) => {
      const title = entry.title || "Untitled";
      const link = entry.link || "";
      const source = entry.source || "";
      lines.push(`- [${title}](${link})`);
      if (source) {
        lines.push(`  - ${source}`);
      }
    });
    lines.push("");
  }
  if (!items.length) {
    lines.push("No items available.");
    return lines.join("\n");
  }
  const grouped = {};
  items.forEach((entry) => {
    const key = entry.platform || entry.source || "Other";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(entry);
  });
  Object.keys(grouped).forEach((group) => {
    lines.push(`## ${group}`);
    grouped[group].forEach((entry) => {
      const title = entry.title || "Untitled";
      const link = entry.link || "";
      const source = entry.source || "";
      const published = entry.published || "";
      lines.push(`- [${title}](${link})`);
      const meta = [source, published].filter(Boolean).join(" | ");
      if (meta) {
        lines.push(`  - ${meta}`);
      }
    });
    lines.push("");
  });
  return lines.join("\n");
}

function renderMediaBriefPreview(data, message) {
  if (!mediaBriefPreview) return;
  if (!data && message) {
    mediaBriefPreview.textContent = message;
    return;
  }
  const markdown = buildMediaBriefMarkdown(data);
  if (!markdown) {
    mediaBriefPreview.textContent = message || "No brief selected.";
    return;
  }
  mediaBriefPreview.innerHTML = renderMarkdown(markdown);
}

function renderMediaBriefList(items) {
  if (!mediaBriefList) return;
  mediaBriefList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No briefs yet.";
    mediaBriefList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const date = item.date || "--";
    const count = item.total_items ?? 0;
    row.innerHTML = `<strong>${date}</strong> ${count} items`;
    row.addEventListener("click", () => {
      loadMediaBrief(date);
    });
    mediaBriefList.appendChild(row);
  });
}

async function loadMediaBriefList() {
  if (!mediaBriefList) return;
  try {
    const data = await fetchJson("/api/media/briefs");
    const items = data.items || [];
    renderMediaBriefList(items);
    if (mediaBriefPreview && items.length && !mediaBriefPreview.dataset.loaded) {
      mediaBriefPreview.dataset.loaded = "true";
      loadMediaBrief(items[0].date);
    }
  } catch (err) {
    addError(`Media briefs load failed: ${err.message}`);
  }
}

async function loadMediaBrief(dateKey) {
  if (!mediaBriefPreview || !dateKey) return;
  mediaBriefPreview.textContent = "Loading...";
  try {
    const data = await fetchJson(`/api/media/brief?date=${encodeURIComponent(dateKey)}`);
    if (data && !data.error) {
      renderMediaBriefPreview(data);
      return;
    }
    renderMediaBriefPreview(null, "Brief not found.");
  } catch (err) {
    renderMediaBriefPreview(null, "Brief load failed.");
    addError(`Media brief load failed: ${err.message}`);
  }
}

function renderMediaSources(items) {
  if (!mediaSourcesList) return;
  mediaSourcesList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No sources yet.";
    mediaSourcesList.appendChild(empty);
    return;
  }
  items.forEach((source) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const status = source.enabled ? "ON" : "OFF";
    const note = source.note ? ` | ${escapeHtml(source.note)}` : "";
    row.innerHTML = `<strong>${escapeHtml(source.name || source.id || "source")}</strong> ${status}<br>${escapeHtml(source.platform || source.type || "")}${note}`;
    const actions = document.createElement("div");
    actions.className = "message-actions";
    const toggleBtn = document.createElement("button");
    toggleBtn.className = "mini ghost";
    toggleBtn.textContent = source.enabled ? "DISABLE" : "ENABLE";
    toggleBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleMediaSource(source.id);
    });
    const removeBtn = document.createElement("button");
    removeBtn.className = "mini ghost";
    removeBtn.textContent = "REMOVE";
    removeBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      removeMediaSource(source.id);
    });
    actions.appendChild(toggleBtn);
    actions.appendChild(removeBtn);
    row.appendChild(actions);
    mediaSourcesList.appendChild(row);
  });
}

async function loadMediaSources() {
  if (!mediaSourcesList) return;
  try {
    const data = await fetchJson("/api/media/sources");
    state.media.sources = data.sources || [];
    renderMediaSources(state.media.sources);
  } catch (err) {
    addError(`Media sources load failed: ${err.message}`);
  }
}

async function saveMediaSources(sources) {
  try {
    const data = await postJson("/api/media/sources", { sources });
    state.media.sources = data.sources || sources;
    renderMediaSources(state.media.sources);
  } catch (err) {
    addError(`Media sources save failed: ${err.message}`);
  }
}

function addMediaSource() {
  if (!mediaSourceName) return;
  const name = (mediaSourceName.value || "").trim();
  if (!name) {
    addError("Source name is required.");
    return;
  }
  const platform = mediaSourcePlatform ? mediaSourcePlatform.value.trim() : "";
  const type = mediaSourceType ? mediaSourceType.value : "rss";
  const url = mediaSourceUrl ? mediaSourceUrl.value.trim() : "";
  const enabled = mediaSourceEnabled ? mediaSourceEnabled.value === "true" : false;
  const requiresConfig = !url;
  const entry = {
    name,
    platform: platform || type.toUpperCase(),
    type,
    url,
    enabled,
    requires_config: requiresConfig,
    note: requiresConfig ? "Setup required." : "",
  };
  const next = Array.isArray(state.media.sources) ? [...state.media.sources, entry] : [entry];
  saveMediaSources(next);
  if (mediaSourceName) mediaSourceName.value = "";
  if (mediaSourcePlatform) mediaSourcePlatform.value = "";
  if (mediaSourceUrl) mediaSourceUrl.value = "";
}

function toggleMediaSource(sourceId) {
  if (!sourceId) return;
  const next = (state.media.sources || []).map((source) => {
    if (source.id !== sourceId) return source;
    return { ...source, enabled: !source.enabled };
  });
  saveMediaSources(next);
}

function removeMediaSource(sourceId) {
  if (!sourceId) return;
  const next = (state.media.sources || []).filter((source) => source.id !== sourceId);
  saveMediaSources(next);
}

function renderMediaItems(items) {
  if (!mediaItemList) return;
  mediaItemList.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No items found.";
    mediaItemList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item media-item";
    const title = item.title || "Untitled";
    const metaParts = [item.source, item.platform, item.published].filter(Boolean);
    const badges = [];
    if (item.alert_hits && item.alert_hits.length) badges.push("ALERT");
    if (item.saved) badges.push("SAVED");
    if (!item.read) badges.push("UNREAD");
    const badgeText = badges.length ? ` | ${badges.join(" ")}` : "";
    row.innerHTML = `<strong>${escapeHtml(title)}</strong>${badgeText}<br>${escapeHtml(metaParts.join(" | "))}`;
    const actions = document.createElement("div");
    actions.className = "message-actions";
    const openBtn = document.createElement("button");
    openBtn.className = "mini ghost";
    openBtn.textContent = "OPEN";
    openBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      if (item.link) {
        window.open(item.link, "_blank");
      }
    });
    const saveBtn = document.createElement("button");
    saveBtn.className = "mini ghost";
    saveBtn.textContent = item.saved ? "UNSAVE" : "SAVE";
    saveBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      updateMediaItem(item.id, { saved: !item.saved });
    });
    const readBtn = document.createElement("button");
    readBtn.className = "mini ghost";
    readBtn.textContent = item.read ? "UNREAD" : "READ";
    readBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      updateMediaItem(item.id, { read: !item.read });
    });
    actions.appendChild(openBtn);
    actions.appendChild(saveBtn);
    actions.appendChild(readBtn);
    row.appendChild(actions);
    mediaItemList.appendChild(row);
  });
}

function renderMediaList(target, items, emptyMessage) {
  if (!target) return;
  target.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = emptyMessage || "No items.";
    target.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const title = item.title || "Untitled";
    const source = item.source || "";
    row.innerHTML = `<strong>${escapeHtml(title)}</strong><br>${escapeHtml(source)}`;
    row.addEventListener("click", () => {
      if (item.link) {
        window.open(item.link, "_blank");
      }
    });
    target.appendChild(row);
  });
}

async function loadMediaItems() {
  if (!mediaItemList) return;
  const params = new URLSearchParams();
  const query = mediaSearchInput ? mediaSearchInput.value.trim() : "";
  if (query) params.set("q", query);
  const filter = mediaFilterSelect ? mediaFilterSelect.value : "all";
  if (filter === "saved") params.set("saved", "true");
  if (filter === "unread") params.set("read", "false");
  if (filter === "alerts") params.set("alerted", "true");
  params.set("limit", "60");
  try {
    const data = await fetchJson(`/api/media/items?${params.toString()}`);
    state.media.items = data.items || [];
    renderMediaItems(state.media.items);
  } catch (err) {
    addError(`Media feed load failed: ${err.message}`);
  }
}

async function loadMediaSaved() {
  if (!mediaSavedList) return;
  try {
    const data = await fetchJson("/api/media/items?saved=true&limit=12");
    renderMediaList(mediaSavedList, data.items || [], "No saved items.");
  } catch (err) {
    addError(`Saved list failed: ${err.message}`);
  }
}

async function loadMediaAlerts() {
  if (!mediaAlertList) return;
  try {
    const data = await fetchJson("/api/media/items?alerted=true&limit=10");
    renderMediaList(mediaAlertList, data.items || [], "No alert hits.");
  } catch (err) {
    addError(`Alert list failed: ${err.message}`);
  }
}

function renderMediaTrends(items) {
  if (!mediaTrends) return;
  mediaTrends.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No trends yet.";
    mediaTrends.appendChild(empty);
    return;
  }
  items.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${escapeHtml(entry.keyword || entry.label || "")}</strong> ${entry.count || 0}`;
    mediaTrends.appendChild(row);
  });
}

async function loadMediaStats() {
  if (!mediaTrends) return;
  try {
    const data = await fetchJson("/api/media/stats");
    state.media.stats = data || {};
    state.media.alerts = Array.isArray(data.alerts) ? data.alerts : [];
    if (mediaAlertInput && Array.isArray(data.alerts) && document.activeElement !== mediaAlertInput) {
      mediaAlertInput.value = data.alerts.join(", ");
    }
    renderMediaTrends(data.trends || []);
  } catch (err) {
    addError(`Media stats failed: ${err.message}`);
  }
}

async function updateMediaItem(itemId, updates) {
  if (!itemId) return;
  try {
    await postJson("/api/media/item", { id: itemId, updates });
    await loadMediaItems();
    await loadMediaSaved();
    await loadMediaAlerts();
    await loadMediaStats();
  } catch (err) {
    addError(`Media update failed: ${err.message}`);
  }
}

async function refreshMedia() {
  if (!refreshMediaBtn) return;
  try {
    await postJson("/api/media/refresh", {});
    await loadMediaSources();
    await loadMediaItems();
    await loadMediaSaved();
    await loadMediaAlerts();
    await loadMediaStats();
    await loadMediaBriefList();
    addRunLog("MEDIA", "Media hub refreshed.");
  } catch (err) {
    addError(`Media refresh failed: ${err.message}`);
  }
}

async function applyMediaConfig() {
  if (!mediaAlertInput || !mediaTimeInput || !mediaEnabled) return;
  const alerts = parseCsvList(mediaAlertInput.value);
  const scheduleTime = mediaTimeInput.value || "12:00";
  const enabled = mediaEnabled.value === "true";
  const obsidianEnabled = mediaObsidianEnabled ? mediaObsidianEnabled.value === "true" : false;
  const obsidianDir = mediaObsidianDir ? mediaObsidianDir.value.trim() : "";
  const obsidianFile = mediaObsidianFile ? mediaObsidianFile.value.trim() : "";
  try {
    await postJson("/api/media/alerts", { alerts });
    await postJson("/api/config", {
      overrides: {
        media_hub: {
          enabled,
          schedule_time: scheduleTime,
          obsidian_enabled: obsidianEnabled,
          obsidian_dir: obsidianDir,
          obsidian_filename: obsidianFile || "media_{date}.md",
          alerts,
        },
      },
    });
    renderMessage("system", "Media settings saved.", { skipStore: true });
    await loadConfig();
    await loadMediaStats();
  } catch (err) {
    addError(`Media settings failed: ${err.message}`);
  }
}

async function addManualMediaItem() {
  if (!mediaItemTitle) return;
  const title = mediaItemTitle.value.trim();
  if (!title) {
    addError("Title is required.");
    return;
  }
  const payload = {
    title,
    link: mediaItemLink ? mediaItemLink.value.trim() : "",
    source: mediaItemSource ? mediaItemSource.value.trim() : "",
  };
  try {
    await postJson("/api/media/add", payload);
    if (mediaItemTitle) mediaItemTitle.value = "";
    if (mediaItemLink) mediaItemLink.value = "";
    if (mediaItemSource) mediaItemSource.value = "";
    await loadMediaItems();
    await loadMediaSaved();
  } catch (err) {
    addError(`Media add failed: ${err.message}`);
  }
}

async function loadMediaAll() {
  await loadMediaSources();
  await loadMediaItems();
  await loadMediaSaved();
  await loadMediaAlerts();
  await loadMediaStats();
  await loadMediaBriefList();
}

function renderWebhookLogs(entries) {
  if (!webhookLogList) return;
  webhookLogList.innerHTML = "";
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No webhook events.";
    webhookLogList.appendChild(empty);
    return;
  }
  entries.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "list-item";
    if (entry.raw) {
      row.textContent = entry.raw;
      webhookLogList.appendChild(row);
      return;
    }
    const type = String(entry.type || "event").toUpperCase();
    const stamp = entry.timestamp || "";
    const summary = entry.url ? `URL ${entry.url}` : "";
    row.innerHTML = `<strong>${escapeHtml(type)}</strong> ${escapeHtml(stamp)}<br>${escapeHtml(summary)}`;
    webhookLogList.appendChild(row);
  });
}

async function loadWebhookLogs() {
  if (!webhookLogList) return;
  const limitRaw = webhookLimitInput ? webhookLimitInput.value : "";
  const parsed = parseInt(limitRaw || "80", 10);
  const limit = Number.isNaN(parsed) ? 80 : Math.max(1, parsed);
  try {
    const data = await fetchJson(`/api/webhooks/logs?limit=${limit}`);
    state.webhooks.logs = data.entries || [];
    renderWebhookLogs(state.webhooks.logs);
  } catch (err) {
    addError(`Webhook log failed: ${err.message}`);
  }
}

async function sendWebhookNow() {
  if (!webhookUrlInput) return;
  const url = webhookUrlInput.value.trim();
  if (!url) {
    addError("Webhook URL required.");
    return;
  }
  const payloadText = webhookPayloadInput ? webhookPayloadInput.value.trim() : "";
  const headerText = webhookHeadersInput ? webhookHeadersInput.value.trim() : "";
  const payload = payloadText ? safeParseJson(payloadText) : null;
  if (payloadText && !payload) {
    addError("Payload JSON invalid.");
    return;
  }
  const headers = headerText ? safeParseJson(headerText) : null;
  if (headerText && !headers) {
    addError("Headers JSON invalid.");
    return;
  }
  try {
    await postJson("/api/webhooks/send", {
      url,
      payload: payload || { message: "Ping from SAMA" },
      headers: headers || {},
    });
    await loadWebhookLogs();
    renderMessage("system", "Webhook sent.", { skipStore: true });
  } catch (err) {
    addError(`Webhook send failed: ${err.message}`);
  }
}

async function clearWebhookLogs() {
  try {
    await postJson("/api/webhooks/clear", {});
    await loadWebhookLogs();
  } catch (err) {
    addError(`Webhook clear failed: ${err.message}`);
  }
}

function clearArtifactPreview(message = "Select an artifact set.") {
  if (artifactMeta) artifactMeta.textContent = message;
  if (artifactFiles) artifactFiles.innerHTML = "";
  if (artifactPreview) artifactPreview.textContent = "";
  if (artifactDiffList) artifactDiffList.innerHTML = "";
  if (artifactDiff) artifactDiff.textContent = "";
  state.artifactDiffBundle = null;
  if (state.artifactPreviewUrl) {
    URL.revokeObjectURL(state.artifactPreviewUrl);
    state.artifactPreviewUrl = null;
  }
}

function isArtifactSelected(taskId) {
  return state.selectedArtifacts.includes(taskId);
}

function setArtifactSelected(taskId, selected) {
  if (!taskId) return;
  const current = new Set(state.selectedArtifacts);
  if (selected) {
    current.add(taskId);
  } else {
    current.delete(taskId);
  }
  state.selectedArtifacts = Array.from(current);
}

function clearArtifactSelection() {
  state.selectedArtifacts = [];
}

function renderArtifacts(items) {
  if (!artifactList) return;
  artifactList.innerHTML = "";
  const validIds = new Set(items.map((entry) => entry.task_id));
  state.selectedArtifacts = state.selectedArtifacts.filter((id) => validIds.has(id));
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No artifacts yet.";
    artifactList.appendChild(empty);
    clearArtifactPreview("No artifacts available.");
    return;
  }
  items.slice(-20).reverse().forEach((entry) => {
    const item = document.createElement("div");
    item.className = "list-item";
    const status = entry.success === true ? "OK" : entry.success === false ? "FAIL" : "UNKNOWN";
    const prompt = truncate(entry.prompt || "", 110);
    const header = document.createElement("div");
    header.className = "artifact-header";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "artifact-select";
    checkbox.checked = isArtifactSelected(entry.task_id);
    checkbox.addEventListener("click", (event) => {
      event.stopPropagation();
      setArtifactSelected(entry.task_id, checkbox.checked);
    });
    const title = document.createElement("div");
    title.className = "artifact-title";
    title.innerHTML = `<strong>${entry.task_id}</strong> ${status}<br>${prompt}`;
    header.appendChild(checkbox);
    header.appendChild(title);
    const actions = document.createElement("div");
    actions.className = "message-actions";
    const openBtn = document.createElement("button");
    openBtn.textContent = "OPEN";
    openBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      loadArtifactDetail(entry.task_id);
    });
    const compareBtn = document.createElement("button");
    compareBtn.textContent = "COMPARE";
    compareBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      setCompareTarget(entry.task_id);
    });
    const rerunBtn = document.createElement("button");
    rerunBtn.textContent = "RERUN";
    rerunBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      rerunArtifact(entry.task_id);
    });
    const archiveBtn = document.createElement("button");
    archiveBtn.textContent = "ARCHIVE";
    archiveBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      archiveArtifact(entry.task_id);
    });
    actions.appendChild(openBtn);
    actions.appendChild(compareBtn);
    actions.appendChild(rerunBtn);
    actions.appendChild(archiveBtn);
    item.appendChild(header);
    item.appendChild(actions);
    item.addEventListener("click", () => {
      loadArtifactDetail(entry.task_id);
    });
    artifactList.appendChild(item);
  });
}

async function loadArtifacts() {
  try {
    clearArtifactPreview();
    const data = await fetchJson("/api/artifacts");
    renderArtifacts(data.tasks || []);
  } catch (err) {
    addError(`Artifacts load failed: ${err.message}`);
  }
}

async function loadArtifactDetail(taskId) {
  if (!taskId) return;
  if (artifactMeta) artifactMeta.textContent = `Loading ${taskId}...`;
  if (artifactPreview) artifactPreview.textContent = "";
  if (artifactFiles) artifactFiles.innerHTML = "";
  try {
    const data = await fetchJson(`/api/artifacts?task_id=${encodeURIComponent(taskId)}`);
    renderArtifactDetail(taskId, data.record || {}, data.artifacts || []);
  } catch (err) {
    addError(`Artifact detail failed: ${err.message}`);
    if (artifactMeta) artifactMeta.textContent = "Preview unavailable.";
  }
}

function renderArtifactDetail(taskId, record, artifacts) {
  const status = record.success === true ? "OK" : record.success === false ? "FAIL" : "UNKNOWN";
  const stamp = record.timestamp || "--";
  if (artifactMeta) {
    artifactMeta.textContent = `Task ${taskId} | ${status} | ${stamp}`;
  }
  renderArtifactFiles(taskId, artifacts);
  if (artifactPreview) {
    artifactPreview.textContent = record.final_answer ? truncate(record.final_answer, 400) : "Select a file to preview.";
  }
}

function renderArtifactFiles(taskId, artifacts) {
  if (!artifactFiles) return;
  artifactFiles.innerHTML = "";
  if (!artifacts.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No files for this task.";
    artifactFiles.appendChild(empty);
    return;
  }
  artifacts.forEach((name) => {
    const item = document.createElement("div");
    item.className = "list-item";
    item.textContent = name;
    item.addEventListener("click", () => {
      previewArtifactFile(taskId, name);
      const path = `${taskId}/${name}`;
      if (artifactLeft && !artifactLeft.value) {
        artifactLeft.value = path;
      } else if (artifactRight && !artifactRight.value) {
        artifactRight.value = path;
      }
    });
    artifactFiles.appendChild(item);
  });
}

async function previewArtifactFile(taskId, name) {
  if (!artifactPreview || !taskId || !name) return;
  artifactPreview.textContent = "Loading preview...";
  const url = `/api/artifact?task_id=${encodeURIComponent(taskId)}&name=${encodeURIComponent(name)}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      artifactPreview.textContent = `Preview failed: ${res.status}`;
      return;
    }
    const type = res.headers.get("Content-Type") || "";
    if (type.startsWith("image/")) {
      const blob = await res.blob();
      if (state.artifactPreviewUrl) {
        URL.revokeObjectURL(state.artifactPreviewUrl);
      }
      state.artifactPreviewUrl = URL.createObjectURL(blob);
      artifactPreview.innerHTML = `<img src="${state.artifactPreviewUrl}" alt="${name}">`;
      return;
    }
    if (type.startsWith("text/") || type.includes("json")) {
      const text = await res.text();
      const lang = detectLanguageFromFile(name);
      const safe = escapeHtml(text);
      if (lang) {
        artifactPreview.innerHTML = `<pre><code class="language-${lang}">${safe}</code></pre>`;
      } else {
        artifactPreview.innerHTML = `<pre><code>${safe}</code></pre>`;
      }
      enhanceCodeBlocks(artifactPreview);
      return;
    }
    artifactPreview.textContent = "Preview not supported for this file type.";
  } catch (err) {
    artifactPreview.textContent = `Preview failed: ${err.message}`;
  }
}

async function searchArtifacts() {
  const query = artifactSearchInput ? artifactSearchInput.value.trim() : "";
  const filters = {};
  if (artifactSuccessFilter && artifactSuccessFilter.value) {
    filters.success = artifactSuccessFilter.value === "true";
  }
  if (artifactSourceFilter && artifactSourceFilter.value.trim()) {
    filters.source = artifactSourceFilter.value.trim();
  }
  if (artifactTagFilter && artifactTagFilter.value.trim()) {
    filters.tag = artifactTagFilter.value.trim();
  }
  if (!query && !Object.keys(filters).length) {
    loadArtifacts();
    return;
  }
  try {
    const label = query ? `Search results for "${query}"` : "Filtered results";
    clearArtifactPreview(label);
    const data = await postJson("/api/artifacts/search", { query, filters });
    renderArtifacts(data.results || []);
    if (artifactMeta) {
      artifactMeta.textContent = label;
    }
  } catch (err) {
    addError(`Artifact search failed: ${err.message}`);
  }
}

async function diffArtifacts() {
  if (!artifactDiff) return;
  const left = artifactLeft ? artifactLeft.value.trim() : "";
  const right = artifactRight ? artifactRight.value.trim() : "";
  if (!left || !right) {
    addError("Diff requires both left and right files.");
    return;
  }
  artifactDiff.textContent = "Diffing...";
  if (artifactDiffList) artifactDiffList.innerHTML = "";
  state.artifactDiffBundle = null;
  try {
    const data = await postJson("/api/artifacts/diff", { left, right });
    const lines = data.diff || [];
    renderDiffLines(lines);
  } catch (err) {
    artifactDiff.textContent = `Diff failed: ${err.message}`;
  }
}

async function diffArtifactsAll() {
  if (!artifactDiff) return;
  const left = artifactLeft ? artifactLeft.value.trim() : "";
  const right = artifactRight ? artifactRight.value.trim() : "";
  if (!left || !right) {
    addError("Compare all requires both task IDs.");
    return;
  }
  artifactDiff.textContent = "Diffing...";
  if (artifactDiffList) artifactDiffList.innerHTML = "";
  try {
    const data = await postJson("/api/artifacts/diff", { left, right, mode: "all" });
    renderDiffBundle(data);
  } catch (err) {
    artifactDiff.textContent = `Diff failed: ${err.message}`;
  }
}

function renderDiffBundle(bundle) {
  state.artifactDiffBundle = bundle;
  if (!artifactDiffList) return;
  artifactDiffList.innerHTML = "";
  const files = (bundle && bundle.files) || [];
  if (!files.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No diff files.";
    artifactDiffList.appendChild(empty);
    artifactDiff.textContent = "";
    return;
  }
  files.forEach((file, idx) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const status = file.status || "both";
    row.innerHTML = `<strong>${file.name}</strong> ${status}`;
    row.addEventListener("click", () => showDiffFile(idx));
    artifactDiffList.appendChild(row);
  });
  showDiffFile(0);
}

function showDiffFile(index) {
  const bundle = state.artifactDiffBundle;
  if (!bundle || !bundle.files || !bundle.files[index]) return;
  const file = bundle.files[index];
  if (file.status !== "both") {
    artifactDiff.textContent = file.status === "left_only"
      ? "Only in left task."
      : "Only in right task.";
    return;
  }
  renderDiffLines(file.diff || []);
}

function renderDiffLines(lines) {
  if (!artifactDiff) return;
  if (!lines || !lines.length) {
    artifactDiff.textContent = "No differences.";
    return;
  }
  const html = lines.map((line) => {
    const safe = escapeHtml(line);
    if (line.startsWith("+") && !line.startsWith("+++")) {
      return `<div class="diff-line diff-add">${safe}</div>`;
    }
    if (line.startsWith("-") && !line.startsWith("---")) {
      return `<div class="diff-line diff-del">${safe}</div>`;
    }
    if (line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++")) {
      return `<div class="diff-line diff-meta">${safe}</div>`;
    }
    return `<div class="diff-line">${safe}</div>`;
  });
  artifactDiff.innerHTML = html.join("");
}

function setCompareTarget(taskId) {
  if (!taskId) return;
  if (artifactLeft && !artifactLeft.value) {
    artifactLeft.value = taskId;
    return;
  }
  if (artifactRight && !artifactRight.value) {
    artifactRight.value = taskId;
    return;
  }
  if (artifactLeft) {
    artifactLeft.value = taskId;
  }
}

async function rerunArtifact(taskId) {
  if (!taskId) return;
  try {
    const data = await postJson("/api/artifacts/rerun", { task_id: taskId, session_id: state.sessionId });
    renderMessage("system", `Rerun started: ${data.task_id}`, { skipStore: true });
    loadArtifacts();
  } catch (err) {
    addError(`Rerun failed: ${err.message}`);
  }
}

async function archiveArtifact(taskId) {
  if (!taskId) return;
  try {
    const data = await postJson("/api/artifacts/archive", { task_id: taskId });
    if (data.download_url) {
      window.open(data.download_url, "_blank");
    }
    renderMessage("system", "Archive ready.", { skipStore: true });
  } catch (err) {
    addError(`Archive failed: ${err.message}`);
  }
}

async function archiveSelectedArtifacts() {
  if (!state.selectedArtifacts.length) {
    addError("No artifacts selected.");
    return;
  }
  try {
    const data = await postJson("/api/artifacts/archive/batch", { task_ids: state.selectedArtifacts });
    if (data.download_url) {
      window.open(data.download_url, "_blank");
    }
    if (data.skipped && data.skipped.length) {
      renderMessage("system", `Skipped ${data.skipped.length} tasks.`, { skipStore: true });
    } else {
      renderMessage("system", "Bundle archive ready.", { skipStore: true });
    }
  } catch (err) {
    addError(`Batch archive failed: ${err.message}`);
  }
}

function clearSelectedArtifacts() {
  clearArtifactSelection();
  loadArtifacts();
}

async function cleanupArtifacts() {
  const payload = {};
  if (cleanupKeepRecent && cleanupKeepRecent.value) {
    payload.keep_recent = Number(cleanupKeepRecent.value);
  }
  if (cleanupMaxDays && cleanupMaxDays.value) {
    payload.max_days = Number(cleanupMaxDays.value);
  }
  if (cleanupKeepFailed && cleanupKeepFailed.value) {
    payload.keep_failed = cleanupKeepFailed.value === "true";
  }
  try {
    const data = await postJson("/api/artifacts/cleanup", payload);
    const removed = data.removed ? data.removed.length : 0;
    const kept = data.kept ? data.kept.length : 0;
    renderMessage("system", `Cleanup done. Removed ${removed}, kept ${kept}.`, { skipStore: true });
    loadArtifacts();
  } catch (err) {
    addError(`Cleanup failed: ${err.message}`);
  }
}

function renderPlugins(catalog, loaded) {
  if (!pluginList) return;
  pluginList.innerHTML = "";
  if (!catalog.length && !loaded.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No plugins found.";
    pluginList.appendChild(empty);
    return;
  }
  if (loaded.length) {
    const header = document.createElement("div");
    header.className = "list-item";
    header.innerHTML = "<strong>LOADED TOOLS</strong>";
    pluginList.appendChild(header);
    loaded.forEach((item) => {
      const row = document.createElement("div");
      row.className = "list-item";
      const perms = (item.permissions || []).join(", ") || "--";
      row.innerHTML = `<strong>${item.name}</strong> ${truncate(item.description || "", 80)}<br>Perms: ${perms}`;
      pluginList.appendChild(row);
    });
  }
  if (catalog.length) {
    const header = document.createElement("div");
    header.className = "list-item";
    header.innerHTML = "<strong>AVAILABLE PLUGINS</strong>";
    pluginList.appendChild(header);
    catalog.forEach((item) => {
      const row = document.createElement("div");
      row.className = "list-item";
      const signed = item.signed ? "SIGNED" : "UNSIGNED";
      row.innerHTML = `<strong>${item.name || "plugin"}</strong> ${signed}<br>${truncate(item.path || "", 120)}`;
      pluginList.appendChild(row);
    });
  }
}

async function loadPlugins() {
  try {
    const data = await fetchJson("/api/plugins");
    renderPlugins(data.plugins || [], data.loaded || []);
  } catch (err) {
    addError(`Plugin sync failed: ${err.message}`);
  }
}

async function reloadPlugins() {
  try {
    await postJson("/api/plugins/reload", {});
    loadPlugins();
    renderMessage("system", "Plugins reloaded.", { skipStore: true });
  } catch (err) {
    addError(`Plugin reload failed: ${err.message}`);
  }
}

async function loadConfig() {
  try {
    const data = await fetchJson("/api/config");
    const config = data.config || {};
    const memory = config.memory || {};
    if (configIterations) configIterations.value = config.agent ? config.agent.max_iterations : "";
    if (configMemory) configMemory.value = memory.max_entries ?? "";
    if (configTemp) configTemp.value = config.model ? config.model.temperature : "";
    if (configContext) configContext.value = memory.max_context_tokens || "";
    if (configModelName) configModelName.value = config.model ? (config.model.main_model_name || config.model.model_name || "") : "";
    if (configBaseUrl) configBaseUrl.value = config.model ? (config.model.base_url || "") : "";
    if (configSystemRatio) configSystemRatio.value = memory.system_token_ratio ?? "";
    if (configHistoryRatio) configHistoryRatio.value = memory.history_token_ratio ?? "";
    if (configFileRatio) configFileRatio.value = memory.file_context_token_ratio ?? "";
    if (configFileChunk) configFileChunk.value = memory.file_context_chunk_size ?? "";
    if (configFileMaxChunks) configFileMaxChunks.value = memory.file_context_max_chunks_per_file ?? "";
    if (configFileMinScore) configFileMinScore.value = memory.file_context_min_score ?? "";
    if (configFileQueryMessages) configFileQueryMessages.value = memory.file_context_query_messages ?? "";
    if (configHistoryRetrieval) {
      configHistoryRetrieval.value = memory.history_retrieval_enabled === true
        ? "true"
        : memory.history_retrieval_enabled === false
          ? "false"
          : "";
    }
    if (configRetrievalRatio) configRetrievalRatio.value = memory.history_retrieval_token_ratio ?? "";
    if (configRetrievalMaxMessages) configRetrievalMaxMessages.value = memory.history_retrieval_max_messages ?? "";
    if (configRetrievalMinScore) configRetrievalMinScore.value = memory.history_retrieval_min_score ?? "";
    if (configRetrievalQueryMessages) configRetrievalQueryMessages.value = memory.history_retrieval_query_messages ?? "";
    if (configRetrievalRoles) {
      configRetrievalRoles.value = Array.isArray(memory.history_retrieval_include_roles)
        ? memory.history_retrieval_include_roles.join(", ")
        : "";
    }
    if (configNotesMaxTokens) configNotesMaxTokens.value = memory.notes_max_tokens ?? "";
    const news = config.news_digest || {};
    if (newsTopicInput) {
      const topics = Array.isArray(news.topics) ? news.topics.join(", ") : "";
      newsTopicInput.value = topics;
    }
    if (newsTimeInput) {
      const timeValue = news.schedule_time || "12:00";
      newsTimeInput.value = timeValue.length >= 5 ? timeValue.slice(0, 5) : timeValue;
    }
    if (newsEnabled) {
      newsEnabled.value = news.enabled === false ? "false" : "true";
    }
    if (newsObsidianEnabled) {
      newsObsidianEnabled.value = news.obsidian_enabled === true ? "true" : "false";
    }
    if (newsObsidianDir) {
      newsObsidianDir.value = news.obsidian_dir || "";
    }
    if (newsObsidianFile) {
      newsObsidianFile.value = news.obsidian_filename || "news_{date}.md";
    }
    const media = config.media_hub || {};
    if (mediaAlertInput) {
      const alerts = Array.isArray(media.alerts) ? media.alerts.join(", ") : "";
      mediaAlertInput.value = alerts;
    }
    if (mediaTimeInput) {
      const timeValue = media.schedule_time || "12:00";
      mediaTimeInput.value = timeValue.length >= 5 ? timeValue.slice(0, 5) : timeValue;
    }
    if (mediaEnabled) {
      mediaEnabled.value = media.enabled === false ? "false" : "true";
    }
    if (mediaObsidianEnabled) {
      mediaObsidianEnabled.value = media.obsidian_enabled === true ? "true" : "false";
    }
    if (mediaObsidianDir) {
      mediaObsidianDir.value = media.obsidian_dir || "";
    }
    if (mediaObsidianFile) {
      mediaObsidianFile.value = media.obsidian_filename || "media_{date}.md";
    }
    state.maxIterations = config.agent ? config.agent.max_iterations : null;
  } catch (err) {
    addError(`Config load failed: ${err.message}`);
  }
}

async function applyConfig() {
  const overrides = { agent: {}, memory: {}, model: {} };
  if (configIterations && configIterations.value) {
    overrides.agent.max_iterations = Number(configIterations.value);
  }
  if (configMemory && configMemory.value) {
    overrides.memory.max_entries = Number(configMemory.value);
  }
  if (configTemp && configTemp.value) {
    overrides.model.temperature = Number(configTemp.value);
  }
  if (configContext && configContext.value) {
    overrides.memory.max_context_tokens = Number(configContext.value);
  }
  if (configModelName && configModelName.value) {
    overrides.model.main_model_name = configModelName.value.trim();
  }
  if (configBaseUrl && configBaseUrl.value) {
    overrides.model.base_url = configBaseUrl.value.trim();
  }
  if (configSystemRatio && configSystemRatio.value !== "") {
    overrides.memory.system_token_ratio = Number(configSystemRatio.value);
  }
  if (configHistoryRatio && configHistoryRatio.value !== "") {
    overrides.memory.history_token_ratio = Number(configHistoryRatio.value);
  }
  if (configFileRatio && configFileRatio.value !== "") {
    overrides.memory.file_context_token_ratio = Number(configFileRatio.value);
  }
  if (configFileChunk && configFileChunk.value !== "") {
    overrides.memory.file_context_chunk_size = Number(configFileChunk.value);
  }
  if (configFileMaxChunks && configFileMaxChunks.value !== "") {
    overrides.memory.file_context_max_chunks_per_file = Number(configFileMaxChunks.value);
  }
  if (configFileMinScore && configFileMinScore.value !== "") {
    overrides.memory.file_context_min_score = Number(configFileMinScore.value);
  }
  if (configFileQueryMessages && configFileQueryMessages.value !== "") {
    overrides.memory.file_context_query_messages = Number(configFileQueryMessages.value);
  }
  if (configHistoryRetrieval && configHistoryRetrieval.value !== "") {
    overrides.memory.history_retrieval_enabled = configHistoryRetrieval.value === "true";
  }
  if (configRetrievalRatio && configRetrievalRatio.value !== "") {
    overrides.memory.history_retrieval_token_ratio = Number(configRetrievalRatio.value);
  }
  if (configRetrievalMaxMessages && configRetrievalMaxMessages.value !== "") {
    overrides.memory.history_retrieval_max_messages = Number(configRetrievalMaxMessages.value);
  }
  if (configRetrievalMinScore && configRetrievalMinScore.value !== "") {
    overrides.memory.history_retrieval_min_score = Number(configRetrievalMinScore.value);
  }
  if (configRetrievalQueryMessages && configRetrievalQueryMessages.value !== "") {
    overrides.memory.history_retrieval_query_messages = Number(configRetrievalQueryMessages.value);
  }
  if (configRetrievalRoles && configRetrievalRoles.value.trim()) {
    overrides.memory.history_retrieval_include_roles = parseCsvList(configRetrievalRoles.value);
  }
  if (configNotesMaxTokens && configNotesMaxTokens.value !== "") {
    overrides.memory.notes_max_tokens = Number(configNotesMaxTokens.value);
  }
  try {
    await postJson("/api/config", { overrides });
    renderMessage("system", "Config applied.", { skipStore: true });
    loadConfig();
    loadInfo();
  } catch (err) {
    addError(`Config update failed: ${err.message}`);
  }
}

function renderProfiles(profiles, currentProfile) {
  if (!profileSelect) return;
  profileSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select profile";
  profileSelect.appendChild(placeholder);
  profiles.forEach((profile) => {
    const option = document.createElement("option");
    option.value = profile.name;
    option.textContent = profile.name;
    if (currentProfile && profile.name === currentProfile) {
      option.selected = true;
    }
    profileSelect.appendChild(option);
  });
  if (currentProfile && profileNameEl) {
    profileNameEl.textContent = currentProfile;
  }
}

async function loadProfiles() {
  if (!state.sessionId) return;
  try {
    const data = await fetchJson(`/api/profiles?session_id=${encodeURIComponent(state.sessionId)}`);
    renderProfiles(data.profiles || [], data.current_profile || data.active_profile);
  } catch (err) {
    addError(`Profile load failed: ${err.message}`);
  }
}

async function applyProfile() {
  if (!state.sessionId || !profileSelect) return;
  const value = profileSelect.value;
  if (!value) return;
  try {
    await postJson("/api/profile", { session_id: state.sessionId, profile: value });
    renderMessage("system", `Profile switched to ${value}.`, { skipStore: true });
    await loadInfo();
    await loadConfig();
    await loadProfiles();
  } catch (err) {
    addError(`Profile apply failed: ${err.message}`);
  }
}

function renderKbStatus(data) {
  if (!kbStatus) return;
  if (!data) {
    kbStatus.textContent = "KB not available.";
    return;
  }
  if (data.enabled === false) {
    kbStatus.textContent = "KB disabled.";
    return;
  }
  kbStatus.textContent = `Entries ${data.total_entries || 0} | Files ${data.files || 0}`;
}

function highlightTerms(text, query) {
  if (!query) return escapeHtml(text || "");
  const terms = (query.toLowerCase().match(/[a-z0-9\u4e00-\u9fff]{2,}/g) || [])
    .filter((value, index, self) => self.indexOf(value) === index)
    .slice(0, 8);
  if (!terms.length) {
    return escapeHtml(text || "");
  }
  let safe = escapeHtml(text || "");
  terms.forEach((term) => {
    const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    safe = safe.replace(regex, (match) => `<mark>${match}</mark>`);
  });
  return safe;
}

function renderKbAliases(aliases) {
  if (!kbAliases) return;
  kbAliases.innerHTML = "";
  const entries = aliases && typeof aliases === "object" ? Object.entries(aliases) : [];
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No aliases.";
    kbAliases.appendChild(empty);
    return;
  }
  entries.forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>@${key}</strong> ${value}`;
    kbAliases.appendChild(row);
  });
}

function renderKbResults(items, query = "") {
  if (!kbResults) return;
  kbResults.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No results.";
    kbResults.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const snippet = highlightTerms(truncate(item.snippet || "", 120), query);
    row.innerHTML = `<strong>${escapeHtml(item.path)}</strong><br>Score ${item.score} | Chunk ${item.chunk_id}<br>${snippet}`;
    row.addEventListener("click", () => loadKbEntry(item.path, item.chunk_id));
    kbResults.appendChild(row);
  });
}

async function loadKbStatus() {
  try {
    const data = await fetchJson("/api/kb/status");
    renderKbStatus(data);
    renderKbAliases(data.aliases || {});
  } catch (err) {
    renderKbStatus(null);
    renderKbAliases({});
    addError(`KB status failed: ${err.message}`);
  }
}

async function searchKb() {
  const query = kbSearchInput ? kbSearchInput.value.trim() : "";
  if (!query) {
    renderKbResults([], "");
    if (kbPreview) kbPreview.textContent = "";
    return;
  }
  try {
    const data = await postJson("/api/kb/search", { query });
    renderKbResults(data.results || [], query);
  } catch (err) {
    addError(`KB search failed: ${err.message}`);
  }
}

async function indexKb(fullRebuild) {
  const raw = kbPathInput ? kbPathInput.value.trim() : "";
  const paths = raw ? raw.split(",").map((item) => item.trim()).filter(Boolean) : [];
  try {
    await postJson("/api/kb/index", { paths, full_rebuild: Boolean(fullRebuild) });
    await loadKbStatus();
    renderMessage("system", "KB index updated.", { skipStore: true });
  } catch (err) {
    addError(`KB index failed: ${err.message}`);
  }
}

async function clearKb() {
  try {
    await postJson("/api/kb/clear", {});
    await loadKbStatus();
    renderKbResults([]);
    if (kbPreview) kbPreview.textContent = "";
  } catch (err) {
    addError(`KB clear failed: ${err.message}`);
  }
}

async function loadKbEntry(path, chunkId) {
  if (!kbPreview) return;
  kbPreview.textContent = "Loading...";
  try {
    const data = await fetchJson(`/api/kb/entry?path=${encodeURIComponent(path)}&chunk_id=${encodeURIComponent(chunkId)}`);
    kbPreview.textContent = data.content || "";
  } catch (err) {
    kbPreview.textContent = `Preview failed: ${err.message}`;
  }
}

function renderTaskStats(stats) {
  if (!taskStats) return;
  taskStats.innerHTML = "";
  if (!stats || !stats.total) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No task stats yet.";
    taskStats.appendChild(empty);
    return;
  }
  const counts = stats.counts || {};
  const summary = document.createElement("div");
  summary.className = "list-item";
  summary.innerHTML = `<strong>Total ${stats.total || 0}</strong><br>Todo ${counts.todo || 0} | Doing ${counts.doing || 0} | Blocked ${counts.blocked || 0} | Done ${counts.done || 0}`;
  taskStats.appendChild(summary);
  if (stats.priorities && stats.priorities.length) {
    const priorityRow = document.createElement("div");
    priorityRow.className = "list-item";
    priorityRow.innerHTML = `<strong>Priorities</strong><br>${stats.priorities.map((item) => `${escapeHtml(item.label)} ${item.count}`).join(" | ")}`;
    taskStats.appendChild(priorityRow);
  }
  if (stats.tags && stats.tags.length) {
    const tagsRow = document.createElement("div");
    tagsRow.className = "list-item";
    tagsRow.innerHTML = `<strong>Tags</strong><br>${stats.tags.slice(0, 8).map((item) => `${escapeHtml(item.label)} ${item.count}`).join(" | ")}`;
    taskStats.appendChild(tagsRow);
  }
}

function renderTaskList(items) {
  if (!taskList) return;
  taskList.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No tasks yet.";
    taskList.appendChild(empty);
    return;
  }
  items.forEach((task) => {
    const row = document.createElement("div");
    row.className = "list-item task-item";
    row.dataset.taskId = task.id;
    const tags = Array.isArray(task.tags) ? task.tags : [];
    const tagMarkup = tags.length
      ? `<div class="task-meta">${tags.map((tag) => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join(" ")}</div>`
      : "";
    const due = task.due ? `Due ${escapeHtml(task.due)}` : "No due date";
    const archived = task.archived ? " | ARCHIVED" : "";
    row.innerHTML = `
      <div class="task-title">${escapeHtml(task.title || "Untitled")}</div>
      <div class="task-meta">Status ${escapeHtml(String(task.status || "todo").toUpperCase())} | Priority ${escapeHtml(String(task.priority || "P2").toUpperCase())} | ${due}${archived}</div>
      ${tagMarkup}
      <div class="list-actions">
        <button data-action="start" data-task-id="${task.id}">START</button>
        <button data-action="done" data-task-id="${task.id}" class="ghost">DONE</button>
        <button data-action="block" data-task-id="${task.id}" class="ghost">BLOCK</button>
        <button data-action="archive" data-task-id="${task.id}" class="ghost">ARCHIVE</button>
        <button data-action="remove" data-task-id="${task.id}" class="ghost">DELETE</button>
      </div>
    `;
    taskList.appendChild(row);
  });
}

async function loadTasks() {
  try {
    const data = await fetchJson("/api/tasks");
    state.taskBoard.items = data.tasks || [];
    renderTaskList(state.taskBoard.items);
    syncTodoTasks(state.taskBoard.items);
  } catch (err) {
    addError(`Task load failed: ${err.message}`);
  }
  try {
    const stats = await fetchJson("/api/tasks/stats");
    state.taskBoard.stats = stats || {};
    renderTaskStats(state.taskBoard.stats);
  } catch (err) {
    renderTaskStats(null);
  }
}

function fillTaskForm(task) {
  if (!task) return;
  state.taskBoard.selectedId = task.id;
  if (taskTitleInput) taskTitleInput.value = task.title || "";
  if (taskStatusInput) taskStatusInput.value = task.status || "todo";
  if (taskPriorityInput) taskPriorityInput.value = task.priority || "P2";
  if (taskTagsInput) taskTagsInput.value = Array.isArray(task.tags) ? task.tags.join(", ") : "";
  if (taskDueInput) taskDueInput.value = task.due ? task.due.slice(0, 19) : "";
  if (taskLinksInput) taskLinksInput.value = Array.isArray(task.links) ? task.links.join(", ") : "";
  if (taskNotesInput) taskNotesInput.value = task.notes || "";
}

async function addTask() {
  if (!taskTitleInput) return;
  const title = taskTitleInput.value.trim();
  if (!title) {
    addError("Task title required.");
    return;
  }
  const payload = {
    title,
    status: taskStatusInput ? taskStatusInput.value : "todo",
    priority: taskPriorityInput ? taskPriorityInput.value : "P2",
    tags: parseCsvList(taskTagsInput ? taskTagsInput.value : ""),
    due: taskDueInput ? taskDueInput.value : "",
    notes: taskNotesInput ? taskNotesInput.value.trim() : "",
    links: parseCsvList(taskLinksInput ? taskLinksInput.value : ""),
  };
  try {
    await postJson("/api/tasks", payload);
    if (taskTitleInput) taskTitleInput.value = "";
    if (taskNotesInput) taskNotesInput.value = "";
    if (taskLinksInput) taskLinksInput.value = "";
    if (taskTagsInput) taskTagsInput.value = "";
    await loadTasks();
  } catch (err) {
    addError(`Task add failed: ${err.message}`);
  }
}

async function updateTaskItem(taskId, updates) {
  if (!taskId) return;
  try {
    await postJson("/api/tasks", { action: "update", id: taskId, updates });
    await loadTasks();
  } catch (err) {
    addError(`Task update failed: ${err.message}`);
  }
}

async function removeTaskItem(taskId) {
  if (!taskId) return;
  try {
    await postJson("/api/tasks", { action: "remove", id: taskId });
    await loadTasks();
  } catch (err) {
    addError(`Task remove failed: ${err.message}`);
  }
}

function handleTaskListClick(event) {
  const button = event.target.closest("button");
  const row = event.target.closest(".task-item");
  if (!row) return;
  const taskId = row.dataset.taskId;
  if (!taskId) return;
  if (!button) {
    const item = state.taskBoard.items.find((entry) => entry.id === taskId);
    if (item) fillTaskForm(item);
    return;
  }
  const action = button.dataset.action;
  if (action === "start") {
    updateTaskItem(taskId, { status: "doing" });
    return;
  }
  if (action === "done") {
    updateTaskItem(taskId, { status: "done" });
    return;
  }
  if (action === "block") {
    updateTaskItem(taskId, { status: "blocked" });
    return;
  }
  if (action === "archive") {
    updateTaskItem(taskId, { archived: true });
    return;
  }
  if (action === "remove") {
    removeTaskItem(taskId);
  }
}

function initTodoSections() {
  Object.entries(todoSections).forEach(([key, list]) => {
    if (list) {
      list.dataset.section = key;
    }
  });
}

function loadTodoFilters() {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(todoFiltersKey) || "{}");
  } catch (err) {
    stored = {};
  }
  const query = typeof stored.query === "string" ? stored.query : "";
  const tags = Array.isArray(stored.tags) ? stored.tags : [];
  state.todo.filters = { query, tags };
  if (todoSearchInput) todoSearchInput.value = query;
  if (todoTagFilterInput) todoTagFilterInput.value = tags.join(", ");
}

function saveTodoFilters() {
  localStorage.setItem(todoFiltersKey, JSON.stringify(state.todo.filters || { query: "", tags: [] }));
}

function applyTodoFilters() {
  if (!state.todo.filters) {
    state.todo.filters = { query: "", tags: [] };
  }
  state.todo.filters.query = todoSearchInput ? todoSearchInput.value.trim() : "";
  state.todo.filters.tags = parseCsvList(todoTagFilterInput ? todoTagFilterInput.value : "");
  saveTodoFilters();
  renderTodoBoard();
}

function clearTodoFilters() {
  if (todoSearchInput) todoSearchInput.value = "";
  if (todoTagFilterInput) todoTagFilterInput.value = "";
  state.todo.filters = { query: "", tags: [] };
  saveTodoFilters();
  renderTodoBoard();
}

function loadTodoCollapses() {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(todoCollapseKey) || "{}");
  } catch (err) {
    stored = {};
  }
  document.querySelectorAll(".todo-collapse").forEach((section) => {
    const key = section.dataset.collapse;
    if (!key) return;
    section.classList.toggle("collapsed", stored[key] === true);
  });
}

function saveTodoCollapses() {
  const states = {};
  document.querySelectorAll(".todo-collapse").forEach((section) => {
    const key = section.dataset.collapse;
    if (!key) return;
    states[key] = section.classList.contains("collapsed");
  });
  localStorage.setItem(todoCollapseKey, JSON.stringify(states));
}

function toggleTodoCollapse(target) {
  if (!target) return;
  const block = document.querySelector(`.todo-collapse[data-collapse="${target}"]`);
  if (!block) return;
  block.classList.toggle("collapsed");
  saveTodoCollapses();
}

function canDragTodo() {
  const filters = state.todo.filters || { query: "", tags: [] };
  const hasQuery = Boolean((filters.query || "").trim());
  const hasTags = Array.isArray(filters.tags) && filters.tags.length > 0;
  return !(hasQuery || hasTags);
}

function getTodoDropSlot() {
  if (!todoDropSlot) {
    todoDropSlot = document.createElement("div");
    todoDropSlot.className = "todo-drop-slot";
  }
  return todoDropSlot;
}

function clearTodoDropSlot() {
  if (todoDropSlot && todoDropSlot.parentElement) {
    todoDropSlot.parentElement.removeChild(todoDropSlot);
  }
}

function clearTodoDragOver() {
  Object.values(todoSections).forEach((section) => {
    if (section) {
      section.classList.remove("drag-over");
    }
  });
}

function getTodoDragAfterElement(container, y) {
  const elements = Array.from(container.querySelectorAll(".todo-item:not(.dragging)"));
  return elements.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      return { offset, element: child };
    }
    return closest;
  }, { offset: Number.NEGATIVE_INFINITY, element: null }).element;
}

function handleTodoDragStart(event) {
  const card = event.target.closest(".todo-item");
  if (!card || !canDragTodo()) {
    event.preventDefault();
    return;
  }
  const container = card.closest(".todo-items");
  state.todo.drag = {
    taskId: card.dataset.taskId || "",
    sourceSection: container ? container.dataset.section || "" : "",
  };
  card.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", state.todo.drag.taskId || "");
}

function handleTodoDragEnd(event) {
  const card = event.target.closest(".todo-item");
  if (card) {
    card.classList.remove("dragging");
  }
  clearTodoDropSlot();
  clearTodoDragOver();
  state.todo.drag = { taskId: null, sourceSection: "" };
}

function handleTodoDragOver(event) {
  if (!canDragTodo()) return;
  event.preventDefault();
  const container = event.currentTarget;
  if (!container) return;
  const after = getTodoDragAfterElement(container, event.clientY);
  const slot = getTodoDropSlot();
  if (!after) {
    container.appendChild(slot);
  } else if (after.parentElement === container) {
    container.insertBefore(slot, after);
  }
  container.classList.add("drag-over");
}

function handleTodoDrop(event) {
  if (!canDragTodo()) return;
  event.preventDefault();
  const container = event.currentTarget;
  if (!container) return;
  const taskId = state.todo.drag.taskId || event.dataTransfer.getData("text/plain");
  if (!taskId) return;
  const targetSection = container.dataset.section || "";
  const slot = getTodoDropSlot();
  const card = document.querySelector(`.todo-item[data-task-id="${taskId}"]`);
  if (card) {
    if (slot.parentElement === container) {
      container.insertBefore(card, slot);
    } else {
      container.appendChild(card);
    }
  }
  const emptyRow = container.querySelector(".list-item");
  if (emptyRow && container.querySelector(".todo-item")) {
    emptyRow.remove();
  }
  clearTodoDropSlot();
  clearTodoDragOver();
  applyTodoDrop(taskId, targetSection);
}

function buildTodoOrderUpdates(container) {
  if (!container) return [];
  const ids = Array.from(container.querySelectorAll(".todo-item"))
    .map((item) => item.dataset.taskId)
    .filter((value) => value);
  return ids.map((id, index) => ({ id, updates: { order: (index + 1) * 1000 } }));
}

function mergeTodoUpdateEntries(entries) {
  const merged = {};
  entries.forEach((entry) => {
    if (!entry || !entry.id || !entry.updates) return;
    merged[entry.id] = { ...(merged[entry.id] || {}), ...entry.updates };
  });
  return Object.entries(merged).map(([id, updates]) => ({ id, updates }));
}

async function batchUpdateTodoTasks(entries) {
  if (!entries.length) return;
  const results = await Promise.allSettled(
    entries.map((entry) => postJson("/api/tasks", { action: "update", id: entry.id, updates: entry.updates }))
  );
  const failed = results.filter((res) => res.status === "rejected");
  if (failed.length) {
    addError(`Todo batch update failed: ${failed.length} items.`);
  }
  await loadTasks();
}

function buildTodoMoveUpdates(task, targetSection) {
  if (!task || !targetSection) return {};
  const updates = {};
  const status = String(task.status || "todo").toLowerCase();
  const now = new Date();
  if (targetSection === "blocked") {
    updates.status = "blocked";
  } else if (targetSection === "done") {
    updates.status = "done";
  } else if (status === "blocked" || status === "done") {
    updates.status = "todo";
  }
  if (targetSection === "today") {
    updates.due = formatLocalIso(now);
  } else if (targetSection === "upcoming") {
    const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 2, 10, 0, 0);
    updates.due = formatLocalIso(next);
  } else if (targetSection === "backlog") {
    updates.due = "";
  }
  if (targetSection !== "done" && task.archived) {
    updates.archived = false;
  }
  return updates;
}

async function applyTodoDrop(taskId, targetSection) {
  const task = state.todo.tasks.find((item) => item.id === taskId);
  if (!task) return;
  if (!todoSections[targetSection]) return;
  const updates = [];
  const targetEl = todoSections[targetSection];
  const sourceEl = todoSections[state.todo.drag.sourceSection];
  if (targetEl) {
    updates.push(...buildTodoOrderUpdates(targetEl));
  }
  if (sourceEl && sourceEl !== targetEl) {
    updates.push(...buildTodoOrderUpdates(sourceEl));
  }
  const moveUpdates = buildTodoMoveUpdates(task, targetSection);
  if (Object.keys(moveUpdates).length) {
    updates.push({ id: taskId, updates: moveUpdates });
  }
  const merged = mergeTodoUpdateEntries(updates);
  if (merged.length) {
    await batchUpdateTodoTasks(merged);
  }
}

function loadTodoProjects() {
  try {
    const stored = JSON.parse(localStorage.getItem(todoProjectsKey) || "[]");
    state.todo.projects = Array.isArray(stored) ? stored : [];
  } catch (err) {
    state.todo.projects = [];
  }
}

function saveTodoProjects() {
  localStorage.setItem(todoProjectsKey, JSON.stringify(state.todo.projects));
}

function normalizeProjectName(value) {
  const name = (value || "").trim();
  return name || "Inbox";
}

function getTaskProject(task) {
  return normalizeProjectName(task.project || "");
}

function setTodoView(type, id) {
  state.todo.view = { type, id };
  updateTodoBadges();
  renderTodoProjects();
  renderTodoSmartLists();
  renderTodoBoard();
}

function updateTodoBadges() {
  if (todoProjectBadge) {
    if (state.todo.view.type === "project") {
      todoProjectBadge.textContent = `PROJECT: ${String(state.todo.view.id || "INBOX").toUpperCase()}`;
    } else {
      todoProjectBadge.textContent = `VIEW: ${String(state.todo.view.id || "ALL").toUpperCase()}`;
    }
  }
  if (todoCountBadge) {
    const items = filterTodoTasks(state.todo.tasks || []);
    todoCountBadge.textContent = `TASKS: ${items.length}`;
  }
}

function buildProjectList(tasks) {
  const names = new Set(["Inbox"]);
  (tasks || []).forEach((task) => {
    names.add(getTaskProject(task));
  });
  (state.todo.projects || []).forEach((item) => {
    if (item && item.trim()) names.add(normalizeProjectName(item));
  });
  const list = Array.from(names).sort((a, b) => a.localeCompare(b));
  return ["All", ...list.filter((name) => name !== "All")];
}

function buildProjectCounts(tasks) {
  const counts = {};
  (tasks || []).forEach((task) => {
    const project = getTaskProject(task);
    counts[project] = (counts[project] || 0) + 1;
  });
  counts.All = tasks ? tasks.length : 0;
  return counts;
}

function renderTodoProjects() {
  if (!todoProjectList) return;
  todoProjectList.innerHTML = "";
  const projects = buildProjectList(state.todo.tasks || []);
  const counts = buildProjectCounts(state.todo.tasks || []);
  projects.forEach((project) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.dataset.project = project;
    const active = state.todo.view.type === "project" && state.todo.view.id === project;
    row.classList.toggle("active", active);
    const count = counts[project] || 0;
    row.innerHTML = `<strong>${escapeHtml(project)}</strong> ${count}`;
    todoProjectList.appendChild(row);
  });
}

function buildSmartLists(tasks) {
  const defs = [
    { id: "all", label: "ALL TASKS" },
    { id: "today", label: "TODAY" },
    { id: "overdue", label: "OVERDUE" },
    { id: "no_due", label: "NO DUE" },
    { id: "doing", label: "IN PROGRESS" },
    { id: "blocked", label: "BLOCKED" },
    { id: "done", label: "DONE" },
  ];
  return defs.map((def) => {
    return { ...def, count: filterSmartTasks(tasks, def.id).length };
  });
}

function renderTodoSmartLists() {
  if (!todoSmartList) return;
  todoSmartList.innerHTML = "";
  const lists = buildSmartLists(state.todo.tasks || []);
  state.todo.smartLists = lists;
  lists.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.dataset.smart = item.id;
    const active = state.todo.view.type === "smart" && state.todo.view.id === item.id;
    row.classList.toggle("active", active);
    row.innerHTML = `<strong>${escapeHtml(item.label)}</strong> ${item.count || 0}`;
    todoSmartList.appendChild(row);
  });
}

function parseTaskDue(task) {
  if (!task || !task.due) return null;
  const value = new Date(task.due);
  if (Number.isNaN(value.getTime())) return null;
  return value;
}

function formatTaskDue(value) {
  if (!value) return "NO DUE";
  const dt = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(dt.getTime())) return String(value);
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

function isTaskDone(task) {
  const status = String(task.status || "").toLowerCase();
  return status === "done" || task.archived === true;
}

function filterSmartTasks(tasks, smartId) {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrowStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return (tasks || []).filter((task) => {
    const due = parseTaskDue(task);
    const status = String(task.status || "").toLowerCase();
    if (smartId === "done") {
      return isTaskDone(task);
    }
    if (smartId === "blocked") {
      return status === "blocked" && !isTaskDone(task);
    }
    if (isTaskDone(task)) return false;
    if (smartId === "doing") {
      return status === "doing";
    }
    if (smartId === "no_due") {
      return !due;
    }
    if (smartId === "today") {
      return due && due >= todayStart && due < tomorrowStart;
    }
    if (smartId === "overdue") {
      return due && due < todayStart;
    }
    return true;
  });
}

function filterTodoByQuery(tasks) {
  const raw = (state.todo.filters && state.todo.filters.query) || "";
  const query = raw.trim().toLowerCase();
  if (!query) return tasks;
  const terms = query.split(/\s+/).filter((item) => item);
  if (!terms.length) return tasks;
  return (tasks || []).filter((task) => {
    const haystack = [
      task.title,
      task.notes,
      task.project,
      ...(Array.isArray(task.tags) ? task.tags : []),
      ...(Array.isArray(task.links) ? task.links : []),
    ]
      .filter((item) => item)
      .join(" ")
      .toLowerCase();
    return terms.every((term) => haystack.includes(term));
  });
}

function filterTodoByTags(tasks) {
  const tags = Array.isArray(state.todo.filters && state.todo.filters.tags)
    ? state.todo.filters.tags
    : [];
  if (!tags.length) return tasks;
  const normalized = tags.map((tag) => String(tag).toLowerCase());
  return (tasks || []).filter((task) => {
    const taskTags = Array.isArray(task.tags)
      ? task.tags.map((tag) => String(tag).toLowerCase())
      : [];
    return normalized.every((tag) => taskTags.includes(tag));
  });
}

function filterTodoTasks(tasks) {
  const view = state.todo.view || { type: "project", id: "Inbox" };
  let filtered = tasks || [];
  if (view.type === "smart") {
    filtered = filterSmartTasks(filtered, view.id);
  } else if (view.id !== "All") {
    filtered = filtered.filter((task) => getTaskProject(task) === view.id);
  }
  filtered = filterTodoByQuery(filtered);
  filtered = filterTodoByTags(filtered);
  return filtered;
}

function classifyTodoTasks(tasks) {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrowStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const weekEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 7);
  const groups = {
    today: [],
    upcoming: [],
    backlog: [],
    blocked: [],
    done: [],
  };
  (tasks || []).forEach((task) => {
    const status = String(task.status || "").toLowerCase();
    if (isTaskDone(task)) {
      groups.done.push(task);
      return;
    }
    if (status === "blocked") {
      groups.blocked.push(task);
      return;
    }
    const due = parseTaskDue(task);
    if (due && due < todayStart) {
      groups.today.push(task);
      return;
    }
    if (due && due >= todayStart && due < tomorrowStart) {
      groups.today.push(task);
      return;
    }
    if (due && due >= tomorrowStart && due < weekEnd) {
      groups.upcoming.push(task);
      return;
    }
    groups.backlog.push(task);
  });
  return groups;
}

function getTodoOrderValue(task) {
  const raw = task ? task.order : null;
  if (raw === undefined || raw === null) return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function compareTodoItems(a, b) {
  const orderA = getTodoOrderValue(a);
  const orderB = getTodoOrderValue(b);
  if (orderA !== null && orderB !== null) return orderA - orderB;
  if (orderA !== null) return -1;
  if (orderB !== null) return 1;
  const dueA = parseTaskDue(a);
  const dueB = parseTaskDue(b);
  if (dueA && dueB) return dueA.getTime() - dueB.getTime();
  if (dueA && !dueB) return -1;
  if (!dueA && dueB) return 1;
  const priorityOrder = { P0: 0, P1: 1, P2: 2, P3: 3 };
  const prioA = priorityOrder[String(a.priority || "P2").toUpperCase()] ?? 9;
  const prioB = priorityOrder[String(b.priority || "P2").toUpperCase()] ?? 9;
  if (prioA !== prioB) return prioA - prioB;
  const updatedA = String(a.updated_at || a.created_at || "");
  const updatedB = String(b.updated_at || b.created_at || "");
  return updatedA.localeCompare(updatedB);
}

function sortTodoItems(items) {
  return (items || []).slice().sort(compareTodoItems);
}

function renderTodoSection(target, items) {
  if (!target) return;
  target.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No tasks.";
    target.appendChild(empty);
    return;
  }
  sortTodoItems(items).forEach((task) => {
    const row = document.createElement("div");
    row.className = "todo-item";
    row.dataset.taskId = task.id;
    row.classList.toggle("active", task.id === state.todo.selectedTaskId);
    const due = parseTaskDue(task);
    const priority = String(task.priority || "P2").toUpperCase();
    const status = String(task.status || "todo").toUpperCase();
    const project = getTaskProject(task);
    const overdue = due && due.getTime() < Date.now();
    const priorityClass = `priority-${priority.toLowerCase()}`;
    row.classList.toggle("overdue", overdue);
    row.draggable = canDragTodo();
    if (row.draggable) {
      row.addEventListener("dragstart", handleTodoDragStart);
      row.addEventListener("dragend", handleTodoDragEnd);
    }
    row.innerHTML = `
      <div class="todo-title">${escapeHtml(task.title || "Untitled")}</div>
      <div class="todo-meta">
        <span class="todo-pill ${priorityClass}">${escapeHtml(priority)}</span>
        <span class="todo-pill">${escapeHtml(status)}</span>
        <span class="todo-pill">${escapeHtml(project)}</span>
        <span class="todo-pill">${escapeHtml(formatTaskDue(due))}</span>
      </div>
      <div class="todo-actions">
        <button data-action="start" data-task-id="${task.id}">START</button>
        <button data-action="done" data-task-id="${task.id}" class="ghost">DONE</button>
        <button data-action="block" data-task-id="${task.id}" class="ghost">BLOCK</button>
      </div>
    `;
    target.appendChild(row);
  });
}

function renderTodoBoard() {
  const filtered = filterTodoTasks(state.todo.tasks || []);
  const groups = classifyTodoTasks(filtered);
  renderTodoSection(todoTodayList, groups.today);
  renderTodoSection(todoUpcomingList, groups.upcoming);
  renderTodoSection(todoBacklogList, groups.backlog);
  renderTodoSection(todoBlockedList, groups.blocked);
  renderTodoSection(todoDoneList, groups.done);
  updateTodoBadges();
}

function syncTodoTasks(tasks) {
  state.todo.tasks = tasks || [];
  if (!state.todo.projects.length) {
    loadTodoProjects();
  }
  const projects = buildProjectList(state.todo.tasks || []);
  if (state.todo.view.type === "project" && !projects.includes(state.todo.view.id)) {
    state.todo.view = { type: "project", id: "Inbox" };
  }
  renderTodoProjects();
  renderTodoSmartLists();
  renderTodoBoard();
  const selected = state.todo.selectedTaskId;
  if (selected && !state.todo.tasks.some((task) => task.id === selected)) {
    state.todo.selectedTaskId = null;
    clearTodoDetail();
  }
}

function addTodoProject() {
  if (!todoProjectInput) return;
  const name = normalizeProjectName(todoProjectInput.value);
  if (!name || state.todo.projects.includes(name)) {
    todoProjectInput.value = "";
    return;
  }
  state.todo.projects = [...state.todo.projects, name];
  saveTodoProjects();
  todoProjectInput.value = "";
  setTodoView("project", name);
}

async function addTodoQuickTask() {
  if (!todoQuickInput) return;
  const title = todoQuickInput.value.trim();
  if (!title) return;
  const project = state.todo.view.type === "project" && state.todo.view.id && state.todo.view.id !== "All"
    ? state.todo.view.id
    : "Inbox";
  const payload = {
    title,
    project,
    priority: todoQuickPriority ? todoQuickPriority.value : "P2",
    due: todoQuickDue ? todoQuickDue.value : "",
    status: "todo",
  };
  try {
    await postJson("/api/tasks", payload);
    todoQuickInput.value = "";
    if (todoQuickDue) todoQuickDue.value = "";
    await loadTasks();
  } catch (err) {
    addError(`Quick add failed: ${err.message}`);
  }
}

function handleTodoProjectClick(event) {
  const row = event.target.closest(".list-item");
  if (!row || !row.dataset.project) return;
  setTodoView("project", row.dataset.project);
}

function handleTodoSmartClick(event) {
  const row = event.target.closest(".list-item");
  if (!row || !row.dataset.smart) return;
  setTodoView("smart", row.dataset.smart);
}

function handleTodoItemClick(event) {
  const button = event.target.closest("button");
  const card = event.target.closest(".todo-item");
  if (!card) return;
  const taskId = card.dataset.taskId;
  if (!taskId) return;
  if (button) {
    const action = button.dataset.action;
    if (action === "start") {
      updateTodoTask(taskId, { status: "doing" });
      return;
    }
    if (action === "done") {
      updateTodoTask(taskId, { status: "done" });
      return;
    }
    if (action === "block") {
      updateTodoTask(taskId, { status: "blocked" });
      return;
    }
  }
  selectTodoTask(taskId);
}

function selectTodoTask(taskId) {
  state.todo.selectedTaskId = taskId;
  const task = state.todo.tasks.find((item) => item.id === taskId);
  if (task) {
    fillTodoDetail(task);
  }
  renderTodoBoard();
}

function fillTodoDetail(task) {
  if (!task) return;
  if (todoDetailTitle) todoDetailTitle.value = task.title || "";
  if (todoDetailStatus) todoDetailStatus.value = task.status || "todo";
  if (todoDetailPriority) todoDetailPriority.value = task.priority || "P2";
  if (todoDetailProject) todoDetailProject.value = getTaskProject(task);
  if (todoDetailDue) todoDetailDue.value = task.due ? task.due.slice(0, 19) : "";
  if (todoDetailTags) todoDetailTags.value = Array.isArray(task.tags) ? task.tags.join(", ") : "";
  if (todoDetailLinks) todoDetailLinks.value = Array.isArray(task.links) ? task.links.join(", ") : "";
  if (todoDetailNotes) todoDetailNotes.value = task.notes || "";
}

function clearTodoDetail() {
  if (todoDetailTitle) todoDetailTitle.value = "";
  if (todoDetailStatus) todoDetailStatus.value = "todo";
  if (todoDetailPriority) todoDetailPriority.value = "P2";
  if (todoDetailProject) todoDetailProject.value = "";
  if (todoDetailDue) todoDetailDue.value = "";
  if (todoDetailTags) todoDetailTags.value = "";
  if (todoDetailLinks) todoDetailLinks.value = "";
  if (todoDetailNotes) todoDetailNotes.value = "";
}

async function updateTodoTask(taskId, updates) {
  try {
    await postJson("/api/tasks", { action: "update", id: taskId, updates });
    await loadTasks();
  } catch (err) {
    addError(`Todo update failed: ${err.message}`);
  }
}

async function saveTodoDetail() {
  if (!state.todo.selectedTaskId) return;
  const updates = {
    title: todoDetailTitle ? todoDetailTitle.value.trim() : "",
    status: todoDetailStatus ? todoDetailStatus.value : "todo",
    priority: todoDetailPriority ? todoDetailPriority.value : "P2",
    project: todoDetailProject ? todoDetailProject.value.trim() : "",
    due: todoDetailDue ? todoDetailDue.value : "",
    tags: parseCsvList(todoDetailTags ? todoDetailTags.value : ""),
    links: parseCsvList(todoDetailLinks ? todoDetailLinks.value : ""),
    notes: todoDetailNotes ? todoDetailNotes.value.trim() : "",
  };
  await updateTodoTask(state.todo.selectedTaskId, updates);
}

async function archiveTodoTask() {
  if (!state.todo.selectedTaskId) return;
  await updateTodoTask(state.todo.selectedTaskId, { archived: true, status: "done" });
}

async function deleteTodoTask() {
  if (!state.todo.selectedTaskId) return;
  try {
    await postJson("/api/tasks", { action: "remove", id: state.todo.selectedTaskId });
    state.todo.selectedTaskId = null;
    clearTodoDetail();
    await loadTasks();
  } catch (err) {
    addError(`Todo delete failed: ${err.message}`);
  }
}

function renderBookmarks(items) {
  if (!bookmarkList) return;
  bookmarkList.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No bookmarks yet.";
    bookmarkList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item bookmark-item";
    row.dataset.bookmarkId = item.id;
    const tags = Array.isArray(item.tags) ? item.tags : [];
    const tagMarkup = tags.length
      ? `<div class="bookmark-meta">${tags.map((tag) => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join(" ")}</div>`
      : "";
    const pinned = item.pinned ? " | PINNED" : "";
    row.innerHTML = `
      <div class="bookmark-title"><a href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener">${escapeHtml(item.title || "Untitled")}</a></div>
      <div class="bookmark-meta">${escapeHtml(item.source || "direct")} ${pinned}</div>
      ${tagMarkup}
      <div class="list-actions">
        <button data-action="open" data-bookmark-id="${item.id}">OPEN</button>
        <button data-action="pin" data-bookmark-id="${item.id}" class="ghost">${item.pinned ? "UNPIN" : "PIN"}</button>
        <button data-action="remove" data-bookmark-id="${item.id}" class="ghost">DELETE</button>
      </div>
    `;
    bookmarkList.appendChild(row);
  });
}

async function loadBookmarks() {
  try {
    const data = await fetchJson("/api/bookmarks");
    state.bookmarks.items = data.items || [];
    renderBookmarks(state.bookmarks.items);
  } catch (err) {
    addError(`Bookmark load failed: ${err.message}`);
  }
}

function fillBookmarkForm(item) {
  if (!item) return;
  state.bookmarks.selectedId = item.id;
  if (bookmarkTitleInput) bookmarkTitleInput.value = item.title || "";
  if (bookmarkUrlInput) bookmarkUrlInput.value = item.url || "";
  if (bookmarkTagsInput) bookmarkTagsInput.value = Array.isArray(item.tags) ? item.tags.join(", ") : "";
  if (bookmarkSourceInput) bookmarkSourceInput.value = item.source || "";
  if (bookmarkNotesInput) bookmarkNotesInput.value = item.notes || "";
}

async function addBookmark() {
  if (!bookmarkTitleInput || !bookmarkUrlInput) return;
  const title = bookmarkTitleInput.value.trim();
  const url = bookmarkUrlInput.value.trim();
  if (!title || !url) {
    addError("Title and URL required.");
    return;
  }
  const payload = {
    title,
    url,
    tags: parseCsvList(bookmarkTagsInput ? bookmarkTagsInput.value : ""),
    source: bookmarkSourceInput ? bookmarkSourceInput.value.trim() : "",
    notes: bookmarkNotesInput ? bookmarkNotesInput.value.trim() : "",
  };
  try {
    await postJson("/api/bookmarks", payload);
    if (bookmarkTitleInput) bookmarkTitleInput.value = "";
    if (bookmarkUrlInput) bookmarkUrlInput.value = "";
    if (bookmarkTagsInput) bookmarkTagsInput.value = "";
    if (bookmarkSourceInput) bookmarkSourceInput.value = "";
    if (bookmarkNotesInput) bookmarkNotesInput.value = "";
    await loadBookmarks();
  } catch (err) {
    addError(`Bookmark add failed: ${err.message}`);
  }
}

async function updateBookmarkItem(itemId, updates) {
  if (!itemId) return;
  try {
    await postJson("/api/bookmarks", { action: "update", id: itemId, updates });
    await loadBookmarks();
  } catch (err) {
    addError(`Bookmark update failed: ${err.message}`);
  }
}

async function removeBookmarkItem(itemId) {
  if (!itemId) return;
  try {
    await postJson("/api/bookmarks", { action: "remove", id: itemId });
    await loadBookmarks();
  } catch (err) {
    addError(`Bookmark remove failed: ${err.message}`);
  }
}

function handleBookmarkListClick(event) {
  const button = event.target.closest("button");
  const row = event.target.closest(".bookmark-item");
  if (!row) return;
  const itemId = row.dataset.bookmarkId;
  if (!itemId) return;
  const item = state.bookmarks.items.find((entry) => entry.id === itemId);
  if (!button) {
    if (item) fillBookmarkForm(item);
    return;
  }
  const action = button.dataset.action;
  if (action === "open" && item && item.url) {
    window.open(item.url, "_blank");
    return;
  }
  if (action === "pin") {
    updateBookmarkItem(itemId, { pinned: !item?.pinned });
    return;
  }
  if (action === "remove") {
    removeBookmarkItem(itemId);
  }
}

function renderReminders(items) {
  if (!reminderList) return;
  reminderList.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No reminders yet.";
    reminderList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item reminder-item";
    row.dataset.reminderId = item.id;
    row.innerHTML = `
      <div class="reminder-title">${escapeHtml(item.title || "Reminder")}</div>
      <div class="reminder-meta">Due ${escapeHtml(item.due || "--")} | Status ${escapeHtml(String(item.status || "pending").toUpperCase())}</div>
      <div class="list-actions">
        <button data-action="done" data-reminder-id="${item.id}">DONE</button>
        <button data-action="snooze" data-reminder-id="${item.id}" class="ghost">SNOOZE 10M</button>
        <button data-action="remove" data-reminder-id="${item.id}" class="ghost">DELETE</button>
      </div>
    `;
    reminderList.appendChild(row);
  });
}

async function loadReminders() {
  try {
    const data = await fetchJson("/api/reminders");
    state.reminders.items = data.items || [];
    renderReminders(state.reminders.items);
  } catch (err) {
    addError(`Reminder load failed: ${err.message}`);
  }
}

function fillReminderForm(item) {
  if (!item) return;
  state.reminders.selectedId = item.id;
  if (reminderTitleInput) reminderTitleInput.value = item.title || "";
  if (reminderDueInput) reminderDueInput.value = item.due ? item.due.slice(0, 19) : "";
  if (reminderNotesInput) reminderNotesInput.value = item.notes || "";
}

async function addReminder() {
  if (!reminderTitleInput || !reminderDueInput) return;
  const title = reminderTitleInput.value.trim();
  const due = reminderDueInput.value;
  if (!title || !due) {
    addError("Title and due time required.");
    return;
  }
  const payload = {
    title,
    due,
    notes: reminderNotesInput ? reminderNotesInput.value.trim() : "",
    session_id: state.sessionId,
  };
  try {
    await postJson("/api/reminders", payload);
    if (reminderTitleInput) reminderTitleInput.value = "";
    if (reminderDueInput) reminderDueInput.value = "";
    if (reminderNotesInput) reminderNotesInput.value = "";
    await loadReminders();
    await loadReminderLogs();
  } catch (err) {
    addError(`Reminder add failed: ${err.message}`);
  }
}

async function updateReminderItem(reminderId, updates) {
  if (!reminderId) return;
  try {
    await postJson("/api/reminders", { action: "update", id: reminderId, updates, session_id: state.sessionId });
    await loadReminders();
  } catch (err) {
    addError(`Reminder update failed: ${err.message}`);
  }
}

async function removeReminderItem(reminderId) {
  if (!reminderId) return;
  try {
    await postJson("/api/reminders", { action: "remove", id: reminderId });
    await loadReminders();
  } catch (err) {
    addError(`Reminder remove failed: ${err.message}`);
  }
}

async function loadReminderLogs() {
  if (!reminderLogList) return;
  const limit = reminderLogLimit && reminderLogLimit.value ? Number(reminderLogLimit.value) : 60;
  try {
    const data = await fetchJson(`/api/reminders/logs?limit=${encodeURIComponent(limit)}`);
    state.reminders.logs = data.entries || [];
    reminderLogList.innerHTML = "";
    if (!state.reminders.logs.length) {
      const empty = document.createElement("div");
      empty.className = "list-item";
      empty.textContent = "No reminder logs yet.";
      reminderLogList.appendChild(empty);
      return;
    }
    state.reminders.logs.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "list-item";
      row.innerHTML = `<strong>${escapeHtml(entry.type || "log")}</strong> ${escapeHtml(entry.timestamp || "")}<br>${escapeHtml(entry.title || entry.reminder_id || "")}`;
      reminderLogList.appendChild(row);
    });
  } catch (err) {
    addError(`Reminder logs failed: ${err.message}`);
  }
}

function handleReminderListClick(event) {
  const button = event.target.closest("button");
  const row = event.target.closest(".reminder-item");
  if (!row) return;
  const reminderId = row.dataset.reminderId;
  if (!reminderId) return;
  const item = state.reminders.items.find((entry) => entry.id === reminderId);
  if (!button) {
    if (item) fillReminderForm(item);
    return;
  }
  const action = button.dataset.action;
  if (action === "done") {
    updateReminderItem(reminderId, { status: "done" });
    return;
  }
  if (action === "snooze") {
    const next = formatLocalIso(new Date(Date.now() + 10 * 60 * 1000), false);
    updateReminderItem(reminderId, { due: next, status: "pending" });
    return;
  }
  if (action === "remove") {
    removeReminderItem(reminderId);
  }
}

function renderFocusSessions(items) {
  if (!focusList) return;
  focusList.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No focus sessions yet.";
    focusList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${escapeHtml(item.label || "Focus")}</strong><br>${escapeHtml(item.start_at || "")} → ${escapeHtml(item.end_at || "")}<br>${Math.round((item.duration_sec || 0) / 60)} min`;
    focusList.appendChild(row);
  });
}

async function loadFocusSessions() {
  try {
    const data = await fetchJson("/api/focus/sessions");
    state.focus.items = data.items || [];
    renderFocusSessions(state.focus.items);
  } catch (err) {
    addError(`Focus load failed: ${err.message}`);
  }
}

function updateFocusTimer() {
  if (!focusTimer) return;
  if (!state.focus.active) {
    focusTimer.textContent = "Idle.";
    focusTimer.classList.remove("focus-timer");
    return;
  }
  focusTimer.classList.add("focus-timer");
  const active = state.focus.active;
  const elapsed = Math.max(0, Math.floor((Date.now() - active.startedAtMs) / 1000));
  const remaining = active.durationSec ? Math.max(0, active.durationSec - elapsed) : null;
  const status = remaining !== null
    ? `Remaining ${Math.ceil(remaining / 60)} min`
    : `Elapsed ${Math.ceil(elapsed / 60)} min`;
  focusTimer.textContent = `${active.label.toUpperCase()} | ${status}`;
}

function startFocusSession() {
  if (state.focus.active) {
    addError("Focus session already running.");
    return;
  }
  const label = focusLabelInput ? focusLabelInput.value.trim() : "";
  const minutes = focusDurationInput ? Number(focusDurationInput.value) : 0;
  const durationSec = Number.isFinite(minutes) && minutes > 0 ? Math.round(minutes * 60) : 0;
  state.focus.active = {
    label: label || "Focus",
    notes: focusNotesInput ? focusNotesInput.value.trim() : "",
    durationSec,
    startedAtMs: Date.now(),
  };
  if (state.focus.timer) {
    clearInterval(state.focus.timer);
  }
  state.focus.timer = setInterval(updateFocusTimer, 1000);
  updateFocusTimer();
}

async function stopFocusSession() {
  if (!state.focus.active) {
    return;
  }
  const active = state.focus.active;
  const endAt = new Date();
  const startAt = new Date(active.startedAtMs);
  const durationSec = Math.max(0, Math.floor((endAt.getTime() - startAt.getTime()) / 1000));
  const payload = {
    label: active.label,
    notes: active.notes || "",
    start_at: formatLocalIso(startAt),
    end_at: formatLocalIso(endAt),
    duration_sec: durationSec,
  };
  try {
    await postJson("/api/focus/sessions", payload);
    await loadFocusSessions();
  } catch (err) {
    addError(`Focus save failed: ${err.message}`);
  }
  state.focus.active = null;
  if (state.focus.timer) {
    clearInterval(state.focus.timer);
    state.focus.timer = null;
  }
  updateFocusTimer();
}

function renderKbMap(data) {
  if (kbFolderList) {
    kbFolderList.innerHTML = "";
    const folders = data && data.folders ? data.folders : [];
    if (!folders.length) {
      const empty = document.createElement("div");
      empty.className = "list-item";
      empty.textContent = "No folder stats yet.";
      kbFolderList.appendChild(empty);
    } else {
      folders.forEach((item) => {
        const row = document.createElement("div");
        row.className = "list-item";
        row.innerHTML = `<strong>${escapeHtml(item.path || "--")}</strong><br>${item.count || 0} files`;
        kbFolderList.appendChild(row);
      });
    }
  }
  if (kbRecentList) {
    kbRecentList.innerHTML = "";
    const recent = data && data.recent ? data.recent : [];
    if (!recent.length) {
      const empty = document.createElement("div");
      empty.className = "list-item";
      empty.textContent = "No recent files.";
      kbRecentList.appendChild(empty);
    } else {
      recent.forEach((item) => {
        const row = document.createElement("div");
        row.className = "list-item";
        row.innerHTML = `<strong>${escapeHtml(item.path || "--")}</strong><br>${escapeHtml(item.updated_at || "")}`;
        kbRecentList.appendChild(row);
      });
    }
  }
}

async function loadKbMap() {
  try {
    const data = await fetchJson("/api/kb/map");
    renderKbMap(data || {});
  } catch (err) {
    addError(`KB map failed: ${err.message}`);
  }
}

function renderWorkflowTemplates(items) {
  if (!workflowList) return;
  workflowList.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No templates yet.";
    workflowList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item workflow-item";
    row.dataset.templateId = item.id;
    row.classList.toggle("active", item.id === state.workflowTemplates.selectedId);
    const tags = Array.isArray(item.tags) ? item.tags : [];
    const tagMarkup = tags.length
      ? `<div class="workflow-meta">${tags.map((tag) => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join(" ")}</div>`
      : "";
    row.innerHTML = `
      <div class="workflow-title">${escapeHtml(item.title || "Template")}</div>
      <div class="workflow-meta">${escapeHtml(item.updated_at || "")}</div>
      ${tagMarkup}
    `;
    workflowList.appendChild(row);
  });
}

function renderWorkflowRuns(items) {
  if (!workflowRunLog) return;
  workflowRunLog.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No workflow runs yet.";
    workflowRunLog.appendChild(empty);
    return;
  }
  items.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const nodes = (entry.nodes || []).map((node) => `${escapeHtml(node.node_id)}:${escapeHtml(node.status)}`).join(" | ");
    row.innerHTML = `<strong>${escapeHtml(entry.workflow_id || "workflow")}</strong><br>${nodes}`;
    workflowRunLog.appendChild(row);
  });
}

async function loadWorkflowTemplates() {
  try {
    const data = await fetchJson("/api/workflow/templates");
    state.workflowTemplates.items = data.items || [];
    if (state.workflowTemplates.selectedId) {
      const exists = state.workflowTemplates.items.some((item) => item.id === state.workflowTemplates.selectedId);
      if (!exists) {
        state.workflowTemplates.selectedId = null;
      }
    }
    renderWorkflowTemplates(state.workflowTemplates.items);
    renderWorkflowRuns(state.workflowTemplates.runs);
  } catch (err) {
    addError(`Workflow templates failed: ${err.message}`);
  }
}

function selectWorkflowTemplate(templateId) {
  const item = (state.workflowTemplates.items || []).find((entry) => entry.id === templateId);
  if (!item) return;
  state.workflowTemplates.selectedId = item.id;
  if (workflowTitleInput) workflowTitleInput.value = item.title || "";
  if (workflowTagsInput) workflowTagsInput.value = Array.isArray(item.tags) ? item.tags.join(", ") : "";
  if (workflowSpecInput) {
    workflowSpecInput.value = item.spec ? JSON.stringify(item.spec, null, 2) : "";
  }
  renderWorkflowTemplates(state.workflowTemplates.items);
}

async function addWorkflowTemplate() {
  const title = workflowTitleInput ? workflowTitleInput.value.trim() : "";
  const specRaw = workflowSpecInput ? workflowSpecInput.value.trim() : "";
  if (!title || !specRaw) {
    addError("Template title and spec required.");
    return;
  }
  const spec = safeParseJson(specRaw);
  if (!spec) {
    addError("Invalid workflow spec JSON.");
    return;
  }
  const payload = {
    title,
    spec,
    tags: parseCsvList(workflowTagsInput ? workflowTagsInput.value : ""),
  };
  try {
    await postJson("/api/workflow/templates", payload);
    await loadWorkflowTemplates();
  } catch (err) {
    addError(`Template add failed: ${err.message}`);
  }
}

async function updateWorkflowTemplate() {
  if (!state.workflowTemplates.selectedId) {
    addError("Select a template first.");
    return;
  }
  const title = workflowTitleInput ? workflowTitleInput.value.trim() : "";
  const specRaw = workflowSpecInput ? workflowSpecInput.value.trim() : "";
  const spec = specRaw ? safeParseJson(specRaw) : null;
  if (specRaw && !spec) {
    addError("Invalid workflow spec JSON.");
    return;
  }
  const updates = {
    title,
    tags: parseCsvList(workflowTagsInput ? workflowTagsInput.value : ""),
  };
  if (spec) {
    updates.spec = spec;
  }
  try {
    await postJson("/api/workflow/templates", { action: "update", id: state.workflowTemplates.selectedId, updates });
    await loadWorkflowTemplates();
  } catch (err) {
    addError(`Template update failed: ${err.message}`);
  }
}

async function runWorkflowTemplate() {
  if (!state.workflowTemplates.selectedId) {
    addError("Select a template first.");
    return;
  }
  try {
    const data = await postJson("/api/workflow/templates", {
      action: "run",
      id: state.workflowTemplates.selectedId,
      session_id: state.sessionId,
    });
    state.workflowTemplates.runs.unshift({ workflow_id: data.workflow_id, nodes: data.nodes || [] });
    state.workflowTemplates.runs = state.workflowTemplates.runs.slice(0, 8);
    renderWorkflowRuns(state.workflowTemplates.runs);
  } catch (err) {
    addError(`Workflow run failed: ${err.message}`);
  }
}

async function exportWorkflowTemplate() {
  if (!state.workflowTemplates.selectedId) {
    addError("Select a template first.");
    return;
  }
  try {
    const data = await postJson("/api/workflow/templates", { action: "export", id: state.workflowTemplates.selectedId });
    renderMessage("system", `Workflow exported: ${data.path || "--"}`, { skipStore: true });
  } catch (err) {
    addError(`Workflow export failed: ${err.message}`);
  }
}

function handleWorkflowListClick(event) {
  const row = event.target.closest(".workflow-item");
  if (!row) return;
  const templateId = row.dataset.templateId;
  if (templateId) {
    selectWorkflowTemplate(templateId);
  }
}

function renderArtifactTags(items) {
  if (!artifactTagList) return;
  artifactTagList.innerHTML = "";
  const entries = items && typeof items === "object" ? Object.entries(items) : [];
  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No tags yet.";
    artifactTagList.appendChild(empty);
    return;
  }
  entries.forEach(([taskId, info]) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const tags = Array.isArray(info.tags) ? info.tags.join(", ") : "";
    row.innerHTML = `<strong>${escapeHtml(taskId)}</strong><br>${escapeHtml(tags || "--")}<br>${escapeHtml(info.notes || "")}`;
    row.addEventListener("click", () => {
      if (artifactTagTaskInput) artifactTagTaskInput.value = taskId;
      if (artifactTagInput) artifactTagInput.value = tags;
      if (artifactTagNotesInput) artifactTagNotesInput.value = info.notes || "";
    });
    artifactTagList.appendChild(row);
  });
}

async function loadArtifactTags() {
  try {
    const data = await fetchJson("/api/artifacts/tags");
    state.artifactTags.items = data.items || {};
    renderArtifactTags(state.artifactTags.items);
  } catch (err) {
    addError(`Artifact tags failed: ${err.message}`);
  }
}

async function saveArtifactTags() {
  const taskId = artifactTagTaskInput ? artifactTagTaskInput.value.trim() : "";
  if (!taskId) {
    addError("Task ID required.");
    return;
  }
  const payload = {
    task_id: taskId,
    tags: parseCsvList(artifactTagInput ? artifactTagInput.value : ""),
    notes: artifactTagNotesInput ? artifactTagNotesInput.value.trim() : "",
  };
  try {
    await postJson("/api/artifacts/tags", payload);
    await loadArtifactTags();
  } catch (err) {
    addError(`Tag save failed: ${err.message}`);
  }
}

async function removeArtifactTags() {
  const taskId = artifactTagTaskInput ? artifactTagTaskInput.value.trim() : "";
  if (!taskId) {
    addError("Task ID required.");
    return;
  }
  try {
    await postJson("/api/artifacts/tags", { action: "remove", task_id: taskId });
    await loadArtifactTags();
  } catch (err) {
    addError(`Tag remove failed: ${err.message}`);
  }
}

function renderSystemMetrics(data) {
  if (!systemMetrics) return;
  systemMetrics.innerHTML = "";
  if (!data) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No metrics available.";
    systemMetrics.appendChild(empty);
    return;
  }
  const entries = [
    ["Platform", data.platform || "--"],
    ["Python", data.python || "--"],
    ["CPU", data.cpu_percent !== null && data.cpu_percent !== undefined ? `${data.cpu_percent}%` : "--"],
    ["Memory", `${formatBytes(data.mem_used)} / ${formatBytes(data.mem_total)}`],
    ["Disk", `${formatBytes(data.disk_used)} / ${formatBytes(data.disk_total)}`],
  ];
  entries.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${escapeHtml(label)}</strong> ${escapeHtml(value)}`;
    systemMetrics.appendChild(row);
  });
}

async function loadSystemMetrics() {
  try {
    const data = await fetchJson("/api/system/metrics");
    state.systemMetrics = data || {};
    renderSystemMetrics(state.systemMetrics);
  } catch (err) {
    addError(`System metrics failed: ${err.message}`);
  }
}

function renderReviewIssues(issues, analysis) {
  if (reviewSummary) {
    if (analysis) {
      reviewSummary.innerHTML = renderMarkdown(String(analysis));
    } else {
      reviewSummary.textContent = "Review output will appear here.";
    }
  }
  if (!reviewList) return;
  reviewList.innerHTML = "";
  if (!Array.isArray(issues) || !issues.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No issues found.";
    reviewList.appendChild(empty);
    return;
  }
  issues.forEach((issue) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const line = issue.line ? `Line ${issue.line}` : "Line --";
    row.innerHTML = `<strong>${escapeHtml(issue.type || "issue")}</strong> ${escapeHtml(line)}<br>${escapeHtml(issue.path || "")}<br>${escapeHtml(issue.detail || "")}`;
    reviewList.appendChild(row);
  });
}

async function reviewPaths() {
  if (!reviewPathInput) return;
  const paths = parseLines(reviewPathInput.value);
  if (!paths.length) {
    addError("Provide file paths.");
    return;
  }
  try {
    const data = await postJson("/api/code/review", { paths });
    renderReviewIssues(data.issues || [], data.analysis || "");
  } catch (err) {
    addError(`Code review failed: ${err.message}`);
  }
}

async function reviewSnippet() {
  if (!reviewTextInput) return;
  const text = reviewTextInput.value.trim();
  if (!text) {
    addError("Paste a snippet first.");
    return;
  }
  try {
    const data = await postJson("/api/code/review", { text, name: "snippet" });
    renderReviewIssues(data.issues || [], data.analysis || "");
  } catch (err) {
    addError(`Snippet review failed: ${err.message}`);
  }
}

function renderDataPreview(data) {
  if (!dataPreview) return;
  dataPreview.innerHTML = "";
  if (!data || data.error) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = data && data.error ? data.error : "No data preview.";
    dataPreview.appendChild(empty);
    return;
  }
  const header = Array.isArray(data.header) ? data.header : [];
  const rows = Array.isArray(data.rows) ? data.rows : [];
  if (!header.length && !rows.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No rows.";
    dataPreview.appendChild(empty);
    return;
  }
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  header.forEach((cell) => {
    const th = document.createElement("th");
    th.textContent = cell;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((cell) => {
      const td = document.createElement("td");
      td.textContent = cell;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(thead);
  table.appendChild(tbody);
  dataPreview.appendChild(table);
}

async function previewData() {
  const content = dataCsvInput ? dataCsvInput.value : "";
  const pathValue = dataPathInput ? dataPathInput.value.trim() : "";
  const limit = dataLimitInput && dataLimitInput.value ? Number(dataLimitInput.value) : 20;
  try {
    const data = await postJson("/api/data/preview", { content, path: pathValue, limit });
    renderDataPreview(data);
  } catch (err) {
    addError(`Preview failed: ${err.message}`);
  }
}

async function transformData() {
  const content = dataCsvInput ? dataCsvInput.value : "";
  const pathValue = dataPathInput ? dataPathInput.value.trim() : "";
  const limit = dataLimitInput && dataLimitInput.value ? Number(dataLimitInput.value) : 50;
  const rawOps = dataOpsInput ? dataOpsInput.value.trim() : "";
  const operations = rawOps ? safeParseJson(rawOps) : [];
  if (rawOps && !Array.isArray(operations)) {
    addError("Operations must be a JSON array.");
    return;
  }
  try {
    const data = await postJson("/api/data/transform", {
      content,
      path: pathValue,
      limit,
      operations: Array.isArray(operations) ? operations : [],
    });
    renderDataPreview(data);
  } catch (err) {
    addError(`Transform failed: ${err.message}`);
  }
}

function renderLogsCenter(entries) {
  if (!logsList) return;
  logsList.innerHTML = "";
  if (!Array.isArray(entries) || !entries.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No logs yet.";
    logsList.appendChild(empty);
    return;
  }
  entries.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "list-item";
    const stamp = entry.timestamp || entry.time || "";
    const summary = entry.message || entry.type || entry.prompt || entry.schedule_id || entry.task_id || "";
    row.innerHTML = `<strong>${escapeHtml(entry.source || "log")}</strong> ${escapeHtml(stamp)}<br>${escapeHtml(String(summary))}`;
    logsList.appendChild(row);
  });
}

async function loadLogsCenter() {
  const limit = logsLimitInput && logsLimitInput.value ? Number(logsLimitInput.value) : 200;
  try {
    const data = await fetchJson(`/api/logs/combined?limit=${encodeURIComponent(limit)}`);
    state.logsCenter = data.entries || [];
    renderLogsCenter(state.logsCenter);
  } catch (err) {
    addError(`Logs load failed: ${err.message}`);
  }
}

function renderTriggers(items) {
  if (!triggerList) return;
  triggerList.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "list-item";
    empty.textContent = "No triggers configured.";
    triggerList.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "list-item";
    row.innerHTML = `<strong>${escapeHtml(item.type || "trigger")}</strong><br>${escapeHtml(item.prompt || "")}`;
    triggerList.appendChild(row);
  });
}

async function loadTriggers() {
  try {
    const data = await fetchJson("/api/triggers");
    state.triggers = data.triggers || [];
    renderTriggers(state.triggers);
  } catch (err) {
    addError(`Trigger load failed: ${err.message}`);
  }
}

async function sendCommand(commandText) {
  if (!commandText) return null;
  const payload = {
    command: commandText,
    session_id: state.sessionId,
    client_id: state.clientId,
  };
  try {
    const data = await postJson("/api/command", payload);
    handleCommandResponse(data);
    return data;
  } catch (err) {
    addError(`Command failed: ${err.message}`);
    return null;
  }
}

function handleCommandResponse(data) {
  if (!data) return;
  if (data.session_id && data.session_id !== state.sessionId) {
    activateSession(data.session_id, state.activeSlot, true);
  }
  if (Array.isArray(data.messages)) {
    data.messages.forEach((msg) => {
      renderMessage("system", msg, { skipStore: false });
    });
  }
  if (data.command && ["pin", "unpin", "pins"].includes(data.command)) {
    refreshPins();
  }
  if (data.command && ["note", "notes"].includes(data.command)) {
    loadNotes();
  }
  if (data.command && data.command === "schedule") {
    loadSchedules();
  }
  if (data.command && data.command === "dashboard" && data.data && data.data.url) {
    setDashboardStatus(data.data.url, true);
    window.open(data.data.url, "_blank");
  }
  if (data.command && (data.command === "plugins" || data.command === "reload")) {
    loadPlugins();
  }
  if (data.data && data.data.schedules) {
    renderSchedules(data.data.schedules);
  }
  if (data.data && data.data.results) {
    state.lastReply = "";
  }
  if (data.data && data.data.document) {
    renderDocumentMessage(data.data.document);
    loadArtifacts();
  }
  updateAnalytics();
}

function formatAge(timestamp) {
  if (!timestamp) return "Linked";
  const diff = Date.now() - timestamp;
  if (diff < 60000) return "Active moments ago";
  if (diff < 3600000) return `Idle ${Math.floor(diff / 60000)}m`;
  if (diff < 86400000) return `Idle ${Math.floor(diff / 3600000)}h`;
  return `Idle ${Math.floor(diff / 86400000)}d`;
}

function updateSlotUI() {
  slotItems.forEach((item) => {
    const slot = item.dataset.slot;
    const info = state.slots[slot];
    const meta = item.querySelector(".session-meta");
    if (!info) return;
    if (!info.sessionId) {
      meta.textContent = "Unlinked";
    } else if (slot === state.activeSlot) {
      meta.textContent = "Active";
    } else {
      meta.textContent = formatAge(info.lastUsed);
    }
    item.classList.toggle("active", slot === state.activeSlot);
  });
}

function activateSession(sessionId, slot, silent = false) {
  const previous = state.sessionId;
  state.sessionId = sessionId;
  localStorage.setItem(storeKey, state.sessionId);
  clearReplyTarget();
  if (slot && state.slots[slot]) {
    state.activeSlot = slot;
    state.slots[slot].sessionId = sessionId;
    state.slots[slot].lastUsed = Date.now();
    saveSlots();
  }
  updateSessionView();
  updateSlotUI();
  updateShareLink();
  if (previous && previous !== sessionId) {
    state.stats = { total: 0, success: 0 };
    state.lastReply = "";
    latencyBadge.textContent = "LATENCY: --";
    state.renderLimit = 120;
    updateStats();
    resetProgress();
  }
  renderTranscript(sessionId);
  refreshPins();
  loadNotes();
  loadContextReport();
  loadMemoryStats();
  loadAuditLogs();
  loadDraft();
  loadSnapshots();
  loadArchives();
  loadProfiles();
  loadSchedules();
  if (!silent) {
    const label = (state.slots[slot] && state.slots[slot].label) || "Session";
    renderMessage("system", `Switched to ${label}.`, { skipStore: true });
  }
}

function applyTheme(theme) {
  document.body.classList.remove("theme-dark", "theme-red");
  if (theme === "dark") {
    document.body.classList.add("theme-dark");
  } else if (theme === "red") {
    document.body.classList.add("theme-red");
  }
  themeButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.theme === theme);
  });
  localStorage.setItem(themeKey, theme);
}

function loadTheme() {
  const stored = localStorage.getItem(themeKey) || "light";
  applyTheme(stored);
}

function loadStreamSetting() {
  const stored = localStorage.getItem(streamKey);
  if (stored === "false") {
    state.streamEnabled = false;
  } else if (stored === "true") {
    state.streamEnabled = true;
  }
  updateStreamButton();
}

function updateStreamButton() {
  if (!streamBtn) return;
  streamBtn.textContent = state.streamEnabled ? "STREAM ON" : "STREAM OFF";
  streamBtn.classList.toggle("active", state.streamEnabled);
}

function toggleStream() {
  state.streamEnabled = !state.streamEnabled;
  localStorage.setItem(streamKey, state.streamEnabled ? "true" : "false");
  updateStreamButton();
}

async function createSessionForSlot(slot) {
  const sessionId = await createSession();
  activateSession(sessionId, slot, true);
  renderMessage("system", "New session created. Pixel terminal online.");
}

async function resetSession() {
  if (!state.sessionId) {
    await createSessionForSlot(state.activeSlot);
    return;
  }
  try {
    await postJson("/api/reset", { session_id: state.sessionId });
    renderMessage("system", "Session memory reset.");
    clearReplyTarget();
    clearTranscriptCache(state.sessionId);
    state.stats = { total: 0, success: 0 };
    updateStats();
    resetProgress();
    refreshStatus(false);
  } catch (err) {
    renderMessage("system", `Reset failed: ${err.message}`);
    addError(`Reset failed: ${err.message}`);
  }
}

function updateStats(latencySeconds) {
  iterationCountEl.textContent = state.stats.total;
  elapsedTimeEl.textContent = latencySeconds ? `${latencySeconds.toFixed(2)}s` : "--";
  if (state.stats.total === 0) {
    successRateEl.textContent = "--";
  } else {
    const rate = Math.round((state.stats.success / state.stats.total) * 100);
    successRateEl.textContent = `${rate}%`;
  }
}

function updateProgress(step, maxIterations) {
  const current = Number(step) || 0;
  const max = Number(maxIterations) || 0;
  if (progressLabel) {
    progressLabel.textContent = max ? `Step ${current}/${max}` : `Step ${current}`;
  }
  if (progressFill) {
    const percent = max ? Math.min(100, Math.round((current / max) * 100)) : 0;
    progressFill.style.width = `${percent}%`;
  }
}

function resetProgress() {
  if (progressLabel) {
    progressLabel.textContent = "Step 0";
  }
  if (progressFill) {
    progressFill.style.width = "0%";
  }
  if (tokenUsage) {
    tokenUsage.textContent = "Tokens --";
  }
  if (tokenCount) {
    tokenCount.textContent = "--";
  }
}

function setTokenUsage(tokens) {
  const value = tokens === undefined || tokens === null ? "--" : String(tokens);
  if (tokenUsage) {
    tokenUsage.textContent = `Tokens ${value}`;
  }
  if (tokenCount) {
    tokenCount.textContent = value;
  }
}

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || state.busy) {
    return;
  }
  if (state.streamEnabled && window.ReadableStream) {
    await sendMessageStream(text);
  } else {
    await sendMessageStandard(text);
  }
}

async function runStreamFlow(payload, options = {}) {
  if (!state.sessionId) {
    await createSessionForSlot(state.activeSlot);
  }
  const replyTarget = options.replyTarget || null;
  const userText = options.userText || "";
  const systemNote = options.systemNote || "";
  if (userText) {
    renderMessage("user", userText, { reply: replyTarget });
  }
  if (systemNote) {
    renderMessage("system", systemNote, { skipStore: true });
  }
  if (options.clearInput) {
    messageInput.value = "";
    clearDraft();
  }
  if (replyTarget) {
    clearReplyTarget();
  }
  setBusy(true);
  resetProgress();
  removeTyping();

  const assistantWrapper = renderMessage("assistant", "", { skipStore: true, markdown: false });
  const body = assistantWrapper.querySelector(".message-body");
  const stamp = assistantWrapper.dataset.time || formatTime();
  let streamContent = "";
  let messageId = null;
  let replyPayload = null;
  let commandMode = false;
  let streamComplete = false;
  let terminalError = null;

  if (replyTarget) {
    replyPayload = {
      role: replyTarget.role,
      content: replyTarget.content,
      time: replyTarget.time,
      messageId: replyTarget.messageId,
    };
  }

  const requestPayload = Object.assign({}, payload || {});
  requestPayload.session_id = requestPayload.session_id || state.sessionId;
  requestPayload.client_id = requestPayload.client_id || state.clientId;
  if (requestPayload.continue) {
    if (requestPayload.resume_message_id === undefined) {
      requestPayload.resume_message_id = state.lastAssistantMessageId || null;
    }
    if (requestPayload.resume_text === undefined) {
      requestPayload.resume_text = state.lastReply || "";
    }
  }

  if (userText) {
    addRunLog("STREAM", truncate(userText, 160));
  } else if (requestPayload.continue) {
    addRunLog("STREAM", "Continue requested.");
  } else {
    addRunLog("STREAM", "Stream request.");
  }

  const buildRetryPayload = () => {
    if (!streamContent && !requestPayload.continue) {
      return requestPayload;
    }
    const resumeText = streamContent || requestPayload.resume_text || state.lastReply || "";
    const resumeMessageId = requestPayload.resume_message_id || state.lastAssistantMessageId || null;
    return {
      continue: true,
      session_id: state.sessionId,
      client_id: state.clientId,
      resume_message_id: resumeMessageId,
      resume_text: resumeText,
    };
  };

  try {
    for (let attempt = 0; attempt <= STREAM_RETRY_DELAYS.length; attempt += 1) {
      const attemptPayload = attempt === 0 ? requestPayload : buildRetryPayload();
      let stalled = false;
      const controller = new AbortController();
      const resetStall = () => {
        clearTimeout(resetStall.timer);
        resetStall.timer = setTimeout(() => {
          stalled = true;
          controller.abort();
        }, STREAM_STALL_MS);
      };
      resetStall.timer = null;

      if (attempt > 0) {
        addRunLog("RETRY", `Reconnect #${attempt}`);
      }

      try {
        const res = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(attemptPayload),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) {
          throw new Error(`Stream failed: ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        const handleEvent = (event) => {
          if (!event || !event.type) return;
          const payloadData = event.payload || {};
          if (event.type === "ping") {
            return;
          }
          if (event.type === "meta") {
            if (payloadData.session_id && payloadData.session_id !== state.sessionId) {
              state.sessionId = payloadData.session_id;
              localStorage.setItem(storeKey, state.sessionId);
              updateSessionView();
              updateShareLink();
              updateSlotUI();
            }
            if (payloadData.max_iterations) {
              state.maxIterations = payloadData.max_iterations;
            }
            if (payloadData.model) {
              modelBadge.textContent = `MODEL: ${payloadData.model}`;
            }
            return;
          }
          if (event.type === "llm_start") {
            updateProgress(payloadData.iteration || 0, state.maxIterations || 0);
            setStatus("THINKING", "busy");
            return;
          }
          if (event.type === "thinking") {
            if (payloadData.step) {
              updateProgress(payloadData.step, state.maxIterations || 0);
            }
            return;
          }
          if (event.type === "tool_start") {
            queueHint.textContent = payloadData.tool ? `Tool ${payloadData.tool}` : "Tool running";
            statusHint.textContent = "Tool executing";
            return;
          }
          if (event.type === "tool_end") {
            queueHint.textContent = payloadData.tool ? `Tool ${payloadData.tool} done` : "Tool complete";
            return;
          }
          if (event.type === "delta") {
            streamContent += payloadData.text || "";
            if (body) {
              body.textContent = streamContent;
              chatLog.scrollTop = chatLog.scrollHeight;
            }
            return;
          }
          if (event.type === "command") {
            assistantWrapper.remove();
            commandMode = true;
            handleCommandResponse(payloadData);
            return;
          }
          if (event.type === "error") {
            if (!streamContent) {
              assistantWrapper.remove();
            }
            renderMessage("system", payloadData.message || "Stream error.", { skipStore: true });
            addError(payloadData.message || "Stream error.");
            terminalError = new Error(payloadData.message || "Stream error.");
            streamComplete = true;
            addRunLog("ERROR", payloadData.message || "Stream error.");
            return;
          }
          if (event.type === "done") {
            if (commandMode) {
              streamComplete = true;
              return;
            }
            const reply = payloadData.reply || streamContent;
            streamContent = reply;
            messageId = payloadData.assistant_message_id || null;
            renderMessageBody(body, streamContent || "", true);
            attachCollapseControl(assistantWrapper, streamContent || "", true);
            if (messageId) {
              assistantWrapper.dataset.messageId = messageId;
              ensurePinButton(assistantWrapper, messageId);
              ensureRatingButtons(assistantWrapper, messageId);
              state.lastAssistantMessageId = messageId;
            }
            state.stats.total += 1;
            if (payloadData.success) {
              state.stats.success += 1;
              state.lastReply = reply || "";
              storeMessage("assistant", reply || "", stamp, messageId, state.pins.includes(messageId), replyPayload, 0);
              addRunLog("DONE", `Success in ${payloadData.execution_time ? payloadData.execution_time.toFixed(2) : "--"}s`);
            } else if (payloadData.cancelled) {
              state.lastReply = reply || "";
              renderMessage("system", "Stream cancelled.", { skipStore: true });
              addRunLog("CANCEL", "Stream cancelled.");
            } else {
              renderMessage("system", payloadData.error_message || "Execution failed.");
              addError(payloadData.error_message || "Execution failed.");
              addRunLog("ERROR", payloadData.error_message || "Execution failed.");
            }
            latencyBadge.textContent = `LATENCY: ${payloadData.execution_time ? payloadData.execution_time.toFixed(2) : "--"}s`;
            updateProgress(payloadData.total_iterations || 0, state.maxIterations || 0);
            setTokenUsage(payloadData.total_tokens_used);
            updateStats(payloadData.execution_time || 0);
            updateAnalytics();
            streamComplete = true;
          }
        };

        resetStall();
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          resetStall();
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";
          parts.forEach((block) => {
            const lines = block.split("\n").filter((line) => line.startsWith("data:"));
            if (!lines.length) return;
            const raw = lines.map((line) => line.slice(5).trim()).join("");
            if (!raw) return;
            try {
              const event = JSON.parse(raw);
              handleEvent(event);
            } catch (err) {
              addError("Stream decode failed.");
            }
          });
          if (streamComplete || commandMode) {
            break;
          }
        }
        clearTimeout(resetStall.timer);
        if (streamComplete || commandMode) {
          break;
        }
        if (stalled) {
          throw new Error("Stream stalled.");
        }
        throw new Error("Stream disconnected.");
      } catch (err) {
        clearTimeout(resetStall.timer);
        if (streamComplete || commandMode) {
          break;
        }
        terminalError = err;
        if (attempt >= STREAM_RETRY_DELAYS.length) {
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, STREAM_RETRY_DELAYS[attempt] || 1000));
      }
    }
  } catch (err) {
    terminalError = err;
  } finally {
    if (!streamComplete && !commandMode) {
      if (assistantWrapper && !streamContent) {
        assistantWrapper.remove();
      }
      const message = terminalError ? terminalError.message : "Stream failed.";
      renderMessage("system", `Stream failed: ${message}`);
      addError(`Stream failed: ${message}`);
      addRunLog("ERROR", message);
    }
    setBusy(false);
  }
}

async function sendMessageStandard(rawText) {
  if (!state.sessionId) {
    await createSessionForSlot(state.activeSlot);
  }
  const replyTarget = state.replyTarget;
  renderMessage("user", rawText, { reply: replyTarget });
  messageInput.value = "";
  clearDraft();
  clearReplyTarget();
  setBusy(true);
  addRunLog("REQUEST", truncate(rawText, 160));
  resetProgress();
  removeTyping();
  renderMessage("system", "SAMA is thinking...", { typing: true, skipStore: true });
  try {
    const payloadText = replyTarget ? buildReplyContext(replyTarget, rawText) : rawText;
    const data = await postJson("/api/chat", {
      message: payloadText,
      session_id: state.sessionId,
      client_id: state.clientId,
    });
    removeTyping();
    if (data.command) {
      handleCommandResponse(data);
      return;
    }
    activateSession(data.session_id || state.sessionId, state.activeSlot, true);
    state.stats.total += 1;
    if (data.success) {
      state.stats.success += 1;
      state.lastReply = data.reply || "";
      addRunLog("DONE", `Success in ${data.execution_time ? data.execution_time.toFixed(2) : "--"}s`);
      renderMessage("assistant", data.reply || "(empty response)", {
        messageId: data.assistant_message_id,
        pinned: state.pins.includes(data.assistant_message_id),
      });
    } else if (data.cancelled) {
      state.lastReply = data.reply || "";
      addRunLog("CANCEL", "Request cancelled.");
      renderMessage("system", "Request cancelled.", { skipStore: true });
    } else {
      addRunLog("ERROR", data.error_message || "Execution failed.");
      renderMessage("system", data.error_message || "Execution failed.");
      addError(data.error_message || "Execution failed.");
    }
    latencyBadge.textContent = `LATENCY: ${data.execution_time ? data.execution_time.toFixed(2) : "--"}s`;
    updateProgress(data.total_iterations || 0, state.maxIterations || 0);
    setTokenUsage(data.total_tokens_used);
    updateStats(data.execution_time || 0);
    updateAnalytics();
  } catch (err) {
    removeTyping();
    renderMessage("system", `Request failed: ${err.message}`);
    addError(`Request failed: ${err.message}`);
    addRunLog("ERROR", `Request failed: ${err.message}`);
  } finally {
    setBusy(false);
  }
}

async function sendMessageStream(rawText) {
  const replyTarget = state.replyTarget;
  const payloadText = replyTarget ? buildReplyContext(replyTarget, rawText) : rawText;
  await runStreamFlow(
    { message: payloadText },
    { replyTarget, userText: rawText, clearInput: true }
  );
}

async function sendContinueStream() {
  if (state.busy) return;
  await runStreamFlow(
    {
      continue: true,
      resume_message_id: state.lastAssistantMessageId || null,
      resume_text: state.lastReply || "",
    },
    { systemNote: "Continue requested." }
  );
}

async function sendContinueStandard() {
  if (!state.sessionId) {
    await createSessionForSlot(state.activeSlot);
  }
  if (state.busy) return;
  setBusy(true);
  resetProgress();
  removeTyping();
  renderMessage("system", "Continue requested.", { skipStore: true });
  try {
    const data = await postJson("/api/chat", {
      session_id: state.sessionId,
      client_id: state.clientId,
      continue: true,
    });
    if (data.command) {
      handleCommandResponse(data);
      return;
    }
    activateSession(data.session_id || state.sessionId, state.activeSlot, true);
    state.stats.total += 1;
    if (data.success) {
      state.stats.success += 1;
      state.lastReply = data.reply || "";
      renderMessage("assistant", data.reply || "(empty response)", {
        messageId: data.assistant_message_id,
        pinned: state.pins.includes(data.assistant_message_id),
      });
    } else if (data.cancelled) {
      state.lastReply = data.reply || "";
      renderMessage("system", "Continue cancelled.", { skipStore: true });
    } else {
      renderMessage("system", data.error_message || "Execution failed.");
      addError(data.error_message || "Execution failed.");
    }
    latencyBadge.textContent = `LATENCY: ${data.execution_time ? data.execution_time.toFixed(2) : "--"}s`;
    updateProgress(data.total_iterations || 0, state.maxIterations || 0);
    setTokenUsage(data.total_tokens_used);
    updateStats(data.execution_time || 0);
    updateAnalytics();
  } catch (err) {
    renderMessage("system", `Continue failed: ${err.message}`);
    addError(`Continue failed: ${err.message}`);
  } finally {
    setBusy(false);
  }
}

async function cancelStream() {
  if (!state.sessionId || !state.busy) return;
  try {
    await postJson("/api/chat/cancel", { session_id: state.sessionId });
    renderMessage("system", "Cancel requested.", { skipStore: true });
    addRunLog("CANCEL", "Cancel requested.");
  } catch (err) {
    addError(`Cancel failed: ${err.message}`);
  }
}

function clearScreen() {
  chatLog.innerHTML = "";
  renderMessage("system", "Screen cleared.", { skipStore: true });
}

async function copyLastReply() {
  if (!state.lastReply) {
    renderMessage("system", "No reply to copy yet.", { skipStore: true });
    return;
  }
  const ok = await copyToClipboard(state.lastReply);
  if (ok) {
    renderMessage("system", "Last reply copied.", { skipStore: true });
    return;
  }
  renderMessage("system", "Copy failed. Please select manually.", { skipStore: true });
  addError("Copy failed.");
}

sendBtn.addEventListener("click", sendMessage);
if (stopBtn) {
  stopBtn.addEventListener("click", cancelStream);
}
if (continueBtn) {
  continueBtn.addEventListener("click", () => {
    if (state.streamEnabled && window.ReadableStream) {
      sendContinueStream();
    } else {
      sendContinueStandard();
    }
  });
}
newSessionBtn.addEventListener("click", async () => {
  await createSessionForSlot(state.activeSlot);
});
resetBtn.addEventListener("click", resetSession);
clearBtn.addEventListener("click", clearScreen);
copyBtn.addEventListener("click", copyLastReply);
syncBtn.addEventListener("click", async () => {
  await loadInfo();
  await loadDashboardStatus();
  await refreshStatus(true);
  await loadConfig();
  await refreshPins();
  await loadNotes();
  await loadContextReport();
  await loadMemoryStats();
  await loadAuditLogs();
  await loadMetrics();
  await loadNewsList();
  await loadMediaAll();
  await loadWebhookLogs();
  await loadSnapshots();
  await loadArchives();
  await loadSchedules();
  await loadTasks();
  await loadBookmarks();
  await loadReminders();
  await loadReminderLogs();
  await loadFocusSessions();
  await loadKbMap();
  await loadWorkflowTemplates();
  await loadArtifactTags();
  await loadSystemMetrics();
  await loadLogsCenter();
  await loadTriggers();
  await loadArtifacts();
  await loadPlugins();
  await loadProfiles();
  await loadKbStatus();
});
if (dashboardBtn) {
  dashboardBtn.addEventListener("click", openDashboard);
}
if (dashboardOpenBtn) {
  dashboardOpenBtn.addEventListener("click", openDashboard);
}
if (dashboardCopyBtn) {
  dashboardCopyBtn.addEventListener("click", copyDashboardLink);
}
if (presetButtons.length) {
  presetButtons.forEach((btn) => {
    btn.addEventListener("click", () => applyPreset(btn.dataset.preset || ""));
  });
}
linkBtn.addEventListener("click", copyShareLink);
searchInput.addEventListener("input", () => {
  state.filters.query = searchInput.value || "";
  if (state.sessionId) {
    renderTranscript(state.sessionId);
  }
});
searchClearBtn.addEventListener("click", () => {
  searchInput.value = "";
  state.filters.query = "";
  if (state.sessionId) {
    renderTranscript(state.sessionId);
  }
});
loadOlderBtn.addEventListener("click", () => {
  loadOlderMessages();
});
refreshPinsBtn.addEventListener("click", refreshPins);
if (exportMdBtn) {
  exportMdBtn.addEventListener("click", exportTranscriptMarkdown);
}
if (exportJsonBtn) {
  exportJsonBtn.addEventListener("click", exportTranscriptJson);
}
if (exportDocxBtn) {
  exportDocxBtn.addEventListener("click", () => generateDocument("docx"));
}
if (exportPdfBtn) {
  exportPdfBtn.addEventListener("click", () => generateDocument("pdf"));
}
saveTemplateBtn.addEventListener("click", () => {
  const name = (templateNameInput.value || "").trim();
  const content = (messageInput.value || "").trim();
  if (!name || !content) {
    addError("Template name and content are required.");
    return;
  }
  const existing = state.templates.find((tpl) => tpl.name === name);
  if (existing) {
    existing.content = content;
  } else {
    state.templates.unshift({ name, content });
  }
  state.templates = state.templates.slice(0, 20);
  saveTemplates();
  renderTemplateSelect();
  templateNameInput.value = "";
});
insertTemplateBtn.addEventListener("click", () => {
  const selected = templateSelect.value;
  if (!selected) return;
  const tpl = state.templates.find((item) => item.name === selected);
  if (!tpl) return;
  messageInput.value = tpl.content;
  messageInput.focus();
});
clearErrorsBtn.addEventListener("click", clearErrors);
if (refreshAuditBtn) {
  refreshAuditBtn.addEventListener("click", loadAuditLogs);
}
if (auditScopeSelect) {
  auditScopeSelect.addEventListener("change", loadAuditLogs);
}
if (auditLimitInput) {
  auditLimitInput.addEventListener("change", loadAuditLogs);
}
if (auditTypeInput) {
  auditTypeInput.addEventListener("input", loadAuditLogs);
}
if (exportAuditBtn) {
  exportAuditBtn.addEventListener("click", exportAuditLogs);
}
if (clearRunLogBtn) {
  clearRunLogBtn.addEventListener("click", clearRunLog);
}
if (refreshMetricsBtn) {
  refreshMetricsBtn.addEventListener("click", loadMetrics);
}
addProjectNoteBtn.addEventListener("click", () => addNote("project"));
addLongNoteBtn.addEventListener("click", () => addNote("long_term"));
if (createSnapshotBtn) {
  createSnapshotBtn.addEventListener("click", createSnapshot);
}
if (refreshSnapshotsBtn) {
  refreshSnapshotsBtn.addEventListener("click", loadSnapshots);
}
if (refreshContextBtn) {
  refreshContextBtn.addEventListener("click", async () => {
    await loadContextReport();
    await loadMemoryStats();
  });
}
if (archiveNowBtn) {
  archiveNowBtn.addEventListener("click", createArchiveNow);
}
if (refreshArchivesBtn) {
  refreshArchivesBtn.addEventListener("click", loadArchives);
}
addScheduleBtn.addEventListener("click", addSchedule);
refreshScheduleBtn.addEventListener("click", loadSchedules);
if (moduleToggleBtn) {
  moduleToggleBtn.addEventListener("click", () => setModulesOpen(true));
}
if (moduleCloseBtn) {
  moduleCloseBtn.addEventListener("click", () => setModulesOpen(false));
}
if (moduleBackdrop) {
  moduleBackdrop.addEventListener("click", () => setModulesOpen(false));
}
if (moduleFilter) {
  moduleFilter.addEventListener("change", applyModuleFilter);
}
if (addTaskBtn) {
  addTaskBtn.addEventListener("click", addTask);
}
if (refreshTasksBtn) {
  refreshTasksBtn.addEventListener("click", loadTasks);
}
if (taskList) {
  taskList.addEventListener("click", handleTaskListClick);
}
if (addBookmarkBtn) {
  addBookmarkBtn.addEventListener("click", addBookmark);
}
if (refreshBookmarksBtn) {
  refreshBookmarksBtn.addEventListener("click", loadBookmarks);
}
if (bookmarkList) {
  bookmarkList.addEventListener("click", handleBookmarkListClick);
}
if (addReminderBtn) {
  addReminderBtn.addEventListener("click", addReminder);
}
if (refreshRemindersBtn) {
  refreshRemindersBtn.addEventListener("click", loadReminders);
}
if (refreshReminderLogsBtn) {
  refreshReminderLogsBtn.addEventListener("click", loadReminderLogs);
}
if (reminderList) {
  reminderList.addEventListener("click", handleReminderListClick);
}
if (startFocusBtn) {
  startFocusBtn.addEventListener("click", startFocusSession);
}
if (stopFocusBtn) {
  stopFocusBtn.addEventListener("click", stopFocusSession);
}
if (refreshKbMapBtn) {
  refreshKbMapBtn.addEventListener("click", loadKbMap);
}
if (addWorkflowBtn) {
  addWorkflowBtn.addEventListener("click", addWorkflowTemplate);
}
if (updateWorkflowBtn) {
  updateWorkflowBtn.addEventListener("click", updateWorkflowTemplate);
}
if (runWorkflowBtn) {
  runWorkflowBtn.addEventListener("click", runWorkflowTemplate);
}
if (exportWorkflowBtn) {
  exportWorkflowBtn.addEventListener("click", exportWorkflowTemplate);
}
if (refreshWorkflowBtn) {
  refreshWorkflowBtn.addEventListener("click", loadWorkflowTemplates);
}
if (workflowList) {
  workflowList.addEventListener("click", handleWorkflowListClick);
}
if (saveArtifactTagsBtn) {
  saveArtifactTagsBtn.addEventListener("click", saveArtifactTags);
}
if (removeArtifactTagsBtn) {
  removeArtifactTagsBtn.addEventListener("click", removeArtifactTags);
}
if (refreshArtifactTagsBtn) {
  refreshArtifactTagsBtn.addEventListener("click", loadArtifactTags);
}
if (refreshSystemMetricsBtn) {
  refreshSystemMetricsBtn.addEventListener("click", loadSystemMetrics);
}
if (reviewPathsBtn) {
  reviewPathsBtn.addEventListener("click", reviewPaths);
}
if (reviewTextBtn) {
  reviewTextBtn.addEventListener("click", reviewSnippet);
}
if (previewDataBtn) {
  previewDataBtn.addEventListener("click", previewData);
}
if (transformDataBtn) {
  transformDataBtn.addEventListener("click", transformData);
}
if (refreshLogsBtn) {
  refreshLogsBtn.addEventListener("click", loadLogsCenter);
}
if (refreshTriggerBtn) {
  refreshTriggerBtn.addEventListener("click", loadTriggers);
}
if (todoProjectList) {
  todoProjectList.addEventListener("click", handleTodoProjectClick);
}
if (todoSmartList) {
  todoSmartList.addEventListener("click", handleTodoSmartClick);
}
if (addTodoProjectBtn) {
  addTodoProjectBtn.addEventListener("click", addTodoProject);
}
if (todoProjectInput) {
  todoProjectInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addTodoProject();
    }
  });
}
if (todoAddBtn) {
  todoAddBtn.addEventListener("click", addTodoQuickTask);
}
if (todoQuickInput) {
  todoQuickInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addTodoQuickTask();
    }
  });
}
if (todoTodayList) {
  todoTodayList.addEventListener("click", handleTodoItemClick);
}
if (todoUpcomingList) {
  todoUpcomingList.addEventListener("click", handleTodoItemClick);
}
if (todoBacklogList) {
  todoBacklogList.addEventListener("click", handleTodoItemClick);
}
if (todoBlockedList) {
  todoBlockedList.addEventListener("click", handleTodoItemClick);
}
if (todoDoneList) {
  todoDoneList.addEventListener("click", handleTodoItemClick);
}
if (todoSaveBtn) {
  todoSaveBtn.addEventListener("click", saveTodoDetail);
}
if (todoArchiveBtn) {
  todoArchiveBtn.addEventListener("click", archiveTodoTask);
}
if (todoDeleteBtn) {
  todoDeleteBtn.addEventListener("click", deleteTodoTask);
}
if (todoSearchInput) {
  todoSearchInput.addEventListener("input", applyTodoFilters);
}
if (todoTagFilterInput) {
  todoTagFilterInput.addEventListener("input", applyTodoFilters);
}
if (todoFilterClearBtn) {
  todoFilterClearBtn.addEventListener("click", clearTodoFilters);
}
if (todoCollapseToggles.length) {
  todoCollapseToggles.forEach((btn) => {
    btn.addEventListener("click", () => toggleTodoCollapse(btn.dataset.target || ""));
  });
}
Object.values(todoSections).forEach((section) => {
  if (!section) return;
  section.addEventListener("dragover", handleTodoDragOver);
  section.addEventListener("drop", handleTodoDrop);
  section.addEventListener("dragenter", handleTodoDragOver);
  section.addEventListener("dragleave", () => section.classList.remove("drag-over"));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && document.body.classList.contains("modules-open")) {
    setModulesOpen(false);
  }
});
if (refreshNewsBtn) {
  refreshNewsBtn.addEventListener("click", refreshNews);
}
if (loadNewsBtn) {
  loadNewsBtn.addEventListener("click", loadNewsList);
}
if (saveNewsConfigBtn) {
  saveNewsConfigBtn.addEventListener("click", applyNewsConfig);
}
if (saveMediaConfigBtn) {
  saveMediaConfigBtn.addEventListener("click", applyMediaConfig);
}
if (refreshMediaBtn) {
  refreshMediaBtn.addEventListener("click", refreshMedia);
}
if (loadMediaBtn) {
  loadMediaBtn.addEventListener("click", loadMediaAll);
}
if (loadMediaSourcesBtn) {
  loadMediaSourcesBtn.addEventListener("click", loadMediaSources);
}
if (mediaSearchBtn) {
  mediaSearchBtn.addEventListener("click", loadMediaItems);
}
if (mediaSearchInput) {
  mediaSearchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadMediaItems();
    }
  });
}
if (addMediaSourceBtn) {
  addMediaSourceBtn.addEventListener("click", addMediaSource);
}
if (addMediaItemBtn) {
  addMediaItemBtn.addEventListener("click", addManualMediaItem);
}
if (refreshMediaBriefsBtn) {
  refreshMediaBriefsBtn.addEventListener("click", loadMediaBriefList);
}
if (sendWebhookBtn) {
  sendWebhookBtn.addEventListener("click", sendWebhookNow);
}
if (refreshWebhookBtn) {
  refreshWebhookBtn.addEventListener("click", loadWebhookLogs);
}
if (clearWebhookBtn) {
  clearWebhookBtn.addEventListener("click", clearWebhookLogs);
}
refreshArtifactsBtn.addEventListener("click", loadArtifacts);
if (artifactSearchBtn) {
  artifactSearchBtn.addEventListener("click", searchArtifacts);
}
if (artifactFilterBtn) {
  artifactFilterBtn.addEventListener("click", searchArtifacts);
}
if (artifactSearchInput) {
  artifactSearchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchArtifacts();
    }
  });
}
if (artifactDiffBtn) {
  artifactDiffBtn.addEventListener("click", diffArtifacts);
}
if (artifactDiffAllBtn) {
  artifactDiffAllBtn.addEventListener("click", diffArtifactsAll);
}
if (archiveSelectedBtn) {
  archiveSelectedBtn.addEventListener("click", archiveSelectedArtifacts);
}
if (clearSelectedBtn) {
  clearSelectedBtn.addEventListener("click", clearSelectedArtifacts);
}
if (cleanupBtn) {
  cleanupBtn.addEventListener("click", cleanupArtifacts);
}
applyConfigBtn.addEventListener("click", applyConfig);
modeFastBtn.addEventListener("click", () => sendCommand("/mode fast"));
modeBalancedBtn.addEventListener("click", () => sendCommand("/mode balanced"));
modeQualityBtn.addEventListener("click", () => sendCommand("/mode quality"));
if (reloadPluginsBtn) {
  reloadPluginsBtn.addEventListener("click", reloadPlugins);
}
if (replyClearBtn) {
  replyClearBtn.addEventListener("click", clearReplyTarget);
}
if (commandBtn) {
  commandBtn.addEventListener("click", openCommandPalette);
}
if (streamBtn) {
  streamBtn.addEventListener("click", toggleStream);
}
if (applyProfileBtn) {
  applyProfileBtn.addEventListener("click", applyProfile);
}
if (kbIndexBtn) {
  kbIndexBtn.addEventListener("click", () => indexKb(false));
}
if (kbRebuildBtn) {
  kbRebuildBtn.addEventListener("click", () => indexKb(true));
}
if (kbClearBtn) {
  kbClearBtn.addEventListener("click", clearKb);
}
if (kbSearchBtn) {
  kbSearchBtn.addEventListener("click", searchKb);
}
if (kbSearchInput) {
  kbSearchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchKb();
    }
  });
}

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.ctrlKey) {
    event.preventDefault();
    sendMessage();
  }
});
document.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && key === "k") {
    event.preventDefault();
    openCommandPalette();
  }
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && key === "p") {
    event.preventDefault();
    openCommandPalette();
  }
  if (event.key === "Escape" && suggestionsEl && suggestionsEl.classList.contains("active")) {
    suggestionsEl.classList.remove("active");
    suggestionsEl.innerHTML = "";
  }
});
messageInput.addEventListener("input", () => {
  updateSuggestions();
  saveDraft(messageInput.value);
});
messageInput.addEventListener("blur", () => {
  setTimeout(() => {
    if (suggestionsEl) {
      suggestionsEl.classList.remove("active");
      suggestionsEl.innerHTML = "";
    }
  }, 120);
});
if (chatLog) {
  chatLog.addEventListener("scroll", () => {
    if (chatLog.scrollTop < 40) {
      loadOlderMessages();
    }
  });
}

slotItems.forEach((item) => {
  item.addEventListener("click", async () => {
    const slot = item.dataset.slot;
    if (!slot || !state.slots[slot]) return;
    const info = state.slots[slot];
    if (info.sessionId) {
      const ok = await checkSession(info.sessionId);
      if (ok) {
        activateSession(info.sessionId, slot, false);
        refreshStatus(false);
        return;
      }
    }
    await createSessionForSlot(slot);
    refreshStatus(false);
  });
});

railButtons.forEach((btn) => {
  btn.addEventListener("click", () => handleRailAction(btn));
});

themeButtons.forEach((btn) => {
  btn.addEventListener("click", () => applyTheme(btn.dataset.theme || "light"));
});

filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => setFilterRole(btn.dataset.role));
});

function handleRailAction(button) {
  const action = button.dataset.action;
  if (!action) return;
  if (action === "todo") {
    setMainView("todo");
    setRailActive("todo");
    return;
  }
  if (action === "focus") {
    setMainView("chat");
    setRailActive("focus");
    messageInput.focus();
    return;
  }
  if (action === "top") {
    chatLog.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }
  if (action === "bottom") {
    chatLog.scrollTo({ top: chatLog.scrollHeight, behavior: "smooth" });
    return;
  }
  if (action === "export") {
    exportTranscript();
    return;
  }
  if (action === "compact") {
    document.body.classList.toggle("compact");
    button.classList.toggle("is-on");
    renderMessage(
      "system",
      document.body.classList.contains("compact") ? "Compact view enabled." : "Compact view disabled.",
      { skipStore: true }
    );
    return;
  }
  if (action === "calm") {
    document.body.classList.toggle("calm");
    button.classList.toggle("is-on");
    renderMessage(
      "system",
      document.body.classList.contains("calm") ? "Calm mode enabled." : "Calm mode disabled.",
      { skipStore: true }
    );
  }
}

function exportTranscript() {
  const lines = [];
  chatLog.querySelectorAll(".message").forEach((node) => {
    const role = node.dataset.role || "system";
    const time = node.dataset.time || "";
    const body = node.querySelector(".message-body");
    const text = body ? body.textContent : "";
    lines.push(`[${time}] ${role.toUpperCase()}: ${text}`);
  });
  const payload = lines.join("\n");
  const filename = `sama_chat_${Date.now()}.txt`;
  downloadText(payload, filename);
  renderMessage("system", "Transcript exported.", { skipStore: true });
}

function exportTranscriptMarkdown() {
  if (!state.sessionId) return;
  const items = getTranscriptItems(state.sessionId);
  const lines = ["# SAMA Transcript", ""];
  items.forEach((item) => {
    const role = (item.role || "system").toUpperCase();
    const time = item.time || "";
    lines.push(`## [${time}] ${role}`);
    lines.push("");
    lines.push(item.content || "");
    lines.push("");
  });
  const payload = lines.join("\n");
  const filename = `sama_chat_${Date.now()}.md`;
  downloadText(payload, filename);
  renderMessage("system", "Markdown exported.", { skipStore: true });
}

function exportTranscriptJson() {
  if (!state.sessionId) return;
  const items = getTranscriptItems(state.sessionId);
  const payload = JSON.stringify({ session_id: state.sessionId, messages: items }, null, 2);
  const filename = `sama_chat_${Date.now()}.json`;
  downloadText(payload, filename);
  renderMessage("system", "JSON exported.", { skipStore: true });
}

function downloadText(content, filename) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

function buildDocumentTitle(content) {
  const raw = (content || "").split("\n").map((line) => line.trim()).find((line) => line);
  if (!raw) return "SAMA Export";
  return truncate(raw.replace(/^#+\s*/, ""), 60) || "SAMA Export";
}

function normalizeAttachment(attachment) {
  if (!attachment || !attachment.url) return null;
  const name = String(attachment.name || "file").replace(/[\r\n]+/g, " ").trim();
  const title = String(attachment.title || name || "File").replace(/[\r\n]+/g, " ").trim();
  const format = String(attachment.format || "").replace(/[\r\n]+/g, " ").trim();
  const url = String(attachment.url || "").trim();
  const safeUrl = sanitizeUrl(url);
  if (safeUrl === "#") return null;
  return {
    type: attachment.type || "file",
    name: name || "file",
    title: title || name || "File",
    format,
    url: safeUrl,
  };
}

function buildDocumentAttachment(document) {
  if (!document) return null;
  return normalizeAttachment({
    type: "document",
    name: document.name || document.file_name || "document",
    title: document.title || document.name || "Document",
    format: document.format || "",
    url: document.url || "",
  });
}

function openAttachment(attachment) {
  const url = attachment && attachment.url ? attachment.url : "";
  if (!url) return;
  window.open(url, "_blank", "noopener");
}

async function downloadAttachment(attachment) {
  const url = attachment && attachment.url ? attachment.url : "";
  if (!url) return;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Download failed: ${res.status}`);
    }
    const blob = await res.blob();
    const name = attachment.name || "document";
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    renderMessage("system", "File saved.", { skipStore: true });
  } catch (err) {
    renderMessage("system", `Download failed: ${err.message}`, { skipStore: true });
    addError(`Download failed: ${err.message}`);
  }
}

function buildAttachmentCard(attachment) {
  const card = document.createElement("div");
  card.className = "attachment-card";
  card.addEventListener("click", () => {
    openAttachment(attachment);
  });

  const header = document.createElement("div");
  header.className = "attachment-header";

  const title = document.createElement("div");
  title.className = "attachment-title";
  title.textContent = attachment.title || attachment.name || "File";

  const meta = document.createElement("div");
  meta.className = "attachment-meta";
  const format = String(attachment.format || "").toUpperCase() || "FILE";
  meta.textContent = `${format} · ${attachment.name || "file"}`;

  header.appendChild(title);
  header.appendChild(meta);

  const actions = document.createElement("div");
  actions.className = "attachment-actions";

  const openBtn = document.createElement("button");
  openBtn.textContent = "OPEN";
  openBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    openAttachment(attachment);
  });

  const saveBtn = document.createElement("button");
  saveBtn.textContent = "SAVE";
  saveBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    downloadAttachment(attachment);
  });

  actions.appendChild(openBtn);
  actions.appendChild(saveBtn);

  card.appendChild(header);
  card.appendChild(actions);
  return card;
}

function renderAttachments(wrapper, attachments) {
  if (!wrapper || !Array.isArray(attachments) || !attachments.length) return;
  const body = wrapper.querySelector(".message-body");
  if (!body) return;
  const container = document.createElement("div");
  container.className = "message-attachments";
  attachments.forEach((attachment) => {
    const normalized = normalizeAttachment(attachment);
    if (!normalized) return;
    const card = buildAttachmentCard(normalized);
    container.appendChild(card);
  });
  if (container.childElementCount) {
    body.appendChild(container);
  }
}

function renderDocumentMessage(document) {
  const attachment = buildDocumentAttachment(document);
  if (!attachment) return;
  const label = attachment.title || attachment.name || "Document";
  const message = `File ready: ${label}`;
  renderMessage("assistant", message, { skipStore: false, markdown: false, attachments: [attachment] });
}

async function generateDocument(format) {
  const replySource = state.replyTarget ? state.replyTarget.content : "";
  const items = getTranscriptItems(state.sessionId);
  const assistantFallback = getLatestTranscriptContent(items, "assistant");
  const userFallback = getLatestTranscriptContent(items, "user");
  const inputFallback = messageInput.value.trim();
  let content = replySource || state.lastReply || assistantFallback || "";
  if (!content && inputFallback) {
    content = inputFallback;
  }
  if (!content && userFallback) {
    content = userFallback;
  }
  if (!content) {
    content = buildTranscriptExport(items, 8);
  }
  if (!content) {
    renderMessage("system", "No content to export.", { skipStore: true });
    return;
  }
  const title = buildDocumentTitle(content);
  const formatLabel = String(format || "").toUpperCase();
  renderMessage("system", `Generating ${formatLabel}...`, { skipStore: true });
  try {
    const data = await postJson("/api/documents/generate", {
      format,
      title,
      content,
      session_id: state.sessionId,
    });
    if (data && data.document) {
      renderDocumentMessage(data.document);
      loadArtifacts();
    }
  } catch (err) {
    addError(`Document export failed: ${err.message}`);
    renderMessage("system", `Document export failed: ${err.message}`, { skipStore: true });
  }
}

async function refreshStatus(showMessage) {
  if (!state.sessionId) return;
  try {
    const data = await fetchJson(`/api/status?session_id=${encodeURIComponent(state.sessionId)}&client_id=${encodeURIComponent(state.clientId || "")}`);
    if (data && data.state) {
      const rawState = String(data.state).toLowerCase();
      const tone = rawState === "thinking" || rawState === "executing" ? "busy" : "ready";
      setStatus(String(data.state).toUpperCase(), tone);
      statusHint.textContent = `State ${String(data.state).toUpperCase()}`;
      queueHint.textContent = `Steps ${data.current_step || 0}`;
      updateProgress(data.current_step || 0, state.maxIterations || 0);
    }
    if (typeof data.collaborators === "number" && collabCount) {
      collabCount.textContent = String(data.collaborators);
    }
    if (showMessage) {
      renderMessage("system", "Status synced.", { skipStore: true });
    }
  } catch (err) {
    if (showMessage) {
      renderMessage("system", `Sync failed: ${err.message}`, { skipStore: true });
    }
    addError(`Status sync failed: ${err.message}`);
  }
}

async function copyShareLink() {
  if (!state.sessionId) {
    renderMessage("system", "No active session.");
    return;
  }
  const url = new URL(window.location.href);
  url.searchParams.set("session", state.sessionId);
  try {
    await navigator.clipboard.writeText(url.toString());
    renderMessage("system", "Session link copied.", { skipStore: true });
  } catch (err) {
    renderMessage("system", "Copy failed. Please copy the URL manually.", { skipStore: true });
  }
}

async function openDashboard() {
  const popup = window.open("", "_blank");
  try {
    const data = await fetchJson("/api/dashboard?start=1");
    if (data && data.url) {
      setDashboardStatus(data.url, data.running);
      if (popup) {
        popup.location = data.url;
      } else {
        window.open(data.url, "_blank");
      }
      renderMessage("system", "Dashboard link ready.", { skipStore: true });
      return;
    }
    setDashboardStatus("", false);
    renderMessage("system", "Dashboard unavailable.", { skipStore: true });
  } catch (err) {
    setDashboardStatus("", false);
    addError(`Dashboard open failed: ${err.message}`);
    if (popup) {
      popup.close();
    }
  }
}

async function boot() {
  setBusy(false);
  initClientId();
  loadSlots();
  loadTranscripts();
  loadTheme();
  loadStreamSetting();
  loadTemplates();
  loadErrors();
  loadPresetState();
  setMainView("chat");
  setRailActive("focus");
  initTodoSections();
  loadTodoProjects();
  loadTodoFilters();
  loadTodoCollapses();
  initModuleDock();
  renderRunLog();
  updateReplyBanner();
  updateFilterButtons();
  updateSlotUI();
  await loadInfo();
  await loadConfig();
  resetProgress();
  await ensureSession();
  loadDraft();
  await loadDashboardStatus();
  await loadAuditLogs();
  await loadMetrics();
  await loadNewsList();
  await loadMediaAll();
  await loadWebhookLogs();
  loadArtifacts();
  loadPlugins();
  loadProfiles();
  loadContextReport();
  loadMemoryStats();
  loadSnapshots();
  loadArchives();
  loadKbStatus();
  loadTasks();
  loadBookmarks();
  loadReminders();
  loadReminderLogs();
  loadFocusSessions();
  loadKbMap();
  loadWorkflowTemplates();
  loadArtifactTags();
  loadSystemMetrics();
  loadLogsCenter();
  loadTriggers();
  refreshStatus(false);
}

boot();
