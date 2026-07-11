/* ======================================
   AI NEXUS — UI
   Sidebar panel switching, plus the Files, Search, and
   Settings panels (Chat lives in chat.js, Memory in memory.js).
====================================== */

const UI = {
    panels: ["chat", "memory", "files", "search", "settings"],

    init() {
        document.querySelectorAll(".menu-btn[data-panel]").forEach((btn) => {
            btn.addEventListener("click", () => this.showPanel(btn.dataset.panel));
        });

        this.showPanel("chat");
        Files.init();
        Search.init();
        Settings.init();
    },

    showPanel(name) {
        if (!this.panels.includes(name)) return;

        this.panels.forEach((p) => {
            const el = document.getElementById(`panel-${p}`);
            if (el) el.classList.toggle("hidden", p !== name);
        });

        document.querySelectorAll(".menu-btn[data-panel]").forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.panel === name);
        });

        if (name === "memory") Memory.refreshList();
        if (name === "files") Files.refreshList();
        if (name === "chat") messageInput?.focus();
    }
};

/* ---------- Files panel ---------- */

const Files = {
    listEl: null,
    inputEl: null,

    init() {
        this.listEl = document.getElementById("filesList");
        this.inputEl = document.getElementById("fileInput");

        document.getElementById("fileUploadBtn")?.addEventListener("click", () => this.inputEl.click());
        this.inputEl?.addEventListener("change", () => this.handleUpload());
    },

    async handleUpload() {
        const file = this.inputEl.files[0];
        if (!file) return;

        try {
            await Api.uploadFile(file);
            this.inputEl.value = "";
            this.refreshList();
        } catch (error) {
            console.error("Upload failed:", error);
            alert(`Upload failed: ${error.message}`);
        }
    },

    async refreshList() {
        if (!this.listEl) return;
        this.listEl.innerHTML = `<li class="memory-empty">Loading…</li>`;

        try {
            const files = await Api.listFiles();

            if (files.length === 0) {
                this.listEl.innerHTML = `<li class="memory-empty">No files uploaded yet.</li>`;
                return;
            }

            this.listEl.innerHTML = "";

            files.forEach((f) => {
                const item = document.createElement("li");
                item.className = "memory-item";
                item.innerHTML = `
                    <span class="memory-title">📄 ${escapeHtml(f.filename)}</span>
                    <span class="memory-date">${formatBytes(f.size)}</span>
                    <button class="memory-download" title="Download">⬇️</button>
                    <button class="memory-delete" title="Delete">🗑️</button>
                `;

                item.querySelector(".memory-download").addEventListener("click", () => {
                    window.open(Api.fileDownloadUrl(f.id), "_blank");
                });

                item.querySelector(".memory-delete").addEventListener("click", async () => {
                    if (!confirm(`Delete "${f.filename}"?`)) return;
                    await Api.deleteFile(f.id);
                    this.refreshList();
                });

                this.listEl.appendChild(item);
            });
        } catch (error) {
            console.error("Failed to load files:", error);
            this.listEl.innerHTML = `<li class="memory-empty">⚠️ Couldn't reach the server.</li>`;
        }
    }
};

function formatBytes(bytes) {
    if (!bytes) return "0 KB";
    const kb = bytes / 1024;
    return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(1)} MB`;
}

/* ---------- Search panel ---------- */

const Search = {
    inputEl: null,
    resultsEl: null,

    init() {
        this.inputEl = document.getElementById("searchInput");
        this.resultsEl = document.getElementById("searchResults");

        document.getElementById("searchBtn")?.addEventListener("click", () => this.runSearch());
        this.inputEl?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") this.runSearch();
        });
    },

    async runSearch() {
        const query = this.inputEl.value.trim();
        if (!query) return;

        this.resultsEl.innerHTML = `<li class="memory-empty">Searching…</li>`;

        try {
            const results = await Api.searchMessages(query);

            if (results.length === 0) {
                this.resultsEl.innerHTML = `<li class="memory-empty">No messages found for "${escapeHtml(query)}".</li>`;
                return;
            }

            this.resultsEl.innerHTML = "";

            results.forEach((r) => {
                const item = document.createElement("li");
                item.className = "memory-item";
                const snippet = r.content.length > 90 ? r.content.slice(0, 90) + "…" : r.content;

                item.innerHTML = `
                    <span class="memory-title">${r.sender === "bot" ? "🤖" : "👤"} ${escapeHtml(snippet)}</span>
                `;

                item.addEventListener("click", () => Memory.loadConversation(r.conversation_id, r.content));
                this.resultsEl.appendChild(item);
            });
        } catch (error) {
            console.error("Search failed:", error);
            this.resultsEl.innerHTML = `<li class="memory-empty">⚠️ Couldn't reach the server.</li>`;
        }
    }
};

/* ---------- Settings panel ---------- */

const Settings = {
    init() {
        // Elements
        const backendUrlInput = document.getElementById("backendUrlInput");
        const smartAwakeToggle = document.getElementById("smartAwakeToggle");
        const voiceResponseToggle = document.getElementById("voiceResponseToggle");
        const modelSelect = document.getElementById("modelSelect");

        // Load current URL
        if (backendUrlInput) {
            backendUrlInput.value = getApiBaseUrl();
            backendUrlInput.addEventListener("change", (e) => {
                const val = e.target.value.trim();
                if (val) {
                    localStorage.setItem("customBackendUrl", val);
                } else {
                    localStorage.removeItem("customBackendUrl");
                }
            });
        }

        // Set initial values
        if (smartAwakeToggle) {
            smartAwakeToggle.checked = localStorage.getItem("smartAwake") === "true";
            smartAwakeToggle.addEventListener("change", (e) => {
                if (e.target.checked) {
                    Voice.startSmartAwake();
                } else {
                    Voice.stopSmartAwake();
                }
            });
        }

        if (voiceResponseToggle) {
            voiceResponseToggle.checked = localStorage.getItem("voiceResponse") !== "false";
            voiceResponseToggle.addEventListener("change", (e) => {
                localStorage.setItem("voiceResponse", e.target.checked ? "true" : "false");
            });
        }

        if (modelSelect) {
            modelSelect.value = localStorage.getItem("selectedModel") || "deepseek/deepseek-chat-v3-0324";
            modelSelect.addEventListener("change", (e) => {
                localStorage.setItem("selectedModel", e.target.value);
            });
        }

        document.getElementById("clearLocalCacheBtn")?.addEventListener("click", () => {
            if (!confirm("Clear the local chat cache stored in this browser? Server-side history is unaffected.")) return;
            localStorage.removeItem("chatHistory");
            alert("Local cache cleared.");
        });
    }
};

document.addEventListener("DOMContentLoaded", () => UI.init());
