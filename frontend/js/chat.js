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

const VISION_MODELS = new Set(["google/gemini-2.5-flash", "openai/gpt-4o-mini", "openrouter/free"]);
const DEFAULT_VISION_MODEL = "openrouter/free";

function fileIsImage(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    return file.type.startsWith("image/") || ["jpg", "jpeg", "png", "webp", "gif", "bmp"].includes(ext);
}

function ensureVisionModelForAttachments(files) {
    if (!files.some(fileIsImage)) return;

    const current = localStorage.getItem("selectedModel") || "deepseek/deepseek-chat-v3-0324";
    if (VISION_MODELS.has(current)) return;

    localStorage.setItem("selectedModel", DEFAULT_VISION_MODEL);
    const modelSelect = document.getElementById("modelSelect");
    if (modelSelect) modelSelect.value = DEFAULT_VISION_MODEL;
}

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

const SVG_COPY = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
const SVG_CHECK = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
const SVG_REGEN = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>`;
const SVG_EDIT = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4z"></path></svg>`;

function addMessage(text, sender, save = true, files = null, id = null) {
    const message = document.createElement("div");
    message.className = `message ${sender}`;
    if (id) {
        message.dataset.id = id;
    }
    message.dataset.rawText = text;

    const avatar = sender === "bot" ? "⚙️" : "👨‍💻";

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

    let actionsHtml = "";
    if (sender === "bot") {
        // Only show regenerate if there is a preceding user message
        const showRegen = id !== null || (chatBox.children.length > 0 && chatBox.lastElementChild.classList.contains("user"));
        actionsHtml = `
            <div class="message-actions">
                <button class="action-btn copy-btn" title="Copy Message">${SVG_COPY}</button>
                ${showRegen ? `<button class="action-btn regenerate-btn" title="Regenerate Response">${SVG_REGEN}</button>` : ""}
            </div>
        `;
    } else if (sender === "user") {
        actionsHtml = `
            <div class="message-actions">
                <button class="action-btn edit-btn" title="Edit Message">${SVG_EDIT}</button>
            </div>
        `;
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
                ${actionsHtml}
            </div>
        </div>
    `;

    chatBox.appendChild(message);

    if (window.hljs) {
        message.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
    }

    setupCodeExecution(message);

    const copyBtn = message.querySelector(".copy-btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(message.dataset.rawText || text);
            copyBtn.innerHTML = SVG_CHECK;
            copyBtn.classList.add("copied");
            setTimeout(() => {
                copyBtn.innerHTML = SVG_COPY;
                copyBtn.classList.remove("copied");
            }, 2000);
        });
    }

    const editBtn = message.querySelector(".edit-btn");
    if (editBtn) {
        editBtn.addEventListener("click", () => enterEditMode(message));
    }

    const regenBtn = message.querySelector(".regenerate-btn");
    if (regenBtn) {
        regenBtn.addEventListener("click", () => retryResponse(message));
    }

    scrollBottom();

    if (save) {
        chatHistory.push({ sender, text, files, id });
        saveHistory();
    }
}

function showTyping() {
    const typing = document.createElement("div");
    typing.className = "message bot";
    typing.id = "typing";
    typing.innerHTML = `
        <div class="avatar">⚙️</div>
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
                return;
            }
        }
    }

    addMessage(text, "user", true, uploadedFilesMeta);
    messageInput.value = "";
    messageInput.focus();
    showTyping();

    try {
        ensureVisionModelForAttachments(filesToSend);
        const selectedModel = localStorage.getItem("selectedModel") || "deepseek/deepseek-chat-v3-0324";
        const data = await Api.sendMessage(text, AppState.currentConversationId, selectedModel, fileIds);

        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";
        if (chatAttachBtn) chatAttachBtn.disabled = false;

        if (data.error) {
            console.error("Backend error detail:", data.error);
        }

        if (!data.reply) {
            throw new Error("No 'reply' received from backend.");
        }

        if (data.conversation_id) {
            AppState.currentConversationId = data.conversation_id;
            if (typeof Memory !== "undefined") {
                Memory.refreshList();
            }
        }

        // Apply message IDs to user message in DOM and state
        if (data.user_message_id) {
            const userMessages = chatBox.querySelectorAll(".message.user");
            if (userMessages.length > 0) {
                const lastUserMsg = userMessages[userMessages.length - 1];
                lastUserMsg.dataset.id = data.user_message_id;
            }
            if (chatHistory.length > 0) {
                for (let i = chatHistory.length - 1; i >= 0; i--) {
                    if (chatHistory[i].sender === "user") {
                        chatHistory[i].id = data.user_message_id;
                        break;
                    }
                }
                saveHistory();
            }
        }

        addMessage(data.reply, "bot", true, null, data.bot_message_id);

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
            ensureVisionModelForAttachments(attachedFiles);
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

function enterEditMode(messageEl) {
    cancelAllEdits();
    const bubble = messageEl.querySelector(".bubble");
    if (!bubble) return;
    const rawText = messageEl.dataset.rawText || "";
    messageEl.dataset.originalBubbleHtml = bubble.innerHTML;
    bubble.innerHTML = `
        <div class="edit-container">
            <textarea class="edit-textarea">${escapeHtml(rawText)}</textarea>
            <div class="edit-buttons">
                <button class="save-edit-btn">Save & Submit</button>
                <button class="cancel-edit-btn">Cancel</button>
            </div>
        </div>
    `;
    const textarea = bubble.querySelector(".edit-textarea");
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    bubble.querySelector(".cancel-edit-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        cancelEdit(messageEl);
    });
    bubble.querySelector(".save-edit-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        const newText = textarea.value.trim();
        if (newText === "") return;
        submitEdit(messageEl, newText);
    });
}

function cancelEdit(messageEl) {
    const bubble = messageEl.querySelector(".bubble");
    if (bubble && messageEl.dataset.originalBubbleHtml) {
        bubble.innerHTML = messageEl.dataset.originalBubbleHtml;
        delete messageEl.dataset.originalBubbleHtml;
    }
}

function cancelAllEdits() {
    document.querySelectorAll(".message.user").forEach((msgEl) => {
        if (msgEl.dataset.originalBubbleHtml) {
            cancelEdit(msgEl);
        }
    });
}

async function submitEdit(messageEl, newText) {
    const messageId = messageEl.dataset.id;
    if (!messageId) {
        messageInput.value = newText;
        removeMessagesFromDOMAndHistory(messageEl);
        messageInput.focus();
        return;
    }
    sendBtn.disabled = true;
    sendBtn.innerHTML = "⏳";
    if (chatAttachBtn) chatAttachBtn.disabled = true;
    removeMessagesFromDOMAfter(messageEl);
    showTyping();
    try {
        const selectedModel = localStorage.getItem("selectedModel") || "deepseek/deepseek-chat-v3-0324";
        const data = await Api.editOrRetryMessage(parseInt(messageId), newText, selectedModel);
        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";
        if (chatAttachBtn) chatAttachBtn.disabled = false;
        if (data.error) {
            console.error("Backend error detail:", data.error);
        }
        if (!data.reply) {
            throw new Error("No 'reply' received from backend.");
        }
        messageEl.dataset.rawText = newText;
        const bubble = messageEl.querySelector(".bubble");
        if (bubble) {
            bubble.innerHTML = formatMessage(newText);
            if (window.hljs) {
                bubble.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
            }
            setupCodeExecution(messageEl);
        }
        delete messageEl.dataset.originalBubbleHtml;
        const msgIndex = chatHistory.findIndex(m => m.id && String(m.id) === String(messageId));
        if (msgIndex !== -1) {
            chatHistory = chatHistory.slice(0, msgIndex + 1);
            chatHistory[msgIndex].text = newText;
        } else {
            chatHistory = [{ sender: "user", text: newText, id: parseInt(messageId) }];
        }
        saveHistory();
        addMessage(data.reply, "bot", true, null, data.bot_message_id);
        if (typeof Voice !== "undefined") {
            Voice.speak(data.reply);
        }
        if (typeof Memory !== "undefined") {
            Memory.refreshList();
        }
    } catch (error) {
        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";
        if (chatAttachBtn) chatAttachBtn.disabled = false;
        alert(`Edit failed: ${error.message}`);
        cancelEdit(messageEl);
    }
}

function removeMessagesFromDOMAfter(messageEl) {
    let next = messageEl.nextElementSibling;
    while (next) {
        const toRemove = next;
        next = next.nextElementSibling;
        if (toRemove.id !== "typing") {
            toRemove.remove();
        }
    }
}

function removeMessagesFromDOMAndHistory(messageEl) {
    const index = chatHistory.findIndex(m => m.text === messageEl.dataset.rawText && m.sender === "user");
    if (index !== -1) {
        chatHistory = chatHistory.slice(0, index);
        saveHistory();
    }
    let next = messageEl.nextElementSibling;
    while (next) {
        const toRemove = next;
        next = next.nextElementSibling;
        toRemove.remove();
    }
    messageEl.remove();
}

async function retryResponse(botMessageEl) {
    const userMessageEl = botMessageEl.previousElementSibling;
    if (!userMessageEl || !userMessageEl.classList.contains("user")) {
        alert("Could not find preceding user message to retry.");
        return;
    }
    const messageId = userMessageEl.dataset.id;
    if (!messageId) {
        messageInput.value = userMessageEl.dataset.rawText || "";
        removeMessagesFromDOMAndHistory(userMessageEl);
        sendMessage();
        return;
    }
    sendBtn.disabled = true;
    sendBtn.innerHTML = "⏳";
    if (chatAttachBtn) chatAttachBtn.disabled = true;
    removeMessagesFromDOMAfter(userMessageEl);
    showTyping();
    try {
        const selectedModel = localStorage.getItem("selectedModel") || "deepseek/deepseek-chat-v3-0324";
        const data = await Api.editOrRetryMessage(parseInt(messageId), userMessageEl.dataset.rawText, selectedModel, Settings.getActiveSystemPrompt());
        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";
        if (chatAttachBtn) chatAttachBtn.disabled = false;
        if (data.error) {
            console.error("Backend error detail:", data.error);
        }
        if (!data.reply) {
            throw new Error("No 'reply' received from backend.");
        }
        const msgIndex = chatHistory.findIndex(m => m.id && String(m.id) === String(messageId));
        if (msgIndex !== -1) {
            chatHistory = chatHistory.slice(0, msgIndex + 1);
        } else {
            chatHistory = [{ sender: "user", text: userMessageEl.dataset.rawText, id: parseInt(messageId) }];
        }
        saveHistory();
        addMessage(data.reply, "bot", true, null, data.bot_message_id);
        if (typeof Voice !== "undefined") {
            Voice.speak(data.reply);
        }
    } catch (error) {
        hideTyping();
        sendBtn.disabled = false;
        sendBtn.innerHTML = "➤";
        if (chatAttachBtn) chatAttachBtn.disabled = false;
        alert(`Regeneration failed: ${error.message}`);
    }
}

sendBtn.addEventListener("click", sendMessage);

function autoResizeInput() {
    messageInput.style.height = "auto";
    const maxHeight = 180;
    const nextHeight = Math.min(messageInput.scrollHeight, maxHeight);
    messageInput.style.height = `${nextHeight}px`;
}

messageInput.addEventListener("input", autoResizeInput);
messageInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
        messageInput.style.height = "56px";
    }
});

autoResizeInput();

clearBtn.addEventListener("click", function () {
    if (!confirm("Start a new chat?")) return;
    startNewChat();
});

/* ======================================
   CODE BLOCK EXECUTION RUNNERS
   ====================================== */

function loadScript(url) {
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = url;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

function setupCodeExecution(messageEl) {
    const codeBlocks = messageEl.querySelectorAll("pre code");
    codeBlocks.forEach(codeEl => {
        const preEl = codeEl.parentElement;
        if (!preEl || preEl.tagName !== "PRE" || preEl.parentElement.classList.contains("code-block-wrapper")) {
            return;
        }

        let lang = "";
        const classes = codeEl.className.split(" ");
        for (const cls of classes) {
            if (cls.startsWith("language-")) {
                lang = cls.replace("language-", "").toLowerCase();
            } else if (cls.startsWith("lang-")) {
                lang = cls.replace("lang-", "").toLowerCase();
            }
        }

        const executableLangs = ["javascript", "js", "html", "htm", "python", "py"];
        const isExecutable = executableLangs.includes(lang);

        // Create neubrutalist wrapper
        const wrapper = document.createElement("div");
        wrapper.className = "code-block-wrapper";

        // Insert wrapper before preEl
        preEl.parentNode.insertBefore(wrapper, preEl);
        wrapper.appendChild(preEl);

        // Create header
        const header = document.createElement("div");
        header.className = "code-block-header";

        const langLabel = document.createElement("span");
        langLabel.className = "code-block-lang";
        langLabel.textContent = lang || "code";

        const actions = document.createElement("div");
        actions.className = "code-block-actions";

        // Copy Code Button
        const copyBtn = document.createElement("button");
        copyBtn.className = "code-action-btn copy-code-btn";
        copyBtn.title = "Copy Code";
        copyBtn.innerHTML = `${SVG_COPY} <span>Copy</span>`;
        copyBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(codeEl.textContent);
            const btnSpan = copyBtn.querySelector("span");
            btnSpan.textContent = "Copied!";
            copyBtn.classList.add("copied");
            setTimeout(() => {
                copyBtn.innerHTML = `${SVG_COPY} <span>Copy</span>`;
                copyBtn.classList.remove("copied");
            }, 2000);
        });
        actions.appendChild(copyBtn);

        // Run Code Button
        if (isExecutable) {
            const runBtn = document.createElement("button");
            runBtn.className = "code-action-btn run-code-btn";
            runBtn.title = "Run Code";
            runBtn.innerHTML = `▶ <span>Run</span>`;
            runBtn.addEventListener("click", () => {
                executeCodeBlock(codeEl, lang, wrapper);
            });
            actions.appendChild(runBtn);
        }

        header.appendChild(langLabel);
        header.appendChild(actions);
        wrapper.insertBefore(header, preEl);
    });
}

async function executeCodeBlock(codeEl, lang, wrapper) {
    let outputContainer = wrapper.querySelector(".code-execution-container");
    if (!outputContainer) {
        outputContainer = document.createElement("div");
        outputContainer.className = "code-execution-container";
        outputContainer.innerHTML = `
            <div class="code-execution-header">
                <span class="code-execution-status">⚙️ Executing...</span>
                <div class="code-execution-controls">
                    <button class="code-execution-clear-btn" title="Clear Output">🧹 Clear</button>
                    <button class="code-execution-close-btn" title="Close Pane">✕ Close</button>
                </div>
            </div>
            <div class="code-execution-output-wrapper">
                <pre class="code-execution-console-output"></pre>
                <div class="code-execution-preview-wrapper hidden"></div>
            </div>
        `;
        wrapper.appendChild(outputContainer);

        outputContainer.querySelector(".code-execution-clear-btn").addEventListener("click", () => {
            const consoleOut = outputContainer.querySelector(".code-execution-console-output");
            if (consoleOut) consoleOut.textContent = "";
            const previewWrap = outputContainer.querySelector(".code-execution-preview-wrapper");
            if (previewWrap) previewWrap.innerHTML = "";
        });

        outputContainer.querySelector(".code-execution-close-btn").addEventListener("click", () => {
            outputContainer.classList.add("hidden");
        });
    }

    const execId = "exec-" + Math.random().toString(36).substr(2, 9);
    outputContainer.dataset.execId = execId;
    outputContainer.classList.remove("hidden");

    const runStatus = outputContainer.querySelector(".code-execution-status");
    const consoleOut = outputContainer.querySelector(".code-execution-console-output");
    const previewWrap = outputContainer.querySelector(".code-execution-preview-wrapper");

    consoleOut.classList.add("hidden");
    consoleOut.textContent = "";
    previewWrap.classList.add("hidden");
    previewWrap.innerHTML = "";

    const rawCode = codeEl.textContent;

    if (lang === "html" || lang === "htm") {
        runStatus.textContent = "🌐 Rendering Preview...";
        previewWrap.classList.remove("hidden");

        const iframe = document.createElement("iframe");
        iframe.sandbox = "allow-scripts";
        iframe.style.width = "100%";
        iframe.style.height = "300px";
        iframe.style.border = "2px solid #22201e";
        iframe.style.background = "#ffffff";
        iframe.style.borderRadius = "6px";
        iframe.style.boxShadow = "2px 2px 0px #22201e";

        const logWrapperScript = `
            <script>
                (function() {
                    const wrap = (type) => (...args) => {
                        window.parent.postMessage({
                            type: 'console-log',
                            execId: '${execId}',
                            logType: type,
                            text: args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ')
                        }, '*');
                    };
                    console.log = wrap('log');
                    console.error = wrap('error');
                    console.warn = wrap('warn');
                    window.onerror = (msg, src, line) => {
                        wrap('error')("Runtime Error: " + msg + " (line " + line + ")");
                    };
                })();
            </script>
        `;

        try {
            iframe.srcdoc = logWrapperScript + rawCode;
            previewWrap.appendChild(iframe);
            consoleOut.classList.remove("hidden");
            runStatus.textContent = "🌐 Preview Ready";
        } catch (err) {
            runStatus.textContent = "❌ Failed";
            consoleOut.classList.remove("hidden");
            consoleOut.textContent = `Preview error: ${err.message}`;
        }

    } else if (lang === "javascript" || lang === "js") {
        runStatus.textContent = "⚙️ Executing JS...";
        consoleOut.classList.remove("hidden");

        try {
            const iframe = document.createElement("iframe");
            iframe.style.display = "none";
            iframe.sandbox = "allow-scripts";

            const htmlContent = `
                <script>
                    (function() {
                        const wrap = (type) => (...args) => {
                            window.parent.postMessage({
                                type: 'console-log',
                                execId: '${execId}',
                                logType: type,
                                text: args.map(a => {
                                    if (a === null) return 'null';
                                    if (a === undefined) return 'undefined';
                                    return typeof a === 'object' ? JSON.stringify(a) : String(a);
                                }).join(' ')
                            }, '*');
                        };
                        console.log = wrap('log');
                        console.error = wrap('error');
                        console.warn = wrap('warn');
                        
                        window.onerror = (msg, src, line) => {
                            wrap('error')("Runtime Error: " + msg + " (line " + line + ")");
                            return true;
                        };
                    })();
                    
                    try {
                        ${rawCode}
                    } catch (err) {
                        console.error(err.stack || err.message);
                    }
                </script>
            `;
            iframe.srcdoc = htmlContent;
            document.body.appendChild(iframe);

            setTimeout(() => {
                if (iframe.parentNode) {
                    iframe.parentNode.removeChild(iframe);
                }
                if (runStatus.textContent === "⚙️ Executing JS...") {
                    runStatus.textContent = "✅ Finished";
                }
            }, 1000);

        } catch (err) {
            consoleOut.textContent += `\n❌ Execution failed: ${err.message}`;
            runStatus.textContent = "❌ Failed";
        }

    } else if (lang === "python" || lang === "py") {
        runStatus.textContent = "⚙️ Loading Python Environment...";
        consoleOut.classList.remove("hidden");

        if (!window.pyodideLoading && !window.pyodide) {
            window.pyodideLoading = true;
            try {
                await loadScript("https://cdn.jsdelivr.net/pyodide/v0.26.1/full/pyodide.js");
                runStatus.textContent = "⚙️ Initializing Python VM...";
                window.pyodide = await loadPyodide({
                    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.1/full/"
                });
                window.pyodideLoading = false;
            } catch (err) {
                window.pyodideLoading = false;
                runStatus.textContent = "❌ Load Failed";
                consoleOut.textContent = `Failed to load Pyodide environment: ${err.message}`;
                return;
            }
        } else if (window.pyodideLoading) {
            while (window.pyodideLoading) {
                await new Promise(r => setTimeout(r, 100));
            }
        }

        runStatus.textContent = "⚙️ Running Python Code...";
        try {
            const decoder = new TextDecoder("utf-8");
            window.pyodide.setStdout({
                write: (buffer) => {
                    const text = decoder.decode(buffer);
                    consoleOut.textContent += text;
                    const wrapper = outputContainer.querySelector(".code-execution-output-wrapper");
                    if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
                    return buffer.length;
                }
            });
            window.pyodide.setStderr({
                write: (buffer) => {
                    const text = decoder.decode(buffer);
                    consoleOut.textContent += text;
                    const wrapper = outputContainer.querySelector(".code-execution-output-wrapper");
                    if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
                    return buffer.length;
                }
            });

            await window.pyodide.runPythonAsync(rawCode);
            runStatus.textContent = "✅ Python Finished";
        } catch (err) {
            consoleOut.textContent += `❌ Python Error:\n${err.message}\n`;
            runStatus.textContent = "❌ Python Error";
        }
    }
}

// Global console log message listener for sandboxed executions
window.addEventListener("message", (event) => {
    if (event.data && event.data.type === "console-log") {
        const { execId, logType, text } = event.data;
        const container = document.querySelector(`[data-exec-id="${execId}"]`);
        if (container) {
            const consoleOut = container.querySelector(".code-execution-console-output");
            if (consoleOut) {
                let prefix = "";
                if (logType === "error") prefix = "❌ ";
                else if (logType === "warn") prefix = "⚠️ ";
                consoleOut.textContent += prefix + text + "\n";
                
                const wrapper = container.querySelector(".code-execution-output-wrapper");
                if (wrapper) {
                    wrapper.scrollTop = wrapper.scrollHeight;
                }
            }
        }
    }
});
