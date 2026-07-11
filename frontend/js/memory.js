/* ======================================
   AI NEXUS — MEMORY
   The "🧠 Memory" sidebar panel: past conversations stored
   server-side, so they persist across devices/browsers.
====================================== */

const Memory = {
    listEl: null,

    init() {
        this.listEl = document.getElementById("memoryList");
        document.getElementById("newChatFromMemory")?.addEventListener("click", () => {
            startNewChat();
            UI.showPanel("chat");
        });
        this.refreshList();
    },

    async refreshList() {
        if (!this.listEl) return;

        this.listEl.innerHTML = `<li class="memory-empty">Loading…</li>`;

        try {
            const conversations = await Api.listConversations();

            if (conversations.length === 0) {
                this.listEl.innerHTML = `<li class="memory-empty">No conversations yet. Say hi! 👋</li>`;
                return;
            }

            this.listEl.innerHTML = "";

            conversations.forEach((c) => {
                const item = document.createElement("li");
                item.className = "memory-item";
                if (c.id === AppState.currentConversationId) {
                    item.classList.add("active");
                }

                const date = new Date(c.created_at).toLocaleDateString([], {
                    month: "short",
                    day: "numeric"
                });

                item.innerHTML = `
                    <span class="memory-title">${escapeHtml(c.title || "New Chat")}</span>
                    <span class="memory-date">${date}</span>
                    <button class="memory-delete" title="Delete conversation">🗑️</button>
                `;

                item.querySelector(".memory-title").addEventListener("click", () => this.loadConversation(c.id));
                item.querySelector(".memory-date").addEventListener("click", () => this.loadConversation(c.id));
                item.querySelector(".memory-delete").addEventListener("click", (e) => {
                    e.stopPropagation();
                    this.deleteConversation(c.id);
                });

                this.listEl.appendChild(item);
            });
        } catch (error) {
            console.error("Failed to load conversations:", error);
            this.listEl.innerHTML = `<li class="memory-empty">⚠️ Couldn't reach the server.</li>`;
        }
    },

    async loadConversation(conversationId, matchContent = null) {
        try {
            const conversation = await Api.getConversation(conversationId);

            chatHistory = [];
            AppState.currentConversationId = conversation.id;
            chatBox.innerHTML = "";

            conversation.messages.forEach((m) => addMessage(m.content, m.sender, false));

            UI.showPanel("chat");
            this.refreshList();

            if (matchContent) {
                // Wait briefly for elements to render
                setTimeout(() => {
                    const messageElements = chatBox.querySelectorAll(".message");
                    for (let msgEl of messageElements) {
                        const bubble = msgEl.querySelector(".bubble");
                        if (bubble && bubble.textContent.trim().includes(matchContent.trim())) {
                            msgEl.scrollIntoView({ behavior: "smooth", block: "center" });
                            msgEl.classList.add("highlighted-message");
                            setTimeout(() => {
                                msgEl.classList.remove("highlighted-message");
                            }, 3000);
                            break;
                        }
                    }
                }, 100);
            }
        } catch (error) {
            console.error("Failed to load conversation:", error);
            alert("Couldn't load that conversation. It may have been deleted.");
        }
    },

    async deleteConversation(conversationId) {
        if (!confirm("Delete this conversation? This can't be undone.")) return;

        try {
            await Api.deleteConversation(conversationId);

            if (AppState.currentConversationId === conversationId) {
                startNewChat();
            }

            this.refreshList();
        } catch (error) {
            console.error("Failed to delete conversation:", error);
            alert("Couldn't delete that conversation.");
        }
    }
};

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
