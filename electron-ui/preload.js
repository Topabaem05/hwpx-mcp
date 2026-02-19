const { contextBridge, ipcRenderer, shell } = require("electron");

const mcpHttpUrl = process.env.HWPX_MCP_HTTP_URL || "http://127.0.0.1:8000/mcp";

contextBridge.exposeInMainWorld("hwpxUi", {
  openExternal: (url) => shell.openExternal(url),
  getConfig: () => ({ mcpHttpUrl }),

  saveFileDialog: (opts) => ipcRenderer.invoke("dialog:saveFile", opts),
  openFileDialog: (opts) => ipcRenderer.invoke("dialog:openFile", opts),
  selectFolderDialog: (opts) => ipcRenderer.invoke("dialog:selectFolder", opts),

  getBackendStatus: () => ipcRenderer.invoke("backend:status"),
  restartBackend: () => ipcRenderer.invoke("backend:restart"),
});
