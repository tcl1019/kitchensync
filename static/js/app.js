/**
 * KitchenSync — Main Application
 */

// ============================================================================
// Utilities
// ============================================================================

async function apiCall(method, endpoint, data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) options.body = JSON.stringify(data);

    try {
        const response = await fetch(endpoint, options);
        let json;
        try {
            json = await response.json();
        } catch {
            throw new Error(response.ok ? 'Invalid response from server' : `Request failed (HTTP ${response.status}). Please try again.`);
        }
        if (!response.ok) throw new Error(json.error || `HTTP ${response.status}`);
        return json;
    } catch (error) {
        console.error('API Error:', error);
        const msg = error.message === 'Failed to fetch'
            ? 'Request timed out. Please try again.'
            : error.message;
        showToast(msg, 'error');
        throw error;
    }
}

function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('dismissing');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ============================================================================
// Tab Switching
// ============================================================================

function setupTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;

            // Update tab buttons
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            const content = document.getElementById(`tab-${target}`);
            if (content) content.classList.add('active');
        });
    });
}

// ============================================================================
// Modal Management
// ============================================================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('hidden');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('hidden');
}

function setupModalHandlers() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => modal.classList.add('hidden'));
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.add('hidden');
        });
    });
}

// ============================================================================
// Import Modal
// ============================================================================

function setupImportModal() {
    const importBtn = document.getElementById('import-btn');
    if (importBtn) {
        importBtn.addEventListener('click', () => openModal('import-modal'));
    }
}

// ============================================================================
// Add Bar Toggle
// ============================================================================

function setupAddBarToggle() {
    const toggle = document.getElementById('toggle-details');
    const details = document.getElementById('add-details');
    if (toggle && details) {
        toggle.addEventListener('click', () => {
            details.classList.toggle('hidden');
            toggle.textContent = details.classList.contains('hidden') ? 'More options' : 'Less options';
        });
    }
}

// ============================================================================
// User Management
// ============================================================================

async function setUserName(name) {
    if (!name.trim()) {
        showToast('Please enter a valid name', 'error');
        return;
    }
    try {
        await apiCall('POST', '/api/set-user', { name });
        document.getElementById('user-display').textContent = name;
        closeModal('user-modal');
        showToast(`Welcome, ${name}!`, 'success');
    } catch (error) { /* shown */ }
}

function setupUserHandlers() {
    const userBtn = document.getElementById('user-btn');
    const userInput = document.getElementById('user-name-input');
    const userSaveBtn = document.getElementById('user-save-btn');

    if (userBtn) {
        userBtn.addEventListener('click', () => {
            if (userInput) userInput.value = document.getElementById('user-display').textContent;
            openModal('user-modal');
            if (userInput) userInput.focus();
        });
    }

    if (userSaveBtn) {
        userSaveBtn.addEventListener('click', () => setUserName(userInput.value));
    }

    if (userInput) {
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') setUserName(userInput.value);
        });
    }
}

// ============================================================================
// Keyboard Shortcuts
// ============================================================================

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        const tag = (e.target.tagName || '').toLowerCase();
        const isInput = tag === 'input' || tag === 'textarea' || tag === 'select';

        // Escape: close modals or clear search
        if (e.key === 'Escape') {
            if (isInput) {
                // If in search, clear it and blur
                if (e.target.id === 'pantry-search') {
                    if (typeof clearSearch === 'function') clearSearch();
                }
                e.target.blur();
                return;
            }

            // Close any open modals
            const openModals = document.querySelectorAll('.modal:not(.hidden)');
            openModals.forEach(m => m.classList.add('hidden'));
            return;
        }

        // Don't trigger shortcuts when typing
        if (isInput) return;

        // "/" — focus search
        if (e.key === '/') {
            e.preventDefault();
            const pantryTab = document.querySelector('.tab[data-tab="pantry"]');
            if (pantryTab && !pantryTab.classList.contains('active')) {
                pantryTab.click();
            }
            const search = document.getElementById('pantry-search');
            if (search) search.focus();
            return;
        }

        // "g" — switch to grocery tab
        if (e.key === 'g') {
            e.preventDefault();
            const groceryTab = document.querySelector('.tab[data-tab="grocery"]');
            if (groceryTab) groceryTab.click();
            const groceryInput = document.getElementById('grocery-item-name');
            if (groceryInput) groceryInput.focus();
            return;
        }

        // "n" — focus add item input
        if (e.key === 'n') {
            e.preventDefault();
            const pantryTab = document.querySelector('.tab[data-tab="pantry"]');
            if (pantryTab && !pantryTab.classList.contains('active')) {
                pantryTab.click();
            }
            const nameInput = document.getElementById('item-name');
            if (nameInput) nameInput.focus();
            return;
        }
    });
}

// ============================================================================
// Category Chip Overflow Detection
// ============================================================================

function checkChipOverflow() {
    const filters = document.getElementById('category-filters');
    if (!filters) return;
    const isOverflowing = filters.scrollWidth > filters.clientWidth + 2;
    filters.classList.toggle('no-overflow', !isOverflowing);
}

// ============================================================================
// Button Hover Effect (ripple glow tracking)
// ============================================================================

function setupButtonEffects() {
    document.addEventListener('mousemove', (e) => {
        const btn = e.target.closest('.btn-primary');
        if (btn) {
            const rect = btn.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            btn.style.setProperty('--x', x + '%');
            btn.style.setProperty('--y', y + '%');
        }
    });
}

// ============================================================================
// Theme Toggle
// ============================================================================

function setupThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    const moonIcon = document.getElementById('theme-icon-moon');
    const sunIcon = document.getElementById('theme-icon-sun');
    if (!btn || !moonIcon || !sunIcon) return;

    // Determine initial theme
    const saved = localStorage.getItem('ks-theme');
    let theme;
    if (saved) {
        theme = saved;
    } else {
        theme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }
    applyTheme(theme);

    btn.addEventListener('click', () => {
        const current = document.body.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        localStorage.setItem('ks-theme', next);
    });

    function applyTheme(t) {
        document.body.setAttribute('data-theme', t);
        if (t === 'light') {
            moonIcon.classList.add('hidden');
            sunIcon.classList.remove('hidden');
        } else {
            moonIcon.classList.remove('hidden');
            sunIcon.classList.add('hidden');
        }
        // Update theme-color meta for PWA
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.content = t === 'light' ? '#F5F5F7' : '#111115';
    }
}

// ============================================================================
// Init
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    setupThemeToggle();
    setupTabs();
    setupModalHandlers();
    setupImportModal();
    setupAddBarToggle();
    setupUserHandlers();
    setupKeyboardShortcuts();
    setupButtonEffects();

    // Initial chip overflow check
    checkChipOverflow();
    window.addEventListener('resize', checkChipOverflow);
});
