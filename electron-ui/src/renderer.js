const CONFIG_KEY = "hwpxUi.config.v3";

const defaultConfig = {
  mcpHttpUrl: window.hwpxUi?.getConfig?.()?.mcpHttpUrl ?? "http://127.0.0.1:8000/mcp",
};

const loadConfig = () => {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (raw) {
      const p = JSON.parse(raw);
      if (p && typeof p === "object") return { ...defaultConfig, ...p };
    }
  } catch { /* ignore */ }
  return { ...defaultConfig };
};

let config = loadConfig();
const persistConfig = () => localStorage.setItem(CONFIG_KEY, JSON.stringify(config));

// ─── DOM ───
const $ = (id) => document.getElementById(id);
const messageLog = $("chatLog");
const sessionList = $("sessionList");
const statusText = $("statusText");
const messageInput = $("messageInput");
const chatForm = $("chatForm");
const newSessionBtn = $("newSession");
const checkGateway = $("checkGateway");
const restartBackendBtn = $("restartBackend");
const mcpHttpUrlInput = $("mcpHttpUrlInput");
const saveSettings = $("saveSettings");
const resetSettings = $("resetSettings");
const chatTitle = $("chatTitle");
const sendBtn = $("sendBtn");
const sidebarToggle = $("sidebarToggle");
const appShell = $("appShell");
const backdrop = $("backdrop");

// ─── State ───
let activeSessionId = null;
let sessions = [];
let currentAbort = null;
let mcpSessionId = null;
let mcpReady = false;
let mcpToolsCache = null;
let nextRpcId = 1;

const MCP_ACCEPT = "application/json, text/event-stream";
const MCP_PROTO = "2024-11-05";

// ─── Helpers ───
const fmt = (ms) => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const makeTitle = (t) => { const c = t.trim().replace(/\s+/g, " "); return !c ? "New Chat" : c.length > 24 ? c.slice(0, 21) + "..." : c; };
const typingHtml = () => '<span class="typing"><span></span><span></span><span></span></span>';
const status = (msg) => { statusText.textContent = msg; };
const closeSidebar = () => appShell.classList.remove("sidebar-open");

// ─── Session ───
const createSession = () => {
  const s = { id: crypto.randomUUID(), title: "New Chat", messages: [] };
  sessions.unshift(s);
  activeSessionId = s.id;
  renderAll();
  return s;
};
const activeSession = () => sessions.find((s) => s.id === activeSessionId);

const renderSessionList = () => {
  sessionList.innerHTML = "";
  for (const s of sessions) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = `session-item${s.id === activeSessionId ? " active" : ""}`;
    el.textContent = s.title;
    el.addEventListener("click", () => { activeSessionId = s.id; renderAll(); closeSidebar(); });
    sessionList.appendChild(el);
  }
};

const renderMessages = () => {
  messageLog.innerHTML = "";
  const s = activeSession();
  if (!s) return;
  for (const m of s.messages) {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${m.role}`;
    if (m.streaming && !m.text) {
      bubble.innerHTML = typingHtml();
    } else {
      bubble.textContent = m.text;
    }
    if (m.ts) {
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = fmt(m.ts);
      bubble.appendChild(meta);
    }
    messageLog.appendChild(bubble);
  }
  messageLog.scrollTop = messageLog.scrollHeight;
};

const renderConfig = () => {
  mcpHttpUrlInput.value = config.mcpHttpUrl;
};

const renderAll = () => {
  renderSessionList();
  renderMessages();
  chatTitle.textContent = activeSession()?.title ?? "HWPX MCP";
};

const addMsg = (role, text, streaming = false) => {
  const s = activeSession();
  if (!s) return null;
  const m = { role, text, ts: Date.now(), streaming };
  s.messages.push(m);
  renderMessages();
  return m;
};

const updateSendBtn = () => {
  sendBtn.textContent = currentAbort ? "Stop" : "Send";
  sendBtn.type = currentAbort ? "button" : "submit";
};

// ─── MCP Backend ───
const sendMcp = async (method, params = {}) => {
  const res = await fetch(config.mcpHttpUrl, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: MCP_ACCEPT,
      ...(mcpSessionId ? { "mcp-session-id": mcpSessionId } : {}),
      "MCP-Protocol-Version": MCP_PROTO,
    },
    body: JSON.stringify({ jsonrpc: "2.0", id: nextRpcId++, method, params }),
  });
  const sid = res.headers.get("mcp-session-id");
  if (sid) mcpSessionId = sid;
  if (!res.ok) {
    const txt = await res.text();
    if ([400, 404, 409, 410].includes(res.status)) { mcpSessionId = null; mcpReady = false; }
    throw new Error(`MCP ${res.status}: ${txt.slice(0, 200)}`);
  }
  const raw = await res.text();
  if (!raw.trim()) return null;
  const ct = res.headers.get("content-type")?.toLowerCase() ?? "";
  let payload;
  if (ct.includes("application/json") || raw.trim().startsWith("{")) {
    payload = JSON.parse(raw);
  } else {
    const lines = raw.split(/\r?\n/).filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim());
    payload = JSON.parse(lines[lines.length - 1]);
  }
  if (payload.error) throw new Error(payload.error.message || JSON.stringify(payload.error));
  return payload.result;
};

const ensureMcp = async () => {
  if (mcpReady) return true;
  try {
    const r = await sendMcp("initialize", {
      protocolVersion: MCP_PROTO, capabilities: {},
      clientInfo: { name: "hwpx-mcp-ui", version: "0.3.0" },
    });
    if (!r?.protocolVersion) return false;
    await sendMcp("initialized", {});
    mcpReady = true;
    return true;
  } catch {
    return false;
  }
};

const callMcpTool = async (name, args = {}) => {
  const ok = await ensureMcp();
  if (!ok) throw new Error("MCP backend not connected");
  return await sendMcp("tools/call", { name, arguments: args });
};

const extractToolPayload = (toolCallResult) => {
  if (!toolCallResult) return null;
  if (typeof toolCallResult === "string") {
    try {
      return JSON.parse(toolCallResult);
    } catch {
      return toolCallResult;
    }
  }

  const content = toolCallResult.content;
  if (Array.isArray(content)) {
    for (const item of content) {
      const text = typeof item === "string" ? item : item?.text || item?.content || "";
      if (!text) continue;
      try {
        return JSON.parse(text);
      } catch {
        return text;
      }
    }
  }
  return toolCallResult;
};

const runToolOnlyAgent = async (userText, botMsg, signal) => {
  if (signal.aborted) throw new Error("Cancelled");

  const raw = await callMcpTool("hwp_agent_chat", {
    message: userText,
    session_id: activeSessionId || "",
  });
  const payload = extractToolPayload(raw);

  let reply = "";
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    reply = payload.reply || payload.message || JSON.stringify(payload, null, 2);
    if (payload.case && payload.subagent) {
      status(`Case: ${payload.case} | Subagent: ${payload.subagent}`);
    }
  } else if (typeof payload === "string") {
    reply = payload;
  } else {
    reply = JSON.stringify(payload ?? raw, null, 2);
  }

  botMsg.text = reply;
  botMsg.streaming = false;
};

// ─── Main Chat Handler ───
const handleUserMessage = async (text) => {
  const botMsg = addMsg("bot", "", true);
  const controller = new AbortController();
  currentAbort = controller;
  updateSendBtn();

  try {
    await runToolOnlyAgent(text, botMsg, controller.signal);
  } catch (e) {
    if (botMsg) {
      botMsg.text = controller.signal.aborted ? "Cancelled." : `Error: ${e.message}`;
      botMsg.streaming = false;
    }
  } finally {
    currentAbort = null;
    updateSendBtn();
    renderMessages();
  }
};

// ─── MCP Health Check ───
const waitForBackend = async (maxAttempts = 15, delayMs = 2000) => {
  status("Waiting for MCP backend to start...");

  if (window.hwpxUi?.getBackendStatus) {
    const bs = await window.hwpxUi.getBackendStatus();
    if (bs.running) {
      status(`Backend process running (pid ${bs.pid}). Connecting...`);
    } else {
      status("Backend process not running. Trying to connect anyway...");
    }
  }

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const res = await fetch(config.mcpHttpUrl, {
        method: "POST",
        headers: { "content-type": "application/json", accept: MCP_ACCEPT },
        body: JSON.stringify({ jsonrpc: "2.0", id: nextRpcId++, method: "initialize", params: {
          protocolVersion: MCP_PROTO, capabilities: {},
          clientInfo: { name: "hwpx-mcp-ui", version: "0.3.0" },
        }}),
      });

      if (res.ok || res.status < 500) {
        const sid = res.headers.get("mcp-session-id");
        if (sid) mcpSessionId = sid;

        const raw = await res.text();
        if (raw.trim()) {
          mcpReady = false;
          const ok = await ensureMcp();
          if (ok) {
            const tools = await fetchMcpTools();
            status(`MCP connected (${tools.length} tools available)`);
            return true;
          }
        }
      }

      status(`MCP starting... (${attempt}/${maxAttempts})`);
    } catch {
      status(`Waiting for backend... (${attempt}/${maxAttempts})`);
    }

    await new Promise((r) => setTimeout(r, delayMs));
  }

  if (window.hwpxUi?.getBackendStatus) {
    const bs = await window.hwpxUi.getBackendStatus();
    if (bs.log?.length) {
      const lastLines = bs.log.slice(-5).join("\n");
      status(`MCP failed to start. Log:\n${lastLines}`);
      return false;
    }
  }

  status("MCP backend not reachable. Click 'Restart' to try again.");
  return false;
};

const checkMcpEndpoint = async () => {
  mcpReady = false;
  mcpToolsCache = null;
  mcpSessionId = null;
  return waitForBackend(5, 1500);
};

// ─── Events ───
saveSettings.addEventListener("click", () => {
  config.mcpHttpUrl = mcpHttpUrlInput.value.trim() || defaultConfig.mcpHttpUrl;
  mcpReady = false; mcpToolsCache = null; mcpSessionId = null;
  persistConfig();
  status("Settings saved");
});

resetSettings.addEventListener("click", () => {
  localStorage.removeItem(CONFIG_KEY);
  config = { ...defaultConfig };
  mcpReady = false; mcpToolsCache = null; mcpSessionId = null;
  renderConfig();
  status("Settings reset");
});

newSessionBtn.addEventListener("click", createSession);

checkGateway.addEventListener("click", checkMcpEndpoint);

restartBackendBtn.addEventListener("click", async () => {
  status("Restarting backend...");
  mcpReady = false; mcpToolsCache = null; mcpSessionId = null;
  try {
    if (window.hwpxUi?.restartBackend) {
      const r = await window.hwpxUi.restartBackend();
      status(`Backend restarted (pid ${r.pid || "?"}). Waiting...`);
    }
  } catch (e) {
    status(`Restart failed: ${e.message}`);
  }
  await new Promise((r) => setTimeout(r, 3000));
  await waitForBackend(10, 2000);
});

sidebarToggle.addEventListener("click", () => appShell.classList.toggle("sidebar-open"));
backdrop.addEventListener("click", closeSidebar);

sendBtn.addEventListener("click", (e) => {
  if (currentAbort) { e.preventDefault(); currentAbort.abort(); currentAbort = null; updateSendBtn(); }
});

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  let s = activeSession();
  if (!s) s = createSession();

  addMsg("user", text);
  messageInput.value = "";

  if (s.title === "New Chat" && s.messages.length <= 2) {
    s.title = makeTitle(text);
    renderSessionList();
    chatTitle.textContent = s.title;
  }

  handleUserMessage(text);
});

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); chatForm.requestSubmit(); }
});

// ─── Init ───
if (sessions.length === 0) createSession();
renderConfig();
renderAll();

(async () => {
  await new Promise((r) => setTimeout(r, 5000));
  await waitForBackend(15, 2000);
})();
