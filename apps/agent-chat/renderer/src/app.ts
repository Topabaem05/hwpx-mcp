import { runStubAgent } from "./agent/stubAgent";

type MessageRole = "user" | "assistant";

type Message = {
  id: string;
  role: MessageRole;
  text: string;
  createdAt: number;
  streaming: boolean;
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
};

type MdTextField = HTMLElement & { value: string };

function formatTime(epochMs: number): string {
  const date = new Date(epochMs);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function makeTitleFromText(text: string): string {
  const cleaned = text.trim().replace(/\s+/g, " ");
  if (!cleaned) {
    return "New chat";
  }
  const limit = 28;
  return cleaned.length > limit ? `${cleaned.slice(0, limit - 3)}...` : cleaned;
}

function typingIndicatorHtml(): string {
  return "<span class=\"typing\" aria-hidden=\"true\"><span></span><span></span><span></span></span>";
}

export function mountApp(root: HTMLElement): void {
  const initialConversation: Conversation = {
    id: crypto.randomUUID(),
    title: "New chat",
    messages: [],
  };

  const state: {
    conversations: Conversation[];
    activeConversationId: string;
    generation: { controller: AbortController; assistantMessageId: string } | null;
  } = {
    conversations: [initialConversation],
    activeConversationId: initialConversation.id,
    generation: null,
  };

  root.innerHTML = `
    <div class="shell" id="shell">
      <aside class="sidebar" aria-label="Conversations">
        <div class="sidebar__top">
          <md-filled-button id="new-chat">
            <md-icon slot="icon">add</md-icon>
            New chat
          </md-filled-button>
        </div>
        <md-divider></md-divider>
        <md-list id="conversation-list"></md-list>
      </aside>
      <main class="main">
        <header class="topbar">
          <md-icon-button class="topbar__menu" id="sidebar-toggle" aria-label="Toggle sidebar">
            <md-icon>menu</md-icon>
          </md-icon-button>
          <div class="topbar__title" id="chat-title"></div>
        </header>
        <section class="chat">
          <div class="chat__scroll" id="chat-scroll">
            <div class="chat__inner" id="message-list" role="log" aria-live="polite"></div>
          </div>
        </section>
        <footer class="composer">
          <div class="composer__inner">
            <md-outlined-text-field
              id="composer-input"
              label="Message"
              type="textarea"
              rows="1"
              placeholder="Message an agent..."
              aria-label="Message"
            ></md-outlined-text-field>
            <md-icon-button id="send" aria-label="Send message">
              <md-icon>send</md-icon>
            </md-icon-button>
          </div>
        </footer>
      </main>
    </div>
    <div class="backdrop" id="backdrop" aria-hidden="true"></div>
  `.trim();

  const shell = document.getElementById("shell");
  const backdrop = document.getElementById("backdrop");
  const newChatButton = document.getElementById("new-chat");
  const conversationList = document.getElementById("conversation-list");
  const chatTitle = document.getElementById("chat-title");
  const messageList = document.getElementById("message-list");
  const chatScroll = document.getElementById("chat-scroll");
  const input = document.getElementById("composer-input") as MdTextField | null;
  const sendButton = document.getElementById("send");
  const sidebarToggle = document.getElementById("sidebar-toggle");

  if (
    !shell ||
    !backdrop ||
    !newChatButton ||
    !conversationList ||
    !chatTitle ||
    !messageList ||
    !chatScroll ||
    !input ||
    !sendButton ||
    !sidebarToggle
  ) {
    throw new Error("Agent Chat: missing required DOM nodes");
  }

  const shellEl = shell;
  const backdropEl = backdrop;
  const newChatButtonEl = newChatButton;
  const conversationListEl = conversationList;
  const chatTitleEl = chatTitle;
  const messageListEl = messageList;
  const chatScrollEl = chatScroll;
  const inputEl = input;
  const sendButtonEl = sendButton;
  const sidebarToggleEl = sidebarToggle;

  function activeConversation(): Conversation {
    const convo = state.conversations.find((c) => c.id === state.activeConversationId);
    if (!convo) {
      throw new Error("Agent Chat: active conversation not found");
    }
    return convo;
  }

  function setSidebarOpen(open: boolean): void {
    shellEl.classList.toggle("shell--sidebar-open", open);
  }

  function scrollToBottom(): void {
    chatScrollEl.scrollTo({ top: chatScrollEl.scrollHeight, behavior: "auto" });
  }

  function renderConversationList(): void {
    conversationListEl.innerHTML = "";
    for (const convo of state.conversations) {
      const item = document.createElement("md-list-item");
      item.setAttribute("type", "button");
      item.tabIndex = 0;
      item.dataset.conversationId = convo.id;
      item.innerHTML = `
        <span slot="headline">${escapeHtml(convo.title)}</span>
      `.trim();
      if (convo.id === state.activeConversationId) {
        item.style.setProperty("--md-list-item-label-text-color", "var(--app-accent)");
      }
      item.addEventListener("click", () => {
        state.activeConversationId = convo.id;
        renderAll();
        setSidebarOpen(false);
      });
      conversationListEl.appendChild(item);
    }
  }

  function renderTitle(): void {
    chatTitleEl.textContent = activeConversation().title;
  }

  function renderMessages(): void {
    const convo = activeConversation();
    messageListEl.innerHTML = "";
    for (const msg of convo.messages) {
      const messageEl = document.createElement("div");
      messageEl.className = `message message--${msg.role}`;
      const bubble = document.createElement("div");
      bubble.className = "message__bubble";

      if (msg.streaming && msg.role === "assistant" && msg.text.length === 0) {
        bubble.innerHTML = typingIndicatorHtml();
      } else {
        bubble.textContent = msg.text;
      }

      messageEl.appendChild(bubble);

      if (msg.role === "assistant") {
        const meta = document.createElement("div");
        meta.className = "message__meta";
        meta.textContent = formatTime(msg.createdAt);
        bubble.appendChild(meta);
      }

      messageListEl.appendChild(messageEl);
    }
  }

  function setSendButtonMode(mode: "send" | "stop"): void {
    const icon = sendButtonEl.querySelector("md-icon");
    if (!icon) {
      return;
    }
    icon.textContent = mode === "send" ? "send" : "stop";
    sendButtonEl.setAttribute("aria-label", mode === "send" ? "Send message" : "Stop generating");
  }

  function renderAll(): void {
    renderConversationList();
    renderTitle();
    renderMessages();
    setSendButtonMode(state.generation ? "stop" : "send");
    requestAnimationFrame(() => scrollToBottom());
  }

  function startNewConversation(): void {
    const convo: Conversation = {
      id: crypto.randomUUID(),
      title: "New chat",
      messages: [],
    };
    state.conversations = [convo, ...state.conversations];
    state.activeConversationId = convo.id;
    renderAll();
    inputEl.value = "";
    setSidebarOpen(false);
  }

  function addMessage(role: MessageRole, text: string, streaming: boolean): Message {
    const msg: Message = {
      id: crypto.randomUUID(),
      role,
      text,
      createdAt: Date.now(),
      streaming,
    };
    activeConversation().messages.push(msg);
    return msg;
  }

  async function sendMessage(): Promise<void> {
    const raw = inputEl.value ?? "";
    const userText = raw.trim();
    if (!userText) {
      return;
    }

    const convo = activeConversation();
    addMessage("user", userText, false);

    if (convo.title === "New chat") {
      convo.title = makeTitleFromText(userText);
    }

    inputEl.value = "";

    const assistant = addMessage("assistant", "", true);
    const controller = new AbortController();
    state.generation = { controller, assistantMessageId: assistant.id };
    renderAll();

    try {
      for await (const chunk of runStubAgent(userText, controller.signal)) {
        assistant.text += chunk;
        assistant.streaming = true;
        renderMessages();
        scrollToBottom();
      }
    } finally {
      assistant.streaming = false;
      state.generation = null;
      renderAll();
    }
  }

  function stopGeneration(): void {
    const gen = state.generation;
    if (!gen) {
      return;
    }
    gen.controller.abort();
  }

  function escapeHtml(text: string): string {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  newChatButtonEl.addEventListener("click", () => startNewConversation());
  sidebarToggleEl.addEventListener("click", () => setSidebarOpen(!shellEl.classList.contains("shell--sidebar-open")));
  backdropEl.addEventListener("click", () => setSidebarOpen(false));

  sendButtonEl.addEventListener("click", () => {
    if (state.generation) {
      stopGeneration();
      return;
    }
    void sendMessage();
  });

  inputEl.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key !== "Enter") {
      return;
    }
    if (event.shiftKey) {
      return;
    }
    event.preventDefault();
    if (state.generation) {
      stopGeneration();
      return;
    }
    void sendMessage();
  });

  renderAll();
}
