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
    /* ---------- Chat ---------- */

    async sendMessage(message, conversationId, modelName, fileIds = null) {
        const response = await fetch(`${getApiBaseUrl()}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                conversation_id: conversationId ?? null,
                model_name: modelName ?? null,
                file_ids: fileIds ?? null
            })
        });
        return handleResponse(response);
    },

    /* ---------- Memory (conversation history) ---------- */

    async listConversations() {
        const response = await fetch(`${getApiBaseUrl()}/memory/conversations`);
        return handleResponse(response);
    },

    async getConversation(conversationId) {
        const response = await fetch(`${getApiBaseUrl()}/memory/conversations/${conversationId}`);
        return handleResponse(response);
    },

    async deleteConversation(conversationId) {
        const response = await fetch(`${getApiBaseUrl()}/memory/conversations/${conversationId}`, {
            method: "DELETE"
        });
        return handleResponse(response);
    },

    async searchMessages(query) {
        const response = await fetch(`${getApiBaseUrl()}/memory/search?q=${encodeURIComponent(query)}`);
        return handleResponse(response);
    },

    /* ---------- Files ---------- */

    async listFiles() {
        const response = await fetch(`${getApiBaseUrl()}/files`);
        return handleResponse(response);
    },

    async uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${getApiBaseUrl()}/files/upload`, {
            method: "POST",
            body: formData
        });
        return handleResponse(response);
    },

    async deleteFile(fileId) {
        const response = await fetch(`${getApiBaseUrl()}/files/${fileId}`, {
            method: "DELETE"
        });
        return handleResponse(response);
    },

    fileDownloadUrl(fileId) {
        return `${getApiBaseUrl()}/files/${fileId}/download`;
    }
};
