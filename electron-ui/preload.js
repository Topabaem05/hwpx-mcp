const { contextBridge, ipcRenderer, shell } = require("electron");

const mcpHttpUrl = process.env.HWPX_MCP_HTTP_URL || "http://127.0.0.1:8000/mcp";
const agentHttpUrl = process.env.HWPX_AGENT_HTTP_URL || mcpHttpUrl.replace(/\/mcp\/?$/i, "");
const defaultAgentProvider = process.env.HWPX_AGENT_PROVIDER || "openrouter";
const defaultAgentModel = process.env.HWPX_AGENT_MODEL || "openai/gpt-oss-120b";
const defaultLocalModelId = process.env.HWPX_LOCAL_MODEL_ID || "Qwen/Qwen2.5-1.5B-Instruct";
const defaultCodexProxyUrl =
  process.env.HWPX_CODEX_PROXY_URL || "http://127.0.0.1:2455/v1/chat/completions";

contextBridge.exposeInMainWorld("hwpxUi", {
  openExternal: (url) => shell.openExternal(url),
  getConfig: () => ({
    mcpHttpUrl,
    backendBaseUrl: agentHttpUrl || "http://127.0.0.1:8000",
    provider: defaultAgentProvider,
    model: defaultAgentModel,
    localModelId: defaultLocalModelId,
    codexProxyUrl: defaultCodexProxyUrl,
  }),

  saveFileDialog: (opts) => ipcRenderer.invoke("dialog:saveFile", opts),
  openFileDialog: (opts) => ipcRenderer.invoke("dialog:openFile", opts),
  selectFolderDialog: (opts) => ipcRenderer.invoke("dialog:selectFolder", opts),

  getBackendStatus: () => ipcRenderer.invoke("backend:status"),
  restartBackend: (opts) => ipcRenderer.invoke("backend:restart", opts),
  getAppUpdateStatus: () => ipcRenderer.invoke("app:update-status"),
  openAiOauthLogin: () => ipcRenderer.invoke("auth:openai-oauth-login"),
  onAppUpdateStatus: (callback) => {
    if (typeof callback !== "function") {
      return () => {};
    }

    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("app:update-status", listener);

    return () => {
      ipcRenderer.removeListener("app:update-status", listener);
    };
  },
  onOpenAiOauthProgress: (callback) => {
    if (typeof callback !== "function") {
      return () => {};
    }

    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("auth:openai-oauth-progress", listener);

    return () => {
      ipcRenderer.removeListener("auth:openai-oauth-progress", listener);
    };
  },
});
