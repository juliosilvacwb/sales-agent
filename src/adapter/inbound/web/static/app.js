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
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    function addMessage(content, type) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", type);
        
        const contentDiv = document.createElement("div");
        contentDiv.classList.add("message-content");
        
        if (type === "bot-message") {
            // Parse Markdown for bot messages
            contentDiv.innerHTML = marked.parse(content);
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
                addMessage("Sorry, I encountered an error: " + data.response, "bot-message");
            } else {
                addMessage(data.response, "bot-message");
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
