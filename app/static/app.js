// Banco de Links - Frontend Logic

const API_BASE = '/api';
let currentPage = 0;
const ITEMS_PER_PAGE = 12;

// Broadcast Channel for real-time sync between tabs
let broadcastChannel = null;

function initBroadcastChannel() {
    if ('BroadcastChannel' in window) {
        try {
            broadcastChannel = new BroadcastChannel('banco-links-sync');
            broadcastChannel.addEventListener('message', handleBroadcastMessage);
            console.log('Broadcast Channel initialized');
        } catch (e) {
            console.log('Broadcast Channel not supported:', e);
        }
    }
}

function handleBroadcastMessage(event) {
    const { type, data } = event.data;

    switch(type) {
        case 'link-added':
            showToast('✨ Novo link adicionado em outra aba', 'info');
            handleSearch();
            break;
        case 'link-updated':
            showToast('📝 Link atualizado em outra aba', 'info');
            handleSearch();
            break;
        case 'link-deleted':
            showToast('🗑️ Link removido em outra aba', 'info');
            handleSearch();
            break;
        case 'favorite-toggled':
            showToast('⭐ Favorito atualizado em outra aba', 'info');
            handleSearch();
            break;
    }
}

function broadcastEvent(type, data) {
    if (broadcastChannel) {
        broadcastChannel.postMessage({ type, data, timestamp: Date.now() });
    }
}
let currentSearch = '';
let currentCategory = '';
let currentPlatform = '';
let currentFavoriteFilter = false;

// Modo de visualização (cards ou lista) - padrão grid para Fase 1
let viewMode = localStorage.getItem('linkViewMode') || 'grid';

// DOM Elements - inicializadas em init()
let searchInput, clearSearchBtn, categoryFilter, platformFilter, favoritesFilter;
let linksContainer, loadingEl, emptyStateEl, resultsCount, newLinkBtn;
let newLinkModal, editLinkModal, confirmModal, paginationEl;
let prevPageBtn, nextPageBtn, pageInfo;
let categoriesList, categoriesBar, tagsList, selectedTagsContainer, clearTagsBtn;

let totalResults = 0;
let categoriesData = {};
let selectedTags = new Set();
let favoritesViewActive = false;
let favoritesData = [];
let favoritesSortBy = 'recentes';
let editingLinkId = null;
let confirmCallback = null;
let suggestionsDropdown = null;
let lastToast = null;

// Init
document.addEventListener('DOMContentLoaded', () => {
    init();
    registerServiceWorker();
});

function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/service-worker.js')
            .then(registration => {
                console.log('Service Worker registered:', registration);
            })
            .catch(error => {
                console.log('Service Worker registration failed:', error);
            });
    }
}

// AI Chat Functions
let aiChatOpen = false;

function initAIChat() {
    const chatBubbleBtn = document.getElementById('chat-bubble-btn');
    const closeBtn = document.getElementById('close-chat-btn');
    const chatInput = document.getElementById('ai-chat-input');
    const sendBtn = document.getElementById('ai-send-btn');
    const chatModal = document.getElementById('ai-chat-modal');

    chatBubbleBtn.addEventListener('click', toggleAIChat);
    closeBtn.addEventListener('click', closeAIChat);
    sendBtn.addEventListener('click', sendAIChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendAIChatMessage();
        }
    });

    // Check if API key is configured
    checkAIConfigured();
}

async function checkAIConfigured() {
    try {
        const status = await fetch(`${API_BASE}/ai/status`).then(r => r.json());
        const chatBtn = document.getElementById('chat-bubble-btn');
        if (!status.configured) {
            chatBtn.disabled = true;
            chatBtn.title = '⚠️ API key não configurada. Configure ANTHROPIC_API_KEY no Railway.';
            document.getElementById('ai-chat-bubble').style.opacity = '0.5';
        }
    } catch (e) {
        console.log('AI status check failed:', e);
    }
}

function toggleAIChat() {
    const modal = document.getElementById('ai-chat-modal');
    if (aiChatOpen) {
        closeAIChat();
    } else {
        modal.style.display = 'block';
        aiChatOpen = true;
        document.getElementById('ai-chat-input').focus();
    }
}

function closeAIChat() {
    document.getElementById('ai-chat-modal').style.display = 'none';
    aiChatOpen = false;
}

async function sendAIChatMessage() {
    const input = document.getElementById('ai-chat-input');
    const message = input.value.trim();

    if (!message) return;

    const messagesContainer = document.getElementById('ai-chat-messages');
    const sendBtn = document.getElementById('ai-send-btn');

    // Add user message
    const userMsgEl = document.createElement('div');
    userMsgEl.className = 'user-message';
    userMsgEl.innerHTML = `<div class="message-content">${escapeHtml(message)}</div>`;
    messagesContainer.appendChild(userMsgEl);

    // Clear input and disable send
    input.value = '';
    sendBtn.disabled = true;
    sendBtn.textContent = '⏳ Pensando...';

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const aiModel = localStorage.getItem('aiModel') || 'claude-sonnet-5';
        const response = await fetch(`${API_BASE}/ai/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, limit: 5, model: aiModel })
        });

        if (!response.ok) throw new Error('Erro ao enviar mensagem');

        const data = await response.json();

        // Add AI response
        const aiMsgEl = document.createElement('div');
        aiMsgEl.className = 'ai-message';
        let costText = '';
        if (data.usage && data.usage.cost_usd > 0) {
            costText = ` <small style="opacity: 0.7; font-size: 0.8em;">💵 $${data.usage.cost_usd.toFixed(4)}</small>`;

            // Show toast with cost
            showToast(`💬 Chat processado • Custo: $${data.usage.cost_usd.toFixed(4)} • ${data.usage.input_tokens} in + ${data.usage.output_tokens} out tokens`, 'info', 4000);
        }
        aiMsgEl.innerHTML = `<div class="message-content">${data.response.replace(/\n/g, '<br>')}${costText}</div>`;
        messagesContainer.appendChild(aiMsgEl);

        // Add links if available
        if (data.links && data.links.length > 0) {
            const linksEl = document.createElement('div');
            linksEl.className = 'ai-message';
            linksEl.innerHTML = `<div class="message-content">
                <strong>📎 Links relacionados:</strong><br>
                ${data.links.map(link => `
                    <div style="margin-top: 8px; padding: 8px; background: rgba(99, 102, 241, 0.1); border-radius: 4px;">
                        <strong>${escapeHtml(link.titulo)}</strong><br>
                        <small>${escapeHtml(link.categoria)} | ${escapeHtml(link.plataforma)}</small>
                    </div>
                `).join('')}
            </div>`;
            messagesContainer.appendChild(linksEl);
        }

        // Update stats counter
        loadAICostStats();

        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (e) {
        const errorEl = document.createElement('div');
        errorEl.className = 'ai-message';
        errorEl.innerHTML = `<div class="message-content">❌ ${e.message}</div>`;
        messagesContainer.appendChild(errorEl);
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Enviar';
    }
}

async function loadAICostStats() {
    try {
        const response = await fetch(`${API_BASE}/ai/stats`);
        if (!response.ok) return;

        const stats = await response.json();

        // Update settings panel if visible
        const statAICostEl = document.getElementById('stat-ai-cost');
        const statAIChatEl = document.getElementById('stat-ai-chats');
        if (statAICostEl) {
            statAICostEl.textContent = `$${stats.total.cost_usd.toFixed(2)}`;
        }
        if (statAIChatEl) {
            statAIChatEl.textContent = stats.total.chats;
        }
    } catch (e) {
        console.log('Error loading AI stats:', e);
    }
}

async function init() {
    // Apply dark mode if saved
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
    }

    // Initialize Broadcast Channel for real-time sync
    initBroadcastChannel();

    // Initialize DOM Elements
    searchInput = document.getElementById('search-input');
    clearSearchBtn = document.getElementById('clear-search-btn');
    categoryFilter = document.getElementById('category-filter');
    platformFilter = document.getElementById('platform-filter');
    favoritesFilter = document.getElementById('favorites-filter');
    linksContainer = document.getElementById('links-container');
    loadingEl = document.getElementById('loading');
    emptyStateEl = document.getElementById('empty-state');
    resultsCount = document.getElementById('results-count');
    newLinkBtn = document.getElementById('new-link-btn');
    newLinkModal = document.getElementById('new-link-modal');
    editLinkModal = document.getElementById('edit-link-modal');
    confirmModal = document.getElementById('confirm-modal');
    paginationEl = document.getElementById('pagination');
    prevPageBtn = document.getElementById('prev-page-btn');
    nextPageBtn = document.getElementById('next-page-btn');
    pageInfo = document.getElementById('page-info');
    categoriesList = document.getElementById('categories-list');
    categoriesBar = document.querySelector('.categories-bar');
    tagsList = document.getElementById('tags-list');
    selectedTagsContainer = document.getElementById('selected-tags');
    clearTagsBtn = document.getElementById('clear-tags-btn');

    // Display network info
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            const localIp = getLocalIP();
            const port = window.location.port || 8765;
            document.getElementById('network-info').innerHTML =
                `Acesso local: <strong>http://localhost:${port}</strong> | Rede: <strong>http://${localIp}:${port}</strong>`;
        }
    } catch (e) {
        console.error('Health check failed:', e);
    }

    // Load filters
    loadCategories();
    loadPlatforms();
    loadCategoriesBar();
    loadTagsBar();

    // Categories bar "Todas" button
    document.querySelector('[data-category=""]')?.addEventListener('click', () => selectCategory(''));

    // Clear tags button
    clearTagsBtn.addEventListener('click', clearAllTags);

    // Event listeners
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('keydown', handleSearchKeydown);
    searchInput.addEventListener('blur', () => {
        setTimeout(() => {
            if (suggestionsDropdown) suggestionsDropdown.remove();
        }, 200);
    });

    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearSearchBtn.classList.remove('visible');
        searchInput.focus();
        if (suggestionsDropdown) suggestionsDropdown.remove();
        handleSearch();
    });

    categoryFilter.addEventListener('change', handleSearch);
    platformFilter.addEventListener('change', handleSearch);
    favoritesFilter.addEventListener('change', handleSearch);

    // Favorites panel
    document.getElementById('favorites-shortcut')?.addEventListener('click', toggleFavoritesPanel);
    document.getElementById('close-favorites-btn')?.addEventListener('click', () => {
        favoritesViewActive = false;
        document.getElementById('favorites-panel').style.display = 'none';
    });
    document.getElementById('favorites-category-filter')?.addEventListener('change', loadFavorites);
    document.getElementById('favorites-platform-filter')?.addEventListener('change', loadFavorites);
    document.getElementById('favorites-sort')?.addEventListener('change', (e) => {
        favoritesSortBy = e.target.value;
        renderFavoritesData();
    });

    // Settings
    document.getElementById('settings-header-btn')?.addEventListener('click', (e) => {
        e.preventDefault();
        openSettings();
    });

    newLinkBtn.addEventListener('click', openNewLinkModal);
    prevPageBtn.addEventListener('click', () => previousPage());
    nextPageBtn.addEventListener('click', () => nextPage());

    // Modal close buttons
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', (e) => closeAllModals());
    });

    // Export/Import
    document.getElementById('export-csv-btn').addEventListener('click', () => exportLinks('csv'));
    document.getElementById('export-xlsx-btn').addEventListener('click', () => exportLinks('xlsx'));
    document.getElementById('import-btn').addEventListener('click', () => {
        document.getElementById('import-file').click();
    });
    document.getElementById('import-file').addEventListener('change', handleImport);
    document.getElementById('github-backup-btn').addEventListener('click', handleGitHubBackup);

    // New link modal
    document.getElementById('extract-btn').addEventListener('click', extractMetadata);
    document.getElementById('save-new-link-btn').addEventListener('click', saveNewLink);
    document.getElementById('cancel-new-link-btn').addEventListener('click', closeAllModals);

    // Edit link modal
    document.getElementById('save-edit-btn').addEventListener('click', saveEditLink);
    document.getElementById('cancel-edit-btn').addEventListener('click', closeAllModals);
    document.getElementById('analyze-ai-btn').addEventListener('click', analyzeWithAI);
    document.getElementById('suggest-tags-edit-btn').addEventListener('click', suggestTagsForEdit);

    // Suggest tags for new link
    document.getElementById('suggest-tags-btn').addEventListener('click', suggestTagsForNew);

    // Confirm modal
    document.getElementById('confirm-cancel-btn').addEventListener('click', closeAllModals);
    document.getElementById('confirm-yes-btn').addEventListener('click', () => {
        if (confirmCallback) confirmCallback();
        closeAllModals();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // Initialize AI Chat
    initAIChat();

    // Fase 3: Initialize display mode controls
    initDisplayModeControls();

    // Initial search
    handleSearch();
}

function initDisplayModeControls() {
    // Adicionar botões de modo compacto/normal/expandido ao navbar de shortcuts
    const shortcutsContainer = document.querySelector('.quick-shortcuts');
    if (shortcutsContainer) {
        const modesHtml = `
            <div style="margin-left: auto; display: flex; gap: 8px;">
                <button class="shortcut-btn" id="mode-compact-btn" title="Modo Compacto">📦 Compacto</button>
                <button class="shortcut-btn" id="mode-normal-btn" title="Modo Normal" style="display:none;">📊 Normal</button>
                <button class="shortcut-btn" id="mode-expanded-btn" title="Modo Expandido">📖 Expandido</button>
            </div>
        `;
        const modesDiv = document.createElement('div');
        modesDiv.innerHTML = modesHtml;
        shortcutsContainer.appendChild(modesDiv);

        // Event listeners
        document.getElementById('mode-compact-btn').addEventListener('click', () => {
            setDisplayMode('compact');
        });
        document.getElementById('mode-expanded-btn').addEventListener('click', () => {
            setDisplayMode('expanded');
        });
    }
}

function setDisplayMode(mode) {
    localStorage.setItem('cardDisplayMode', mode);
    const cards = document.querySelectorAll('.link-card:not(.blocked-link)');
    cards.forEach(card => toggleCardMode(card, mode));

    // Atualizar buttons
    document.getElementById('mode-compact-btn').classList.toggle('active', mode === 'compact');
    document.getElementById('mode-expanded-btn').classList.toggle('active', mode === 'expanded');
}

function getLocalIP() {
    return window.location.hostname;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function handleSearchInput(e) {
    const query = e.target.value.trim();

    // Show/hide clear button based on input
    if (query.length > 0) {
        clearSearchBtn.classList.add('visible');
        fetchSuggestions(query);
    } else {
        clearSearchBtn.classList.remove('visible');
        if (suggestionsDropdown) suggestionsDropdown.remove();
        handleSearch();
    }

    // Debounced search
    debounce(handleSearch, 300)();
}

function handleSearchKeydown(e) {
    if (e.key === 'Enter') {
        handleSearch();
        if (suggestionsDropdown) suggestionsDropdown.remove();
    }
}

async function fetchSuggestions(query) {
    try {
        const response = await fetch(`${API_BASE}/search/suggest?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.suggestions && data.suggestions.length > 0) {
            showSuggestionsDropdown(data.suggestions, query);
        } else {
            if (suggestionsDropdown) suggestionsDropdown.remove();
        }
    } catch (e) {
        console.error('Error fetching suggestions:', e);
    }
}

function showSuggestionsDropdown(suggestions, query) {
    // Remove old dropdown if exists
    if (suggestionsDropdown) suggestionsDropdown.remove();

    // Create dropdown
    const dropdown = document.createElement('div');
    dropdown.style.cssText = `
        position: absolute;
        top: ${searchInput.getBoundingClientRect().bottom + window.scrollY}px;
        left: ${searchInput.getBoundingClientRect().left}px;
        width: ${searchInput.offsetWidth}px;
        background: #1a1a18;
        border: 1px solid #383835;
        border-radius: 6px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        z-index: 100;
        max-height: 300px;
        overflow-y: auto;
    `;

    suggestions.slice(0, 8).forEach(suggestion => {
        const item = document.createElement('div');
        item.style.cssText = `
            padding: 12px 16px;
            cursor: pointer;
            border-bottom: 1px solid #383835;
            font-size: 0.95em;
            color: #f9f9f7;
        `;

        // Highlight matching part
        const regex = new RegExp(`(${query})`, 'gi');
        const highlighted = suggestion.replace(regex, '<strong>$1</strong>');
        item.innerHTML = highlighted;

        item.addEventListener('mouseenter', () => {
            item.style.backgroundColor = '#2c2c2a';
        });
        item.addEventListener('mouseleave', () => {
            item.style.backgroundColor = '#1a1a18';
        });

        item.addEventListener('click', () => {
            searchInput.value = suggestion;
            if (suggestionsDropdown) suggestionsDropdown.remove();
            handleSearch();
        });

        dropdown.appendChild(item);
    });

    document.body.appendChild(dropdown);
    suggestionsDropdown = dropdown;
}

async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/filters/categorias`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const select = document.getElementById('category-filter');

        if (!data.categorias || !Array.isArray(data.categorias)) {
            console.error('Invalid categorias response:', data);
            return;
        }

        data.categorias.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat;
            select.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to load categories:', e);
    }
}

async function loadPlatforms() {
    try {
        const response = await fetch(`${API_BASE}/filters/plataformas`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const select = document.getElementById('platform-filter');

        if (!data.plataformas || !Array.isArray(data.plataformas)) {
            console.error('Invalid plataformas response:', data);
            return;
        }

        data.plataformas.forEach(plat => {
            const option = document.createElement('option');
            option.value = plat;
            option.textContent = plat;
            select.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to load platforms:', e);
    }
}

async function loadCategoriesBar() {
    try {
        const response = await fetch(`${API_BASE}/filters/categorias-count`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        if (!data.categorias || !Array.isArray(data.categorias)) {
            console.error('Invalid categorias-count response:', data);
            return;
        }

        categoriesList.innerHTML = '';
        data.categorias.forEach(cat => {
            const btn = document.createElement('button');
            btn.className = 'category-btn';
            btn.dataset.category = cat.name;
            btn.textContent = `📂 ${cat.name} (${cat.count})`;
            btn.addEventListener('click', () => selectCategory(cat.name));
            categoriesList.appendChild(btn);
        });
    } catch (e) {
        console.error('Failed to load categories bar:', e);
    }
}

function selectCategory(categoryName) {
    currentCategory = categoryName;
    currentPage = 0;

    // Update active button
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    if (categoryName) {
        document.querySelector(`[data-category="${categoryName}"]`)?.classList.add('active');
        categoryFilter.value = categoryName;
    } else {
        categoryFilter.value = '';
        document.querySelector(`[data-category=""]`)?.classList.add('active');
    }

    performSearch();
}

async function loadTagsBar() {
    try {
        const response = await fetch(`${API_BASE}/filters/tags-count`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        if (!data.tags || !Array.isArray(data.tags)) {
            console.error('Invalid tags-count response:', data);
            return;
        }

        tagsList.innerHTML = '';
        data.tags.forEach(tag => {
            const btn = document.createElement('button');
            btn.className = 'tag-btn';
            btn.dataset.tag = tag.name;
            btn.textContent = `🏷️ ${tag.name} (${tag.count})`;
            btn.addEventListener('click', () => toggleTag(tag.name));
            tagsList.appendChild(btn);
        });
    } catch (e) {
        console.error('Failed to load tags bar:', e);
    }
}

function toggleTag(tagName) {
    if (selectedTags.has(tagName)) {
        selectedTags.delete(tagName);
    } else {
        selectedTags.add(tagName);
    }

    updateSelectedTagsDisplay();
    currentPage = 0;
    performSearch();
}

function updateSelectedTagsDisplay() {
    // Update button states
    document.querySelectorAll('.tag-btn').forEach(btn => {
        const tagName = btn.dataset.tag;
        if (selectedTags.has(tagName)) {
            btn.classList.add('selected');
        } else {
            btn.classList.remove('selected');
        }
    });

    // Update selected tags container
    selectedTagsContainer.innerHTML = '';
    if (selectedTags.size > 0) {
        clearTagsBtn.style.display = 'inline-block';
        selectedTags.forEach(tag => {
            const badge = document.createElement('div');
            badge.className = 'selected-tag-badge';
            badge.innerHTML = `
                ${tag}
                <span class="remove-tag" data-tag="${tag}">×</span>
            `;
            badge.querySelector('.remove-tag').addEventListener('click', () => toggleTag(tag));
            selectedTagsContainer.appendChild(badge);
        });
    } else {
        clearTagsBtn.style.display = 'none';
    }
}

function clearAllTags() {
    selectedTags.clear();
    updateSelectedTagsDisplay();
    currentPage = 0;
    performSearch();
}

async function toggleFavoritesPanel() {
    const panel = document.getElementById('favorites-panel');
    const favoritesCategoryFilter = document.getElementById('favorites-category-filter');
    const favoritesPlatformFilter = document.getElementById('favorites-platform-filter');

    if (!favoritesViewActive) {
        favoritesViewActive = true;
        panel.style.display = 'block';

        // Load categories and platforms for favorites filters
        if (favoritesCategoryFilter.children.length === 1) {
            const categories = await fetch(`${API_BASE}/filters/categorias`)
                .then(r => r.json())
                .catch(() => ({ categorias: [] }));
            categories.categorias?.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                favoritesCategoryFilter.appendChild(option);
            });
        }

        if (favoritesPlatformFilter.children.length === 1) {
            const platforms = await fetch(`${API_BASE}/filters/plataformas`)
                .then(r => r.json())
                .catch(() => ({ plataformas: [] }));
            platforms.plataformas?.forEach(plat => {
                const option = document.createElement('option');
                option.value = plat;
                option.textContent = plat;
                favoritesPlatformFilter.appendChild(option);
            });
        }

        loadFavorites();
    } else {
        favoritesViewActive = false;
        panel.style.display = 'none';
    }
}

async function loadFavorites() {
    try {
        const categoryFilter = document.getElementById('favorites-category-filter').value;
        const platformFilter = document.getElementById('favorites-platform-filter').value;

        let url = `${API_BASE}/links?favorito=true`;
        if (categoryFilter) url += `&categoria=${encodeURIComponent(categoryFilter)}`;
        if (platformFilter) url += `&plataforma=${encodeURIComponent(platformFilter)}`;

        const response = await fetch(url);
        const data = await response.json();

        favoritesData = data.data || [];
        document.getElementById('favorites-count').textContent = `(${favoritesData.length})`;

        renderFavoritesData();
    } catch (e) {
        console.error('Failed to load favorites:', e);
        showError('Erro ao carregar favoritos');
    }
}

function renderFavoritesData() {
    // Apply sorting
    const sorted = [...favoritesData];
    if (favoritesSortBy === 'recentes') {
        sorted.sort((a, b) => new Date(b.atualizado_em) - new Date(a.atualizado_em));
    } else if (favoritesSortBy === 'antigos') {
        sorted.sort((a, b) => new Date(a.atualizado_em) - new Date(b.atualizado_em));
    } else if (favoritesSortBy === 'alfabetico') {
        sorted.sort((a, b) => (a.titulo || a.url).localeCompare(b.titulo || b.url));
    } else if (favoritesSortBy === 'alfabetico-desc') {
        sorted.sort((a, b) => (b.titulo || b.url).localeCompare(a.titulo || a.url));
    }

    // Update the main links container
    linksContainer.innerHTML = '';
    if (sorted.length === 0) {
        emptyStateEl.style.display = 'block';
        return;
    }

    emptyStateEl.style.display = 'none';
    if (viewMode === 'lista') {
        linksContainer.classList.add('links-list-mode');
        linksContainer.classList.remove('links-grid');
    } else {
        linksContainer.classList.add('links-grid');
        linksContainer.classList.remove('links-list-mode');
    }

    renderLinks(sorted);
    resultsCount.textContent = `${sorted.length} link${sorted.length !== 1 ? 's' : ''} encontrado${sorted.length !== 1 ? 's' : ''}`;
}

async function openSettings() {
    const settingsModal = document.getElementById('settings-modal');
    if (!settingsModal) {
        console.error('Settings modal not found');
        return;
    }
    settingsModal.style.display = 'flex';

    // Show loading state
    const statsItems = document.querySelectorAll('.stat-value');
    statsItems.forEach(item => item.textContent = '⏳');

    // Load statistics
    try {
        const stats = await fetch(`${API_BASE}/search/stats`).then(r => r.json());
        document.getElementById('stat-total').textContent = stats.total_links || 0;
        document.getElementById('stat-categories').textContent = stats.total_categorias || 0;
        document.getElementById('stat-tags').textContent = '0'; // TODO: Get from API
        document.getElementById('stat-favorites').textContent = stats.total_favoritos || 0;
    } catch (e) {
        console.error('Failed to load stats:', e);
        document.getElementById('stat-total').textContent = '0';
        document.getElementById('stat-categories').textContent = '0';
        document.getElementById('stat-tags').textContent = '0';
        document.getElementById('stat-favorites').textContent = '0';
        showToast('⚠️ Erro ao carregar estatísticas', 'error');
    }

    // Load AI usage statistics
    try {
        const aiStats = await fetch(`${API_BASE}/ai/stats`).then(r => r.json());
        const totalChats = aiStats.total.chats;
        const totalCost = aiStats.total.cost_usd;
        const avgCost = totalChats > 0 ? (totalCost / totalChats).toFixed(4) : 0;

        document.getElementById('stat-ai-chats').textContent = totalChats;
        document.getElementById('stat-ai-cost').textContent = `$${totalCost.toFixed(2)}`;
        document.getElementById('stat-ai-avg').textContent = `$${avgCost}`;
    } catch (e) {
        console.log('Failed to load AI stats:', e);
        // Set defaults if AI stats fail, don't break Settings
        if (document.getElementById('stat-ai-chats')) document.getElementById('stat-ai-chats').textContent = '0';
        if (document.getElementById('stat-ai-cost')) document.getElementById('stat-ai-cost').textContent = '$0.00';
        if (document.getElementById('stat-ai-avg')) document.getElementById('stat-ai-avg').textContent = '$0.0000';
    }

    // Set current view mode
    document.getElementById('view-mode-select').value = viewMode;

    // Settings close button
    document.getElementById('close-settings-btn').addEventListener('click', () => {
        settingsModal.style.display = 'none';
    });

    // Export buttons in settings
    document.getElementById('export-csv-settings')?.addEventListener('click', () => exportLinks('csv'));
    document.getElementById('export-xlsx-settings')?.addEventListener('click', () => exportLinks('xlsx'));
    document.getElementById('github-backup-settings')?.addEventListener('click', handleGitHubBackup);

    // Import file
    document.getElementById('settings-import-file')?.addEventListener('change', handleImport);

    // View mode change
    document.getElementById('view-mode-select')?.addEventListener('change', (e) => {
        viewMode = e.target.value;
        localStorage.setItem('linkViewMode', viewMode);
        renderLinks(linksContainer.innerHTML === '' ? [] : document.querySelectorAll('.link-card, .link-list-item'));
    });

    // Dark mode toggle
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    darkModeToggle.checked = localStorage.getItem('darkMode') === 'true';
    darkModeToggle?.addEventListener('change', toggleDarkMode);

    // AI Model selector
    const aiModelSelect = document.getElementById('ai-model-select');
    const savedModel = localStorage.getItem('aiModel') || 'claude-sonnet-5';
    if (aiModelSelect) {
        aiModelSelect.value = savedModel;
        aiModelSelect.addEventListener('change', (e) => {
            localStorage.setItem('aiModel', e.target.value);
            showSuccess(`🤖 Modelo alterado para ${e.target.options[e.target.selectedIndex].text}`);
        });
    }
}

async function handleSearch() {
    currentSearch = searchInput.value.trim();
    currentCategory = categoryFilter.value;
    currentPlatform = platformFilter.value;
    currentFavoriteFilter = favoritesFilter.checked;
    currentPage = 0;
    performSearch();
}

async function performSearch() {
    showLoading(true);

    try {
        // BUG FIX: Use /api/links if filtering by favorites, otherwise use /api/search for full-text
        let endpoint = currentFavoriteFilter ? '/api/links' : '/api/search';
        let url = `${endpoint}?limit=${ITEMS_PER_PAGE}&offset=${currentPage * ITEMS_PER_PAGE}`;

        if (currentSearch && !currentFavoriteFilter) {
            url += `&q=${encodeURIComponent(currentSearch)}`;
        }
        if (currentCategory) {
            url += `&categoria=${encodeURIComponent(currentCategory)}`;
        }
        if (currentPlatform) {
            url += `&plataforma=${encodeURIComponent(currentPlatform)}`;
        }
        if (selectedTags.size > 0) {
            const tagsString = Array.from(selectedTags).join(',');
            url += `&tags=${encodeURIComponent(tagsString)}`;
        }
        if (currentFavoriteFilter) {
            url += `&favorito=true`;
        }

        console.log('📡 Search URL:', url);
        const response = await fetch(url);
        const data = await response.json();

        totalResults = data.total;
        renderLinks(data.data);
        updatePagination();
        updateResultsCount();

    } catch (e) {
        console.error('Search failed:', e);
        showError('Erro ao buscar links');
    } finally {
        showLoading(false);
    }
}

function renderLinks(links) {
    linksContainer.innerHTML = '';

    if (links.length === 0) {
        emptyStateEl.style.display = 'block';
        return;
    }

    emptyStateEl.style.display = 'none';

    // Renderizar baseado no modo de visualização
    if (viewMode === 'lista') {
        linksContainer.classList.add('links-list-mode');
        linksContainer.classList.remove('links-grid');
        links.forEach(link => {
            const item = createLinkListItem(link);
            linksContainer.appendChild(item);
        });
    } else {
        linksContainer.classList.add('links-grid');
        linksContainer.classList.remove('links-list-mode');
        const displayMode = localStorage.getItem('cardDisplayMode') || 'normal';
        links.forEach(link => {
            const card = createLinkCard(link);
            if (displayMode !== 'normal') {
                toggleCardMode(card, displayMode);
            }
            linksContainer.appendChild(card);
        });
    }
}

function getPlaceholderImageUrl(categoria, tema, titulo) {
    const colors = ['FF8C00', '1E3A8A', '22C55E', 'DC2626', 'A855F7', '06B6D4'];
    let color = colors[0];

    if (categoria === 'Receita') color = 'FF8C00';
    else if (categoria === 'SAP' || categoria === 'Tecnologia') color = '1E3A8A';
    else if (categoria === 'Tutorial' || categoria === 'Educação') color = '22C55E';
    else if (categoria === 'Vídeo') color = 'DC2626';
    else if (categoria === 'Artigo') color = 'A855F7';
    else if (categoria === 'Ferramenta' || categoria === 'Negócios') color = '06B6D4';
    else {
        const charCode = (titulo || categoria || 'link').charCodeAt(0);
        color = colors[charCode % colors.length];
    }

    const emoji = getEmojiForCategory(categoria);
    return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 180'%3E%3Crect fill='%23${color}' width='300' height='180'/%3E%3Ctext x='150' y='90' font-size='80' fill='white' text-anchor='middle' dominant-baseline='middle'%3E${emoji}%3C/text%3E%3C/svg%3E`;
}

function getEmojiForCategory(categoria) {
    const emojiMap = {
        'Receita': '🍳', 'SAP': '📘', 'Tutorial': '🎓', 'Vídeo': '▶️',
        'Artigo': '📄', 'Ferramenta': '🛠️', 'Tecnologia': '💻',
        'Educação': '📚', 'IA': '🤖', 'Negócios': '💼', 'Saúde': '⚕️'
    };
    return emojiMap[categoria] || '📌';
}

function getTruncatedTags(categoria, tema, maxCount = 4) {
    const tags = [];
    if (categoria) tags.push(categoria);
    if (tema) tags.push(tema);
    return tags.slice(0, maxCount).map(tag => `#${tag.toLowerCase()}`).join(' ');
}

function createLinkCard(link) {
    const card = document.createElement('div');
    let classNames = link.bloqueado ? 'link-card blocked-link' : 'link-card';

    // Adicionar classe de categoria para cor
    if (link.categoria) {
        const catClass = `cat-${link.categoria.toLowerCase().replace(/\s+/g, '-')}`;
        classNames += ` ${catClass}`;
    }

    card.className = classNames;

    const platform = link.plataforma || 'Link';
    const date = link.data ? new Date(link.data).toLocaleDateString('pt-BR') : '';
    const dateObj = link.data ? new Date(link.data) : null;
    const daysOld = dateObj ? Math.floor((Date.now() - dateObj.getTime()) / (1000 * 60 * 60 * 24)) : null;
    const isNew = daysOld !== null && daysOld <= 7; // Novo se adicionado a menos de 7 dias
    const placeholderImage = getPlaceholderImageUrl(link.categoria, link.tema, link.titulo);
    const tags = getTruncatedTags(link.categoria, link.tema);
    const emoji = getEmojiForCategory(link.categoria);
    const rating = link.rating || 0;

    // Renderizar link bloqueado com UI especial
    if (link.bloqueado) {
        card.innerHTML = `
            <div class="card-header">
                <div>
                    <span class="blocked-badge">🔒 Bloqueado</span>
                </div>
                <button class="star-btn ${link.favorito ? 'favorite' : ''}" data-id="${link.id}" title="Favoritar">
                    ${link.favorito ? '⭐' : '☆'}
                </button>
            </div>
            <div class="card-title">
                <span>${escapeHtml(link.titulo || link.url)}</span>
            </div>
            <div class="card-description" style="color: #666; font-style: italic;">
                ${escapeHtml(link.resumo)}
            </div>
            <div class="card-url"><small>${escapeHtml(link.url.substring(0, 60))}${link.url.length > 60 ? '...' : ''}</small></div>
            <div class="card-actions">
                <button class="btn btn-primary blocked-open-btn" onclick="window.open('${escapeHtml(link.url)}', '_blank')">
                    🔗 Abrir no Site
                </button>
                <button class="btn btn-small btn-edit" data-link-id="${link.id}">✏️ Editar</button>
            </div>
        `;
    } else {
        // Link normal - Fase 1 + Fase 2
        const badgeHtml = isNew ? `<span class="card-badge novo">✨ Novo</span>` : '';
        const ratingStars = rating > 0 ? '⭐'.repeat(Math.min(rating, 5)) : '';

        card.innerHTML = `
            <div class="card-image-container">
                <img src="${placeholderImage}" alt="Thumbnail" class="card-image">
                <div class="card-image-overlay"></div>
            </div>
            <div class="card-content">
                ${badgeHtml ? `<div class="card-badge-group">${badgeHtml}</div>` : ''}

                <div class="card-header">
                    <div class="card-title-wrapper">
                        <span class="card-icon">${emoji}</span>
                        <a href="#" class="card-link" data-link-id="${link.id}">${escapeHtml(link.titulo || link.url)}</a>
                    </div>
                    <button class="star-btn ${link.favorito ? 'favorite' : ''}" data-id="${link.id}" title="Favoritar">
                        ${link.favorito ? '⭐' : '☆'}
                    </button>
                </div>

                ${link.resumo ? `<div class="card-description">${escapeHtml(link.resumo.substring(0, 120))}${link.resumo.length > 120 ? '...' : ''}</div>` : ''}

                ${tags ? `<div class="card-tags">${tags}</div>` : ''}

                ${ratingStars ? `<div class="card-rating">${ratingStars}</div>` : ''}

                <div class="card-footer">
                    <div class="card-meta">
                        ${link.autor ? `<span class="meta-author">👤 ${escapeHtml(link.autor)}</span>` : ''}
                        ${date ? `<span class="meta-date">📅 ${date}</span>` : ''}
                        <span class="meta-platform">${escapeHtml(platform)}</span>
                    </div>
                </div>

                <div class="card-actions">
                    <button class="btn btn-small btn-edit" data-link-id="${link.id}">✏️ Editar</button>
                    <button class="btn btn-small btn-secondary btn-delete" data-link-id="${link.id}">🗑️ Deletar</button>
                </div>
            </div>
        `;
    }

    // Event listener para abrir detalhes do link (only for non-blocked links)
    if (!link.bloqueado) {
        const cardLinkEl = card.querySelector('.card-link');
        if (cardLinkEl) {
            cardLinkEl.addEventListener('click', (e) => {
                e.preventDefault();
                showLinkDetail(link);
            });
        }
    }

    // Event listeners para favoritar
    const starBtn = card.querySelector('.star-btn');
    if (starBtn) {
        starBtn.addEventListener('click', (e) => {
            e.preventDefault();
            toggleFavorite(link.id);
        });
    }

    // Event listeners para editar
    const editBtn = card.querySelector('.btn-edit');
    if (editBtn) {
        editBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            openEditLink(link.id);
        });
    }

    // Event listeners para deletar (only for non-blocked links)
    const deleteBtn = card.querySelector('.btn-delete');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            deleteLink(link.id);
        });
    }

    // Adicionar handler de clique para mostrar detalhes (only for non-blocked links)
    if (!link.bloqueado) {
        addLinkCardClickHandler(card, link);

        // Fase 3: Adicionar preview ao hover
        addCardPreview(card, link);
    }

    return card;
}

function addCardPreview(card, link) {
    const previewHtml = `
        <div class="card-preview">
            <div class="preview-header">📋 Prévia</div>
            <div class="preview-content">
                ${link.resumo ? escapeHtml(link.resumo) : 'Sem descrição'}
            </div>
        </div>
    `;

    // Criar elemento de preview
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = previewHtml;
    const preview = tempDiv.firstElementChild;

    // Adicionar ao card
    const cardContent = card.querySelector('.card-content');
    if (cardContent) {
        cardContent.appendChild(preview);
    }
}

function toggleCardMode(cardElement, mode) {
    if (mode === 'expanded') {
        cardElement.classList.add('expanded');
        cardElement.classList.remove('compact');
    } else if (mode === 'compact') {
        cardElement.classList.add('compact');
        cardElement.classList.remove('expanded');
    } else {
        cardElement.classList.remove('compact', 'expanded');
    }
}

// Nova função para renderizar item da lista (2 linhas compacto)
function createLinkListItem(link) {
    const item = document.createElement('div');
    item.className = 'link-list-item';

    const platform = link.plataforma || 'Link';
    const dateShort = link.data ? new Date(link.data).toLocaleDateString('pt-BR', { month: '2-digit', day: '2-digit' }) : '';
    const tags = [];
    if (link.categoria) tags.push(link.categoria);
    if (link.tema) tags.push(link.tema);

    item.innerHTML = `
        <div class="list-linha1">
            <a href="#" class="list-titulo" data-link-id="${link.id}">${escapeHtml(link.titulo || link.url)}</a>
            <div class="list-direita-l1">
                <span class="list-platform">${escapeHtml(platform)}</span>
                <span class="list-data">${dateShort}</span>
                <div class="list-btns">
                    <button class="btn-list-edit" data-link-id="${link.id}" title="Editar">✏️</button>
                    <button class="btn-list-del" data-link-id="${link.id}" title="Deletar">🗑️</button>
                </div>
            </div>
        </div>
        <div class="list-linha2">
            <div class="list-resumo">${escapeHtml(link.resumo || '')}</div>
            <div class="list-tags">
                ${tags.map(tag => `<span class="list-tag">${escapeHtml(tag)}</span>`).join('')}
            </div>
        </div>
    `;

    // Event listeners
    item.querySelector('.list-titulo').addEventListener('click', (e) => {
        e.preventDefault();
        showLinkDetail(link);
    });

    item.querySelector('.btn-list-edit').addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        openEditLink(link.id);
    });

    item.querySelector('.btn-list-del').addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        deleteLink(link.id);
    });

    return item;
}

function updatePagination() {
    const hasMore = (currentPage + 1) * ITEMS_PER_PAGE < totalResults;
    const hasPrev = currentPage > 0;

    prevPageBtn.disabled = !hasPrev;
    nextPageBtn.disabled = !hasMore;
    pageInfo.textContent = `Página ${currentPage + 1} de ${Math.ceil(totalResults / ITEMS_PER_PAGE) || 1}`;
}

function updateResultsCount() {
    resultsCount.textContent = `${totalResults} link${totalResults !== 1 ? 's' : ''} encontrado${totalResults !== 1 ? 's' : ''}`;
}

function previousPage() {
    if (currentPage > 0) {
        currentPage--;
        performSearch();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function nextPage() {
    if ((currentPage + 1) * ITEMS_PER_PAGE < totalResults) {
        currentPage++;
        performSearch();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function showLoading(show) {
    loadingEl.style.display = show ? 'block' : 'none';
}

function showToast(message, type = 'error', duration = 3000) {
    // Remove previous toast
    if (lastToast) {
        lastToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: ${type === 'error' ? '#8e2626' : type === 'success' ? '#10b981' : '#c6613f'};
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        font-size: 0.95rem;
        max-width: 400px;
        animation: slideIn 0.3s ease;
    `;

    // Add animation style if not exists
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(400px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(400px); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    document.body.appendChild(toast);
    lastToast = toast;

    setTimeout(() => {
        if (lastToast === toast) {  // Only animate if this is still the current toast
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (toast.parentNode) toast.remove();
                if (lastToast === toast) lastToast = null;
            }, 300);
        }
    }, duration);
}

function showError(message) {
    showToast(message, 'error');
}

function showSuccess(message) {
    showToast(message, 'success');
}

// Modal functions
function openNewLinkModal() {
    document.querySelectorAll('[id$="-url"], [id$="-titulo"], [id$="-resumo"], [id$="-categoria"], [id$="-plataforma"], [id$="-tema"], [id$="-autor"]').forEach(el => {
        if (el.id.startsWith('new-')) {
            el.value = '';
        }
    });
    document.getElementById('extract-status').innerHTML = '';
    newLinkModal.style.display = 'flex';
}

function closeAllModals() {
    newLinkModal.style.display = 'none';
    editLinkModal.style.display = 'none';
    confirmModal.style.display = 'none';
}

async function extractMetadata() {
    const url = document.getElementById('new-url').value.trim();
    if (!url) {
        showError('Por favor, insira uma URL');
        return;
    }

    const statusEl = document.getElementById('extract-status');
    const extractBtn = document.getElementById('extract-btn');

    statusEl.textContent = '⏳ Extraindo dados da URL...';
    statusEl.className = 'form-status loading';
    extractBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/metadata/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!response.ok) throw new Error('Falha ao extrair metadados');

        const data = await response.json();

        if (data.titulo) {
            document.getElementById('new-titulo').value = data.titulo;
        }
        if (data.resumo) {
            document.getElementById('new-resumo').value = data.resumo;
        }

        const success = data.titulo && data.titulo !== url;
        statusEl.textContent = success ? '✅ Dados extraídos com sucesso!' : '⚠️ Título/descrição não encontrados (site pode estar bloqueado)';
        statusEl.className = success ? 'form-status success' : 'form-status loading';

        // Auto-clear status after 4 seconds
        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = '';
        }, 4000);

    } catch (e) {
        statusEl.textContent = `❌ Erro ao extrair dados: ${e.message}`;
        statusEl.className = 'form-status error';

        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = '';
        }, 5000);
    } finally {
        extractBtn.disabled = false;
    }
}

async function saveNewLink() {
    const url = document.getElementById('new-url').value.trim();
    if (!url) {
        showError('URL é obrigatória');
        return;
    }

    // Verificar duplicatas
    try {
        const checkResponse = await fetch(`${API_BASE}/links/check-url?url=${encodeURIComponent(url)}`);
        if (checkResponse.ok) {
            const existingLink = await checkResponse.json();
            if (existingLink.exists) {
                showToast(`⚠️ URL já existe! Título: "${existingLink.titulo}"`, 'error', 4000);
                return;
            }
        }
    } catch (e) {
        console.warn('Erro ao verificar URL duplicada:', e);
    }

    const linkData = {
        url,
        titulo: document.getElementById('new-titulo').value || null,
        resumo: document.getElementById('new-resumo').value || null,
        categoria: document.getElementById('new-categoria').value || null,
        plataforma: document.getElementById('new-plataforma').value || null,
        tema: document.getElementById('new-tema').value || null,
        autor: document.getElementById('new-autor').value || null
    };

    try {
        const response = await fetch(`${API_BASE}/links`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(linkData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao salvar link');
        }

        const newLink = await response.json();
        console.log('✅ Link criado com sucesso:', newLink);

        closeAllModals();
        // BUG FIX: Clear form and reload immediately
        clearNewLinkForm();

        // Small delay to ensure database is updated
        await new Promise(r => setTimeout(r, 200));

        // Broadcast to other tabs
        broadcastEvent('link-added', newLink);

        // Reset to page 0 to show new link
        currentPage = 0;
        handleSearch();

    } catch (e) {
        showError(`Erro ao salvar link: ${e.message}`);
    }
}

function clearNewLinkForm() {
    document.getElementById('new-url').value = '';
    document.getElementById('new-titulo').value = '';
    document.getElementById('new-resumo').value = '';
    document.getElementById('new-categoria').value = '';
    document.getElementById('new-plataforma').value = '';
    document.getElementById('new-tema').value = '';
    document.getElementById('new-autor').value = '';
    document.getElementById('extract-status').innerHTML = '';
}

async function openEditLink(linkId) {
    try {
        const response = await fetch(`${API_BASE}/links/${linkId}`);
        const link = await response.json();

        editingLinkId = linkId;
        document.getElementById('edit-url').value = link.url;
        document.getElementById('edit-titulo').value = link.titulo || '';
        document.getElementById('edit-resumo').value = link.resumo || '';
        document.getElementById('edit-categoria').value = link.categoria || '';
        document.getElementById('edit-plataforma').value = link.plataforma || '';
        document.getElementById('edit-tema').value = link.tema || '';
        document.getElementById('edit-autor').value = link.autor || '';

        editLinkModal.style.display = 'flex';

    } catch (e) {
        showError('Erro ao carregar link');
    }
}

async function saveEditLink() {
    if (!editingLinkId) return;

    const updateData = {
        titulo: document.getElementById('edit-titulo').value || null,
        resumo: document.getElementById('edit-resumo').value || null,
        categoria: document.getElementById('edit-categoria').value || null,
        plataforma: document.getElementById('edit-plataforma').value || null,
        tema: document.getElementById('edit-tema').value || null,
        autor: document.getElementById('edit-autor').value || null
    };

    try {
        const response = await fetch(`${API_BASE}/links/${editingLinkId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });

        if (!response.ok) throw new Error('Erro ao atualizar');

        closeAllModals();
        broadcastEvent('link-updated', { id: editingLinkId });
        handleSearch();

    } catch (e) {
        showError(`Erro ao atualizar link: ${e.message}`);
    }
}

async function analyzeWithAI() {
    if (!editingLinkId) return;

    const statusEl = document.getElementById('analyze-ai-status');
    const analyzeBtn = document.getElementById('analyze-ai-btn');

    statusEl.textContent = '🤖 Analisando link com IA...';
    statusEl.className = 'form-status loading';
    analyzeBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/links/${editingLinkId}/analyze-with-ai`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao analisar');
        }

        const result = await response.json();
        const link = result.link;

        // Highlight updated fields
        const fieldsUpdated = [];
        if (link.categoria && link.categoria !== document.getElementById('edit-categoria').value) {
            document.getElementById('edit-categoria').value = link.categoria;
            fieldsUpdated.push('Categoria');
        }
        if (link.tema && link.tema !== document.getElementById('edit-tema').value) {
            document.getElementById('edit-tema').value = link.tema;
            fieldsUpdated.push('Tema');
        }
        if (link.resumo && link.resumo !== document.getElementById('edit-resumo').value) {
            document.getElementById('edit-resumo').value = link.resumo;
            fieldsUpdated.push('Resumo');
        }

        if (fieldsUpdated.length > 0) {
            statusEl.textContent = `✅ Atualizado: ${fieldsUpdated.join(', ')}`;
        } else {
            statusEl.textContent = '✅ Análise concluída (nenhuma alteração necessária)';
        }
        statusEl.className = 'form-status success';

        // Auto-clear status after 5 seconds
        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = '';
        }, 5000);

    } catch (e) {
        statusEl.textContent = `❌ ${e.message}`;
        statusEl.className = 'form-status error';

        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = '';
        }, 5000);
    } finally {
        analyzeBtn.disabled = false;
    }
}

async function suggestTagsForNew() {
    const titulo = document.getElementById('new-titulo').value.trim();
    const resumo = document.getElementById('new-resumo').value.trim();
    const statusEl = document.getElementById('suggest-tags-status');
    const btn = document.getElementById('suggest-tags-btn');

    if (!titulo) {
        showToast('⚠️ Preencha o título primeiro', 'error');
        return;
    }

    statusEl.textContent = '🤖 Gerando sugestões...';
    statusEl.style.color = '#666';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/ai/suggest-tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `${titulo}\n${resumo}`,
                limit: 5
            })
        });

        if (!response.ok) throw new Error('Erro ao gerar tags');

        const data = await response.json();
        const tags = data.tags.join(', ');

        // Se o campo categoria está vazio, usar a primeira tag
        if (!document.getElementById('new-categoria').value && data.tags.length > 0) {
            document.getElementById('new-categoria').value = data.tags[0];
        }

        // Se o campo tema está vazio, usar a segunda tag
        if (!document.getElementById('new-tema').value && data.tags.length > 1) {
            document.getElementById('new-tema').value = data.tags.slice(1).join(', ');
        }

        statusEl.textContent = `✅ Tags sugeridas: ${tags}`;
        statusEl.style.color = '#10b981';
        showToast(`✅ Tags sugeridas: ${tags}`, 'success', 3000);

        setTimeout(() => {
            statusEl.textContent = '';
        }, 5000);
    } catch (e) {
        statusEl.textContent = `❌ ${e.message}`;
        statusEl.style.color = '#ef4444';
        showToast(`❌ Erro: ${e.message}`, 'error');
    } finally {
        btn.disabled = false;
    }
}

async function suggestTagsForEdit() {
    const titulo = document.getElementById('edit-titulo').value.trim();
    const resumo = document.getElementById('edit-resumo').value.trim();
    const statusEl = document.getElementById('suggest-tags-edit-status');
    const btn = document.getElementById('suggest-tags-edit-btn');

    if (!titulo) {
        showToast('⚠️ Preencha o título primeiro', 'error');
        return;
    }

    statusEl.textContent = '🤖 Gerando sugestões...';
    statusEl.style.color = '#666';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/ai/suggest-tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `${titulo}\n${resumo}`,
                limit: 5
            })
        });

        if (!response.ok) throw new Error('Erro ao gerar tags');

        const data = await response.json();
        const tags = data.tags.join(', ');

        // Se o campo categoria está vazio, usar a primeira tag
        if (!document.getElementById('edit-categoria').value && data.tags.length > 0) {
            document.getElementById('edit-categoria').value = data.tags[0];
        }

        // Se o campo tema está vazio, usar a segunda tag
        if (!document.getElementById('edit-tema').value && data.tags.length > 1) {
            document.getElementById('edit-tema').value = data.tags.slice(1).join(', ');
        }

        statusEl.textContent = `✅ Tags sugeridas: ${tags}`;
        statusEl.style.color = '#10b981';
        showToast(`✅ Tags sugeridas: ${tags}`, 'success', 3000);

        setTimeout(() => {
            statusEl.textContent = '';
        }, 5000);
    } catch (e) {
        statusEl.textContent = `❌ ${e.message}`;
        statusEl.style.color = '#ef4444';
        showToast(`❌ Erro: ${e.message}`, 'error');
    } finally {
        btn.disabled = false;
    }
}

async function deleteLink(linkId) {
    confirmCallback = async () => {
        try {
            const response = await fetch(`${API_BASE}/links/${linkId}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Erro ao deletar');
            broadcastEvent('link-deleted', { id: linkId });
            handleSearch();
        } catch (e) {
            showError(`Erro ao deletar link: ${e.message}`);
        }
    };

    document.getElementById('confirm-message').textContent = 'Tem certeza que deseja deletar este link?';
    confirmModal.style.display = 'flex';
}

async function toggleFavorite(linkId) {
    try {
        const response = await fetch(`${API_BASE}/links/${linkId}/favorite`, { method: 'POST' });
        if (!response.ok) throw new Error('Erro ao atualizar favorito');

        const result = await response.json();
        console.log(`⭐ Favorito atualizado para ${result.favorito}`);

        broadcastEvent('favorite-toggled', { id: linkId, favorito: result.favorito });

        // BUG FIX: Reload to show updated state
        performSearch();

    } catch (e) {
        showError(`Erro: ${e.message}`);
    }
}

async function exportLinks(format) {
    try {
        const response = await fetch(`${API_BASE}/export?format=${format}`);
        if (!response.ok) throw new Error('Erro ao exportar');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `banco_de_links.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

    } catch (e) {
        showError(`Erro ao exportar: ${e.message}`);
    }
}

async function handleGitHubBackup() {
    const statusEl = document.getElementById('github-backup-status');
    statusEl.textContent = 'Enviando...';
    try {
        const response = await fetch(`${API_BASE}/github/backup`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            statusEl.textContent = `✅ Backup salvo em ${data.repo}`;
            console.log('GitHub backup:', data);
        } else {
            statusEl.textContent = `❌ ${data.detail || 'Erro no backup'}`;
        }
    } catch (e) {
        console.error('GitHub backup failed:', e);
        statusEl.textContent = '❌ Falha na conexão';
    }
}

async function handleImport(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/import`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        const successMsg = `✅ Importação concluída!\n\n📌 Importados: ${result.imported}\n🔄 Duplicatas ignoradas: ${result.duplicates}\n⚠️ Erros: ${result.errors.length}`;
        showToast(successMsg, 'success', 5000);
        alert(successMsg);
        handleSearch();

    } catch (e) {
        showError(`Erro ao importar: ${e.message}`);
    }

    // Reset input
    e.target.value = '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Função para alternar entre modo cards e lista
function toggleViewMode() {
    viewMode = viewMode === 'cards' ? 'lista' : 'cards';
    localStorage.setItem('linkViewMode', viewMode);

    // Atualizar botão de toggle
    const toggleBtn = document.getElementById('view-mode-toggle');
    if (toggleBtn) {
        toggleBtn.textContent = viewMode === 'cards' ? '📋 Modo Lista' : '🎴 Modo Cards';
    }

    // Re-renderizar links
    performSearch();
}

// Função para limpar input de busca
function clearSearchInput() {
    searchInput.value = '';
    if (suggestionsDropdown) suggestionsDropdown.remove();
}

// ===== NOVAS FUNCIONALIDADES =====

// Histórico de visualizações
let viewHistory = JSON.parse(localStorage.getItem('linkViewHistory') || '[]');
let readerModeActive = false;

// Event listeners para atalhos
document.querySelectorAll('.shortcut-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.shortcut-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');

        const shortcut = e.target.dataset.shortcut;
        handleShortcut(shortcut);
    });
});

// Modo leitor
document.getElementById('reader-mode-btn').addEventListener('click', toggleReaderMode);

function handleShortcut(shortcut) {
    currentPage = 0;
    currentSearch = '';
    currentCategory = '';
    currentPlatform = '';
    currentFavoriteFilter = false;

    switch(shortcut) {
        case 'ultimos':
            currentSearch = '';
            break;
        case 'favoritos':
            currentFavoriteFilter = true;
            break;
        case 'lidos':
            currentSearch = 'lido:true';
            break;
        case 'nao-lidos':
            currentSearch = 'lido:false';
            break;
    }

    handleSearch();
}

function toggleReaderMode() {
    readerModeActive = !readerModeActive;
    linksContainer.parentElement.classList.toggle('reader-mode', readerModeActive);
    document.getElementById('reader-mode-btn').classList.toggle('active', readerModeActive);
    showSuccess(readerModeActive ? 'Modo Leitor ativado' : 'Modo Leitor desativado');
}

// Mostrar detalhes completos do link
function showLinkDetail(link) {
    // Salvar histórico
    if (!viewHistory.find(l => l.id === link.id)) {
        viewHistory.unshift({id: link.id, titulo: link.titulo, viewedAt: new Date().toISOString()});
        if (viewHistory.length > 50) viewHistory.pop();
        localStorage.setItem('linkViewHistory', JSON.stringify(viewHistory));
    }

    // Preencher modal
    document.getElementById('detail-title').textContent = link.titulo || 'Sem título';
    document.getElementById('detail-url').innerHTML = `<a href="${escapeHtml(link.url)}" target="_blank" style="color: inherit; text-decoration: underline; cursor: pointer;">🔗 ${escapeHtml(link.url)}</a>`;
    document.getElementById('detail-category').textContent = link.categoria || '-';
    document.getElementById('detail-platform').textContent = link.plataforma || '-';
    document.getElementById('detail-author').textContent = link.autor || '-';
    document.getElementById('detail-date').textContent = link.data ? new Date(link.data).toLocaleDateString('pt-BR') : '-';
    document.getElementById('detail-rating').textContent = link.rating ? '⭐'.repeat(link.rating) + ` (${link.rating}/5)` : '-';
    document.getElementById('detail-tags').textContent = link.tags ? JSON.parse(link.tags).join(', ') : '-';
    document.getElementById('detail-description').textContent = link.resumo || 'Sem resumo disponível';
    document.getElementById('detail-theme').textContent = link.tema || '-';

    // Botões
    document.getElementById('detail-open-link-btn').onclick = () => window.open(link.url, '_blank');
    document.getElementById('detail-toggle-favorite-btn').textContent = link.favorito ? '💔 Remover de Favoritos' : '⭐ Adicionar aos Favoritos';
    document.getElementById('detail-toggle-favorite-btn').onclick = () => toggleFavorite(link.id);
    document.getElementById('detail-mark-read-btn').textContent = link.lido ? '📖 Marcar como Não Lido' : '✅ Marcar como Lido';
    document.getElementById('detail-mark-read-btn').onclick = () => markAsRead(link.id);

    // Adicionar análise da IA
    addAIAnalysisSection(link);

    // Mostrar modal
    document.getElementById('link-detail-modal').classList.add('show');
}

function closeLinkDetail() {
    document.getElementById('link-detail-modal').classList.remove('show');
}

async function markAsRead(linkId) {
    try {
        const response = await fetch(`${API_BASE}/links/${linkId}/mark-read?lido=true`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Erro ao atualizar');
        showSuccess('✅ Link marcado como lido');
        performSearch();
        closeLinkDetail();
    } catch (e) {
        showError(`Erro: ${e.message}`);
    }
}

async function analyzeLinkWithAI(link) {
    try {
        const response = await fetch(`${API_BASE}/ai/analyze-link`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                titulo: link.titulo,
                resumo: link.resumo,
                categoria: link.categoria,
                tema: link.tema,
                url: link.url,
                plataforma: link.plataforma
            })
        });

        if (!response.ok) return null;
        return await response.json();
    } catch (e) {
        console.log('AI analysis failed:', e);
        return null;
    }
}

function addAIAnalysisSection(link) {
    const bodyEl = document.querySelector('.link-detail-body');

    // Remover seção anterior se existir
    const prevAiSection = bodyEl.querySelector('.ai-analysis-section');
    if (prevAiSection) prevAiSection.remove();

    // Criar seção de análise
    const aiSection = document.createElement('div');
    aiSection.className = 'ai-analysis-section detail-section';
    aiSection.innerHTML = `
        <h3>🤖 Análise Gerada pela IA</h3>
        <div id="ai-analysis-loading" style="text-align: center; padding: 20px;">
            <div class="spinner" style="margin: 0 auto 10px;"></div>
            <p>Analisando com IA...</p>
        </div>
        <div id="ai-analysis-content" style="display: none;"></div>
    `;

    bodyEl.appendChild(aiSection);

    // Carregar análise da IA
    analyzeLinkWithAI(link).then(analysis => {
        const loadingEl = document.getElementById('ai-analysis-loading');
        const contentEl = document.getElementById('ai-analysis-content');

        if (analysis) {
            contentEl.innerHTML = `
                <div style="background: var(--bg-card); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="color: var(--primary-color); margin-top: 0;">📋 Resumo</h4>
                    <p>${analysis.summary || 'N/A'}</p>
                </div>

                <div style="background: var(--bg-card); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="color: var(--primary-color); margin-top: 0;">💡 Principais Insights</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        ${(analysis.insights || []).slice(0, 3).map(insight => `<li>${insight}</li>`).join('')}
                    </ul>
                </div>

                <div style="background: var(--bg-card); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="color: var(--primary-color); margin-top: 0;">🎯 Por Que Ler?</h4>
                    <p>${analysis.why_read || 'N/A'}</p>
                </div>

                <div style="background: var(--bg-card); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                    <h4 style="color: var(--primary-color); margin-top: 0;">🔑 Palavras-Chave</h4>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        ${(analysis.keywords || []).map(kw => `<span style="background: linear-gradient(135deg, var(--primary-color), var(--primary-dark)); color: white; padding: 6px 12px; border-radius: 16px; font-size: 0.9em;">${kw}</span>`).join('')}
                    </div>
                </div>

                <div style="background: var(--bg-card); padding: 16px; border-radius: 8px;">
                    <h4 style="color: var(--primary-color); margin-top: 0;">⏱️ Tempo Estimado de Leitura</h4>
                    <p>${analysis.estimated_time || 'N/A'}</p>
                </div>

                <p style="text-align: center; font-size: 0.8em; color: var(--text-light); margin-top: 12px;">
                    ✨ Análise gerada por IA (${analysis.model || 'Claude'})
                </p>
            `;
            loadingEl.style.display = 'none';
            contentEl.style.display = 'block';
        } else {
            loadingEl.innerHTML = '<p style="color: var(--text-light);">❌ Não foi possível gerar análise</p>';
        }
    });
}

function addLinkCardClickHandler(card, link) {
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
        if (!e.target.closest('button')) {
            showLinkDetail(link);
        }
    });
}

function toggleDarkMode() {
    const isDarkMode = document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', isDarkMode);
    showSuccess(isDarkMode ? '🌙 Modo Escuro ativado' : '☀️ Modo Claro ativado');
}

function handleKeyboardShortcuts(e) {
    // Ctrl+K or Cmd+K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
    }

    // Cmd+M (or Ctrl+M) to toggle AI chat
    if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
        e.preventDefault();
        toggleAIChat();
    }

    // Esc to clear search
    if (e.key === 'Escape' && document.activeElement === searchInput && searchInput.value) {
        searchInput.value = '';
        clearSearchBtn.classList.remove('visible');
        handleSearch();
    }
}
