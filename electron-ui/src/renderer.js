const CONFIG_STORAGE_KEY = "hwpxUi.config.v1";

const defaultConfig = window.hwpxUi?.getConfig?.() ?? {
  openWebUIUrl: "http://localhost:3000",
  mcpHttpUrl: "http://127.0.0.1:8000/mcp",
};

const loadStoredConfig = () => {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return parsed;
    }
  } catch {
    return {};
  }

  return {};
};

const ensureString = (value, fallback) =>
  typeof value === "string" && value.trim() ? value.trim() : fallback;

let config = {
  ...defaultConfig,
  ...loadStoredConfig(),
};

config = {
  openWebUIUrl: ensureString(config.openWebUIUrl, defaultConfig.openWebUIUrl),
  mcpHttpUrl: ensureString(config.mcpHttpUrl, defaultConfig.mcpHttpUrl),
};

const MCP_ACCEPT_HEADER = "application/json, text/event-stream";
const MCP_PROTOCOL_VERSION = "2024-11-05";
const MCP_SESSION_RESET_STATUSES = new Set([400, 404, 409, 410]);

const messageLog = document.getElementById("chatLog");
const sessionList = document.getElementById("sessionList");
const statusText = document.getElementById("statusText");
const messageInput = document.getElementById("messageInput");
const chatForm = document.getElementById("chatForm");
const newSession = document.getElementById("newSession");
const openWebUI = document.getElementById("openWebUI");
const checkGateway = document.getElementById("checkGateway");
const mcpHttpUrlInput = document.getElementById("mcpHttpUrlInput");
const saveSettings = document.getElementById("saveSettings");
const resetSettings = document.getElementById("resetSettings");
const chatTitle = document.getElementById("chatTitle");
const sendBtn = document.getElementById("sendBtn");
const sidebarToggle = document.getElementById("sidebarToggle");
const appShell = document.getElementById("appShell");
const backdrop = document.getElementById("backdrop");

let activeSession = "Session 1";
let currentAbortController = null;

const sessions = [
  {
    title: "Session 1",
    history: [
      {
        role: "bot",
        text: "Welcome. Type a tool command (e.g. hwp_ping) or JSON: {\"tool\": \"hwp_ping\", \"arguments\": {}}",
        timestamp: Date.now(),
        streaming: false,
      },
    ],
  },
];

let nextRequestId = 1;
let mcpSessionId = null;
let mcpReady = false;
let mcpProtocolVersion = MCP_PROTOCOL_VERSION;

const formatTime = (epochMs) => {
  const date = new Date(epochMs);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const makeTitleFromText = (text) => {
  const cleaned = text.trim().replace(/\s+/g, " ");
  if (!cleaned) {
    return "New Session";
  }
  const limit = 24;
  return cleaned.length > limit ? `${cleaned.slice(0, limit - 3)}...` : cleaned;
};

const typingIndicatorHtml = () =>
  '<span class="typing" aria-hidden="true"><span></span><span></span><span></span></span>';

const renderConfigInputs = () => {
  mcpHttpUrlInput.value = config.mcpHttpUrl;
};

const persistConfig = () => {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
};

const applyMcpConfig = (nextConfig = {}) => {
  config = {
    ...config,
    ...nextConfig,
    openWebUIUrl: ensureString(nextConfig.openWebUIUrl, defaultConfig.openWebUIUrl),
    mcpHttpUrl: ensureString(nextConfig.mcpHttpUrl, defaultConfig.mcpHttpUrl),
  };

  persistConfig();
  renderConfigInputs();
};

const updateStatus = (message) => {
  statusText.textContent = message;
};

const renderSessionList = () => {
  sessionList.innerHTML = "";
  sessions.forEach((session) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = `session-item${session.title === activeSession ? " active" : ""}`;
    el.textContent = session.title;
    el.addEventListener("click", () => {
      activeSession = session.title;
      renderSessionList();
      renderMessages();
      updateChatTitle();
      closeSidebar();
    });
    sessionList.appendChild(el);
  });
};

const activeHistory = () => sessions.find((session) => session.title === activeSession)?.history ?? [];

const updateChatTitle = () => {
  chatTitle.textContent = activeSession;
};

const renderMessages = () => {
  messageLog.innerHTML = "";
  activeHistory().forEach((message) => {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${message.role}`;

    if (message.streaming && message.text.length === 0) {
      bubble.innerHTML = typingIndicatorHtml();
    } else {
      bubble.textContent = message.text;
    }

    if (message.timestamp) {
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = formatTime(message.timestamp);
      bubble.appendChild(meta);
    }

    messageLog.appendChild(bubble);
  });
  messageLog.scrollTop = messageLog.scrollHeight;
};

const appendMessage = (role, text, streaming = false) => {
  const session = sessions.find((session) => session.title === activeSession);
  if (!session) {
    return null;
  }
  const msg = { role, text, timestamp: Date.now(), streaming };
  session.history.push(msg);
  renderMessages();
  return msg;
};

const updateSendButton = () => {
  if (currentAbortController) {
    sendBtn.textContent = "Stop";
    sendBtn.type = "button";
  } else {
    sendBtn.textContent = "Send";
    sendBtn.type = "submit";
  }
};

const closeSidebar = () => {
  appShell.classList.remove("sidebar-open");
};

const parseCommand = (rawText) => {
  const input = rawText.trim();
  if (!input) {
    return null;
  }

  const asJson = () => {
    const payload = JSON.parse(input);
    if (!payload || typeof payload !== "object" || !payload.tool) {
      return null;
    }

    return {
      tool: String(payload.tool),
      arguments: payload.arguments && typeof payload.arguments === "object" ? payload.arguments : {},
    };
  };

  let parsedJson = null;
  try {
    parsedJson = asJson();
  } catch {
    parsedJson = null;
  }

  if (parsedJson) {
    return parsedJson;
  }

  const [toolName, ...argTokens] = input.split(/\s+/);
  if (!toolName) {
    return null;
  }

  const parsed = {};
  for (const token of argTokens) {
    const index = token.indexOf("=");
    if (index <= 0) {
      continue;
    }

    const key = token.slice(0, index);
    const value = token.slice(index + 1);
    const lower = value.toLowerCase();
    if (key && lower === "true") {
      parsed[key] = true;
    } else if (key && lower === "false") {
      parsed[key] = false;
    } else if (key && /^-?\d+$/.test(value)) {
      parsed[key] = Number(value);
    } else {
      parsed[key] = value.replace(/^['\"]|['\"]$/g, "");
    }
  }

  return {
    tool: toolName,
    arguments: parsed,
  };
};

const parseMcpEventPayload = async (response) => {
  const raw = await response.text();

  if (!raw.trim()) {
    throw new Error("MCP response was empty");
  }

  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";

  if (contentType.includes("application/json") || raw.trim().startsWith("{")) {
    return JSON.parse(raw);
  }

  const sseLines = raw.split(/\r?\n/);
  const messageLines = [];

  for (const line of sseLines) {
    if (line.startsWith("data:")) {
      messageLines.push(line.slice(5).trimLeft());
    }
  }

  if (messageLines.length === 0) {
    throw new Error("MCP response did not include event data payload");
  }

  const last = messageLines[messageLines.length - 1];
  return JSON.parse(last);
};

const looksLikeSessionResetError = (status) => {
  return MCP_SESSION_RESET_STATUSES.has(status);
};

const decodeToolResultText = (result) => {
  if (!result) {
    return "No response payload";
  }

  if (typeof result === "string") {
    return result;
  }

  if (result.content && Array.isArray(result.content)) {
    const textParts = result.content
      .map((chunk) => {
        if (typeof chunk === "string") {
          return chunk;
        }
        return chunk.text || chunk.content || "";
      })
      .filter((value) => value)
      .join("\n");

    if (textParts) {
      return textParts;
    }
  }

  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
};

const sendMcpRequest = async (method, params = {}, retryAfterReset = false) => {
  const headers = {
    "content-type": "application/json",
    accept: MCP_ACCEPT_HEADER,
    ...(mcpSessionId ? { "mcp-session-id": mcpSessionId } : {}),
    ...(mcpProtocolVersion ? { "MCP-Protocol-Version": mcpProtocolVersion } : {}),
  };

  const response = await fetch(config.mcpHttpUrl, {
    method: "POST",
    headers,
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: nextRequestId++,
      method,
      params,
    }),
  });

  const nextSession = response.headers.get("mcp-session-id");
  if (nextSession) {
    mcpSessionId = nextSession;
  }

  if (!response.ok) {
    const message = await response.text();
    if (!retryAfterReset && looksLikeSessionResetError(response.status)) {
      mcpSessionId = null;
      mcpReady = false;
      if (method === "initialize") {
        return sendMcpRequest(method, params, true);
      }

      await ensureMcpSession();
      return sendMcpRequest(method, params, true);
    }
    throw new Error(`${response.status}: ${response.statusText} ${message}`);
  }

  const payload = await parseMcpEventPayload(response);
  if (payload.error) {
    throw new Error(payload.error.message || JSON.stringify(payload.error));
  }

  return payload.result;
};

const ensureMcpSession = async () => {
  if (mcpReady) {
    return;
  }

  const result = await sendMcpRequest("initialize", {
    protocolVersion: MCP_PROTOCOL_VERSION,
    capabilities: {},
    clientInfo: { name: "hwpx-electron-ui", version: "0.1.0" },
  });

  if (!result || result.protocolVersion !== MCP_PROTOCOL_VERSION) {
    throw new Error("Unexpected MCP initialize response");
  }

  mcpProtocolVersion = result.protocolVersion;

  await sendMcpRequest("initialized", {});
  mcpReady = true;
  updateStatus(`MCP connected | protocol ${result.protocolVersion}`);
};

const callMcpTool = async (tool, toolArguments) => {
  await ensureMcpSession();

  if (!tool) {
    return "No tool specified. Send JSON: {\"tool\": \"hwp_platform_info\", \"arguments\": {}}";
  }

  const result = await sendMcpRequest("tools/call", {
    name: tool,
    arguments: toolArguments || {},
  });
  return decodeToolResultText(result);
};

const createSession = () => {
  const nextIndex = sessions.length + 1;
  const title = `Session ${nextIndex}`;
  sessions.push({
    title,
    history: [
      {
        role: "bot",
        text: "A new session is ready. Use this pane as a command workspace.",
        timestamp: Date.now(),
        streaming: false,
      },
    ],
  });
  activeSession = title;
  renderSessionList();
  renderMessages();
  updateChatTitle();
};

const pingGateway = async () => {
  updateStatus("Checking MCP endpoint...");
  try {
    const response = await fetch(config.mcpHttpUrl, {
      method: "GET",
      headers: {
        accept: MCP_ACCEPT_HEADER,
      },
    });

    mcpSessionId = response.headers.get("mcp-session-id");

    if (!response.ok) {
      if (response.status === 406) {
        updateStatus("Endpoint rejected request (need streamable HTTP SSE headers)");
      } else {
        updateStatus(`Endpoint returned ${response.status}`);
      }
      return;
    }

    updateStatus("MCP endpoint is reachable");
  } catch (error) {
    updateStatus(`Endpoint unavailable: ${error.message}`);
  }
};

saveSettings.addEventListener("click", () => {
  const nextUrl = ensureString(mcpHttpUrlInput.value, "");
  if (!nextUrl) {
    updateStatus("Please provide a valid MCP API URL.");
    return;
  }

  applyMcpConfig({ mcpHttpUrl: nextUrl });
  updateStatus(`MCP API updated: ${config.mcpHttpUrl}`);
});

resetSettings.addEventListener("click", () => {
  localStorage.removeItem(CONFIG_STORAGE_KEY);
  config = {
    ...defaultConfig,
  };
  renderConfigInputs();
  updateStatus(`Gateway target reset to: ${config.mcpHttpUrl}`);
});

newSession.addEventListener("click", createSession);

openWebUI.addEventListener("click", () => {
  window.hwpxUi?.openExternal?.(config.openWebUIUrl);
});

checkGateway.addEventListener("click", pingGateway);

sidebarToggle.addEventListener("click", () => {
  appShell.classList.toggle("sidebar-open");
});

backdrop.addEventListener("click", closeSidebar);

sendBtn.addEventListener("click", (event) => {
  if (currentAbortController) {
    event.preventDefault();
    currentAbortController.abort();
    currentAbortController = null;
    updateSendButton();
    return;
  }
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }

  appendMessage("user", text);
  messageInput.value = "";

  const session = sessions.find((s) => s.title === activeSession);
  if (session && session.title.startsWith("Session ") && session.history.length <= 2) {
    const oldTitle = session.title;
    session.title = makeTitleFromText(text);
    if (activeSession === oldTitle) {
      activeSession = session.title;
    }
    renderSessionList();
    updateChatTitle();
  }

  const botMsg = appendMessage("bot", "", true);
  const controller = new AbortController();
  currentAbortController = controller;
  updateSendButton();

  (async () => {
    const command = parseCommand(text);
    if (!command || typeof command.tool !== "string") {
      if (botMsg) {
        botMsg.text = "Type a tool command, e.g. `hwp_ping` or JSON: {\"tool\": \"hwp_ping\", \"arguments\": {}}";
        botMsg.streaming = false;
      }
      currentAbortController = null;
      updateSendButton();
      renderMessages();
      return;
    }

    try {
      if (controller.signal.aborted) {
        throw new Error("Aborted");
      }
      const reply = await callMcpTool(command.tool, command.arguments);
      if (botMsg) {
        botMsg.text = reply;
        botMsg.streaming = false;
      }
    } catch (error) {
      if (botMsg) {
        botMsg.text = controller.signal.aborted
          ? "Request cancelled."
          : `Tool call failed: ${error.message}`;
        botMsg.streaming = false;
      }
      if (!/MCP connected/.test(statusText.textContent)) {
        updateStatus("MCP session not connected yet");
      }
    } finally {
      currentAbortController = null;
      updateSendButton();
      renderMessages();
    }
  })();
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

renderSessionList();
renderMessages();
renderConfigInputs();
updateChatTitle();
updateStatus(`Gateway target: ${config.mcpHttpUrl}`);
