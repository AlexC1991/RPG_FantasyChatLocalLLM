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

    // TAB LOGIC REMOVED - Using Split View


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

        // Clear & Add Default
        elModelSelect.innerHTML = '<option value="default">Default (System Config)</option>';

        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;

            // Categorization Logic
            let displayName = model;
            // Remove file extension for cleaner look
            const cleanName = model.replace(/\.gguf$/i, '');

            if (model.toLowerCase().includes('dolphin')) {
                displayName = `🔓 ${cleanName} (Unrestricted - Creative)`;
                option.style.color = "#d9534f"; // Reddish for "Unrestricted"
                option.style.fontWeight = "bold";
            } else {
                displayName = `🛡️ ${cleanName} (Safe - Restricted)`;
                option.style.color = "#5cb85c"; // Greenish for "Safe"
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

        // If editing, merge with existing data to keep history
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

        // Auto select if new
        if (!id) selectFantasy(data.id);
        // If current, refresh style
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

        // Reset theme
        document.querySelector('.book-container').className = 'book-container';

        await fetchFantasies();
    }

    async function sendMessage() {
        const text = elUserInput.value.trim();
        if (!text) return;

        addMessageToChat('user', text);
        elUserInput.value = '';

        // Get current fantasy
        const fantasy = fantasies.find(f => f.id === currentFantasyId);

        // Update local history
        if (!fantasy.history) fantasy.history = [];
        fantasy.history.push({ role: "user", content: text });

        // Generate AI Response
        const bubble = addMessageToChat('ai', '...');
        let fullResponse = "";

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    history: fantasy.history, // We send full history for context
                    system_prompt: fantasy.system_prompt,
                    model_config: fantasy.model_config,
                    user_name: fantasy.user_name,
                    ai_name: fantasy.ai_name
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            // Clear loading dots
            bubble.innerHTML = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value);
                fullResponse += chunk;
                bubble.innerHTML = formatMessage(fullResponse);
                elChatWindow.scrollTop = elChatWindow.scrollHeight;
            }

            // Save history
            fantasy.history.push({ role: "assistant", content: fullResponse });
            // Persist to disk (silent save)
            silentSave(fantasy);

        } catch (err) {
            bubble.textContent = "[Error: " + err.message + "]";
        }
    }

    async function clearChat() {
        if (!currentFantasyId) return;

        try {
            // Clear Frontend
            elChatWindow.innerHTML = '';

            // Find fantasy
            const fantasy = fantasies.find(f => f.id === currentFantasyId);
            if (fantasy) {
                fantasy.history = []; // Clear local history
                await silentSave(fantasy); // Save empty history to disk
            }

            // Reset Backend Context
            await fetch('/api/reset', { method: 'POST' });

            // Add starter text
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
        elBtnEditFantasy.style.display = 'block';
        document.getElementById('btn-reset-chat').style.display = 'inline-block';
        toggleInput(true);

        // Apply Theme
        const theme = fantasy.theme || 'default';
        document.querySelector('.book-container').className = `book-container theme-${theme}`;

        // Load History
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
        // 1. Convert Markdown
        let html = marked.parse(text);

        // 2. Wrap text in [brackets] with span (Global replace)
        // We look for [ ... ] and wrap it in a span, stripping the brackets slightly
        // or just hiding them. User requested "not have the [ ] displayed".

        html = html.replace(/\[(.*?)\]/g, '<span class="narrative-text">$1</span>');

        return html;
    }

    function addMessageToChat(role, text) {
        const div = document.createElement('div');
        div.className = `message msg-${role}`;

        // Nameplate
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
        if (role === 'ai') {
            contentDiv.innerHTML = formatMessage(text);
        } else {
            // Even user text might have narration
            contentDiv.innerHTML = formatMessage(text);
        }
        div.appendChild(contentDiv);

        // Remove placeholder if exists
        const ph = elChatWindow.querySelector('.chat-placeholder');
        if (ph) ph.remove();

        elChatWindow.appendChild(div);
        elChatWindow.scrollTop = elChatWindow.scrollHeight;
        return contentDiv; // Return content div for streaming updates
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
});
