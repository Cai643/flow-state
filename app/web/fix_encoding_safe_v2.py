# -*- coding: utf-8 -*-
import os

# HTML Content (English version to avoid encoding issues in script)
html_content = """<!DOCTYPE html>
<html lang='zh-CN'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Flow State Assistant</title>
    <style>
        :root {
            --color-bg-light: #fff5cf;
            --color-green-light: #a4bf5a;
            --color-green-dark: #4f6610;
            --color-green-mid: #789035;
            --color-accent-gold: #c9b365;
            --color-text-main: #4f6610;
            --color-text-sub: #789035;
            --color-white: #ffffff;
            --color-hover: #f0f7e6;
        }

        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background-color: var(--color-bg-light);
            color: var(--color-text-main);
            overflow: hidden;
        }

        #app {
            display: flex;
            height: 100vh;
            width: 100vw;
            position: relative;
        }

        /* --- Sidebar --- */
        .sidebar {
            flex: 0 0 60px;
            height: 100%;
            background-color: var(--color-white);
            border-right: 1px solid rgba(164, 191, 90, 0.3);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 20px;
            z-index: 20;
        }
        .sidebar-icon {
            width: 40px;
            height: 40px;
            margin-bottom: 20px;
            border-radius: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s;
            color: var(--color-green-mid);
            position: relative;
        }
        .sidebar-icon:hover, .sidebar-icon.active {
            background-color: var(--color-bg-light);
            color: var(--color-green-dark);
        }
        .sidebar-icon svg {
            width: 24px;
            height: 24px;
            fill: currentColor;
        }

        /* --- Left Panel --- */
        .left-panel {
            flex: 0 0 auto;
            width: 50%;
            height: 100%;
            background-color: var(--color-bg-light);
            display: flex;
            flex-direction: column;
            border-right: 1px solid var(--color-green-light);
            position: relative;
            overflow: hidden;
            min-width: 300px;
            max-width: 80vw;
        }

        /* Search Bar */
        .search-bar-container {
            background-color: var(--color-white);
            padding: 15px 20px;
            border-bottom: 1px solid rgba(164, 191, 90, 0.2);
            display: none; /* JS control */
            animation: slideDown 0.3s ease;
        }
        .search-bar-container.active {
            display: block;
        }
        @keyframes slideDown {
            from { transform: translateY(-100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .search-input-wrapper {
            display: flex;
            align-items: center;
            background-color: var(--color-bg-light);
            border-radius: 20px;
            padding: 8px 15px;
            border: 1px solid transparent;
        }
        .search-input-wrapper:focus-within {
            border-color: var(--color-green-light);
            background-color: var(--color-white);
        }
        .search-input {
            border: none;
            background: transparent;
            flex: 1;
            margin-left: 10px;
            outline: none;
            color: var(--color-green-dark);
        }

        /* History List */
        .history-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .history-header {
            font-size: 20px;
            font-weight: bold;
            color: var(--color-green-dark);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(164, 191, 90, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .history-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .history-item {
            background-color: var(--color-white);
            border-radius: 12px;
            padding: 15px;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 5px rgba(79, 102, 16, 0.05);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            border: 1px solid transparent;
        }
        .history-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(79, 102, 16, 0.1);
            border-color: var(--color-green-light);
        }
        .item-icon {
            width: 40px;
            height: 40px;
            background-color: var(--color-bg-light);
            border-radius: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            margin-right: 15px;
            color: var(--color-green-mid);
            font-weight: bold;
            font-size: 18px;
        }
        .item-content {
            flex: 1;
            overflow: hidden;
        }
        .item-title {
            font-weight: bold;
            color: var(--color-green-dark);
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .item-subtitle {
            font-size: 12px;
            color: var(--color-text-sub);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .item-time {
            background-color: rgba(164, 191, 90, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
        }

        /* --- Settings Modal --- */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.3);
            z-index: 1000;
            display: none;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.active {
            display: flex;
        }
        .settings-modal {
            background-color: var(--color-white);
            width: 400px;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        @keyframes popIn {
            from { transform: scale(0.8); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .settings-header {
            font-size: 20px;
            font-weight: bold;
            color: var(--color-green-dark);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .close-btn {
            cursor: pointer;
            padding: 5px;
            color: var(--color-text-sub);
        }
        .setting-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
        .setting-label {
            color: var(--color-text-main);
        }
        /* Toggle Switch */
        .switch {
            position: relative;
            display: inline-block;
            width: 40px;
            height: 20px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 34px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 2px;
            bottom: 2px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: var(--color-green-mid); }
        input:checked + .slider:before { transform: translateX(20px); }

        /* --- Resizer --- */
        .resizer {
            flex: 0 0 10px;
            background-color: transparent;
            cursor: col-resize;
            position: relative;
            z-index: 100;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 -5px;
        }
        .resizer::before {
            content: '';
            width: 1px;
            height: 100%;
            background-color: var(--color-green-light);
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
        }
        .resizer-handle {
            width: 24px;
            height: 24px;
            background-color: var(--color-white);
            border: 1px solid var(--color-green-light);
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            z-index: 11;
            position: relative;
        }
        .resizer-handle svg {
            width: 12px;
            height: 12px;
            fill: var(--color-green-mid);
        }

        /* --- Right Panel --- */
        .right-panel {
            flex: 1;
            height: 100%;
            background-color: var(--color-white);
            display: flex;
            flex-direction: column;
            position: relative;
            min-width: 300px;
            padding-left: 5px;
        }

        /* --- Chat Area --- */
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background-color: var(--color-white);
        }
        .chat-header {
            padding: 20px;
            border-bottom: 1px solid rgba(164, 191, 90, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-title {
            font-weight: bold;
            font-size: 16px;
            color: var(--color-green-dark);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .chat-title::before {
            content: '';
            display: block;
            width: 8px;
            height: 8px;
            background-color: var(--color-green-light);
            border-radius: 50%;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .message {
            max-width: 70%;
            padding: 15px 20px;
            border-radius: 12px;
            line-height: 1.6;
            position: relative;
        }
        .message.ai {
            align-self: flex-start;
            background-color: var(--color-bg-light); 
            color: var(--color-green-dark);
            border-top-left-radius: 2px;
            border: 1px solid rgba(164, 191, 90, 0.1);
        }
        .message.user {
            align-self: flex-end;
            background-color: var(--color-green-dark);
            color: var(--color-white);
            border-top-right-radius: 2px;
        }
        .input-area {
            padding: 20px 30px;
            border-top: 1px solid rgba(164, 191, 90, 0.2);
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .input-wrapper {
            flex: 1;
            background-color: var(--color-bg-light);
            border-radius: 25px;
            padding: 5px 20px;
            display: flex;
            align-items: center;
            border: 1px solid transparent;
            transition: border 0.2s;
        }
        .input-wrapper:focus-within {
            border-color: var(--color-green-light);
        }
        .input-box {
            flex: 1;
            border: none;
            background: transparent;
            padding: 10px 0;
            outline: none;
            font-size: 14px;
            color: var(--color-green-dark);
        }
        .input-box::placeholder {
            color: var(--color-green-mid);
            opacity: 0.6;
        }
        .send-btn {
            width: 40px;
            height: 40px;
            background-color: var(--color-green-dark);
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .send-btn:hover {
            transform: scale(1.1);
            background-color: var(--color-green-mid);
        }
        .send-btn svg {
            fill: white;
            width: 18px;
            height: 18px;
            margin-left: 2px;
        }
        body.resizing {
            cursor: col-resize;
            user-select: none;
        }
    </style>
</head>
<body>
    <div id='app'>
        
        <!-- Sidebar -->
        <div class='sidebar'>
            <div class='sidebar-icon active' title='History' onclick='switchTab("history")'>
                <svg viewBox='0 0 24 24'><path d='M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z'/></svg>
            </div>
            <div class='sidebar-icon' title='Search' onclick='toggleSearch()'>
                <svg viewBox='0 0 24 24'><path d='M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z'/></svg>
            </div>
            <div class='sidebar-icon' title='Settings' onclick='toggleSettings()'>
                <svg viewBox='0 0 24 24'><path d='M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.04.17 0 .36.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.58 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.04-.22 0-.45-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z'/></svg>
            </div>
        </div>

        <!-- Left Panel: History -->
        <div class='left-panel' id='left-panel'>
            <!-- Search Bar -->
            <div class='search-bar-container' id='search-bar'>
                <div class='search-input-wrapper'>
                    <svg viewBox='0 0 24 24' width='20' height='20' fill='#a4bf5a'><path d='M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z'/></svg>
                    <input type='text' class='search-input' id='history-search-input' placeholder='Search history...' oninput='filterHistory()'>
                </div>
            </div>

            <div class='history-container'>
                <div class='history-header'>
                    <span>Recent 7 Days</span>
                    <span style='font-size: 12px; font-weight: normal; color: #789035;'>Source: Local Monitor</span>
                </div>
                <div class='history-list' id='history-list'>
                    <!-- JS Dynamic -->
                    <div style='text-align: center; color: #789035; margin-top: 50px;'>Loading data...</div>
                </div>
            </div>
        </div>

        <!-- Resizer -->
        <div class='resizer' id='resizer'>
            <div class='resizer-handle'>
                <svg viewBox='0 0 24 24'><path d='M8 19c0 1.1.9 2 2 2h4c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v14zm6-14h2v14h-2V5zM8 5h2v14H8V5z'/></svg>
            </div>
        </div>

        <!-- Right Panel: AI Chat -->
        <div class='right-panel' id='right-panel'>
            <div class='chat-container'>
                <div class='chat-header'>
                    <div class='chat-title'>Flow-State Chat</div>
                    <div style='color: var(--color-green-mid); cursor: pointer;'>
                        <svg viewBox='0 0 24 24' width='20' height='20' fill='currentColor'><path d='M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z'/></svg>
                    </div>
                </div>
                
                <div class='chat-messages' id='chat-messages'>
                    <div class='message ai'>你好！我是你的 Flow-State 助手。这里可以查看你的历史行为数据，也可以和我聊天。</div>
                </div>
                
                <div class='input-area'>
                    <div class='input-wrapper'>
                        <input type='text' class='input-box' id='chat-input' placeholder='询问 Flow-State 助手...'>
                    </div>
                    <div class='send-btn' id='send-btn'>
                        <svg viewBox='0 0 24 24'><path d='M2.01 21L23 12 2.01 3 2 10l15 2-15 2z'/></svg>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Settings Modal -->
    <div class='modal-overlay' id='settings-modal'>
        <div class='settings-modal'>
            <div class='settings-header'>
                <span>Settings</span>
                <span class='close-btn' onclick='toggleSettings()'>&times;</span>
            </div>
            <div class='setting-item'>
                <div class='setting-label'>Auto Record</div>
                <label class='switch'>
                    <input type='checkbox' checked>
                    <span class='slider'></span>
                </label>
            </div>
            <div class='setting-item'>
                <div class='setting-label'>Dark Mode (N/A)</div>
                <label class='switch'>
                    <input type='checkbox' disabled>
                    <span class='slider'></span>
                </label>
            </div>
            <div class='setting-item'>
                <div class='setting-label'>Notifications</div>
                <label class='switch'>
                    <input type='checkbox' checked>
                    <span class='slider'></span>
                </label>
            </div>
            <div style='margin-top: 20px; text-align: right;'>
                <button onclick='toggleSettings()' style='padding: 8px 20px; background: var(--color-green-dark); color: white; border: none; border-radius: 6px; cursor: pointer;'>Save</button>
            </div>
        </div>
    </div>

    <script>
        // --- Drag Logic ---
        const resizer = document.getElementById('resizer');
        const leftPanel = document.getElementById('left-panel');
        const app = document.getElementById('app');
        let isResizing = false;

        resizer.addEventListener('mousedown', function(e) {
            isResizing = true;
            document.body.classList.add('resizing');
        });

        document.addEventListener('mousemove', function(e) {
            if (!isResizing) return;
            const containerWidth = app.offsetWidth;
            const sidebarWidth = 60;
            let newLeftWidth = ((e.clientX - sidebarWidth) / (containerWidth - sidebarWidth)) * 100;
            if (newLeftWidth < 20) newLeftWidth = 20;
            if (newLeftWidth > 80) newLeftWidth = 80;
            leftPanel.style.width = newLeftWidth + '%';
        });

        document.addEventListener('mouseup', function(e) {
            if (isResizing) {
                isResizing = false;
                document.body.classList.remove('resizing');
            }
        });

        // --- Search & Settings ---
        function toggleSearch() {
            const bar = document.getElementById('search-bar');
            bar.classList.toggle('active');
            if(bar.classList.contains('active')) {
                document.getElementById('history-search-input').focus();
            }
        }

        function toggleSettings() {
            const modal = document.getElementById('settings-modal');
            modal.classList.toggle('active');
        }

        document.getElementById('settings-modal').addEventListener('click', function(e) {
            if (e.target === this) {
                toggleSettings();
            }
        });

        // --- History Logic ---
        let allHistoryData = [];

        async function loadHistory() {
            const listEl = document.getElementById('history-list');
            try {
                const response = await fetch('/api/history/recent');
                const data = await response.json();
                allHistoryData = data;
                renderHistory(data);
            } catch (error) {
                console.error('Failed to load history:', error);
                listEl.innerHTML = "<div style='text-align: center; color: red;'>Load Failed</div>";
            }
        }

        function renderHistory(data) {
            const listEl = document.getElementById('history-list');
            if (!data || data.length === 0) {
                listEl.innerHTML = "<div style='text-align: center; color: #789035;'>No Records</div>";
                return;
            }
            
            listEl.innerHTML = data.map(item => {
                const initial = item.app_name ? item.app_name.charAt(0).toUpperCase() : '?';
                const time = item.timestamp ? item.timestamp.split(' ')[1].substring(0, 5) : '--:--';
                
                return `
                <div class='history-item'>
                    <div class='item-icon'>${initial}</div>
                    <div class='item-content'>
                        <div class='item-title' title='${item.window_title || item.app_name}'>${item.window_title || item.app_name}</div>
                        <div class='item-subtitle'>
                            <span class='item-time'>${time}</span>
                            <span style='margin-left: 8px;'>${item.app_name}</span>
                        </div>
                    </div>
                </div>
                `;
            }).join('');
        }

        function filterHistory() {
            const query = document.getElementById('history-search-input').value.toLowerCase();
            const filtered = allHistoryData.filter(item => {
                const title = (item.window_title || '').toLowerCase();
                const app = (item.app_name || '').toLowerCase();
                return title.includes(query) || app.includes(query);
            });
            renderHistory(filtered);
        }

        // Init
        loadHistory();

        // --- Chat Logic ---
        const chatMessages = document.getElementById('chat-messages');
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');

        function addMessage(role, text) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            div.textContent = text;
            chatMessages.appendChild(div);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function handleSend() {
            const text = chatInput.value.trim();
            if (!text) return;
            addMessage('user', text);
            chatInput.value = '';
            
            setTimeout(() => {
                addMessage('ai', '我已收到您的消息：' + text);
            }, 800);
        }

        sendBtn.addEventListener('click', handleSend);
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') handleSend();
        });

    </script>
</body>
</html>
"""

# Avoid raw strings for paths with unicode chars if possible, but here we just need to target the file
target_path = os.path.join(os.getcwd(), 'app', 'web', 'templates', 'index.html')

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Successfully rewrote index.html with UTF-8 encoding")
