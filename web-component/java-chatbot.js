class JavaChatbot extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback() {
    this.shadowRoot.innerHTML = `
      <style>
        * { box-sizing: border-box; font-family: Arial; }
        .chatbox {
          width: 100%;
          max-width: 400px;
          border: 1px solid #ccc;
          border-radius: 8px;
          padding: 10px;
        }
        .messages {
          height: 300px;
          overflow-y: auto;
          border-bottom: 1px solid #ddd;
          margin-bottom: 8px;
        }
        .msg { margin: 5px 0; }
        .user { font-weight: bold; }
        textarea {
          width: 100%;
          resize: none;
        }
        button {
          width: 100%;
          padding: 6px;
          margin-top: 5px;
        }
      </style>

      <div class="chatbox">
        <div class="messages" id="messages"></div>
        <textarea id="input" rows="3" placeholder="Ask Java question or paste code"></textarea>
        <button id="send">Send</button>
      </div>
    `;

    this.shadowRoot
      .getElementById("send")
      .addEventListener("click", () => this.sendMessage());
  }

  async sendMessage() {
    const input = this.shadowRoot.getElementById("input");
    const text = input.value.trim();
    if (!text) return;

    this.addMessage("You", text);
    input.value = "";

    const res = await fetch("https://java-chatbot-api.onrender.com/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    const data = await res.json();
    this.addMessage("Bot", data.answer || data.message || "No response");
  }

  addMessage(sender, text) {
    const box = this.shadowRoot.getElementById("messages");
    const div = document.createElement("div");
    div.className = "msg";
    div.innerHTML = `<span class="user">${sender}:</span> ${text}`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }
}

customElements.define("java-chatbot", JavaChatbot);
