// --- SESSION ID LOGIC ---
function generateSessionId() {
    return 'session-' + ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}
let sessionId = localStorage.getItem('session_id');
if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem('session_id', sessionId);
}
// --- HISTORIAL DE CONVERSACIONES ---
async function loadConversationList() {
    const resp = await fetch('/conversations');
    if (!resp.ok) return;
    const conversations = await resp.json();
    const listUl = document.getElementById('conversation-list');
    listUl.innerHTML = '';
    conversations.forEach(conv => {
        const li = document.createElement('li');
        li.className = 'conversation-item' + (conv.session_id === sessionId ? ' selected' : '');
        li.innerHTML = `<span class="conv-title">${conv.last_message ? conv.last_message.substring(0, 40) : '(Sin mensaje)'}</span>
                        <span class="conv-date">${new Date(conv.datetime).toLocaleString()}</span>`;
        li.onclick = () => {
            if (sessionId !== conv.session_id) {
                sessionId = conv.session_id;
                localStorage.setItem('session_id', sessionId);
                loadConversationMessages(sessionId);
                loadConversationList();
            }
            // Cierra el sidebar si está en móvil
            if (window.innerWidth <= 600) closeSidebar();
        };
        listUl.appendChild(li);
    });
}
async function loadConversationMessages(sessionIdToLoad) {
    const resp = await fetch(`/conversation/${encodeURIComponent(sessionIdToLoad)}`);
    if (!resp.ok) return;
    const messages = await resp.json();
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = '';
    messages.forEach(msg => {
        const div = document.createElement('div');
        div.className = msg.role === 'user' ? 'user' : 'bot';
        // Mostrar texto
        div.innerHTML = formatResponse(cleanResponse(msg.text));
        // Mostrar imágenes si existen (solo para mensajes del bot)
        if (
            msg.role === 'bot' &&
            msg.images &&
            Array.isArray(msg.images) &&
            msg.images.length > 0
        ) {
            msg.images.forEach(url => {
                const imgContainer = document.createElement('div');
                imgContainer.className = "img-container-chat";
                const imgElem = document.createElement('img');
                imgElem.src = url;
                imgElem.alt = "Imagen generada";
                imgElem.className = "generated-image";
                imgElem.style.cursor = "pointer";
                imgElem.onerror = function() {
                    const errorMsg = document.createElement('div');
                    errorMsg.style.color = "#c00";
                    errorMsg.style.fontSize = "13px";
                    errorMsg.textContent = "No se pudo cargar la imagen. ";
                    const link = document.createElement('a');
                    link.href = url;
                    link.textContent = "Abrir imagen en nueva pestaña";
                    link.target = "_blank";
                    errorMsg.appendChild(link);
                    imgContainer.appendChild(errorMsg);
                };
                imgElem.onclick = () => showImageModal(url);
                imgContainer.appendChild(imgElem);
                div.appendChild(imgContainer);
            });
        }
        chatMessages.appendChild(div);
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
// Nuevo chat
document.getElementById('new-chat-btn').addEventListener('click', function() {
    sessionId = generateSessionId();
    localStorage.setItem('session_id', sessionId);
    document.getElementById('chat-messages').innerHTML = '';
    loadConversationList();
    // Cierra el sidebar si está en móvil
    if (window.innerWidth <= 600) closeSidebar();
});
// --- CHAT LOGIC ---
async function sendMessage() {
    const userInput = document.getElementById('user-input').value;
    if (!userInput.trim()) return;
    sendToChat(userInput);
}
async function sendToChat(userInput) {
    const messagesDiv = document.getElementById('chat-messages');
    const userInputElem = document.getElementById('user-input');
    userInputElem.disabled = true; // Deshabilita input mientras responde el bot
    // Display user message
    const userMessage = document.createElement('div');
    userMessage.className = 'user';
    userMessage.textContent = userInput;
    messagesDiv.appendChild(userMessage);
    userInputElem.value = '';
    // Display bot placeholder (animated dots)
    const botMessage = document.createElement('div');
    botMessage.className = 'bot';
    const dots = document.createElement('div');
    dots.className = 'dots';
    dots.innerHTML = '<span>.</span><span>.</span><span>.</span>';
    botMessage.appendChild(dots);
    messagesDiv.appendChild(botMessage);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    let apiUrl = '/chat';
    if (
        location.protocol === 'file:' ||
        (location.hostname === 'localhost' && location.port !== '')
    ) {
        apiUrl = 'http://localhost:8000/chat';
    }
    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pregunta: userInput, session_id: sessionId }),
        });
        if (!response.ok) {
            let errorText = await response.text();
            throw new Error('Error del servidor: ' + errorText);
        }
        const data = await response.json();
        botMessage.innerHTML = formatResponse(cleanResponse(data.respuesta));
        // Mostrar imágenes si existen
        if (data.imagenes && Array.isArray(data.imagenes) && data.imagenes.length > 0) {
            data.imagenes.forEach((url, idx) => {
                const imgContainer = document.createElement('div');
                imgContainer.className = "img-container-chat";
                const imgElem = document.createElement('img');
                imgElem.src = url;
                imgElem.alt = "Imagen generada";
                imgElem.className = "generated-image";
                imgElem.style.cursor = "pointer";
                imgElem.onerror = function() {
                    const errorMsg = document.createElement('div');
                    errorMsg.style.color = "#c00";
                    errorMsg.style.fontSize = "13px";
                    errorMsg.textContent = "No se pudo cargar la imagen. ";
                    const link = document.createElement('a');
                    link.href = url;
                    link.textContent = "Abrir imagen en nueva pestaña";
                    link.target = "_blank";
                    errorMsg.appendChild(link);
                    imgContainer.appendChild(errorMsg);
                };
                imgElem.onclick = () => showImageModal(url);
                imgContainer.appendChild(imgElem);
                botMessage.appendChild(imgContainer);
            });
        }
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        loadConversationList();
    } catch (error) {
        console.error(error);
        botMessage.textContent = 'Error: ' + error.message;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } finally {
        userInputElem.disabled = false; // Habilita input después de la respuesta del bot
        userInputElem.focus();
    }
}
// Enter para enviar
document.getElementById('user-input').addEventListener('keydown', function (event) {
    if (event.key === 'Enter') sendMessage();
});
// Modal para ver imagen grande (deja esto al final del body si no existe)
if (!document.getElementById('image-modal')) {
    const modalHtml = `
        <div class="image-modal" id="image-modal" style="display:none;position:fixed;z-index:2000;left:0;top:0;width:100vw;height:100vh;background:rgba(0,0,0,0.7);align-items:center;justify-content:center;">
            <span class="close-modal" onclick="closeImageModal();" style="position:absolute;top:30px;right:40px;font-size:2.5em;color:#fff;cursor:pointer;z-index:2100;font-weight:bold;text-shadow:0 2px 8px #000;">&times;</span>
            <img id="modal-img" src="" alt="Imagen ampliada" style="max-width:95vw;max-height:85vh;border-radius:14px;box-shadow:0 4px 24px rgba(0,0,0,0.25);background:#fff;padding:10px;">
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function showImageModal(url) {
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    modal.style.display = 'flex';
    modalImg.src = url;
}
function closeImageModal() {
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    modal.style.display = 'none';
    modalImg.src = '';
}
// Logout
document.getElementById('logout-link').addEventListener('click', function(e) {
    e.preventDefault();
    const sessionId = localStorage.getItem('session_id');
    window.location.href = `/logout${sessionId ? '?session_id=' + encodeURIComponent(sessionId) : ''}`;
});
// Utilidades de formato
function formatResponse(response) {
    // Encabezados tipo Markdown
    let formatted = response
        .replace(/^### (.*)$/gm, '<strong style="display:block;margin-top:14px;font-size:1.1em;">$1</strong>')
        .replace(/^## (.*)$/gm, '<strong style="display:block;margin-top:18px;font-size:1.18em;">$1</strong>')
        .replace(/^# (.*)$/gm, '<strong style="display:block;margin-top:22px;font-size:1.25em;">$1</strong>');
    // Listas
    formatted = formatted.replace(/^- (.*)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/^\d+\.\s(.*)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)+/gs, match => {
        return match.match(/^\d+\./m) ? `<ol>${match}</ol>` : `<ul>${match}</ul>`;
    });
    // Negritas markdown
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Saltos de línea
    formatted = formatted.replace(/\n{2,}/g, '<br><br>');
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}
function cleanResponse(response) {
    return response.replace(/【.*?†source】/g, '').trim();
}
// Inicialización
window.addEventListener('DOMContentLoaded', function () {
    loadConversationList().then(() => {
        loadConversationMessages(sessionId);
    });
    var yearSpan = document.getElementById('footer-year');
    if (yearSpan) { yearSpan.textContent = new Date().getFullYear(); }
    var userDisplay = document.getElementById('user-display');
    // Obtén el username real desde un atributo data-username en el HTML
    if (userDisplay) {
        const realUsername = userDisplay.getAttribute('data-username');
        if (realUsername) {
            userDisplay.textContent = "Usuario: " + realUsername;
        }
    }
});

// Sidebar responsive toggle
const sidebar = document.getElementById('sidebar');
const sidebarBackdrop = document.getElementById('sidebar-backdrop');
const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
const sidebarCloseBtn = document.getElementById('sidebar-close-btn');

function openSidebar() {
    // Solo muestra el sidebar en móvil
    if (window.innerWidth <= 600) {
        sidebar.classList.add('open');
        sidebarBackdrop.classList.add('active');
        sidebarCloseBtn.style.display = 'block';
    }
}
function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarBackdrop.classList.remove('active');
    sidebarCloseBtn.style.display = 'none';
}
sidebarToggleBtn.addEventListener('click', openSidebar);
sidebarBackdrop.addEventListener('click', closeSidebar);
sidebarCloseBtn.addEventListener('click', closeSidebar);

// Oculta la X si cambia el tamaño de pantalla a escritorio
window.addEventListener('resize', function() {
    if (window.innerWidth > 600) sidebarCloseBtn.style.display = 'none';
});
// Al cargar la página, asegúrate de que el sidebar esté oculto en móvil
window.addEventListener('DOMContentLoaded', function () {
    var yearSpan = document.getElementById('footer-year');
    if (yearSpan) { yearSpan.textContent = new Date().getFullYear(); }
    var userDisplay = document.getElementById('user-display');
    // Obtén el username real desde un atributo data-username en el HTML
    if (userDisplay) {
        const realUsername = userDisplay.getAttribute('data-username');
        if (realUsername) {
            userDisplay.textContent = "Usuario: " + realUsername;
        }
    }
    if (window.innerWidth <= 600) {
        sidebar.classList.remove('open');
        sidebarBackdrop.classList.remove('active');
        sidebarCloseBtn.style.display = 'none';
    }
});
