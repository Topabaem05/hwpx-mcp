const CONFIG_KEY = "hwpxUi.config.v6";

const PROVIDER_OPTIONS = {
  "codex-proxy": {
    label: "Codex Proxy",
    defaultModel: "gpt-5",
  },
  openrouter: {
    label: "OpenRouter / Local Qwen",
    defaultModel: "openai/gpt-oss-120b",
  },
  openai: {
    label: "OpenAI",
    defaultModel: "gpt-4o-mini",
  },
};

const normalizeProviderValue = (value) =>
  typeof value === "string" && Object.prototype.hasOwnProperty.call(PROVIDER_OPTIONS, value)
    ? value
    : "openrouter";

const defaultModelForProvider = (provider) =>
  PROVIDER_OPTIONS[normalizeProviderValue(provider)].defaultModel;

const providerLabel = (provider) => PROVIDER_OPTIONS[normalizeProviderValue(provider)].label;

const normalizeModelValue = (provider, value) => {
  const trimmed = typeof value === "string" ? value.trim() : "";
  return trimmed || defaultModelForProvider(provider);
};

const defaultCodexProxyUrl = () =>
  window.hwpxUi?.getConfig?.()?.codexProxyUrl || "http://127.0.0.1:2455/v1/chat/completions";

const normalizeCodexProxyUrl = (value) => {
  const trimmed = typeof value === "string" ? value.trim() : "";
  const base = trimmed || defaultCodexProxyUrl();
  const normalized = base.replace(/\/+$/, "");
  if (/\/chat\/completions$/i.test(normalized)) {
    return normalized;
  }
  if (/\/v1$/i.test(normalized)) {
    return `${normalized}/chat/completions`;
  }
  return `${normalized}/chat/completions`;
};

const defaultConfig = {
  backendBaseUrl:
    window.hwpxUi?.getConfig?.()?.backendBaseUrl ?? "http://127.0.0.1:8000",
  provider: normalizeProviderValue(window.hwpxUi?.getConfig?.()?.provider),
  model: normalizeModelValue(
    window.hwpxUi?.getConfig?.()?.provider,
    window.hwpxUi?.getConfig?.()?.model
  ),
  codexProxyUrl: normalizeCodexProxyUrl(window.hwpxUi?.getConfig?.()?.codexProxyUrl),
  codexProxyAccessToken: "",
  openrouterApiKey: "",
  openaiApiKey: "",
  gptOauthToken: "",
};

const loadConfig = () => {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        const migrated = { ...parsed };
        if (typeof migrated.apiKey === "string" && typeof migrated.openaiApiKey !== "string") {
          migrated.openaiApiKey = migrated.apiKey;
        }
        if (
          typeof migrated.openrouterKey === "string" &&
          typeof migrated.openrouterApiKey !== "string"
        ) {
          migrated.openrouterApiKey = migrated.openrouterKey;
        }
        if (typeof migrated.codexProxyUrl !== "string" && typeof migrated.proxyUrl === "string") {
          migrated.codexProxyUrl = migrated.proxyUrl;
        }
        if (
          typeof migrated.codexProxyAccessToken !== "string" &&
          typeof migrated.proxyAccessToken === "string"
        ) {
          migrated.codexProxyAccessToken = migrated.proxyAccessToken;
        }
        if (typeof migrated.provider !== "string") {
          if ((migrated.codexProxyAccessToken || "").trim()) {
            migrated.provider = "codex-proxy";
          } else if ((migrated.openrouterApiKey || "").trim()) {
            migrated.provider = "openrouter";
          } else if ((migrated.openaiApiKey || "").trim() || (migrated.gptOauthToken || "").trim()) {
            migrated.provider = "openai";
          }
        }
        migrated.provider = normalizeProviderValue(migrated.provider);
        migrated.model = normalizeModelValue(migrated.provider, migrated.model);
        migrated.codexProxyUrl = normalizeCodexProxyUrl(migrated.codexProxyUrl);
        return { ...defaultConfig, ...migrated };
      }
    }
  } catch {
  }
  return { ...defaultConfig };
};

let config = loadConfig();
const persistConfig = () => localStorage.setItem(CONFIG_KEY, JSON.stringify(config));

const $ = (id) => document.getElementById(id);

const sidebar = $("sidebar");
const sidebarOverlay = $("sidebar-overlay");
const closeSidebarBtn = $("closeSidebar");
const sidebarToggleBtn = $("sidebarToggle");

const chatContainer = $("chat-container");
const chatTitle = $("chatTitle");
const messageList = $("message-list");
const welcomeScreen = $("welcome-screen");
const messageInput = $("message-input");
const sendBtn = $("send-btn");
const chatForm = $("chatForm");
const sessionList = $("sessionList");
const newSessionBtn = $("newSession");

const openSettingsBtn = $("openSettingsBtn");
const openSettingsHeaderBtn = $("openSettingsHeaderBtn");
const settingsModal = $("settingsModal");
const settingsOverlay = $("settingsOverlay");
const closeSettingsBtn = $("closeSettingsBtn");

const backendBaseUrlInput = $("backendBaseUrlInput");
const providerSelect = $("providerSelect");
const modelInput = $("modelInput");
const modelModeHint = $("modelModeHint");
const codexProxySection = $("codexProxySection");
const codexProxyUrlInput = $("codexProxyUrlInput");
const codexProxyAccessTokenInput = $("codexProxyAccessTokenInput");
const openrouterApiKeyInput = $("openrouterApiKeyInput");
const localModelStatusBadge = $("localModelStatusBadge");
const openrouterKeyRow = $("openrouterKeyRow");
const openaiAuthSection = $("openaiAuthSection");
const openaiApiKeyInput = $("openaiApiKeyInput");
const gptOauthTokenInput = $("gptOauthTokenInput");
const openAiOauthLoginBtn = $("openAiOauthLoginBtn");
const oauthCodePanel = $("oauthCodePanel");
const oauthUserCode = $("oauthUserCode");
const oauthManualHint = $("oauthManualHint");
const oauthCopyCodeBtn = $("oauthCopyCodeBtn");
const oauthOpenLinkBtn = $("oauthOpenLinkBtn");
const saveSettingsBtn = $("saveSettings");
const resetSettingsBtn = $("resetSettings");
const checkGatewayBtn = $("checkGateway");
const restartBackendBtn = $("restartBackend");
const statusText = $("statusText");
const appUpdateText = $("appUpdateText");

const suggestionButtons = document.querySelectorAll(".suggestion-prompt");

let sessions = [];
let activeSessionId = "";
let currentAbort = null;
let oauthVerificationUrl = "";
let latestAgentHealth = null;

const status = (msg) => {
  if (statusText) {
    statusText.textContent = String(msg);
  }
};

const setAppUpdateText = (msg) => {
  if (appUpdateText) {
    appUpdateText.textContent = String(msg);
  }
};

const currentProvider = () => normalizeProviderValue(config.provider);

const currentModel = () => normalizeModelValue(currentProvider(), config.model);

const currentCodexProxyUrl = () => normalizeCodexProxyUrl(config.codexProxyUrl);

const visibleAuthModeLabel = () => {
  if (currentProvider() === "codex-proxy") {
    return "Codex Proxy Access Token";
  }
  if (currentProvider() === "openrouter") {
    return "OpenRouter API Key or local Qwen3.5-4B";
  }
  return "OpenAI OAuth / API Key";
};

const openRouterKeyPresent = () => Boolean((config.openrouterApiKey || "").trim());

const describeLocalModelBadge = (health) => {
  const localModel = localModelStateFromHealth(health);
  if (currentProvider() !== "openrouter") {
    return {
      text: "OpenRouter provider를 선택하면 로컬 Qwen fallback 상태가 여기에 표시됩니다.",
      className: "rounded-xl border border-zinc-700 bg-zinc-850 px-3 py-2 text-[11px] text-zinc-400",
    };
  }

  if (openRouterKeyPresent()) {
    return {
      text: `OpenRouter API Key configured - remote model ${currentModel()} will be used.`,
      className: "rounded-xl border border-sky-400/20 bg-sky-500/8 px-3 py-2 text-[11px] text-sky-100",
    };
  }

  if (localModel?.ready) {
    return {
      text: `OpenRouter key empty - local ${localModel.model_id || "Qwen/Qwen3.5-4B"} is ready.`,
      className: "rounded-xl border border-emerald-400/20 bg-emerald-500/8 px-3 py-2 text-[11px] text-emerald-100",
    };
  }

  if (localModel?.downloading) {
    return {
      text: `OpenRouter key empty - downloading local ${localModel.model_id || "Qwen/Qwen3.5-4B"} now.`,
      className: "rounded-xl border border-amber-400/20 bg-amber-500/8 px-3 py-2 text-[11px] text-amber-100",
    };
  }

  return {
    text: "OpenRouter key empty - local Qwen/Qwen3.5-4B will be downloaded and used automatically.",
    className: "rounded-xl border border-emerald-400/20 bg-emerald-500/8 px-3 py-2 text-[11px] text-emerald-100",
  };
};

const runtimeConfigFromHealth = (health) => {
  const runtime = health?.runtime && typeof health.runtime === "object" ? health.runtime : null;
  const defaults = health?.defaults && typeof health.defaults === "object" ? health.defaults : null;
  const provider = normalizeProviderValue(runtime?.provider || defaults?.provider || config.provider);
  const model = normalizeModelValue(provider, runtime?.model || defaults?.model || config.model);
  const proxyUrl =
    provider === "codex-proxy"
      ? normalizeCodexProxyUrl(runtime?.proxy_url || config.codexProxyUrl)
      : "";
  return { provider, model, proxyUrl };
};

const updateProviderUi = () => {
  const provider = currentProvider();
  const isCodexProxy = provider === "codex-proxy";
  const isOpenRouter = provider === "openrouter";
  const usesLocalFallback = isOpenRouter && !openRouterKeyPresent();

  codexProxySection?.classList.toggle("hidden", !isCodexProxy);
  openrouterKeyRow?.classList.toggle("hidden", !isOpenRouter);
  openaiAuthSection?.classList.toggle("hidden", isCodexProxy || isOpenRouter);
  if (modelInput) {
    modelInput.placeholder = usesLocalFallback
      ? `${defaultModelForProvider(provider)} (saved for remote use)`
      : defaultModelForProvider(provider);
  }
  if (modelModeHint) {
    modelModeHint.textContent = usesLocalFallback
      ? "현재는 로컬 Qwen/Qwen3.5-4B로 실행됩니다. 여기 입력한 모델 값은 나중에 OpenRouter API Key를 넣었을 때 사용됩니다."
      : "OpenRouter API Key가 있으면 이 모델을 사용하고, 비어 있으면 로컬 Qwen3.5-4B로 실행합니다.";
  }
  if (localModelStatusBadge) {
    const badge = describeLocalModelBadge(latestAgentHealth);
    localModelStatusBadge.textContent = badge.text;
    localModelStatusBadge.className = badge.className;
  }

  if (chatTitle) {
    chatTitle.innerHTML = `${escapeHtml(`${providerLabel(provider)} (${currentModel()})`)} <i data-lucide="chevron-down" class="w-4 h-4 text-zinc-500"></i>`;
  }
};

const describeAppUpdateStatus = (payload) => {
  if (!payload || typeof payload !== "object") {
    return "앱 자동 업데이트 상태를 확인하지 못했습니다.";
  }

  switch (payload.state) {
    case "disabled-dev":
      return "개발 모드에서는 앱 자동 업데이트를 사용하지 않습니다.";
    case "checking":
      return "앱 업데이트 확인 중...";
    case "available":
      return `새 앱 버전 ${payload.version || ""} 다운로드 중...`.trim();
    case "downloading":
      return `앱 업데이트 다운로드 중... ${Number(payload.percent || 0).toFixed(1)}%`;
    case "downloaded":
      return `앱 업데이트 ${payload.version || ""} 준비 완료 - 재시작 시 설치됩니다.`.trim();
    case "not-available":
      return `앱 최신 상태 (${payload.version || "현재 버전"})`;
    case "error":
      return payload.message || "앱 자동 업데이트 확인에 실패했습니다.";
    default:
      return payload.message || "앱 자동 업데이트 대기 중";
  }
};

const describeAgentHealth = (health, prefix = "Agent connected") => {
  const runtime = runtimeConfigFromHealth(health);
  const provider = runtime.provider;
  const model = runtime.model;
  const auth = health?.auth;
  const base = `${prefix} (${provider} / ${model})`;

  if (!auth || typeof auth !== "object") {
    return base;
  }

  if (auth.configured === true) {
    const mode = auth.mode || "configured";
    if (mode === "local-transformers") {
      return `${base}, local fallback Qwen/Qwen3.5-4B active`;
    }
    const source = auth.source ? ` via ${auth.source}` : "";
    return `${base}, auth ${mode}${source}`;
  }

  const acceptedEnv =
    Array.isArray(auth.accepted_env) && auth.accepted_env.length
      ? auth.accepted_env.join(" or ")
      : visibleAuthModeLabel();
  return `${base}, auth missing: ${acceptedEnv}`;
};

const describeRestartResult = (result, successLabel = "Backend restarted") => {
  if (!result || typeof result !== "object") {
    return `${successLabel} (pid ?).`;
  }

  if (result.restarted === false && result.managed === false) {
    return "Backend management is disabled in this app. Restart the active backend manually so new credentials apply.";
  }

  if (result.restarted === false) {
    return "Backend restart failed. Check backend logs and startup command.";
  }

  return `${successLabel} (pid ${result.pid || "?"}).`;
};

const hideOauthCodePanel = () => {
  oauthCodePanel?.classList.add("hidden");
};

const showOauthCodePanel = ({ userCode, verificationUrl, manualCodeRequired }) => {
  if (!oauthCodePanel) {
    return;
  }

  oauthVerificationUrl = (verificationUrl || "").trim();
  oauthCodePanel.classList.remove("hidden");

  if (oauthUserCode) {
    oauthUserCode.textContent = userCode || "-";
  }

  if (oauthManualHint) {
    oauthManualHint.textContent = manualCodeRequired
      ? "브라우저에서 위 코드를 입력해 로그인하세요."
      : "코드 입력 없이 자동 인증 링크로 로그인 진행 중입니다.";
  }
};

const normalizeBaseUrl = (value) => {
  const trimmed = (value || "").trim();
  const base = trimmed || defaultConfig.backendBaseUrl;
  return base.replace(/\/+$/, "");
};

const backendBaseFromMcpUrl = (value) => {
  if (typeof value !== "string") {
    return "";
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }

  return trimmed.replace(/\/mcp\/?$/i, "").replace(/\/+$/, "");
};

const applyBackendBaseUrl = (value) => {
  const backendBase = backendBaseFromMcpUrl(value);
  if (!backendBase) {
    return "";
  }

  if (backendBase !== normalizeBaseUrl(config.backendBaseUrl)) {
    config.backendBaseUrl = backendBase;
    persistConfig();
    renderConfig();
  }

  return backendBase;
};

const authStatusLabel = (auth) => {
  if (!auth || typeof auth !== "object") {
    return "auth:unknown";
  }

  if (auth.configured) {
    if (auth.mode === "local-transformers") {
      return "auth:local-qwen3.5-4b";
    }
    return `auth:${auth.mode || "configured"}`;
  }

  return `auth:missing (${auth.detail || "token not set"})`;
};

const hasStoredAuth = (provider = currentProvider()) => {
  if (normalizeProviderValue(provider) === "codex-proxy") {
    return Boolean((config.codexProxyAccessToken || "").trim());
  }

  if (normalizeProviderValue(provider) === "openrouter") {
    return Boolean((config.openrouterApiKey || "").trim());
  }

  return Boolean((config.openaiApiKey || "").trim() || (config.gptOauthToken || "").trim());
};

const isAuthMissingErrorMessage = (message) => {
  if (typeof message !== "string") {
    return false;
  }

  return (
    message.includes("HWPX_CODEX_PROXY_ACCESS_TOKEN") ||
    message.includes("OPENROUTER_API_KEY") ||
    message.includes("OPENAI_OAUTH_TOKEN") ||
    message.includes("CODEX_OAUTH_TOKEN") ||
    message.includes("OPENAI_API_KEY")
  );
};

const authAvailableModes = (health) => {
  const modes = health?.auth?.available_modes;
  return Array.isArray(modes) ? modes.filter((value) => typeof value === "string") : [];
};

const hasAvailableAuthMode = (health, mode) => authAvailableModes(health).includes(mode);

const shouldSyncStoredAuth = (health) => {
  const runtime = runtimeConfigFromHealth(health);
  if (!hasStoredAuth(runtime.provider)) {
    return false;
  }

  if (!health?.auth?.configured) {
    return true;
  }

  if (runtime.provider === "openrouter") {
    return !hasAvailableAuthMode(health, "openrouter-api-key");
  }

  if (runtime.provider === "codex-proxy") {
    return !hasAvailableAuthMode(health, "codex-proxy-token");
  }

  if ((config.gptOauthToken || "").trim()) {
    const hasOAuthMode =
      hasAvailableAuthMode(health, "openai-oauth") || hasAvailableAuthMode(health, "codex-oauth");
    if (!hasOAuthMode) {
      return true;
    }
  }

  if ((config.openaiApiKey || "").trim() && !hasAvailableAuthMode(health, "openai-api-key")) {
    return true;
  }

  return false;
};

const attemptedAuthModes = (message) => {
  if (typeof message !== "string") {
    return [];
  }

  const marker = "attempted_auth=";
  const start = message.indexOf(marker);
  if (start === -1) {
    return [];
  }

  return message
    .slice(start + marker.length)
    .split("|")[0]
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
};

const isQuotaErrorMessage = (message) => {
  if (typeof message !== "string") {
    return false;
  }

  return message.includes("insufficient_quota") || message.includes("quota_hint");
};

const shouldRetryWithAuthSyncForError = (message) => {
  const provider = currentProvider();
  if (!hasStoredAuth(provider)) {
    return false;
  }

  if (isAuthMissingErrorMessage(message)) {
    return true;
  }

  if (provider !== "openai" || !isQuotaErrorMessage(message)) {
    return false;
  }

  return (
    !attemptedAuthModes(message).includes("openai-api-key") &&
    Boolean((config.openaiApiKey || "").trim())
  );
};

const localModelStateFromHealth = (health) => {
  if (health?.local_model && typeof health.local_model === "object") {
    return health.local_model;
  }
  if (health?.auth?.local_fallback && typeof health.auth.local_fallback === "object") {
    return health.auth.local_fallback;
  }
  return null;
};

const shouldDownloadLocalFallback = (health) => {
  const runtime = runtimeConfigFromHealth(health);
  const localModel = localModelStateFromHealth(health);
  if (!localModel || typeof localModel !== "object") {
    return false;
  }
  if (hasStoredAuth(runtime.provider)) {
    return false;
  }
  if (health?.auth?.configured) {
    return false;
  }
  if (localModel.ready || localModel.downloading) {
    return false;
  }
  return localModel.dependency_installed !== false;
};

const endpointUrl = (path) => `${normalizeBaseUrl(config.backendBaseUrl)}${path}`;

const downloadLocalModel = async (force = false) => {
  await syncBaseUrlWithBackendStatus();
  const response = await fetch(endpointUrl("/agent/local-model/download"), {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify({ force }),
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const reason =
      payload?.error ||
      payload?.message ||
      (typeof detail === "string" ? detail : Array.isArray(detail) ? JSON.stringify(detail) : "") ||
      `HTTP ${response.status}`;
    throw new Error(String(reason));
  }
  return payload;
};

const ensureLocalFallbackReady = async (health) => {
  if (!shouldDownloadLocalFallback(health)) {
    return health;
  }

  const localModel = localModelStateFromHealth(health);
  const modelId = typeof localModel?.model_id === "string" ? localModel.model_id : "local model";
  status(`No API credentials found. Downloading ${modelId} for local fallback...`);
  try {
    await downloadLocalModel();
  } catch (error) {
    status(`Local fallback setup failed: ${error?.message || String(error)}`);
    return health;
  }
  const nextHealth = await checkAgentEndpoint();
  status(describeAgentHealth(nextHealth, "Local model ready"));
  return nextHealth;
};

const closeSidebar = () => {
  sidebar?.classList.add("-translate-x-full");
  sidebarOverlay?.classList.add("hidden");
};

const openSidebar = () => {
  sidebar?.classList.remove("-translate-x-full");
  sidebarOverlay?.classList.remove("hidden");
};

const toggleSidebar = () => {
  if (sidebar?.classList.contains("-translate-x-full")) {
    openSidebar();
  } else {
    closeSidebar();
  }
};

const openSettings = () => {
  settingsModal?.classList.remove("hidden");
};

const closeSettings = () => {
  settingsModal?.classList.add("hidden");
};

const autoResize = () => {
  if (!messageInput) {
    return;
  }
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 192)}px`;
};

const updateSendBtn = () => {
  if (!sendBtn) {
    return;
  }

  const iconContainer = sendBtn.querySelector("div");
  const hasText = (messageInput?.value || "").trim().length > 0;

  if (currentAbort) {
    sendBtn.classList.remove("bg-zinc-700", "text-zinc-400");
    sendBtn.classList.add("bg-red-500", "text-white");
    if (iconContainer) {
      iconContainer.innerHTML = '<i data-lucide="square" class="w-4 h-4"></i>';
    }
  } else if (hasText) {
    sendBtn.classList.remove("bg-zinc-700", "text-zinc-400", "bg-red-500", "text-white");
    sendBtn.classList.add("bg-white", "text-black");
    if (iconContainer) {
      iconContainer.innerHTML = '<i data-lucide="arrow-up" class="w-5 h-5"></i>';
    }
  } else {
    sendBtn.classList.remove("bg-white", "text-black", "bg-red-500", "text-white");
    sendBtn.classList.add("bg-zinc-700", "text-zinc-400");
    if (iconContainer) {
      iconContainer.innerHTML = '<i data-lucide="arrow-up" class="w-5 h-5"></i>';
    }
  }

  if (window.lucide?.createIcons) {
    window.lucide.createIcons();
  }
};

const scrollToBottom = () => {
  chatContainer?.scrollTo({
    top: chatContainer.scrollHeight,
    behavior: "smooth",
  });
};

const fmt = (ms) =>
  new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const createSession = () => {
  const session = {
    id: crypto.randomUUID(),
    title: "새 채팅",
    messages: [],
  };
  sessions.unshift(session);
  activeSessionId = session.id;
  renderAll();
  return session;
};

const activeSession = () => sessions.find((session) => session.id === activeSessionId);

const makeTitle = (text) => {
  const cleaned = text.trim().replace(/\s+/g, " ");
  if (!cleaned) return "새 채팅";
  return cleaned.length > 24 ? `${cleaned.slice(0, 21)}...` : cleaned;
};

const addMsg = (role, text, streaming = false, options = {}) => {
  const session = activeSession();
  if (!session) return null;

  const message = {
    role,
    text,
    ts: Date.now(),
    streaming,
    variant: typeof options.variant === "string" ? options.variant : "",
    title: typeof options.title === "string" ? options.title : "",
  };
  session.messages.push(message);
  renderMessages();
  return message;
};

const escapeHtml = (text) =>
  String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");

const formatAgentPlan = (plan) => {
  if (!plan || typeof plan !== "object" || Array.isArray(plan)) {
    return "";
  }

  const sections = ["Plan"];
  if (typeof plan.summary === "string" && plan.summary.trim()) {
    sections.push(plan.summary.trim());
  }

  if (Array.isArray(plan.steps) && plan.steps.length) {
    const lines = plan.steps
      .map((step, index) => {
        if (!step || typeof step !== "object") {
          return "";
        }

        const title = typeof step.title === "string" ? step.title.trim() : "";
        const objective = typeof step.objective === "string" ? step.objective.trim() : "";
        const toolHint = typeof step.tool_hint === "string" ? step.tool_hint.trim() : "";
        const detail = [objective, toolHint ? `tool: ${toolHint}` : ""].filter(Boolean).join(" | ");
        const prefix = `${index + 1}. ${title || `Step ${index + 1}`}`;
        return detail ? `${prefix} - ${detail}` : prefix;
      })
      .filter(Boolean);

    if (lines.length) {
      sections.push(lines.join("\n"));
    }
  }

  return sections.join("\n\n").trim();
};

const messageVariantMeta = (message) => {
  if (message.variant === "plan") {
    return {
      badge: message.title || "Plan",
      wrapperClass:
        "rounded-2xl border border-amber-400/25 bg-amber-500/8 px-4 py-3 shadow-[0_0_0_1px_rgba(251,191,36,0.04)]",
      badgeClass:
        "inline-flex items-center rounded-full border border-amber-300/25 bg-amber-300/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-200",
      textClass: "text-amber-50",
    };
  }

  if (message.variant === "execution") {
    return {
      badge: message.title || "Execution",
      wrapperClass:
        "rounded-2xl border border-emerald-400/20 bg-emerald-500/8 px-4 py-3 shadow-[0_0_0_1px_rgba(52,211,153,0.04)]",
      badgeClass:
        "inline-flex items-center rounded-full border border-emerald-300/25 bg-emerald-300/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-200",
      textClass: "text-zinc-100",
    };
  }

  return {
    badge: "",
    wrapperClass: "",
    badgeClass: "",
    textClass: "text-zinc-200",
  };
};

const renderSessionList = () => {
  if (!sessionList) {
    return;
  }
  sessionList.innerHTML = "";

  sessions.forEach((session) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className =
      "w-full text-left px-2 py-2 text-sm rounded-lg truncate transition-colors " +
      (session.id === activeSessionId
        ? "bg-zinc-800 text-white"
        : "text-zinc-300 hover:bg-zinc-800/50");
    button.textContent = session.title;
    button.addEventListener("click", () => {
      activeSessionId = session.id;
      renderAll();
      closeSidebar();
    });
    li.appendChild(button);
    sessionList.appendChild(li);
  });
};

const renderMessages = () => {
  if (!messageList) {
    return;
  }
  messageList.innerHTML = "";

  const session = activeSession();
  if (!session) return;

  if (welcomeScreen) {
    welcomeScreen.style.display = session.messages.length ? "none" : "flex";
  }

  session.messages.forEach((message) => {
    const roleName = message.role === "user" ? "User" : "OpenAI";
    const avatar =
      message.role === "user"
        ? '<div class="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-sm">U</div>'
        : '<div class="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center border border-zinc-700"><i data-lucide="bot" class="w-5 h-5"></i></div>';
    const variantMeta = messageVariantMeta(message);

    const body = message.streaming
      ? '<div class="flex items-center gap-1 h-6"><div class="w-2 h-2 bg-zinc-500 rounded-full typing-dot"></div><div class="w-2 h-2 bg-zinc-500 rounded-full typing-dot"></div><div class="w-2 h-2 bg-zinc-500 rounded-full typing-dot"></div></div>'
      : `
        <div class="${variantMeta.wrapperClass || ""}">
          ${
            variantMeta.badge
              ? `<div class="mb-3 ${variantMeta.badgeClass}">${escapeHtml(variantMeta.badge)}</div>`
              : ""
          }
          <div class="prose prose-invert max-w-none ${variantMeta.textClass} text-[15px] leading-relaxed break-words">${escapeHtml(
            message.text
          )}</div>
        </div>`;

    const html = `
      <div class="flex gap-4 px-2 py-4 group">
        <div class="flex-shrink-0">${avatar}</div>
        <div class="flex-1 space-y-2 overflow-hidden">
          <div class="font-semibold text-zinc-100 text-sm">${roleName}</div>
          ${body}
          <div class="text-xs text-zinc-500">${fmt(message.ts)}</div>
        </div>
      </div>
    `;
    messageList.insertAdjacentHTML("beforeend", html);
  });

  if (window.lucide?.createIcons) {
    window.lucide.createIcons();
  }
  scrollToBottom();
};

const renderConfig = () => {
  if (backendBaseUrlInput) backendBaseUrlInput.value = config.backendBaseUrl;
  if (providerSelect) providerSelect.value = currentProvider();
  if (modelInput) modelInput.value = currentModel();
  if (codexProxyUrlInput) codexProxyUrlInput.value = currentCodexProxyUrl();
  if (codexProxyAccessTokenInput) codexProxyAccessTokenInput.value = config.codexProxyAccessToken;
  if (openrouterApiKeyInput) openrouterApiKeyInput.value = config.openrouterApiKey;
  if (openaiApiKeyInput) openaiApiKeyInput.value = config.openaiApiKey;
  if (gptOauthTokenInput) gptOauthTokenInput.value = config.gptOauthToken;
  updateProviderUi();
};

const renderAll = () => {
  renderSessionList();
  renderMessages();
  const title = activeSession()?.title ?? `${providerLabel(currentProvider())} (${currentModel()})`;
  if (chatTitle) {
    chatTitle.innerHTML = `${escapeHtml(title)} <i data-lucide="chevron-down" class="w-4 h-4 text-zinc-500"></i>`;
  }
  if (window.lucide?.createIcons) {
    window.lucide.createIcons();
  }
};

const restartBackendWithCurrentCredentials = async () => {
  if (!window.hwpxUi?.restartBackend) {
    return null;
  }

  const result = await window.hwpxUi.restartBackend({
    provider: currentProvider(),
    model: currentModel(),
    codexProxyUrl: currentCodexProxyUrl(),
    codexProxyAccessToken: config.codexProxyAccessToken,
    openrouterApiKey: config.openrouterApiKey,
    openaiApiKey: config.openaiApiKey,
    gptOauthToken: config.gptOauthToken,
  });

  if (result?.managed !== false) {
    applyBackendBaseUrl(result?.url);
  }
  return result;
};

const syncBaseUrlWithBackendStatus = async () => {
  if (!window.hwpxUi?.getBackendStatus) {
    return "";
  }

  const backendStatus = await window.hwpxUi.getBackendStatus();
  if (backendStatus?.managed !== false && backendStatus?.url) {
    return applyBackendBaseUrl(backendStatus.url);
  }

  if (!backendStatus?.running) {
    return "";
  }

  return applyBackendBaseUrl(backendStatus.url);
};

const checkAgentEndpoint = async () => {
  await syncBaseUrlWithBackendStatus();
  const response = await fetch(endpointUrl("/agent/health"), {
    method: "GET",
    headers: { accept: "application/json" },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Agent ${response.status}: ${body.slice(0, 160)}`);
  }

  const payload = await response.json();
  latestAgentHealth = payload;
  updateProviderUi();
  return payload;
};

const callAgentChat = async (message, signal) => {
  await syncBaseUrlWithBackendStatus();
  const response = await fetch(endpointUrl("/agent/chat"), {
    method: "POST",
    signal,
    headers: {
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: activeSessionId || "",
    }),
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const reason =
      payload?.error ||
      payload?.message ||
      (typeof detail === "string" ? detail : Array.isArray(detail) ? JSON.stringify(detail) : "") ||
      `HTTP ${response.status}`;
    throw new Error(String(reason));
  }
  return payload;
};

const syncAgentAuth = async () => {
  const maxAttempts = 8;
  const delayMs = 750;
  let lastError = "auth sync failed";

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      await syncBaseUrlWithBackendStatus();
      const response = await fetch(endpointUrl("/agent/auth"), {
        method: "POST",
        headers: {
          "content-type": "application/json",
          accept: "application/json",
        },
        body: JSON.stringify({
          codex_proxy_access_token: config.codexProxyAccessToken || "",
          openrouter_api_key: config.openrouterApiKey || "",
          openai_api_key: config.openaiApiKey || "",
          openai_oauth_token: config.gptOauthToken || "",
          codex_oauth_token: config.gptOauthToken || "",
        }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = payload?.detail;
        const reason =
          payload?.error ||
          payload?.message ||
          (typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? JSON.stringify(detail)
            : "") ||
          `HTTP ${response.status}`;
        throw new Error(String(reason));
      }

      return payload;
    } catch (error) {
      lastError = error?.message || String(error);
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }

  throw new Error(lastError);
};

const shouldSyncRuntimeConfig = (health) => {
  const runtime = runtimeConfigFromHealth(health);
  return runtime.provider !== currentProvider() || runtime.model !== currentModel();
};

const syncAgentConfig = async () => {
  const maxAttempts = 8;
  const delayMs = 750;
  let lastError = "config sync failed";

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      await syncBaseUrlWithBackendStatus();
      const response = await fetch(endpointUrl("/agent/config"), {
        method: "POST",
        headers: {
          "content-type": "application/json",
          accept: "application/json",
        },
        body: JSON.stringify({
          provider: currentProvider(),
          model: currentModel(),
          proxy_url: currentProvider() === "codex-proxy" ? currentCodexProxyUrl() : "",
        }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = payload?.detail;
        const reason =
          payload?.error ||
          payload?.message ||
          (typeof detail === "string"
            ? detail
            : Array.isArray(detail)
            ? JSON.stringify(detail)
            : "") ||
          `HTTP ${response.status}`;
        throw new Error(String(reason));
      }

      return payload;
    } catch (error) {
      lastError = error?.message || String(error);
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }

  throw new Error(lastError);
};

const runToolOnlyAgent = async (userText, botMsg, signal) => {
  if (signal.aborted) throw new Error("Cancelled");
  let payload = null;

  try {
    payload = await callAgentChat(userText, signal);
  } catch (error) {
    const reason = error?.message || String(error);
    const shouldRetryWithAuthSync = shouldRetryWithAuthSyncForError(reason);

    if (!shouldRetryWithAuthSync || signal.aborted) {
      throw error;
    }

    await syncAgentConfig();
    await syncAgentAuth();
    if (signal.aborted) {
      throw new Error("Cancelled");
    }
    payload = await callAgentChat(userText, signal);
  }

  let reply = "";
  let planText = "";
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    planText = formatAgentPlan(payload.plan);
    reply = payload.reply || payload.message || (planText ? "" : JSON.stringify(payload, null, 2));
    if (payload.case && payload.subagent) {
      status(`Case: ${payload.case} | Subagent: ${payload.subagent}`);
    }
  } else if (typeof payload === "string") {
    reply = payload;
  } else {
    reply = JSON.stringify(payload, null, 2);
  }

  botMsg.text = planText || reply;
  botMsg.streaming = false;
  botMsg.variant = planText ? "plan" : "";
  botMsg.title = planText ? "Plan" : "";

  if (planText && reply) {
    addMsg("bot", reply, false, { variant: "execution", title: "Execution" });
  }
};

const handleUserMessage = async (text) => {
  const botMsg = addMsg("bot", "", true);
  const controller = new AbortController();
  currentAbort = controller;
  updateSendBtn();

  try {
    await runToolOnlyAgent(text, botMsg, controller.signal);
  } catch (error) {
    if (botMsg) {
      const raw = error?.message || String(error);
      const hasQuotaSignal =
        typeof raw === "string" && (raw.includes("insufficient_quota") || raw.includes("quota_hint"));

      const quotaHelp = hasQuotaSignal
        ? "\n\nTip: OAuth quota is exhausted. Set 'OpenAI API Key (Fallback)' in settings and restart backend."
        : "";

      botMsg.text = controller.signal.aborted ? "Cancelled." : `Error: ${raw}${quotaHelp}`;
      botMsg.streaming = false;
    }
  } finally {
    currentAbort = null;
    updateSendBtn();
    renderMessages();
  }
};

const waitForBackend = async (maxAttempts = 15, delayMs = 2000) => {
  status("Waiting for agent backend to start...");

  if (window.hwpxUi?.getBackendStatus) {
    const backendStatus = await window.hwpxUi.getBackendStatus();
    const backendBase = await syncBaseUrlWithBackendStatus();
    if (backendStatus.running) {
      const baseHint = backendBase ? ` ${backendBase}` : "";
      status(`Backend process running (pid ${backendStatus.pid}). Connecting...${baseHint}`);
    } else if (backendStatus.managed === false) {
      status("Backend process is externally managed. Trying to connect anyway...");
    } else {
      status("Backend process not running. Trying to connect anyway...");
    }
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      let health = await checkAgentEndpoint();

      if (shouldSyncRuntimeConfig(health)) {
        try {
          await syncAgentConfig();
          health = await checkAgentEndpoint();
        } catch {
        }
      }

      if (shouldSyncStoredAuth(health)) {
        try {
          await syncAgentAuth();
          health = await checkAgentEndpoint();
        } catch {
        }
      }

      health = await ensureLocalFallbackReady(health);

      status(
        `Agent connected (${runtimeConfigFromHealth(health).provider} / ${runtimeConfigFromHealth(health).model}, ${authStatusLabel(
          health?.auth
        )})`
      );
      return true;
    } catch {
      status(`Agent starting... (${attempt}/${maxAttempts})`);
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  if (window.hwpxUi?.getBackendStatus) {
    const backendStatus = await window.hwpxUi.getBackendStatus();
    if (backendStatus.log?.length) {
      const pathHint = backendStatus.logPath
        ? `\nStartup log file: ${backendStatus.logPath}`
        : "";
      status(`Agent failed to start. Log:\n${backendStatus.log.slice(-5).join("\n")}${pathHint}`);
      return false;
    }
  }

  status("Agent backend not reachable. Click backend restart.");
  return false;
};

const sendMessage = () => {
  const text = (messageInput?.value || "").trim();
  if (!text || currentAbort) return;

  let session = activeSession();
  if (!session) {
    session = createSession();
  }

  addMsg("user", text);
  if (messageInput) {
    messageInput.value = "";
  }
  autoResize();
  updateSendBtn();

  if (session.title === "새 채팅" && session.messages.length <= 2) {
    session.title = makeTitle(text);
    renderSessionList();
    renderAll();
  }

  handleUserMessage(text);
};

const stopMessage = () => {
  if (currentAbort) {
    currentAbort.abort();
    currentAbort = null;
    updateSendBtn();
  }
};

newSessionBtn?.addEventListener("click", () => {
  createSession();
  closeSidebar();
});

sidebarToggleBtn?.addEventListener("click", toggleSidebar);
closeSidebarBtn?.addEventListener("click", closeSidebar);
sidebarOverlay?.addEventListener("click", closeSidebar);

openSettingsBtn?.addEventListener("click", openSettings);
openSettingsHeaderBtn?.addEventListener("click", openSettings);
closeSettingsBtn?.addEventListener("click", closeSettings);
settingsOverlay?.addEventListener("click", closeSettings);

saveSettingsBtn?.addEventListener("click", async () => {
  config.backendBaseUrl = normalizeBaseUrl(backendBaseUrlInput?.value || "");
  config.provider = normalizeProviderValue(providerSelect?.value);
  config.model = normalizeModelValue(config.provider, modelInput?.value);
  config.codexProxyUrl = normalizeCodexProxyUrl(codexProxyUrlInput?.value || "");
  config.codexProxyAccessToken = (codexProxyAccessTokenInput?.value || "").trim();
  config.openrouterApiKey = (openrouterApiKeyInput?.value || "").trim();
  config.openaiApiKey = (openaiApiKeyInput?.value || "").trim();
  config.gptOauthToken = (gptOauthTokenInput?.value || "").trim();
  persistConfig();
  renderConfig();
  status("Settings saved. Restarting backend...");
  let restartText = "";

  try {
    const result = await restartBackendWithCurrentCredentials();
    if (result?.managed === false) {
      restartText = "Local backend management is disabled. Syncing credentials to the current backend...";
    } else if (result?.restarted === false) {
      restartText = "Backend restart did not complete. Trying auth sync anyway...";
    } else {
      restartText = `Backend restarted (pid ${result?.pid || "?"}).`;
    }
  } catch (error) {
    restartText = `Backend restart failed: ${error?.message || String(error)}`;
  }

  await waitForBackend(10, 1000);

  try {
    await syncAgentConfig();
    if (hasStoredAuth()) {
      await syncAgentAuth();
    }
    const health = await checkAgentEndpoint();
    status(`${restartText} ${describeAgentHealth(health, "Agent ready")}`);
  } catch (error) {
    status(`${restartText} Auth sync failed: ${error?.message || String(error)}`);
  }
});

resetSettingsBtn?.addEventListener("click", () => {
  localStorage.removeItem(CONFIG_KEY);
  config = { ...defaultConfig };
  renderConfig();
  hideOauthCodePanel();
  status("Settings reset");
});

providerSelect?.addEventListener("change", () => {
  const nextProvider = normalizeProviderValue(providerSelect.value);
  const previousProvider = currentProvider();
  config.provider = nextProvider;
  if (!modelInput?.value || normalizeModelValue(previousProvider, modelInput.value) === defaultModelForProvider(previousProvider)) {
    config.model = defaultModelForProvider(nextProvider);
  } else {
    config.model = normalizeModelValue(nextProvider, modelInput.value);
  }
  renderConfig();
});

openrouterApiKeyInput?.addEventListener("input", () => {
  config.openrouterApiKey = (openrouterApiKeyInput.value || "").trim();
  updateProviderUi();
});

oauthCopyCodeBtn?.addEventListener("click", async () => {
  const code = (oauthUserCode?.textContent || "").trim();
  if (!code || code === "-") {
    status("복사할 인증 코드가 없습니다.");
    return;
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(code);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = code;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    status("인증 코드를 클립보드에 복사했습니다.");
  } catch (error) {
    status(`코드 복사 실패: ${error?.message || String(error)}`);
  }
});

oauthOpenLinkBtn?.addEventListener("click", async () => {
  const url = oauthVerificationUrl;
  if (!url) {
    status("열 수 있는 인증 링크가 없습니다.");
    return;
  }

  try {
    if (window.hwpxUi?.openExternal) {
      await window.hwpxUi.openExternal(url);
      status("브라우저에서 인증 페이지를 열었습니다.");
    }
  } catch (error) {
    status(`인증 페이지 열기 실패: ${error?.message || String(error)}`);
  }
});

if (window.hwpxUi?.onOpenAiOauthProgress) {
  window.hwpxUi.onOpenAiOauthProgress((payload) => {
    if (!payload || typeof payload !== "object") {
      return;
    }

    if (payload.stage === "starting") {
      hideOauthCodePanel();
      status("OpenAI OAuth 준비 중...");
      return;
    }

    if (payload.stage === "code_issued") {
      showOauthCodePanel({
        userCode: payload.userCode,
        verificationUrl: payload.verificationUrlComplete || payload.verificationUrl || payload.openUrl,
        manualCodeRequired: Boolean(payload.manualCodeRequired),
      });
      status(
        payload.manualCodeRequired
          ? `OpenAI OAuth 코드 발급됨: ${payload.userCode || "-"}`
          : "OpenAI OAuth 자동 인증 링크로 로그인 진행 중..."
      );
      return;
    }

    if (payload.stage === "browser_opened") {
      status("브라우저에서 OpenAI 로그인 페이지를 열었습니다.");
      return;
    }

    if (payload.stage === "token_ready") {
      status("OpenAI OAuth 토큰 확인됨. 최종 연결 중...");
      return;
    }

    if (payload.stage === "failed") {
      status(`OpenAI OAuth 로그인 실패: ${payload.error || "unknown"}`);
      return;
    }

    if (payload.stage === "completed") {
      status("OpenAI OAuth 인증 완료.");
    }
  });
}

openAiOauthLoginBtn?.addEventListener("click", async () => {
  status("Starting OpenAI OAuth login...");
  openAiOauthLoginBtn.disabled = true;
  try {
    if (!window.hwpxUi?.openAiOauthLogin) {
      throw new Error("OpenAI OAuth login is unavailable in this build");
    }

    const loginResult = await window.hwpxUi.openAiOauthLogin();
    if (!loginResult?.success) {
      throw new Error(loginResult?.error || "OpenAI OAuth login failed");
    }

    config.gptOauthToken =
      typeof loginResult.accessToken === "string" ? loginResult.accessToken : "";
    persistConfig();
    renderConfig();

    showOauthCodePanel({
      userCode: loginResult.userCode,
      verificationUrl:
        loginResult.verificationUrlComplete || loginResult.verificationUrl || loginResult.openUrl,
      manualCodeRequired: Boolean(loginResult.manualCodeRequired),
    });

    status(
      loginResult.manualCodeRequired
        ? `OpenAI OAuth verified (code ${loginResult.userCode || "issued"}). Restarting backend...`
        : "OpenAI OAuth verified. Restarting backend..."
    );
    let restartInfo = null;
    let restartError = null;

    try {
      restartInfo = await restartBackendWithCurrentCredentials();
    } catch (error) {
      restartError = error;
    }

    await waitForBackend(10, 1000);

    await syncAgentConfig();
    const authSync = hasStoredAuth() ? await syncAgentAuth() : { auth: { mode: "none" } };
    const mode = authSync?.auth?.mode || (currentProvider() === "openrouter" ? "openrouter-ready" : "unknown");
    if (restartError) {
      status(
        `OAuth token synced (${mode}). Backend restart failed: ${restartError?.message || String(
          restartError
        )}`
      );
    } else if (restartInfo?.managed === false) {
      status(`OpenAI OAuth synced to the current backend (${mode}).`);
    } else if (restartInfo?.restarted === false) {
      status(`OpenAI OAuth synced after a partial restart (${mode}).`);
    } else {
      status(`OpenAI OAuth connected (pid ${restartInfo?.pid || "?"}, ${mode}).`);
    }
  } catch (error) {
    status(`OpenAI OAuth login failed: ${error?.message || String(error)}`);
  } finally {
    openAiOauthLoginBtn.disabled = false;
  }
});

checkGatewayBtn?.addEventListener("click", async () => {
  try {
    let health = await checkAgentEndpoint();

    if (shouldSyncRuntimeConfig(health)) {
      try {
        await syncAgentConfig();
        health = await checkAgentEndpoint();
      } catch {
      }
    }

    if (shouldSyncStoredAuth(health)) {
      try {
        await syncAgentAuth();
        health = await checkAgentEndpoint();
      } catch {
      }
    }
    status(
      `Agent healthy (${runtimeConfigFromHealth(health).provider} / ${runtimeConfigFromHealth(health).model}, ${authStatusLabel(
        health?.auth
      )})`
    );
  } catch (error) {
    status(`Agent check failed: ${error?.message || String(error)}`);
  }
});

restartBackendBtn?.addEventListener("click", async () => {
  status("Restarting backend...");
  try {
    const result = await restartBackendWithCurrentCredentials();
    if (result?.managed === false) {
      status("Local backend management is disabled. Syncing credentials to the current backend...");
    } else if (result?.restarted === false) {
      status("Backend restart did not complete. Waiting before retrying auth sync...");
    } else {
      status(`Backend restarted (pid ${result?.pid || "?"}). Waiting...`);
    }
  } catch (error) {
    status(`Restart failed: ${error?.message || String(error)}`);
  }
  await new Promise((resolve) => setTimeout(resolve, 3000));
  await waitForBackend(10, 2000);

  try {
    await syncAgentConfig();
    const authSync = hasStoredAuth() ? await syncAgentAuth() : { auth: { mode: "none" } };
    const mode = authSync?.auth?.mode || "unknown";
    status(`Auth synced (${mode}).`);
  } catch (error) {
    status(`Auth sync failed: ${error?.message || String(error)}`);
  }
});

chatForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (currentAbort) {
    stopMessage();
  } else {
    sendMessage();
  }
});

sendBtn?.addEventListener("click", (event) => {
  if (!currentAbort) return;
  event.preventDefault();
  stopMessage();
});

messageInput?.addEventListener("input", () => {
  autoResize();
  updateSendBtn();
});

messageInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm?.requestSubmit();
  }
});

suggestionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const prompt = (button.getAttribute("data-prompt") || "").trim();
    if (!prompt) return;
    if (messageInput) {
      messageInput.value = prompt;
    }
    autoResize();
    updateSendBtn();
    chatForm?.requestSubmit();
  });
});

if (window.lucide?.createIcons) {
  window.lucide.createIcons();
}

if (window.hwpxUi?.getAppUpdateStatus) {
  window.hwpxUi
    .getAppUpdateStatus()
    .then((payload) => {
      setAppUpdateText(describeAppUpdateStatus(payload));
    })
    .catch((error) => {
      setAppUpdateText(`앱 자동 업데이트 상태 확인 실패: ${error?.message || String(error)}`);
    });
}

if (window.hwpxUi?.onAppUpdateStatus) {
  window.hwpxUi.onAppUpdateStatus((payload) => {
    setAppUpdateText(describeAppUpdateStatus(payload));
  });
}

if (sessions.length === 0) createSession();
renderConfig();
renderAll();
autoResize();
updateSendBtn();

(async () => {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  if (hasStoredAuth() || currentProvider() !== "openai") {
    try {
      await restartBackendWithCurrentCredentials();
    } catch (error) {
      status(`Backend restart failed: ${error?.message || String(error)}`);
    }
  }
  const ready = await waitForBackend(15, 2000);

  if (ready) {
    try {
      const health = await checkAgentEndpoint().catch(() => null);
      if (shouldSyncRuntimeConfig(health)) {
        await syncAgentConfig();
      }
      if (shouldSyncStoredAuth(health)) {
        await syncAgentAuth();
      }
    } catch (error) {
      status(`Auth sync failed: ${error?.message || String(error)}`);
    }
  }
})();
