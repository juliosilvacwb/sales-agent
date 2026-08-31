document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const chatMessages = document.getElementById("chat-messages");
    const typingIndicator = document.getElementById("typing-indicator");
    const errorBanner = document.getElementById("error-banner");
    
    // Status elements
    const agentStatusText = document.getElementById("agent-status-text");
    const statusIndicator = document.querySelector(".status-indicator");

    // Auth elements
    const authBtn = document.getElementById("auth-btn");
    const authBtnLabel = document.getElementById("auth-btn-label");
    const authModal = document.getElementById("auth-modal");
    const modalCloseBtn = document.getElementById("modal-close-btn");
    const loginForm = document.getElementById("login-form");
    const authUsernameInput = document.getElementById("auth-username");
    const authPasswordInput = document.getElementById("auth-password");
    const loginErrorMsg = document.getElementById("login-error-msg");
    const logoutBtn = document.getElementById("logout-btn");
    const loginSubmitBtn = document.getElementById("login-submit-btn");

    // Internal Auth Service URL configuration
    const AUTH_SERVICE_URL = window.AUTH_SERVICE_URL || "http://localhost:8001";

    // Initialize or retrieve session ID
    let sessionId = sessionStorage.getItem("chat_session_id");
    if (!sessionId) {
        sessionId = crypto.randomUUID();
        sessionStorage.setItem("chat_session_id", sessionId);
    }

    let pendingMessage = null;

    // JWT Token Management
    function getJwtToken() {
        return sessionStorage.getItem("jwt_access_token");
    }

    function setJwtToken(token, username) {
        if (token) {
            sessionStorage.setItem("jwt_access_token", token);
            sessionStorage.setItem("jwt_auth_user", username || "admin");
        } else {
            sessionStorage.removeItem("jwt_access_token");
            sessionStorage.removeItem("jwt_auth_user");
        }
        updateAuthUI();
    }

    function updateAuthUI() {
        const token = getJwtToken();
        const username = sessionStorage.getItem("jwt_auth_user") || "admin";
        if (token) {
            authBtn.classList.add("authenticated");
            authBtn.classList.remove("unauthenticated");
            authBtnLabel.textContent = `🔑 ${username}`;
            logoutBtn.style.display = "inline-block";
            loginSubmitBtn.textContent = "Renovar Token";
            if (chatInput) {
                chatInput.disabled = false;
                chatInput.placeholder = "Ask about sales data...";
            }
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.removeAttribute("title");
            }
            if (agentStatusText) {
                agentStatusText.textContent = "Online";
                agentStatusText.classList.add("authenticated");
                agentStatusText.classList.remove("unauthenticated");
            }
            if (statusIndicator) {
                statusIndicator.classList.add("authenticated");
                statusIndicator.classList.remove("unauthenticated");
            }
        } else {
            authBtn.classList.remove("authenticated");
            authBtn.classList.add("unauthenticated");
            authBtnLabel.textContent = "Autenticar";
            logoutBtn.style.display = "none";
            loginSubmitBtn.textContent = "Entrar e Obter Token";
            if (chatInput) {
                chatInput.disabled = true;
                chatInput.placeholder = "Faça login para interagir com o Sales Agent...";
            }
            if (sendBtn) {
                sendBtn.disabled = true;
                sendBtn.title = "Autentique-se para enviar mensagens";
            }
            if (agentStatusText) {
                agentStatusText.textContent = "Não autenticado";
                agentStatusText.classList.add("unauthenticated");
                agentStatusText.classList.remove("authenticated");
            }
            if (statusIndicator) {
                statusIndicator.classList.add("unauthenticated");
                statusIndicator.classList.remove("authenticated");
            }
        }
    }

    function openModal(errorMessage = null) {
        if (errorMessage) {
            loginErrorMsg.textContent = errorMessage;
            loginErrorMsg.style.display = "block";
        } else {
            loginErrorMsg.style.display = "none";
        }
        authModal.style.display = "flex";
        if (authUsernameInput) authUsernameInput.focus();
    }

    function closeModal() {
        authModal.style.display = "none";
        loginErrorMsg.style.display = "none";
    }

    // Modal Event Listeners
    authBtn.addEventListener("click", () => openModal());
    modalCloseBtn.addEventListener("click", closeModal);
    authModal.addEventListener("click", (e) => {
        if (e.target === authModal) {
            closeModal();
        }
    });

    logoutBtn.addEventListener("click", () => {
        setJwtToken(null);
        closeModal();
    });

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        loginErrorMsg.style.display = "none";
        loginSubmitBtn.disabled = true;
        loginSubmitBtn.textContent = "Autenticando...";

        const username = authUsernameInput.value.trim();
        const password = authPasswordInput.value;
        const authUrl = AUTH_SERVICE_URL.replace(/\/+$/, "");

        try {
            const response = await fetch(`${authUrl}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({ detail: "Credenciais inválidas" }));
                throw new Error(errData.detail || "Falha na autenticação");
            }

            const data = await response.json();
            setJwtToken(data.access_token, username);
            closeModal();

            // If there was a pending message, send it now
            if (pendingMessage) {
                const msg = pendingMessage;
                pendingMessage = null;
                sendMessage(msg);
            }
        } catch (err) {
            loginErrorMsg.textContent = err.message || "Erro ao conectar com o serviço de autenticação.";
            loginErrorMsg.style.display = "block";
        } finally {
            loginSubmitBtn.disabled = false;
            updateAuthUI();
        }
    });

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

            const headers = {
                "Content-Type": "application/json"
            };

            const token = getJwtToken();
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const response = await fetch("/chat", {
                method: "POST",
                headers: headers,
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (response.status === 401) {
                typingIndicator.style.display = "none";
                pendingMessage = message;
                setJwtToken(null);
                openModal("Autenticação necessária. Por favor, entre com suas credenciais para continuar.");
                return;
            }

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
        } finally {
            updateAuthUI();
        }
    }

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        if (!getJwtToken()) {
            openModal("Por favor, realize a autenticação antes de enviar mensagens.");
            return;
        }
        const message = chatInput.value.trim();
        
        if (message) {
            addMessage(message, "user-message");
            chatInput.value = "";
            sendMessage(message);
        }
    });

    // Initialize Auth UI state
    updateAuthUI();

    // Automatically prompt authentication modal if no JWT token exists
    if (!getJwtToken()) {
        openModal();
    }
});
