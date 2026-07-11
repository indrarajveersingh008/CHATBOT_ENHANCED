/* ======================================
   AI NEXUS — CHAT
   Rendering messages, sending them to the backend, and the
   local "new chat" history kept in the browser as a cache.
====================================== */

const chatBox = document.getElementById("chat-box");
const messageInput = document.getElementById("message");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

// Shared app-wide state other modules (memory.js, ui.js) also read/write.
const AppState = {
    currentConversationId: null
};

let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

marked.setOptions({ breaks: true, gfm: true });

function formatMessage(text) {
    return marked.parse(text);
}

function saveHistory() {
    localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
}

function currentTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function scrollBottom() {
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addMessage(text, sender, save = true) {
    const message = document.createElement("div");
    message.className = `message ${sender}`;

    const avatar = sender === "bot" ? "🤖" : "👤";

    message.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="content">
            <div class="bubble">${formatMessage(text)}</div>
            <div class="message-footer">
                <div class="time">${currentTime()}</div>
                ${sender === "bot" ? `<button class="copy-btn"><span>📋</span><span>Copy</span></button>` : ""}
            </div>
        </div>
    `;

    chatBox.appendChild(message);

    if (window.hljs) {
        message.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
    }

    const copyBtn = message.querySelector(".copy-btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            const code = message.querySelector("pre code");
            navigator.clipboard.writeText(code ? code.innerText : text);
            copyBtn.innerHTML = "<span>✅</span><span>Copied</span>";
            copyBtn.classList.add("copied");
            setTimeout(() => {
                copyBtn.innerHTML = "<span>📋</span><span>Copy</span>";
                copyBtn.classList.remove("copied");
            }, 2000);
        });
    }

    scrollBottom();

    if (save) {
        chatHistory.push({ sender, text });
        saveHistory();
    }
}

function showTyping() {
    const typing = document.createElement("div");
    typing.className = "message bot";
    typing.id = "typing";
    typing.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="bubble typing-bubble">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;
    chatBox.appendChild(typing);
    scrollBottom();
}

function hideTyping() {
    const typing = document.getElementById("typing");
    if (typing) typing.remove();
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (text === "") return;

    addMessage(text, "user");
    messageInput.value = "";
    messageInput.focus();

    sendBtn.disabled = true;
    sendBtn.innerHTML = "⏳";
    showTyping();

    try {
        const selectedModel = localStorage.getItem("selectedModel") || "deepseek/deepseek-chat-v3-0324";
        const data = await Api.sendMessage(text, AppState.currentConversationId, selectedModel);

        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";

        if (!data.reply) {
            throw new Error("No 'reply' received from backend.");
        }

        if (data.conversation_id) {
            AppState.currentConversationId = data.conversation_id;
            if (typeof Memory !== "undefined") {
                Memory.refreshList();
            }
        }

        addMessage(data.reply, "bot");
        
        if (typeof Voice !== "undefined") {
            Voice.speak(data.reply);
        }
    } catch (error) {
        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";

        addMessage("⚠️ Sorry, something went wrong while contacting the AI.", "bot");
        console.error("Frontend Error:", error);
    }
}

function startNewChat(showWelcome = true) {
    chatHistory = [];
    AppState.currentConversationId = null;
    localStorage.removeItem("chatHistory");
    chatBox.innerHTML = "";

    if (showWelcome) {
        addMessage(
            "👋 Welcome to AI Nexus 2.0.<br><br>I'm your intelligent AI assistant.<br><br>Ask me anything about Programming, AI, SQL, Python, Java, or General Knowledge.",
            "bot",
            false
        );
    }

    messageInput.focus();
}

sendBtn.addEventListener("click", sendMessage);

messageInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
});

clearBtn.addEventListener("click", function () {
    if (!confirm("Start a new chat?")) return;
    startNewChat();
});
