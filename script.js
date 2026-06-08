// د HIA AI فرنټاینډ جاوااسکریپټ

let sessionId = localStorage.getItem('sessionId') || generateSessionId();
let currentTheme = localStorage.getItem('theme') || 'light';
let currentMessages = [];

function generateSessionId() {
    const id = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('sessionId', id);
    return id;
}

// د تیم تبادله
function initTheme() {
    if (currentTheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        document.getElementById('themeToggle').innerHTML = '<i class="fas fa-sun"></i>';
    }
}

function toggleTheme() {
    if (currentTheme === 'light') {
        currentTheme = 'dark';
        document.body.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        document.getElementById('themeToggle').innerHTML = '<i class="fas fa-sun"></i>';
    } else {
        currentTheme = 'light';
        document.body.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        document.getElementById('themeToggle').innerHTML = '<i class="fas fa-moon"></i>';
    }
}

// د پیغام اضافه کول
function addMessage(question, answer, isUser = true) {
    const messagesDiv = document.getElementById('messages');
    const welcomeDiv = messagesDiv.querySelector('.welcome');
    if (welcomeDiv && currentMessages.length === 0) {
        welcomeDiv.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'ai'}`;
    
    if (isUser) {
        messageDiv.innerHTML = `
            <div class="message-avatar">👤</div>
            <div class="message-content">${escapeHtml(question)}</div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <img src="https://i.postimg.cc/g2Fdxx5v/file-00000000763c720c968a945c70f95511.png" alt="HIA AI">
            </div>
            <div class="message-content">${formatAnswer(answer)}</div>
        `;
    }
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    currentMessages.push({ role: isUser ? 'user' : 'ai', content: isUser ? question : answer });
    saveMessages();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatAnswer(text) {
    return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
               .replace(/\n/g, '<br>');
}

// د AI څخه ځواب ترلاسه کول
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const question = input.value.trim();
    
    if (!question) return;
    
    addMessage(question, '', true);
    input.value = '';
    input.style.height = 'auto';
    
    showTyping(true);
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, session_id: sessionId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessage(question, data.answer, false);
        } else {
            addMessage(question, 'Sorry, an error occurred. Please try again.', false);
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage(question, 'Network error. Please check your connection.', false);
    } finally {
        showTyping(false);
    }
}

function showTyping(show) {
    document.getElementById('typingIndicator').style.display = show ? 'flex' : 'none';
}

// د تاریخ راوړل
async function loadHistory() {
    try {
        const response = await fetch(`/api/history?session_id=${sessionId}`);
        const data = await response.json();
        
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = '';
        
        if (data.history && data.history.length > 0) {
            data.history.slice(0, 10).forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.textContent = item.user_question.substring(0, 50);
                div.onclick = () => {
                    document.getElementById('messageInput').value = item.user_question;
                    sendMessage();
                };
                historyList.appendChild(div);
            });
        } else {
            historyList.innerHTML = '<div style="text-align:center;color:var(--text-light);">No history yet</div>';
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// د احصایې راوړل
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        const data = await response.json();
        
        const statsBody = document.getElementById('statsBody');
        if (data.success && data.statistics) {
            statsBody.innerHTML = `
                <div class="stat-card">
                    <h3>${data.statistics.total_knowledge || 0}</h3>
                    <p>Saved Knowledge Items</p>
                </div>
                <div class="stat-card">
                    <h3>${data.statistics.total_conversations || 0}</h3>
                    <p>Total Conversations</p>
                </div>
                <div class="stat-card">
                    <h3>${data.statistics.memory_usage || '0 KB'}</h3>
                    <p>Memory Usage</p>
                </div>
            `;
        } else {
            statsBody.innerHTML = '<div class="loading">No data available</div>';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('statsBody').innerHTML = '<div class="loading">Error loading stats</div>';
    }
}

// د پوهې راوړل
async function loadKnowledge() {
    try {
        const response = await fetch('/api/knowledge');
        const data = await response.json();
        
        const knowledgeBody = document.getElementById('knowledgeBody');
        if (data.success && data.knowledge && data.knowledge.length > 0) {
            knowledgeBody.innerHTML = data.knowledge.map(item => `
                <div class="knowledge-item">
                    <h4>❓ ${escapeHtml(item.question.substring(0, 80))}</h4>
                    <p>💡 ${escapeHtml(item.answer.substring(0, 120))}${item.answer.length > 120 ? '...' : ''}</p>
                    <small>🔄 Used ${item.usage_count} times · ${item.ai_provider}</small>
                </div>
            `).join('');
        } else {
            knowledgeBody.innerHTML = '<div class="loading">No knowledge stored yet. Start chatting!</div>';
        }
    } catch (error) {
        console.error('Error loading knowledge:', error);
        document.getElementById('knowledgeBody').innerHTML = '<div class="loading">Error loading knowledge</div>';
    }
}

// د پیغامونو خوندي کول
function saveMessages() {
    localStorage.setItem(`messages_${sessionId}`, JSON.stringify(currentMessages));
}

function loadMessages() {
    const saved = localStorage.getItem(`messages_${sessionId}`);
    if (saved) {
        const messages = JSON.parse(saved);
        messages.forEach(msg => {
            addMessage(msg.content, msg.content, msg.role === 'user');
        });
    }
}

// نوی چت
function newChat() {
    sessionId = generateSessionId();
    currentMessages = [];
    document.getElementById('messages').innerHTML = `
        <div class="welcome">
            <div class="welcome-icon">
                <img src="https://i.postimg.cc/g2Fdxx5v/file-00000000763c720c968a945c70f95511.png" alt="HIA AI">
            </div>
            <h2>HIA AI ته ښه راغلاست</h2>
            <p>زه ستاسو هوښیار مرستیال یم چې حافظه لرم. ما سره په پښتو، دري یا انګلیسي کې خبرې وکړئ!</p>
            <div class="examples">
                <button class="example">What is Artificial Intelligence?</button>
                <button class="example">Who are you?</button>
                <button class="example">Tell me about HIA AI</button>
                <button class="example">سلام! ته څنګه یې؟</button>
            </div>
        </div>
    `;
    loadHistory();
}

// پینلونه
function openPanel(panelId) {
    document.getElementById(panelId).classList.add('open');
}

function closePanel(panelId) {
    document.getElementById(panelId).classList.remove('open');
}

// د انپټ اندازه تنظیمول
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// د پیغام لیږل د Enter سره
function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

// ایونټ لیسینرونه
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadHistory();
    
    document.getElementById('themeToggle').onclick = toggleTheme;
    document.getElementById('sendBtn').onclick = sendMessage;
    document.getElementById('menuToggle').onclick = () => document.getElementById('sidebar').classList.add('open');
    document.getElementById('closeSidebar').onclick = () => document.getElementById('sidebar').classList.remove('open');
    document.getElementById('newChat').onclick = newChat;
    document.getElementById('statsBtn').onclick = () => { loadStatistics(); openPanel('statsPanel'); };
    document.getElementById('knowledgeBtn').onclick = () => { loadKnowledge(); openPanel('knowledgePanel'); };
    document.getElementById('closeStats').onclick = () => closePanel('statsPanel');
    document.getElementById('closeKnowledge').onclick = () => closePanel('knowledgePanel');
    
    document.getElementById('messageInput').oninput = function() { autoResize(this); };
    document.getElementById('messageInput').onkeydown = handleKeyPress;
    
    document.querySelectorAll('.example').forEach(btn => {
        btn.onclick = () => {
            document.getElementById('messageInput').value = btn.textContent;
            sendMessage();
        };
    });
});