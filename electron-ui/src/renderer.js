const CONFIG_KEY = "hwpxUi.config.v2";

const defaultConfig = {
  openrouterKey: "",
  model: "openai/gpt-oss-120b",
  provider: "cerebras/fp16",
  mcpHttpUrl: window.hwpxUi?.getConfig?.()?.mcpHttpUrl ?? "http://127.0.0.1:8000/mcp",
};

const loadConfig = () => {
  try {
    const raw = localStorage.getItem(CONFIG_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") return { ...defaultConfig, ...parsed };
    }
  } catch { /* ignore */ }
  return { ...defaultConfig };
};

let config = loadConfig();

const persistConfig = () => localStorage.setItem(CONFIG_KEY, JSON.stringify(config));

// DOM
const messageLog = document.getElementById("chatLog");
const sessionList = document.getElementById("sessionList");
const statusText = document.getElementById("statusText");
const messageInput = document.getElementById("messageInput");
const chatForm = document.getElementById("chatForm");
const newSessionBtn = document.getElementById("newSession");
const checkGateway = document.getElementById("checkGateway");
const openrouterKeyInput = document.getElementById("openrouterKeyInput");
const modelSelect = document.getElementById("modelSelect");
const mcpHttpUrlInput = document.getElementById("mcpHttpUrlInput");
const saveSettings = document.getElementById("saveSettings");
const resetSettings = document.getElementById("resetSettings");
const chatTitle = document.getElementById("chatTitle");
const sendBtn = document.getElementById("sendBtn");
const sidebarToggle = document.getElementById("sidebarToggle");
const appShell = document.getElementById("appShell");
const backdrop = document.getElementById("backdrop");

// State
let activeSessionId = null;
let sessions = [];
let currentAbort = null;
let mcpSessionId = null;
let mcpReady = false;
let mcpTools = null;
let nextRpcId = 1;

const MCP_ACCEPT = "application/json, text/event-stream";
const MCP_PROTO = "2024-11-05";
const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

const SYSTEM_PROMPT = `You are HWPX MCP Assistant, an AI that helps users create and edit HWP/HWPX documents.
You have access to MCP tools for document operations. When you need to perform a document action, call the appropriate tool.
Always respond in the same language as the user's message.
When showing tool results, format them clearly for the user.
If the MCP backend is not connected, still try to help with general questions about HWP documents.`;

// Helpers
const fmt = (ms) => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const makeTitle = (t) => { const c = t.trim().replace(/\s+/g, " "); return !c ? "New Chat" : c.length > 24 ? c.slice(0, 21) + "..." : c; };
const typingHtml = () => '<span class="typing"><span></span><span></span><span></span></span>';
const status = (msg) => { statusText.textContent = msg; };
const closeSidebar = () => appShell.classList.remove("sidebar-open");

// Session management
const createSession = () => {
  const s = {
    id: crypto.randomUUID(),
    title: "New Chat",
    messages: [],
    llmHistory: [],
  };
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
  openrouterKeyInput.value = config.openrouterKey;
  modelSelect.value = config.model;
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
    if ([400, 404, 409, 410].includes(res.status)) {
      mcpSessionId = null; mcpReady = false;
    }
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
  if (mcpReady) return;
  const r = await sendMcp("initialize", {
    protocolVersion: MCP_PROTO,
    capabilities: {},
    clientInfo: { name: "hwpx-mcp-ui", version: "0.2.0" },
  });
  if (!r?.protocolVersion) throw new Error("MCP init failed");
  await sendMcp("initialized", {});
  mcpReady = true;
  status(`MCP connected`);
};

const fetchMcpTools = async () => {
  if (mcpTools) return mcpTools;
  await ensureMcp();
  const r = await sendMcp("tools/list", {});
  mcpTools = r?.tools ?? [];
  return mcpTools;
};

const callMcpTool = async (name, args) => {
  await ensureMcp();
  const r = await sendMcp("tools/call", { name, arguments: args || {} });
  if (!r) return "No response";
  if (typeof r === "string") return r;
  if (r.content && Array.isArray(r.content)) {
    const parts = r.content.map((c) => (typeof c === "string" ? c : c.text || c.content || "")).filter(Boolean).join("\n");
    if (parts) return parts;
  }
  return JSON.stringify(r, null, 2);
};

// ─── OpenRouter AI ───
const buildToolDefs = (tools) => {
  return tools.map((t) => ({
    type: "function",
    function: {
      name: t.name,
      description: t.description || "",
      parameters: t.inputSchema || { type: "object", properties: {} },
    },
  }));
};

const callOpenRouter = async (messages, tools, signal) => {
  if (!config.openrouterKey) throw new Error("OpenRouter API key not set. Please add it in Settings.");

  const body = {
    model: config.model,
    messages,
    stream: false,
    provider: {
      order: [config.provider || defaultConfig.provider],
      quantizations: [(config.provider || defaultConfig.provider).split("/")[1] || "fp16"],
    },
  };
  if (tools && tools.length > 0) {
    body.tools = buildToolDefs(tools);
    body.tool_choice = "auto";
  }

  const res = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.openrouterKey}`,
      "HTTP-Referer": "https://github.com/Topabaem05/hwpx-mcp",
      "X-Title": "HWPX MCP",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`OpenRouter ${res.status}: ${err.slice(0, 300)}`);
  }

  return res.json();
};

// ─── Chat Flow ───
const handleUserMessage = async (text) => {
  const s = activeSession();
  if (!s) return;

  const botMsg = addMsg("bot", "", true);
  const controller = new AbortController();
  currentAbort = controller;
  updateSendBtn();

  try {
    s.llmHistory.push({ role: "user", content: text });

    let tools = [];
    try {
      tools = await fetchMcpTools();
    } catch {
      // MCP not available; AI will respond without tools
    }

    const messages = [{ role: "system", content: SYSTEM_PROMPT }, ...s.llmHistory];
    let response = await callOpenRouter(messages, tools, controller.signal);
    let choice = response.choices?.[0];
    if (!choice) throw new Error("Empty AI response");

    let maxRounds = 8;
    while (choice.finish_reason === "tool_calls" && choice.message?.tool_calls?.length && maxRounds-- > 0) {
      if (controller.signal.aborted) throw new Error("Cancelled");

      const assistantMsg = choice.message;
      s.llmHistory.push(assistantMsg);

      for (const tc of assistantMsg.tool_calls) {
        const fn = tc.function;
        let args = {};
        try { args = typeof fn.arguments === "string" ? JSON.parse(fn.arguments) : fn.arguments || {}; } catch { /* ignore */ }

        if (botMsg) {
          botMsg.text = `Calling ${fn.name}...`;
          botMsg.streaming = true;
          renderMessages();
        }

        let result;
        try {
          result = await callMcpTool(fn.name, args);
        } catch (e) {
          result = `Tool error: ${e.message}`;
        }

        s.llmHistory.push({ role: "tool", tool_call_id: tc.id, content: typeof result === "string" ? result : JSON.stringify(result) });
      }

      response = await callOpenRouter([{ role: "system", content: SYSTEM_PROMPT }, ...s.llmHistory], tools, controller.signal);
      choice = response.choices?.[0];
      if (!choice) break;
    }

    const finalText = choice.message?.content || "(no response)";
    s.llmHistory.push({ role: "assistant", content: finalText });
    if (botMsg) { botMsg.text = finalText; botMsg.streaming = false; }
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

// ─── Events ───
saveSettings.addEventListener("click", () => {
  config.openrouterKey = openrouterKeyInput.value.trim();
  config.model = modelSelect.value;
  config.mcpHttpUrl = mcpHttpUrlInput.value.trim() || defaultConfig.mcpHttpUrl;
  mcpReady = false; mcpTools = null; mcpSessionId = null;
  persistConfig();
  status("Settings saved");
});

resetSettings.addEventListener("click", () => {
  localStorage.removeItem(CONFIG_KEY);
  config = { ...defaultConfig };
  mcpReady = false; mcpTools = null; mcpSessionId = null;
  renderConfig();
  status("Settings reset");
});

newSessionBtn.addEventListener("click", () => { createSession(); });

checkGateway.addEventListener("click", async () => {
  status("Checking...");
  try {
    const res = await fetch(config.mcpHttpUrl, { method: "GET", headers: { accept: MCP_ACCEPT } });
    mcpSessionId = res.headers.get("mcp-session-id");
    status(res.ok ? "MCP endpoint reachable" : `MCP returned ${res.status}`);
  } catch (e) {
    status(`MCP unavailable: ${e.message}`);
  }
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
status(config.openrouterKey ? "Ready" : "Set OpenRouter API key in Settings to start");
