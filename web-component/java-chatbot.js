const chatBox = document.getElementById("chat-box");
const input = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const typingIndicator = document.getElementById("typing");

// ✅ Deployed backend API
const API_URL = "https://java-chatbot-backend.onrender.com/api/query";

/* -----------------------------
   INPUT HANDLING
------------------------------*/

input.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = this.scrollHeight + "px";
});

input.addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", sendMessage);

/* -----------------------------
   SEND MESSAGE
------------------------------*/

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  input.disabled = true;
  sendBtn.disabled = true;

  addUserMessage(text);
  input.value = "";
  input.style.height = "auto";

  typingIndicator.style.display = "block";

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    const data = await response.json();
    typingIndicator.style.display = "none";

    if (data.type === "QA") {
      // ✅ ONLY ANSWER — NO CONFIDENCE
      addBotMessage(data.answer);
    }
    else if (data.type === "CODE_ANALYSIS") {
      renderCodeAnalysis(data.result);
    }
    else if (data.type === "NO_ANSWER") {
      addBotMessage(data.answer);
    }
    else {
      addBotMessage("Unexpected response from server.", "error");
    }

  } catch (err) {
    typingIndicator.style.display = "none";
    addBotMessage("❌ Failed to connect to backend.", "error");
  }

  input.disabled = false;
  sendBtn.disabled = false;
  input.focus();
}

/* -----------------------------
   MESSAGE RENDERERS
------------------------------*/

function addUserMessage(text) {
  const msg = document.createElement("div");
  msg.className = "message user";

  const content = document.createElement("div");
  content.className = "message-content";
  content.textContent = text;

  msg.appendChild(content);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function addBotMessage(text, type = "") {
  const msg = document.createElement("div");
  msg.className = "message bot";

  const content = document.createElement("div");
  content.className = `message-content ${type}`;
  content.innerHTML = text;

  msg.appendChild(content);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

/* -----------------------------
   CODE ANALYSIS
------------------------------*/

function renderCodeAnalysis(result) {
  if (result.success) {
    let msg = "✅ Code ran successfully";

    if (result.runtime_output && result.runtime_output.trim()) {
      msg += "<br><br><strong>Output:</strong><br>" +
             result.runtime_output.replace(/\n/g, "<br>");
    }

    addBotMessage(msg, "success");
  } else {
    let msg = "❌ Java Error<br><br>";

    if (result.compile_output && result.compile_output.trim()) {
      msg += "<strong>Compiler Output:</strong><br>" +
             result.compile_output.replace(/\n/g, "<br>") + "<br><br>";
    }

    if (result.runtime_output && result.runtime_output.trim()) {
      msg += "<strong>Runtime Output:</strong><br>" +
             result.runtime_output.replace(/\n/g, "<br>") + "<br><br>";
    }

    if (result.suggestions && result.suggestions.length) {
      msg += "<strong>Suggestions:</strong><br>";
      result.suggestions.forEach((s, i) => {
        msg += `${i + 1}. <strong>${s.title}</strong><br>${s.explanation}<br><br>`;
      });
    }

    addBotMessage(msg, "error");
  }
}

/* -----------------------------
   WELCOME MESSAGE
------------------------------*/

window.onload = () => {
  addBotMessage(
    "Hello! 👋 I'm your Java assistant. Ask a Java question or paste your Java code for analysis."
  );
};
