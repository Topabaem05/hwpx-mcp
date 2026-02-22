const CONFIG_KEY = "hwpxUi.config.v6";

const defaultConfig = {
  backendBaseUrl:
    window.hwpxUi?.getConfig?.()?.backendBaseUrl ?? "http://127.0.0.1:8000",
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
          typeof migrated.openaiApiKey !== "string"
        ) {
          migrated.openaiApiKey = migrated.openrouterKey;
        }
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

const suggestionButtons = document.querySelectorAll(".suggestion-prompt");

let sessions = [];
let activeSessionId = "";
let currentAbort = null;
let oauthVerificationUrl = "";

const status = (msg) => {
  if (statusText) {
    statusText.textContent = String(msg);
  }
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

const endpointUrl = (path) => `${normalizeBaseUrl(config.backendBaseUrl)}${path}`;

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

const addMsg = (role, text, streaming = false) => {
  const session = activeSession();
  if (!session) return null;

  const message = { role, text, ts: Date.now(), streaming };
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

    const body = message.streaming
      ? '<div class="flex items-center gap-1 h-6"><div class="w-2 h-2 bg-zinc-500 rounded-full typing-dot"></div><div class="w-2 h-2 bg-zinc-500 rounded-full typing-dot"></div><div class="w-2 h-2 bg-zinc-500 rounded-full typing-dot"></div></div>'
      : `<div class="prose prose-invert max-w-none text-zinc-200 text-[15px] leading-relaxed break-words">${escapeHtml(
          message.text
        )}</div>`;

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
  if (openaiApiKeyInput) openaiApiKeyInput.value = config.openaiApiKey;
  if (gptOauthTokenInput) gptOauthTokenInput.value = config.gptOauthToken;
};

const renderAll = () => {
  renderSessionList();
  renderMessages();
  const title = activeSession()?.title ?? "OpenAI (gpt-4o-mini)";
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
  return window.hwpxUi.restartBackend({
    openaiApiKey: config.openaiApiKey,
    gptOauthToken: config.gptOauthToken,
  });
};

const checkAgentEndpoint = async () => {
  const response = await fetch(endpointUrl("/agent/health"), {
    method: "GET",
    headers: { accept: "application/json" },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Agent ${response.status}: ${body.slice(0, 160)}`);
  }

  return response.json();
};

const callAgentChat = async (message, signal) => {
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
    const reason = payload?.error || payload?.message || `HTTP ${response.status}`;
    throw new Error(String(reason));
  }
  return payload;
};

const runToolOnlyAgent = async (userText, botMsg, signal) => {
  if (signal.aborted) throw new Error("Cancelled");
  const payload = await callAgentChat(userText, signal);

  let reply = "";
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    reply = payload.reply || payload.message || JSON.stringify(payload, null, 2);
    if (payload.case && payload.subagent) {
      status(`Case: ${payload.case} | Subagent: ${payload.subagent}`);
    }
  } else if (typeof payload === "string") {
    reply = payload;
  } else {
    reply = JSON.stringify(payload, null, 2);
  }

  botMsg.text = reply;
  botMsg.streaming = false;
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
      botMsg.text =
        controller.signal.aborted ? "Cancelled." : `Error: ${error?.message || String(error)}`;
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
    if (backendStatus.running) {
      status(`Backend process running (pid ${backendStatus.pid}). Connecting...`);
    } else {
      status("Backend process not running. Trying to connect anyway...");
    }
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const health = await checkAgentEndpoint();
      const defaults = health?.defaults || {};
      status(`Agent connected (${defaults.provider || "openai"} / ${defaults.model || "gpt-4o-mini"})`);
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

saveSettingsBtn?.addEventListener("click", () => {
  config.backendBaseUrl = normalizeBaseUrl(backendBaseUrlInput?.value || "");
  config.openaiApiKey = (openaiApiKeyInput?.value || "").trim();
  config.gptOauthToken = (gptOauthTokenInput?.value || "").trim();
  persistConfig();
  status("Settings saved. Restarting backend...");
  restartBackendWithCurrentCredentials()
    .then((result) => {
      status(`Backend restarted (pid ${result?.pid || "?"}).`);
    })
    .catch((error) => {
      status(`Backend restart failed: ${error?.message || String(error)}`);
    });
});

resetSettingsBtn?.addEventListener("click", () => {
  localStorage.removeItem(CONFIG_KEY);
  config = { ...defaultConfig };
  renderConfig();
  hideOauthCodePanel();
  status("Settings reset");
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
    const restart = await restartBackendWithCurrentCredentials();
    status(`OpenAI OAuth connected (pid ${restart?.pid || "?"}).`);
  } catch (error) {
    status(`OpenAI OAuth login failed: ${error?.message || String(error)}`);
  } finally {
    openAiOauthLoginBtn.disabled = false;
  }
});

checkGatewayBtn?.addEventListener("click", async () => {
  try {
    const health = await checkAgentEndpoint();
    const defaults = health?.defaults || {};
    status(`Agent healthy (${defaults.provider || "openai"} / ${defaults.model || "gpt-4o-mini"})`);
  } catch (error) {
    status(`Agent check failed: ${error?.message || String(error)}`);
  }
});

restartBackendBtn?.addEventListener("click", async () => {
  status("Restarting backend...");
  try {
    const result = await restartBackendWithCurrentCredentials();
    status(`Backend restarted (pid ${result?.pid || "?"}). Waiting...`);
  } catch (error) {
    status(`Restart failed: ${error?.message || String(error)}`);
  }
  await new Promise((resolve) => setTimeout(resolve, 3000));
  await waitForBackend(10, 2000);
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

if (sessions.length === 0) createSession();
renderConfig();
renderAll();
autoResize();
updateSendBtn();

(async () => {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  if (config.openaiApiKey || config.gptOauthToken) {
    try {
      await restartBackendWithCurrentCredentials();
    } catch (error) {
      status(`Backend restart failed: ${error?.message || String(error)}`);
    }
  }
  await waitForBackend(15, 2000);
})();
