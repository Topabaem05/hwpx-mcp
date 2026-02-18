const { contextBridge, shell } = require("electron");

const openWebUIUrl = process.env.OPEN_WEBUI_URL || "http://localhost:3000";
const mcpHttpUrl = process.env.HWPX_MCP_HTTP_URL || "http://127.0.0.1:8000/mcp";

contextBridge.exposeInMainWorld("hwpxUi", {
  openExternal: (url) => shell.openExternal(url),
  getConfig: () => ({
    openWebUIUrl,
    mcpHttpUrl,
  }),
});
