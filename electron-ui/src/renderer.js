const CONFIG_KEY = "hwpxUi.config.v3";

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
const openrouterKeyInput = $("openrouterKeyInput");
const modelSelect = $("modelSelect");
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
const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const MAX_AGENT_ROUNDS = 10;

// ─── Helpers ───
const fmt = (ms) => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const makeTitle = (t) => { const c = t.trim().replace(/\s+/g, " "); return !c ? "New Chat" : c.length > 24 ? c.slice(0, 21) + "..." : c; };
const typingHtml = () => '<span class="typing"><span></span><span></span><span></span></span>';
const status = (msg) => { statusText.textContent = msg; };
const closeSidebar = () => appShell.classList.remove("sidebar-open");

// ─── Session ───
const createSession = () => {
  const s = { id: crypto.randomUUID(), title: "New Chat", messages: [], llmHistory: [] };
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

const fetchMcpTools = async () => {
  if (mcpToolsCache) return mcpToolsCache;
  const ok = await ensureMcp();
  if (!ok) return [];
  try {
    const r = await sendMcp("tools/list", {});
    mcpToolsCache = r?.tools ?? [];
    return mcpToolsCache;
  } catch {
    return [];
  }
};

const callMcpTool = async (name, args) => {
  const ok = await ensureMcp();
  if (!ok) throw new Error("MCP backend not connected");
  const r = await sendMcp("tools/call", { name, arguments: args || {} });
  if (!r) return "No response";
  if (typeof r === "string") return r;
  if (r.content && Array.isArray(r.content)) {
    const parts = r.content.map((c) => (typeof c === "string" ? c : c.text || c.content || "")).filter(Boolean).join("\n");
    if (parts) return parts;
  }
  return JSON.stringify(r, null, 2);
};

// ─── ReAct Agent ───
const buildSystemPrompt = (tools) => {
  let toolDesc = "No MCP tools available (backend not connected).";
  if (tools.length > 0) {
    const toolLines = tools.map((t) => {
      const params = t.inputSchema?.properties
        ? Object.entries(t.inputSchema.properties).map(([k, v]) => {
            const req = (t.inputSchema.required || []).includes(k) ? ", required" : "";
            return `    ${k} (${v.type || "any"}${req}): ${v.description || ""}`;
          }).join("\n")
        : "    (no parameters)";
      return `- ${t.name}: ${t.description || ""}\n  Parameters:\n${params}`;
    }).join("\n\n");
    toolDesc = toolLines;
  }

  return `You are HWPX MCP Assistant — an AI agent that helps users create and edit HWP/HWPX Korean documents.

## Available Tools
${toolDesc}

## How to use tools
When you need to call a tool, output EXACTLY this format on its own line:
ACTION: tool_name
ARGS: {"param1": "value1", "param2": "value2"}

Then STOP and wait. The system will execute the tool and show you the result.
After seeing the result, you may call another tool or give your final answer.

## Rules
- You may call multiple tools in sequence (one per round, up to ${MAX_AGENT_ROUNDS} rounds).
- Always respond in the same language the user writes in.
- When you have the final answer, just write it normally WITHOUT any ACTION/ARGS lines.
- If no tools are available, answer the user's question as best you can.
- For file operations, always use the provided tools.
- Be concise. Show tool results clearly.`;
};

const parseAction = (text) => {
  const actionMatch = text.match(/^ACTION:\s*(.+)$/m);
  if (!actionMatch) return null;
  const toolName = actionMatch[1].trim();

  const argsMatch = text.match(/^ARGS:\s*(.+)$/m);
  let args = {};
  if (argsMatch) {
    try { args = JSON.parse(argsMatch[1].trim()); } catch { /* ignore parse errors */ }
  }
  return { tool: toolName, args };
};

const callLLM = async (messages, signal) => {
  if (!config.openrouterKey) throw new Error("OpenRouter API key not set. Add it in Settings (sidebar).");

  const providerKey = (config.provider || defaultConfig.provider).split("/")[0];
  const quantization = (config.provider || defaultConfig.provider).split("/")[1] || "fp16";

  const res = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.openrouterKey}`,
      "HTTP-Referer": "https://github.com/Topabaem05/hwpx-mcp",
      "X-Title": "HWPX MCP Agent",
    },
    body: JSON.stringify({
      model: config.model,
      messages,
      stream: false,
      provider: {
        order: [providerKey],
        quantizations: [quantization],
      },
    }),
    signal,
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`OpenRouter ${res.status}: ${err.slice(0, 300)}`);
  }

  const data = await res.json();
  return data.choices?.[0]?.message?.content || "";
};

// ─── Agent Loop ───
const runAgent = async (userText, botMsg, signal) => {
  const s = activeSession();
  if (!s) return;

  const tools = await fetchMcpTools();
  const systemPrompt = buildSystemPrompt(tools);

  s.llmHistory.push({ role: "user", content: userText });

  for (let round = 0; round < MAX_AGENT_ROUNDS; round++) {
    if (signal.aborted) throw new Error("Cancelled");

    const messages = [{ role: "system", content: systemPrompt }, ...s.llmHistory];
    const response = await callLLM(messages, signal);

    const action = parseAction(response);

    if (!action) {
      s.llmHistory.push({ role: "assistant", content: response });
      if (botMsg) { botMsg.text = response; botMsg.streaming = false; }
      return;
    }

    const textBeforeAction = response.split(/^ACTION:/m)[0].trim();
    s.llmHistory.push({ role: "assistant", content: response });

    if (botMsg) {
      botMsg.text = textBeforeAction
        ? `${textBeforeAction}\n\n⚙ ${action.tool}(${JSON.stringify(action.args)})...`
        : `⚙ Calling ${action.tool}...`;
      botMsg.streaming = true;
      renderMessages();
    }

    let result;
    try {
      result = await callMcpTool(action.tool, action.args);
    } catch (e) {
      result = `Error: ${e.message}`;
    }

    s.llmHistory.push({
      role: "user",
      content: `[Tool Result for ${action.tool}]\n${result}`,
    });

    if (botMsg) {
      botMsg.text = textBeforeAction
        ? `${textBeforeAction}\n\n⚙ ${action.tool} → done`
        : `⚙ ${action.tool} → done`;
      renderMessages();
    }
  }

  s.llmHistory.push({ role: "assistant", content: "(Agent reached max rounds)" });
  if (botMsg) { botMsg.text = "Agent reached maximum tool call rounds."; botMsg.streaming = false; }
};

// ─── Main Chat Handler ───
const handleUserMessage = async (text) => {
  const botMsg = addMsg("bot", "", true);
  const controller = new AbortController();
  currentAbort = controller;
  updateSendBtn();

  try {
    await runAgent(text, botMsg, controller.signal);
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

// ─── MCP Health Check (with retry) ───
const checkMcpEndpoint = async () => {
  status("Checking MCP backend...");

  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const res = await fetch(config.mcpHttpUrl, { method: "GET", headers: { accept: MCP_ACCEPT } });
      const sid = res.headers.get("mcp-session-id");
      if (sid) mcpSessionId = sid;

      if (res.ok || res.status === 405 || res.status === 307) {
        const ok = await ensureMcp();
        if (ok) {
          const tools = await fetchMcpTools();
          status(`MCP connected (${tools.length} tools)`);
          return;
        }
      }
      status(`MCP returned ${res.status} (attempt ${attempt}/3)`);
    } catch {
      if (attempt < 3) {
        status(`MCP not ready, retrying (${attempt}/3)...`);
        await new Promise((r) => setTimeout(r, 2000));
      } else {
        status("MCP backend not running. Start it or check Settings.");
      }
    }
  }
};

// ─── Events ───
saveSettings.addEventListener("click", () => {
  config.openrouterKey = openrouterKeyInput.value.trim();
  config.model = modelSelect.value;
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
  await new Promise((r) => setTimeout(r, 3000));
  await checkMcpEndpoint();
})();
