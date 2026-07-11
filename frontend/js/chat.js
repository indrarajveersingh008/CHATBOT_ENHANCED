/* ======================================
   AI NEXUS — CHAT
   Rendering messages, sending them to the backend, and the
   local "new chat" history kept in the browser as a cache.
====================================== */

const chatBox = document.getElementById("chat-box");
const messageInput = document.getElementById("message");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

const chatFileInput = document.getElementById("chatFileInput");
const chatAttachBtn = document.getElementById("chatAttachBtn");
const chatFilePreviews = document.getElementById("chatFilePreviews");

let attachedFiles = [];

// Shared app-wide state other modules (memory.js, ui.js) also read/write.
const AppState = {
    _currentConversationId: localStorage.getItem("currentConversationId") || null,
    get currentConversationId() {
        if (this._currentConversationId === "null" || this._currentConversationId === "undefined" || !this._currentConversationId) {
            return null;
        }
        return parseInt(this._currentConversationId);
    },
    set currentConversationId(val) {
        this._currentConversationId = val;
        localStorage.setItem("currentConversationId", val);
    }
};

let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

marked.setOptions({ breaks: true, gfm: true });

function formatMessage(text) {
    return marked.parse(text);
}

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
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

function addMessage(text, sender, save = true, files = null) {
    const message = document.createElement("div");
    message.className = `message ${sender}`;

    const avatar = sender === "bot" ? "🤖" : "👤";

    let attachmentsHtml = "";
    if (files && files.length > 0) {
        attachmentsHtml = `<div class="message-attachments">`;
        files.forEach((f) => {
            const ext = f.filename.split('.').pop().toLowerCase();
            const downloadUrl = Api.fileDownloadUrl(f.id);
            
            const isImage = f.content_type?.startsWith("image/") || ["jpg", "jpeg", "png", "webp", "gif"].includes(ext);
            const isVideo = f.content_type?.startsWith("video/") || ["mp4", "webm", "ogg", "mov"].includes(ext);
            
            if (isImage) {
                attachmentsHtml += `
                    <a href="${downloadUrl}" target="_blank" class="attachment-item image-attachment">
                        <img src="${downloadUrl}" alt="${escapeHtml(f.filename)}" title="${escapeHtml(f.filename)}">
                    </a>
                `;
            } else if (isVideo) {
                attachmentsHtml += `
                    <div class="attachment-item video-attachment">
                        <video src="${downloadUrl}" controls preload="metadata"></video>
                    </div>
                `;
            } else {
                let icon = "📄";
                if (ext === "pdf") icon = "📕";
                else if (["doc", "docx"].includes(ext)) icon = "📘";
                else if (["xls", "xlsx", "csv"].includes(ext)) icon = "📗";
                else if (["zip", "rar", "tar", "gz"].includes(ext)) icon = "📦";
                else if (["mp3", "wav", "ogg", "m4a"].includes(ext)) icon = "🎵";
                
                attachmentsHtml += `
                    <a href="${downloadUrl}" target="_blank" class="attachment-item">
                        <span class="attachment-icon">${icon}</span>
                        <span class="attachment-name">${escapeHtml(f.filename)}</span>
                    </a>
                `;
            }
        });
        attachmentsHtml += `</div>`;
    }

    message.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="content">
            <div class="bubble">
                ${formatMessage(text)}
                ${attachmentsHtml}
            </div>
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
        chatHistory.push({ sender, text, files });
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
    if (text === "" && attachedFiles.length === 0) return;

    // Save attached files and reset input
    const filesToSend = [...attachedFiles];
    attachedFiles = [];
    renderFilePreviews();

    // Disable input buttons
    sendBtn.disabled = true;
    sendBtn.innerHTML = "⏳";
    if (chatAttachBtn) chatAttachBtn.disabled = true;
    showTyping();

    const fileIds = [];
    const uploadedFilesMeta = [];

    // Upload any attached files first
    if (filesToSend.length > 0) {
        for (let file of filesToSend) {
            try {
                const res = await Api.uploadFile(file);
                fileIds.push(res.id);
                uploadedFilesMeta.push(res);
            } catch (err) {
                console.error("Attachment upload failed:", err);
                alert(`Upload failed for "${file.name}": ${err.message}`);
                // Re-enable input UI
                sendBtn.disabled = false;
                sendBtn.innerHTML = "➤";
                if (chatAttachBtn) chatAttachBtn.disabled = false;
                hideTyping();
                return;
            }
        }
    }

    addMessage(text, "user", true, uploadedFilesMeta);
    messageInput.value = "";
    messageInput.focus();

    try {
        const selectedModel = localStorage.getItem("selectedModel") || "deepseek/deepseek-chat-v3-0324";
        const data = await Api.sendMessage(text, AppState.currentConversationId, selectedModel, fileIds);

        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";
        if (chatAttachBtn) chatAttachBtn.disabled = false;

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
        if (chatAttachBtn) chatAttachBtn.disabled = false;

        addMessage("⚠️ Sorry, something went wrong while contacting the AI.", "bot");
        console.error("Frontend Error:", error);
    }
}

function renderFilePreviews() {
    if (!chatFilePreviews) return;

    if (attachedFiles.length === 0) {
        chatFilePreviews.classList.add("hidden");
        chatFilePreviews.innerHTML = "";
        return;
    }

    chatFilePreviews.classList.remove("hidden");
    chatFilePreviews.innerHTML = "";

    attachedFiles.forEach((file, index) => {
        const card = document.createElement("div");
        card.className = "chat-preview-card";

        const ext = file.name.split('.').pop().toLowerCase();
        const isImage = file.type.startsWith("image/") || ["jpg", "jpeg", "png", "webp", "gif"].includes(ext);

        if (isImage) {
            const img = document.createElement("img");
            img.src = URL.createObjectURL(file);
            img.onload = () => {
                URL.revokeObjectURL(img.src);
            };
            card.appendChild(img);
        } else {
            const iconEl = document.createElement("span");
            iconEl.className = "chat-preview-icon";
            let icon = "📄";
            if (file.type.startsWith("video/") || ["mp4", "webm", "ogg", "mov"].includes(ext)) icon = "🎥";
            else if (file.type.startsWith("audio/") || ["mp3", "wav", "m4a"].includes(ext)) icon = "🎵";
            else if (ext === "pdf") icon = "📕";
            else if (["doc", "docx"].includes(ext)) icon = "📘";
            else if (["xls", "xlsx", "csv"].includes(ext)) icon = "📗";
            else if (["zip", "rar"].includes(ext)) icon = "📦";
            
            iconEl.textContent = icon;
            card.appendChild(iconEl);

            const nameEl = document.createElement("span");
            nameEl.className = "chat-preview-name";
            nameEl.textContent = file.name;
            card.appendChild(nameEl);
        }

        const removeBtn = document.createElement("button");
        removeBtn.className = "chat-preview-remove";
        removeBtn.innerHTML = "×";
        removeBtn.addEventListener("click", () => {
            attachedFiles.splice(index, 1);
            renderFilePreviews();
        });
        card.appendChild(removeBtn);

        chatFilePreviews.appendChild(card);
    });
}

if (chatAttachBtn && chatFileInput) {
    chatAttachBtn.addEventListener("click", () => {
        chatFileInput.click();
    });

    chatFileInput.addEventListener("change", () => {
        const newFiles = Array.from(chatFileInput.files);
        if (newFiles.length > 0) {
            attachedFiles = attachedFiles.concat(newFiles);
            renderFilePreviews();
        }
        chatFileInput.value = ""; // Reset file input
    });
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
