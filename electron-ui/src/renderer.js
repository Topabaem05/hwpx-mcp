const CONFIG_KEY = "hwpxUi.config.v5";

const defaultConfig = {
  backendBaseUrl:
    window.hwpxUi?.getConfig?.()?.backendBaseUrl ?? "http://127.0.0.1:8000",
  openrouterKey: "",
  gptOauthToken: "",
};

const loadConfig = () => {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        const migrated = { ...parsed };
        if (
          typeof migrated.apiKey === "string" &&
          typeof migrated.openrouterKey !== "string"
        ) {
          migrated.openrouterKey = migrated.apiKey;
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
const messageLog = $("chatLog");
const sessionList = $("sessionList");
const statusText = $("statusText");
const messageInput = $("messageInput");
const chatForm = $("chatForm");
const newSessionBtn = $("newSession");
const checkGateway = $("checkGateway");
const restartBackendBtn = $("restartBackend");
const backendBaseUrlInput = $("backendBaseUrlInput");
const agentApiKeyInput = $("agentApiKeyInput");
const saveSettings = $("saveSettings");
const resetSettings = $("resetSettings");
const chatTitle = $("chatTitle");
const sendBtn = $("sendBtn");
const gptOauthTokenInput = $("gptOauthTokenInput");
const sidebarToggle = $("sidebarToggle");
const appShell = $("appShell");
const backdrop = $("backdrop");

let activeSessionId = null;
let sessions = [];
let currentAbort = null;

const fmt = (ms) =>
  new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const makeTitle = (text) => {
  const cleaned = text.trim().replace(/\s+/g, " ");
  if (!cleaned) return "New Chat";
  return cleaned.length > 24 ? `${cleaned.slice(0, 21)}...` : cleaned;
};
const typingHtml = () =>
  '<span class="typing"><span></span><span></span><span></span></span>';
const status = (msg) => {
  statusText.textContent = msg;
};
const closeSidebar = () => appShell.classList.remove("sidebar-open");

const normalizeBaseUrl = (value) => {
  const trimmed = value.trim();
  const base = trimmed || defaultConfig.backendBaseUrl;
  return base.replace(/\/+$/, "");
};

const endpointUrl = (path) => `${normalizeBaseUrl(config.backendBaseUrl)}${path}`;

const createSession = () => {
  const session = { id: crypto.randomUUID(), title: "New Chat", messages: [] };
  sessions.unshift(session);
  activeSessionId = session.id;
  renderAll();
  return session;
};

const activeSession = () => sessions.find((session) => session.id === activeSessionId);

const renderSessionList = () => {
  sessionList.innerHTML = "";
  for (const session of sessions) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `session-item${session.id === activeSessionId ? " active" : ""}`;
    button.textContent = session.title;
    button.addEventListener("click", () => {
      activeSessionId = session.id;
      renderAll();
      closeSidebar();
    });
    sessionList.appendChild(button);
  }
};

const renderMessages = () => {
  messageLog.innerHTML = "";
  const session = activeSession();
  if (!session) return;

  for (const message of session.messages) {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${message.role}`;

    if (message.streaming && !message.text) {
      bubble.innerHTML = typingHtml();
    } else {
      bubble.textContent = message.text;
    }

    if (message.ts) {
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = fmt(message.ts);
      bubble.appendChild(meta);
    }

    messageLog.appendChild(bubble);
  }

  messageLog.scrollTop = messageLog.scrollHeight;
};

const renderConfig = () => {
  backendBaseUrlInput.value = config.backendBaseUrl;
  agentApiKeyInput.value = config.openrouterKey;
  gptOauthTokenInput.value = config.gptOauthToken;
};

const renderAll = () => {
  renderSessionList();
  renderMessages();
  chatTitle.textContent = activeSession()?.title ?? "HWPX MCP";
};

const addMsg = (role, text, streaming = false) => {
  const session = activeSession();
  if (!session) return null;

  const message = { role, text, ts: Date.now(), streaming };
  session.messages.push(message);
  renderMessages();
  return message;
};

const updateSendBtn = () => {
  sendBtn.textContent = currentAbort ? "Stop" : "Send";
  sendBtn.type = currentAbort ? "button" : "submit";
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
        controller.signal.aborted ? "Cancelled." : `Error: ${error.message}`;
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
      status(
        `Agent connected (${defaults.provider || "cerebras/fp16"} / ${defaults.model || "openai/gpt-oss-120b"})`
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
      const lastLines = backendStatus.log.slice(-5).join("\n");
      status(`Agent failed to start. Log:\n${lastLines}`);
      return false;
    }
  }

  status("Agent backend not reachable. Click 'Restart' to try again.");
  return false;
};

saveSettings.addEventListener("click", () => {
  config.backendBaseUrl = normalizeBaseUrl(backendBaseUrlInput.value);
  config.openrouterKey = agentApiKeyInput.value.trim();
  config.gptOauthToken = gptOauthTokenInput.value.trim();
  persistConfig();
  status("Settings saved. Restarting backend...");
  if (window.hwpxUi?.restartBackend) {
    window.hwpxUi
      .restartBackend({
        openrouterKey: config.openrouterKey,
        gptOauthToken: config.gptOauthToken,
      })
      .catch((error) => {
        status(`Backend restart failed: ${error?.message || String(error)}`);
      });
  }
});

resetSettings.addEventListener("click", () => {
  localStorage.removeItem(CONFIG_KEY);
  config = { ...defaultConfig };
  renderConfig();
  status("Settings reset");
});

newSessionBtn.addEventListener("click", createSession);

checkGateway.addEventListener("click", async () => {
  try {
    const health = await checkAgentEndpoint();
    const defaults = health?.defaults || {};
    status(
      `Agent healthy (${defaults.provider || "cerebras/fp16"} / ${defaults.model || "openai/gpt-oss-120b"})`
    );
  } catch (error) {
    status(`Agent check failed: ${error.message}`);
  }
});

restartBackendBtn.addEventListener("click", async () => {
  status("Restarting backend...");
  try {
    if (window.hwpxUi?.restartBackend) {
      const result = await window.hwpxUi.restartBackend({
        openrouterKey: config.openrouterKey,
        gptOauthToken: config.gptOauthToken,
      });
      status(`Backend restarted (pid ${result.pid || "?"}). Waiting...`);
    }
  } catch (error) {
    status(`Restart failed: ${error.message}`);
  }
  await new Promise((resolve) => setTimeout(resolve, 3000));
  await waitForBackend(10, 2000);
});

sidebarToggle.addEventListener("click", () => appShell.classList.toggle("sidebar-open"));
backdrop.addEventListener("click", closeSidebar);

sendBtn.addEventListener("click", (event) => {
  if (!currentAbort) return;
  event.preventDefault();
  currentAbort.abort();
  currentAbort = null;
  updateSendBtn();
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  let session = activeSession();
  if (!session) session = createSession();

  addMsg("user", text);
  messageInput.value = "";

  if (session.title === "New Chat" && session.messages.length <= 2) {
    session.title = makeTitle(text);
    renderSessionList();
    chatTitle.textContent = session.title;
  }

  handleUserMessage(text);
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

if (sessions.length === 0) createSession();
renderConfig();
renderAll();

(async () => {
  await new Promise((resolve) => setTimeout(resolve, 5000));
  if ((config.openrouterKey || config.gptOauthToken) && window.hwpxUi?.restartBackend) {
    try {
      await window.hwpxUi.restartBackend({
        openrouterKey: config.openrouterKey,
        gptOauthToken: config.gptOauthToken,
      });
    } catch (error) {
      status(`Backend restart failed: ${error?.message || String(error)}`);
    }
  }
  await waitForBackend(15, 2000);
})();
