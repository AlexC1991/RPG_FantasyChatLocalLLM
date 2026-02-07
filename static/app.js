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
    const elModal = document.getElementById('modal-fantasy');
    const elCloseModal = document.querySelector('.close-modal');
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

    // --- EVENT LISTENERS ---
    elBtnNewFantasy.addEventListener('click', () => openModal());
    elBtnEditFantasy.addEventListener('click', () => {
        const fantasy = fantasies.find(f => f.id === currentFantasyId);
        if (fantasy) openModal(fantasy);
    });

    elBtnReset.addEventListener('click', async () => {
        if (confirm("Are you sure you want to clear the chat history? This cannot be undone.")) {
            await clearChat();
        }
    });

    elCloseModal.addEventListener('click', closeModal);
    window.addEventListener('click', (e) => { if (e.target === elModal) closeModal(); });

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

            let displayName = model;
            const cleanName = model.replace(/\.gguf$/i, '');

            if (model.toLowerCase().includes('dolphin')) {
                displayName = `🔓 ${cleanName} (Unrestricted - Creative)`;
                option.style.color = "#d9534f";
                option.style.fontWeight = "bold";
            } else {
                displayName = `🛡️ ${cleanName} (Safe - Restricted)`;
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
        closeModal();
        await fetchFantasies();

        if (!id) selectFantasy(data.id);
        if (currentFantasyId === data.id) selectFantasy(data.id);
    }

    async function deleteFantasy() {
        const id = document.getElementById('fantasy-id').value;
        await fetch(`/api/fantasies/${id}`, { method: 'DELETE' });
        closeModal();
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

    // --- UI HELPERS ---

    function renderFantasyList() {
        elFantasyList.innerHTML = '';
        fantasies.forEach(f => {
            const div = document.createElement('div');
            div.className = `fantasy-item ${f.id === currentFantasyId ? 'active' : ''}`;
            div.innerHTML = `
                <span class="item-title">${f.title}</span>
                <span class="item-preview">${f.description.substring(0, 50)}...</span>
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
        elBtnEditFantasy.style.display = 'block';
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
            elChatWindow.innerHTML = '<div class="chat-placeholder"><p>The story begins...</p></div>';
        }
    }

    function formatMessage(text) {
        // Convert Markdown
        let html = marked.parse(text);

        // KEEP THE BRACKETS but style the content inside
        // Replace [text] with styled span that INCLUDES the brackets
        html = html.replace(/\[(.*?)\]/g, '<span class="narrative-text">[$1]</span>');

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

        const header = document.createElement('span');
        header.className = 'sender-name';
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

    function openModal(fantasy = null) {
        elModal.classList.remove('hidden');
        if (fantasy) {
            document.getElementById('modal-title').textContent = "Edit Fantasy";
            document.getElementById('fantasy-id').value = fantasy.id;
            document.getElementById('fantasy-title').value = fantasy.title;
            document.getElementById('fantasy-desc').value = fantasy.description;
            document.getElementById('fantasy-prompt').value = fantasy.system_prompt;
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

    function closeModal() {
        elModal.classList.add('hidden');
    }

    function toggleInput(enabled) {
        elUserInput.disabled = !enabled;
        elBtnSend.disabled = !enabled;
        if (enabled) elUserInput.focus();
    }

    // ========================================
    // SETTINGS MODAL FUNCTIONALITY
    // ========================================

    // Open Settings Modal
    async function openSettingsModal() {
        document.getElementById('modal-settings').classList.remove('hidden');
        
        try {
            const response = await fetch('/api/settings');
            const settings = await response.json();
            
            document.getElementById('setting-archive-path').value = settings.archive_path || './context_archive';
            document.getElementById('setting-archive-size').value = settings.max_archive_size_mb || 100;
            document.getElementById('setting-context-size').value = settings.context_window_size || 4096;
            document.getElementById('setting-enable-rag').checked = settings.enable_rag !== false;
            document.getElementById('setting-rag-count').value = settings.rag_retrieve_count || 5;
            
            updateStatsDisplay();
        } catch (error) {
            console.error('Error loading settings:', error);
            alert('Failed to load settings. Using defaults.');
        }
    }

    // Close Settings Modal
    function closeSettingsModal() {
        document.getElementById('modal-settings').classList.add('hidden');
    }

    // Update Statistics Display
    async function updateStatsDisplay() {
        const statsDiv = document.getElementById('stats-display');
        
        try {
            const response = await fetch('/api/stats');
            
            if (!response.ok) {
                statsDiv.textContent = 'Engine not loaded yet. Start a conversation first.';
                return;
            }
            
            const stats = await response.json();
            
            const text = `Model: ${stats.model || 'N/A'}
Mode: ${stats.mode || 'N/A'}
GPU Layers: ${stats.gpu_layers || 0}

Messages in RAM: ${stats.messages_in_history || 0}
Total Archived: ${stats.total_archived_messages || 0}
Context Size: ${stats.context_size || 0} tokens

RAG Enabled: ${stats.rag_enabled ? 'Yes' : 'No'}
Total Retrievals: ${stats.total_rag_retrievals || 0}
Embedding Cache: ${stats.embedding_cache_size || 0}

Archive Size: ${(stats.archive_size_mb || 0).toFixed(2)} MB
Archive Path: ${stats.archive_path || 'N/A'}`;
            
            statsDiv.textContent = text;
        } catch (error) {
            statsDiv.textContent = 'Engine not initialized yet.';
        }
    }

    // Save Settings
    async function saveSettings(event) {
        event.preventDefault();
        
        const settings = {
            archive_path: document.getElementById('setting-archive-path').value,
            max_archive_size_mb: parseInt(document.getElementById('setting-archive-size').value),
            context_window_size: parseInt(document.getElementById('setting-context-size').value),
            enable_rag: document.getElementById('setting-enable-rag').checked,
            rag_retrieve_count: parseInt(document.getElementById('setting-rag-count').value)
        };
        
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(settings)
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                alert('Settings saved successfully!\n\nNote: Context window size changes require restarting the app.');
                closeSettingsModal();
            } else {
                alert('Failed to save settings. Please try again.');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            alert('Error saving settings: ' + error.message);
        }
    }

    // Wire up settings event listeners
    const settingsBtn = document.getElementById('btn-global-settings');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', openSettingsModal);
    }
    
    const closeSettingsBtn = document.getElementById('close-settings');
    if (closeSettingsBtn) {
        closeSettingsBtn.addEventListener('click', closeSettingsModal);
    }
    
    const settingsForm = document.getElementById('form-settings');
    if (settingsForm) {
        settingsForm.addEventListener('submit', saveSettings);
    }
    
    const settingsModal = document.getElementById('modal-settings');
    if (settingsModal) {
        settingsModal.addEventListener('click', function(e) {
            if (e.target === settingsModal) {
                closeSettingsModal();
            }
        });
    }
    
    // ESC key closes modals
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeSettingsModal();
            closeModal();
        }
    });

    // Auto-refresh stats every 10 seconds when modal is open
    setInterval(function() {
        const modal = document.getElementById('modal-settings');
        if (modal && !modal.classList.contains('hidden')) {
            updateStatsDisplay();
        }
    }, 10000);
});
