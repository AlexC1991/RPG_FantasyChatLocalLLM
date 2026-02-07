document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentFantasyId = null;
    let fantasies = [];

    // DOM Elements
    const elFantasyList = document.getElementById('fantasy-list');
    const elChatWindow = document.getElementById('chat-window');
    const elUserInput = document.getElementById('user-input');
    const elBtnSend = document.getElementById('btn-send');
    const elTitle = document.getElementById('current-fantasy-title');
    const elBtnNewFantasy = document.getElementById('btn-new-fantasy');
    const elBtnEditFantasy = document.getElementById('btn-edit-fantasy');
    const elModalFantasy = document.getElementById('modal-fantasy');
    const elModalSettings = document.getElementById('modal-settings');
    const elBtnGlobalSettings = document.getElementById('btn-global-settings');
    const elCloseModals = document.querySelectorAll('.close-modal');
    const elFormFantasy = document.getElementById('form-fantasy');
    const elBtnDelete = document.getElementById('btn-delete-fantasy');
    const elModelSelect = document.getElementById('fantasy-model');
    const elTempInput = document.getElementById('fantasy-temp');
    const elTempVal = document.getElementById('temp-val');
    const elThemeSelect = document.getElementById('fantasy-theme');
    const elBtnReset = document.getElementById('btn-reset-chat');

    console.log("VOX-AI App Initializing...");

    // Check critical elements
    if (!elBtnNewFantasy || !elBtnReset) {
        console.error("Critical DOM elements missing!");
        return;
    }

    // --- INITIALIZATION ---
    fetchFantasies();
    fetchModels();
    loadSettings();

    // --- EVENT LISTENERS ---
    elBtnNewFantasy.addEventListener('click', () => openFantasyModal());
    
    if (elBtnEditFantasy) {
        elBtnEditFantasy.addEventListener('click', () => {
            const fantasy = fantasies.find(f => f.id === currentFantasyId);
            if (fantasy) openFantasyModal(fantasy);
        });
    }

    elBtnReset.addEventListener('click', async () => {
        if (confirm("Are you sure you want to clear the chat history? This cannot be undone.")) {
            await clearChat();
        }
    });

    elCloseModals.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.modal').classList.add('hidden');
        });
    });

    window.addEventListener('click', (e) => {
        if (e.target === elModalFantasy) closeFantasyModal();
        if (e.target === elModalSettings) closeSettingsModal();
    });

    elTempInput.addEventListener('input', (e) => elTempVal.textContent = e.target.value);

    elFormFantasy.addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveFantasy();
    });

    elBtnDelete.addEventListener('click', async () => {
        if (confirm("Are you sure you want to delete this fantasy?")) {
            await deleteFantasy();
        }
    });

    elBtnSend.addEventListener('click', sendMessage);
    elUserInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    if (elBtnGlobalSettings) {
        elBtnGlobalSettings.addEventListener('click', openSettingsModal);
    }

    // --- SETTINGS MODAL FUNCTIONS (DEFINED EARLY) ---
    async function openSettingsModal() {
        elModalSettings.classList.remove('hidden');
        await loadSettings();
        await fetchStats();
    }

    function closeSettingsModal() {
        elModalSettings.classList.add('hidden');
    }

    async function loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const settings = await res.json();
            
            document.getElementById('archive-path').value = settings.archive_path || './context_archive';
            document.getElementById('max-archive-size').value = settings.max_archive_size_mb || 100;
            document.getElementById('context-window-size').value = settings.context_window_size || 4096;
            document.getElementById('enable-rag').checked = settings.enable_rag !== false;
            document.getElementById('rag-retrieve-count').value = settings.rag_retrieve_count || 5;
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    async function saveSettings() {
        const settings = {
            archive_path: document.getElementById('archive-path').value,
            max_archive_size_mb: parseInt(document.getElementById('max-archive-size').value),
            context_window_size: parseInt(document.getElementById('context-window-size').value),
            enable_rag: document.getElementById('enable-rag').checked,
            rag_retrieve_count: parseInt(document.getElementById('rag-retrieve-count').value)
        };

        try {
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            
            alert('Settings saved! Please restart the server for changes to take effect.');
            closeSettingsModal();
        } catch (error) {
            console.error('Error saving settings:', error);
            alert('Error saving settings. See console for details.');
        }
    }

    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            const stats = await res.json();
            
            if (stats.error) {
                document.getElementById('stats-display').textContent = stats.error;
                return;
            }
            
            let statsText = '';
            statsText += `Model: ${stats.model || 'Not loaded'}\n`;
            statsText += `Messages Processed: ${stats.messages_processed || 0}\n`;
            statsText += `Context Usage: ${stats.context_tokens_used || 0} / ${stats.context_size || 0} tokens\n`;
            statsText += `GPU Layers: ${stats.gpu_layers || 0}\n`;
            statsText += `Archive Size: ${(stats.archive_size_mb || 0).toFixed(2)} MB\n`;
            statsText += `RAG Enabled: ${stats.rag_enabled ? 'Yes' : 'No'}\n`;
            
            document.getElementById('stats-display').textContent = statsText;
        } catch (error) {
            console.error('Error fetching stats:', error);
            document.getElementById('stats-display').textContent = 'Error loading statistics';
        }
    }

    // Make functions available globally for onclick handlers
    window.openSettingsModal = openSettingsModal;
    window.closeSettingsModal = closeSettingsModal;
    window.saveSettings = saveSettings;

    // --- API CALLS ---

    async function fetchFantasies() {
        const res = await fetch('/api/fantasies');
        fantasies = await res.json();
        renderFantasyList();
    }

    async function fetchModels() {
        const res = await fetch('/api/models');
        const models = await res.json();

        elModelSelect.innerHTML = '<option value="default">Default (System Config)</option>';

        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;

            let displayName = model.replace(/\.gguf$/i, '');

            if (model.toLowerCase().includes('dolphin')) {
                displayName = `🔓 ${displayName} (Unrestricted)`;
                option.style.color = "#d9534f";
                option.style.fontWeight = "bold";
            } else {
                displayName = `🛡️ ${displayName} (Safe)`;
                option.style.color = "#5cb85c";
            }

            option.textContent = displayName;
            elModelSelect.appendChild(option);
        });
    }

    async function saveFantasy() {
        const title = document.getElementById('fantasy-title').value;
        const desc = document.getElementById('fantasy-desc').value;
        const prompt = document.getElementById('fantasy-prompt').value;
        const startingPrompt = document.getElementById('fantasy-starting-prompt').value;
        const id = document.getElementById('fantasy-id').value;
        const model = elModelSelect.value;
        const temp = parseFloat(elTempInput.value);
        const theme = elThemeSelect.value || 'default';
        const userName = document.getElementById('fantasy-user-name').value;
        const aiName = document.getElementById('fantasy-ai-name').value;

        const payload = {
            id: id || null,
            title,
            description: desc,
            system_prompt: prompt,
            starting_prompt: startingPrompt,
            model_config: { model, temperature: temp },
            theme: theme,
            user_name: userName,
            ai_name: aiName,
            history: []
        };

        if (id) {
            const existing = fantasies.find(f => f.id === id);
            if (existing) payload.history = existing.history || [];
        }

        const res = await fetch('/api/fantasies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        closeFantasyModal();
        await fetchFantasies();

        if (!id) selectFantasy(data.id);
        if (currentFantasyId === data.id) selectFantasy(data.id);
    }

    async function deleteFantasy() {
        const id = document.getElementById('fantasy-id').value;
        await fetch(`/api/fantasies/${id}`, { method: 'DELETE' });
        closeFantasyModal();
        currentFantasyId = null;
        elTitle.textContent = "Select a Fantasy...";
        elChatWindow.innerHTML = '<div class="chat-placeholder"><p>Select a fantasy card from the library to begin your adventure.</p></div>';
        toggleInput(false);
        elBtnEditFantasy.style.display = 'none';
        document.getElementById('btn-reset-chat').style.display = 'none';

        document.querySelector('.book-container').className = 'book-container';

        await fetchFantasies();
    }

    async function sendMessage() {
        const text = elUserInput.value.trim();
        if (!text) return;

        addMessageToChat('user', text);
        elUserInput.value = '';

        const fantasy = fantasies.find(f => f.id === currentFantasyId);

        if (!fantasy.history) fantasy.history = [];
        fantasy.history.push({ role: "user", content: text });

        const bubble = addMessageToChat('ai', '...');
        let fullResponse = "";

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    history: fantasy.history,
                    system_prompt: fantasy.system_prompt,
                    model_config: fantasy.model_config,
                    user_name: fantasy.user_name,
                    ai_name: fantasy.ai_name,
                    fantasy_id: fantasy.id
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            bubble.innerHTML = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                fullResponse += chunk;
                bubble.innerHTML = formatMessage(fullResponse);
                elChatWindow.scrollTop = elChatWindow.scrollHeight;
            }

            fantasy.history.push({ role: "assistant", content: fullResponse });
            silentSave(fantasy);

        } catch (err) {
            bubble.textContent = "[Error: " + err.message + "]";
        }
    }

    async function clearChat() {
        if (!currentFantasyId) return;

        try {
            elChatWindow.innerHTML = '';

            const fantasy = fantasies.find(f => f.id === currentFantasyId);
            if (fantasy) {
                fantasy.history = [];
                await silentSave(fantasy);
            }

            await fetch('/api/reset', { method: 'POST' });

            elChatWindow.innerHTML = '<div class="chat-placeholder"><p>The story begins anew...</p></div>';

            console.log("Chat cleared successfully.");
        } catch (e) {
            console.error("Failed to clear chat:", e);
            alert("Error clearing chat. See console.");
        }
    }

    async function silentSave(fantasy) {
        await fetch('/api/fantasies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(fantasy)
        });
    }

    // --- INITIAL AI MESSAGE ---
    async function requestInitialMessage() {
        if (!currentFantasyId) return;
        
        const fantasy = fantasies.find(f => f.id === currentFantasyId);
        if (!fantasy) return;

        const requestBody = {
            system_prompt: fantasy.system_prompt || "",
            user_name: fantasy.user_name || "User",
            ai_name: fantasy.ai_name || "AI",
            starting_prompt: fantasy.starting_prompt || "",
            model_config: {
                model: fantasy.model_config?.model || 'default',
                temperature: parseFloat(fantasy.model_config?.temperature) || 0.7
            },
            fantasy_id: fantasy.id
        };

        try {
            const response = await fetch('/api/initial-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) throw new Error('Initial message request failed');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedText = '';

            const bubble = addMessageToChat('ai', '');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                accumulatedText += chunk;

                bubble.innerHTML = formatMessage(accumulatedText);
                elChatWindow.scrollTop = elChatWindow.scrollHeight;
            }

            fantasy.history = [{ role: 'assistant', content: accumulatedText }];
            await silentSave(fantasy);

        } catch (error) {
            console.error('Error getting initial message:', error);
            elChatWindow.innerHTML = '<div class="chat-placeholder"><p>Failed to start story. Please try again.</p></div>';
        }
    }

    // --- UI HELPERS ---

    function renderFantasyList() {
        elFantasyList.innerHTML = '';
        fantasies.forEach(f => {
            const div = document.createElement('div');
            div.className = `fantasy-item ${f.id === currentFantasyId ? 'active' : ''}`;
            div.innerHTML = `
                <div class="f-title">${f.title}</div>
                <div class="f-desc" style="font-size:0.8em; color:#666;">${f.description.substring(0, 50)}...</div>
            `;
            div.onclick = () => selectFantasy(f.id);
            elFantasyList.appendChild(div);
        });
    }

    function selectFantasy(id) {
        currentFantasyId = id;
        renderFantasyList();

        const fantasy = fantasies.find(f => f.id === id);
        elTitle.textContent = fantasy.title;
        elBtnEditFantasy.style.display = 'inline-block';
        document.getElementById('btn-reset-chat').style.display = 'inline-block';
        toggleInput(true);

        const theme = fantasy.theme || 'default';
        document.querySelector('.book-container').className = `book-container theme-${theme}`;

        elChatWindow.innerHTML = '';
        
        if (fantasy.history && fantasy.history.length > 0) {
            fantasy.history.forEach(msg => {
                if (msg.role !== 'system') {
                    addMessageToChat(msg.role === 'user' ? 'user' : 'ai', msg.content);
                }
            });
        } else {
            requestInitialMessage();
        }
    }

    function formatMessage(text) {
        let html = text;
        
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/\n/g, '<br>');
        
        html = html.replace(/\[(.*?)\]/g, '<span class="narrative-text">$1</span>');

        return html;
    }

    function addMessageToChat(role, text) {
        const div = document.createElement('div');
        div.className = `message msg-${role}`;

        const fantasy = fantasies.find(f => f.id === currentFantasyId);
        let name = role === 'user' ? "You" : "AI";
        if (fantasy) {
            if (role === 'user' && fantasy.user_name) name = fantasy.user_name;
            if (role === 'ai' && fantasy.ai_name) name = fantasy.ai_name;
        }

        const header = document.createElement('div');
        header.className = 'message-header';
        header.textContent = name;
        div.appendChild(header);

        const contentDiv = document.createElement('div');
        contentDiv.innerHTML = formatMessage(text);
        div.appendChild(contentDiv);

        const ph = elChatWindow.querySelector('.chat-placeholder');
        if (ph) ph.remove();

        elChatWindow.appendChild(div);
        elChatWindow.scrollTop = elChatWindow.scrollHeight;
        return contentDiv;
    }

    function openFantasyModal(fantasy = null) {
        elModalFantasy.classList.remove('hidden');
        if (fantasy) {
            document.getElementById('modal-title').textContent = "Edit Fantasy";
            document.getElementById('fantasy-id').value = fantasy.id;
            document.getElementById('fantasy-title').value = fantasy.title;
            document.getElementById('fantasy-desc').value = fantasy.description;
            document.getElementById('fantasy-prompt').value = fantasy.system_prompt;
            document.getElementById('fantasy-starting-prompt').value = fantasy.starting_prompt || "";
            elModelSelect.value = fantasy.model_config?.model || 'default';
            elTempInput.value = fantasy.model_config?.temperature || 0.7;
            elThemeSelect.value = fantasy.theme || 'default';
            document.getElementById('fantasy-user-name').value = fantasy.user_name || "";
            document.getElementById('fantasy-ai-name').value = fantasy.ai_name || "";
            elTempVal.textContent = elTempInput.value;
            elBtnDelete.classList.remove('hidden');
        } else {
            document.getElementById('modal-title').textContent = "New Fantasy Card";
            elFormFantasy.reset();
            document.getElementById('fantasy-id').value = "";
            elThemeSelect.value = 'default';
            elBtnDelete.classList.add('hidden');
        }
    }

    function closeFantasyModal() {
        elModalFantasy.classList.add('hidden');
    }

    function toggleInput(enabled) {
        elUserInput.disabled = !enabled;
        elBtnSend.disabled = !enabled;
        if (enabled) elUserInput.focus();
    }
});
