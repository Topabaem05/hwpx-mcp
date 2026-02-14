import "./material";
import "./styles.css";

import { mountApp } from "./app";

const root = document.getElementById("app");
if (!root) {
  throw new Error("Agent Chat: #app root not found");
}

mountApp(root);
