/* ======================================
   AI NEXUS — VOICE
   Smart Awake ("Hi Nexus") + Manual Voice Input.
====================================== */

const Voice = {
    recognition: null,
    listening: false,
    waitingForCommand: false,
    smartAwakeEnabled: false,

    init() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            voiceBtn?.addEventListener("click", () => {
                alert("Speech Recognition is not supported in this browser.");
            });
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.lang = "en-US";
        this.recognition.continuous = true;
        this.recognition.interimResults = false;

        // Load setting from localStorage
        this.smartAwakeEnabled = localStorage.getItem("smartAwake") === "true";

        // Bind manual voice button
        voiceBtn?.addEventListener("click", () => {
            if (this.listening) {
                this.stopManual();
            } else {
                this.startManual();
            }
        });

        // Setup recognition handlers
        this.recognition.onstart = () => {
            this.listening = true;
            this.updateButtonUI();
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript
                .toLowerCase()
                .trim();

            console.log("Speech recognition heard:", transcript);

            // Case A: Heard Wake Word ("hi nexus" or "hey nexus")
            if (!this.waitingForCommand && (transcript.includes("hi nexus") || transcript.includes("hey nexus"))) {
                this.waitingForCommand = true;
                this.updateButtonUI();
                this.speak("Hello, how can I help you?");
                return;
            }

            // Case B: In Command Listening State -> Receive and send command
            if (this.waitingForCommand) {
                messageInput.value = transcript;
                this.waitingForCommand = false;
                this.updateButtonUI();
                
                // Trigger message send
                sendMessage();
            }
        };

        this.recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
        };

        this.recognition.onend = () => {
            this.listening = false;
            this.waitingForCommand = false;
            this.updateButtonUI();

            // Auto-restart if Smart Awake is enabled
            if (this.smartAwakeEnabled) {
                setTimeout(() => {
                    try {
                        this.recognition.start();
                    } catch (e) {
                        // Already started
                    }
                }, 400);
            }
        };

        // Enable Smart Awake if saved
        if (this.smartAwakeEnabled) {
            // Require user click to satisfy browser security gesture policies
            const startOnInteraction = () => {
                this.startSmartAwake();
                document.removeEventListener("click", startOnInteraction);
            };
            document.addEventListener("click", startOnInteraction);
        }
    },

    startManual() {
        // Disable smart awake temporarily
        this.smartAwakeEnabled = false;
        localStorage.setItem("smartAwake", "false");
        const toggle = document.getElementById("smartAwakeToggle");
        if (toggle) toggle.checked = false;

        try {
            this.recognition.stop();
        } catch (e) {}

        setTimeout(() => {
            try {
                this.waitingForCommand = true; // Directly wait for command
                this.recognition.start();
            } catch (e) {}
        }, 300);
    },

    stopManual() {
        try {
            this.recognition.stop();
        } catch (e) {}
    },

    startSmartAwake() {
        this.smartAwakeEnabled = true;
        localStorage.setItem("smartAwake", "true");
        this.waitingForCommand = false;
        try {
            this.recognition.start();
        } catch (e) {
            // Already started
        }
        this.updateButtonUI();
    },

    stopSmartAwake() {
        this.smartAwakeEnabled = false;
        localStorage.setItem("smartAwake", "false");
        try {
            this.recognition.stop();
        } catch (e) {}
        this.updateButtonUI();
    },

    updateButtonUI() {
        if (!voiceBtn) return;
        if (this.waitingForCommand) {
            voiceBtn.innerHTML = "🟢"; // Listening for actual query/command
            voiceBtn.title = "Listening for query...";
        } else if (this.listening) {
            voiceBtn.innerHTML = "🎙️"; // Smart awake / listening for wake word
            voiceBtn.title = this.smartAwakeEnabled ? "Smart Awake listening..." : "Listening...";
        } else {
            voiceBtn.innerHTML = "🎤"; // Idle
            voiceBtn.title = "Voice Input";
        }
    },

    speak(text) {
        const speakEnabled = localStorage.getItem("voiceResponse") !== "false";
        if (speakEnabled && 'speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            speechSynthesis.speak(utterance);
        }
    }
};

document.addEventListener("DOMContentLoaded", () => Voice.init());
