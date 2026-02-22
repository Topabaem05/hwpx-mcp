const { contextBridge, ipcRenderer, shell } = require("electron");

const mcpHttpUrl = process.env.HWPX_MCP_HTTP_URL || "http://127.0.0.1:8000/mcp";
const agentHttpUrl = process.env.HWPX_AGENT_HTTP_URL || mcpHttpUrl.replace(/\/mcp\/?$/i, "");

contextBridge.exposeInMainWorld("hwpxUi", {
  openExternal: (url) => shell.openExternal(url),
  getConfig: () => ({
    mcpHttpUrl,
    backendBaseUrl: agentHttpUrl || "http://127.0.0.1:8000",
  }),

  saveFileDialog: (opts) => ipcRenderer.invoke("dialog:saveFile", opts),
  openFileDialog: (opts) => ipcRenderer.invoke("dialog:openFile", opts),
  selectFolderDialog: (opts) => ipcRenderer.invoke("dialog:selectFolder", opts),

  getBackendStatus: () => ipcRenderer.invoke("backend:status"),
  restartBackend: (opts) => ipcRenderer.invoke("backend:restart", opts),
  openAiOauthLogin: () => ipcRenderer.invoke("auth:openai-oauth-login"),
});
