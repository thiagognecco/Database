// Banco de Links - Frontend Logic

const API_BASE = '/api';
let currentPage = 0;
const ITEMS_PER_PAGE = 12;
let currentSearch = '';
let currentCategory = '';
let currentPlatform = '';
let currentFavoriteFilter = false;

// Modo de visualização (cards ou lista) - padrão lista para mostrar layout compacto
let viewMode = localStorage.getItem('linkViewMode') || 'lista';

// DOM Elements
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search-btn');
const categoryFilter = document.getElementById('category-filter');
const platformFilter = document.getElementById('platform-filter');
const favoritesFilter = document.getElementById('favorites-filter');
const linksContainer = document.getElementById('links-container');
const loadingEl = document.getElementById('loading');
const emptyStateEl = document.getElementById('empty-state');
const resultsCount = document.getElementById('results-count');
const newLinkBtn = document.getElementById('new-link-btn');
const newLinkModal = document.getElementById('new-link-modal');
const editLinkModal = document.getElementById('edit-link-modal');
const confirmModal = document.getElementById('confirm-modal');
const paginationEl = document.getElementById('pagination');
const prevPageBtn = document.getElementById('prev-page-btn');
const nextPageBtn = document.getElementById('next-page-btn');
const pageInfo = document.getElementById('page-info');
const categoriesList = document.getElementById('categories-list');
const categoriesBar = document.querySelector('.categories-bar');

let totalResults = 0;
let categoriesData = {};
let editingLinkId = null;
let confirmCallback = null;
let suggestionsDropdown = null;

// Init
document.addEventListener('DOMContentLoaded', () => {
    init();
});

async function init() {
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

    // Categories bar "Todas" button
    document.querySelector('[data-category=""]')?.addEventListener('click', () => selectCategory(''));

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

    // Confirm modal
    document.getElementById('confirm-cancel-btn').addEventListener('click', closeAllModals);
    document.getElementById('confirm-yes-btn').addEventListener('click', () => {
        if (confirmCallback) confirmCallback();
        closeAllModals();
    });

    // Initial search
    handleSearch();
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
    document.querySelector(`[data-category=""]`)?.classList.add('active');

    if (categoryName) {
        document.querySelector(`[data-category="${categoryName}"]`)?.classList.add('active');
        categoryFilter.value = categoryName;
    } else {
        categoryFilter.value = '';
        document.querySelector(`[data-category=""]`)?.classList.add('active');
    }

    performSearch();
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
        links.forEach(link => {
            const card = createLinkCard(link);
            linksContainer.appendChild(card);
        });
    }
}

function createLinkCard(link) {
    const card = document.createElement('div');
    card.className = 'link-card';

    const platform = link.plataforma || 'Link';
    const date = link.data ? new Date(link.data).toLocaleDateString('pt-BR') : '';

    card.innerHTML = `
        <div class="card-header">
            <div>
                <span class="platform-badge">${escapeHtml(platform)}</span>
            </div>
            <button class="star-btn ${link.favorito ? 'favorite' : ''}" data-id="${link.id}" title="Favoritar">
                ${link.favorito ? '⭐' : '☆'}
            </button>
        </div>
        <div class="card-title">
            <a href="${escapeHtml(link.url)}" target="_blank">${escapeHtml(link.titulo || link.url)}</a>
        </div>
        <div class="card-meta">
            ${link.autor ? `<div class="meta-item">👤 ${escapeHtml(link.autor)}</div>` : ''}
            ${date ? `<div class="meta-item">📅 ${date}</div>` : ''}
        </div>
        ${link.resumo ? `<div class="card-description">${escapeHtml(link.resumo.substring(0, 150))}${link.resumo.length > 150 ? '...' : ''}</div>` : ''}
        <div class="card-badges">
            ${link.categoria ? `<span class="badge badge-categoria">${escapeHtml(link.categoria)}</span>` : ''}
            ${link.tema ? `<span class="badge badge-tema">${escapeHtml(link.tema)}</span>` : ''}
        </div>
        <div class="card-url"><small>${escapeHtml(link.url.substring(0, 60))}${link.url.length > 60 ? '...' : ''}</small></div>
        <div class="card-actions">
            <button class="btn btn-small btn-edit" data-link-id="${link.id}">✏️ Editar</button>
            <button class="btn btn-small btn-secondary btn-delete" data-link-id="${link.id}">🗑️ Deletar</button>
        </div>
    `;

    // Event listeners para favoritar
    card.querySelector('.star-btn').addEventListener('click', (e) => {
        e.preventDefault();
        toggleFavorite(link.id);
    });

    // Event listeners para editar e deletar
    card.querySelector('.btn-edit').addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        openEditLink(link.id);
    });

    card.querySelector('.btn-delete').addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        deleteLink(link.id);
    });

    // Adicionar handler de clique para mostrar detalhes
    addLinkCardClickHandler(card, link);

    return card;
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
            <a href="${escapeHtml(link.url)}" class="list-titulo" target="_blank">${escapeHtml(link.titulo || link.url)}</a>
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

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
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

async function deleteLink(linkId) {
    confirmCallback = async () => {
        try {
            const response = await fetch(`${API_BASE}/links/${linkId}`, { method: 'DELETE' });
            if (!response.ok) throw new Error('Erro ao deletar');
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

        alert(`Importação concluída!\n\nImportados: ${result.imported}\nDuplicatas ignoradas: ${result.duplicates}\nErros: ${result.errors.length}`);
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
    document.getElementById('detail-url').textContent = link.url;
    document.getElementById('detail-url').onclick = () => window.open(link.url, '_blank');
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

// Modificar createLinkCard para adicionar clique
function addLinkCardClickHandler(card, link) {
    card.style.cursor = 'pointer';
    card.addEventListener('click', (e) => {
        if (!e.target.closest('button')) {
            showLinkDetail(link);
        }
    });
}
