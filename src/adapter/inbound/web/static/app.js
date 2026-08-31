document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");
    const typingIndicator = document.getElementById("typing-indicator");
    const errorBanner = document.getElementById("error-banner");

    // Initialize or retrieve session ID
    let sessionId = sessionStorage.getItem("chat_session_id");
    if (!sessionId) {
        sessionId = crypto.randomUUID();
        sessionStorage.setItem("chat_session_id", sessionId);
    }

    // Configure marked options
    if (typeof marked !== "undefined" && marked.setOptions) {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
    }

    function addMessage(content, type, dataQueried = false) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", type);
        
        const contentDiv = document.createElement("div");
        contentDiv.classList.add("message-content");
        
        if (type === "bot-message") {
            // Parse Markdown and sanitize with DOMPurify to prevent DOM-based XSS
            const rawHtml = typeof marked !== "undefined" ? marked.parse(content) : content;
            const cleanHtml = typeof DOMPurify !== "undefined" ? DOMPurify.sanitize(rawHtml, {
                FORBID_TAGS: ["style", "script", "iframe"],
                FORBID_ATTR: ["style", "onerror", "onload"]
            }) : rawHtml;
            contentDiv.innerHTML = cleanHtml;

            // Strip any synthetic/forged verified badges injected in LLM markdown content
            contentDiv.querySelectorAll(".verified-data-badge").forEach(el => el.remove());

            if (dataQueried) {
                const badge = document.createElement("div");
                badge.className = "verified-data-badge";
                badge.setAttribute("role", "status");
                badge.setAttribute("aria-label", "Dados verificados no banco de dados");
                badge.innerHTML = `
                    <svg class="verified-badge-icon" viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    <span>Dados Verificados</span>
                `;
                contentDiv.appendChild(badge);
            }
        } else {
            // Escape user input to prevent XSS
            contentDiv.textContent = content;
        }
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function sendMessage(message) {
        try {
            errorBanner.style.display = "none";
            typingIndicator.style.display = "flex";
            
            // Timeout logic
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout

            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error("API returned an error");
            }

            const data = await response.json();
            
            typingIndicator.style.display = "none";
            
            if (data.status === "error") {
                addMessage("Sorry, I encountered an error: " + data.response, "bot-message", false);
            } else {
                addMessage(data.response, "bot-message", Boolean(data.data_queried));
            }
            
        } catch (error) {
            typingIndicator.style.display = "none";
            errorBanner.style.display = "block";
            
            if (error.name === 'AbortError') {
                errorBanner.textContent = "Request timed out. The model might be taking too long.";
            } else {
                errorBanner.textContent = "Network error. Please try again.";
            }
            console.error("Chat error:", error);
        }
    }

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        
        if (message) {
            addMessage(message, "user-message");
            chatInput.value = "";
            sendMessage(message);
        }
    });
});
