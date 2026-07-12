/* ======================================
   AI NEXUS — API LAYER
   Every fetch() call to the backend lives here so the rest of the
   app never has to know a URL or a status code.
====================================== */

function getApiBaseUrl() {
    return localStorage.getItem("customBackendUrl") || 
        ((window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.protocol === "file:")
        ? "http://127.0.0.1:8000"
        : "https://chatbot-enhanced.onrender.com");
}

function getAuthHeaders(extraHeaders = {}) {
    const token = localStorage.getItem("authToken");
    const headers = { ...extraHeaders };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}

async function handleResponse(response) {
    if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
            const body = await response.json();
            detail = body.detail || body.error || detail;
        } catch (_) {
            // response wasn't JSON — keep the generic message
        }
        throw new Error(detail);
    }
    return response.json();
}

const Api = {
    /* ---------- Authentication ---------- */

    async login(username, password) {
        const response = await fetch(`${getApiBaseUrl()}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        return handleResponse(response);
    },

    async register(username, password) {
        const response = await fetch(`${getApiBaseUrl()}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        return handleResponse(response);
    },

    /* ---------- Chat ---------- */

    async sendMessage(message, conversationId, modelName, fileIds = null) {
        const response = await fetch(`${getApiBaseUrl()}/chat`, {
            method: "POST",
            headers: getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                message,
                conversation_id: conversationId ?? null,
                model_name: modelName ?? null,
                file_ids: fileIds ?? null
            })
        });
        return handleResponse(response);
    },

    async editOrRetryMessage(messageId, message, modelName) {
        const response = await fetch(`${getApiBaseUrl()}/chat/edit`, {
            method: "POST",
            headers: getAuthHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({
                message_id: messageId,
                message,
                model_name: modelName ?? null
            })
        });
        return handleResponse(response);
    },

    /* ---------- Memory (conversation history) ---------- */

    async listConversations() {
        const response = await fetch(`${getApiBaseUrl()}/memory/conversations`, {
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    async getConversation(conversationId) {
        const response = await fetch(`${getApiBaseUrl()}/memory/conversations/${conversationId}`, {
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    async deleteConversation(conversationId) {
        const response = await fetch(`${getApiBaseUrl()}/memory/conversations/${conversationId}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    async searchMessages(query) {
        const response = await fetch(`${getApiBaseUrl()}/memory/search?q=${encodeURIComponent(query)}`, {
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    /* ---------- Files ---------- */

    async listFiles() {
        const response = await fetch(`${getApiBaseUrl()}/files`, {
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    async uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${getApiBaseUrl()}/files/upload`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: formData
        });
        return handleResponse(response);
    },

    async deleteFile(fileId) {
        const response = await fetch(`${getApiBaseUrl()}/files/${fileId}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    async getAdminStats() {
        const response = await fetch(`${getApiBaseUrl()}/admin/stats`, {
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    async deleteUser(userId) {
        const response = await fetch(`${getApiBaseUrl()}/admin/users/${userId}`, {
            method: "DELETE",
            headers: getAuthHeaders()
        });
        return handleResponse(response);
    },

    fileDownloadUrl(fileId) {
        const token = localStorage.getItem("authToken") || "";
        return `${getApiBaseUrl()}/files/${fileId}/download?token=${encodeURIComponent(token)}`;
    }
};
