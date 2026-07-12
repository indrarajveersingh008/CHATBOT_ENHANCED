/* ======================================
   AI NEXUS — BOOTSTRAP
   Runs once the page has loaded: restores the last local chat
   (a quick cache so a refresh doesn't lose the current thread)
   and wires up the Memory panel's server-backed list.
====================================== */

console.log("AI Nexus script loaded");

window.addEventListener("load", function () {
    chatBox.innerHTML = "";

    const token = localStorage.getItem("authToken");
    if (!token) {
        return;
    }

    if (chatHistory.length > 0) {
        chatHistory.forEach((msg) => addMessage(msg.text, msg.sender, false, msg.files));
    } else {
        addMessage(
            "👋 Hello! I'm AI Nexus. How can I help you today?",
            "bot",
            false
        );
    }

    Memory.init();
    messageInput.focus();
});
