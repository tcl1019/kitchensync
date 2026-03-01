/**
 * KitchenSync — Pantry Management
 */

let currentFilter = 'all';
let currentSort = 'recent';
let currentSearch = '';

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Search
// ============================================================================

function searchItems(query) {
    currentSearch = query.toLowerCase().trim();
    applyFilters();

    const clearBtn = document.getElementById('search-clear');
    if (clearBtn) clearBtn.classList.toggle('hidden', !currentSearch);
}

function clearSearch() {
    const input = document.getElementById('pantry-search');
    if (input) input.value = '';
    currentSearch = '';
    applyFilters();
    const clearBtn = document.getElementById('search-clear');
    if (clearBtn) clearBtn.classList.add('hidden');
}

// ============================================================================
// Combined Filter (search + category)
// ============================================================================

function applyFilters() {
    const items = document.querySelectorAll('.grid-item');
    let visibleCount = 0;

    items.forEach(item => {
        const matchesCategory = currentFilter === 'all' || item.dataset.category === currentFilter;
        const matchesSearch = !currentSearch || (item.dataset.name || '').toLowerCase().includes(currentSearch);

        if (matchesCategory && matchesSearch) {
            item.classList.remove('filtered-out');
            visibleCount++;
        } else {
            item.classList.add('filtered-out');
        }
    });

    // Show/hide empty search state
    const container = document.getElementById('pantry-items-container');
    let emptySearch = container.querySelector('.empty-search');
    const totalItems = container.querySelectorAll('.grid-item').length;

    if (totalItems > 0 && visibleCount === 0) {
        if (!emptySearch) {
            emptySearch = document.createElement('div');
            emptySearch.className = 'empty-search';
            emptySearch.innerHTML = '<p>No items match your filters</p>';
            container.appendChild(emptySearch);
        }
        emptySearch.style.display = '';
    } else if (emptySearch) {
        emptySearch.style.display = 'none';
    }
}

// ============================================================================
// Add Item
// ============================================================================

async function addItem() {
    const nameInput = document.getElementById('item-name');
    const name = nameInput.value.trim();
    const quantity = parseFloat(document.getElementById('item-quantity').value) || 1;
    const unit = document.getElementById('item-unit').value.trim();
    const category = document.getElementById('item-category').value;
    const notes = document.getElementById('item-notes').value.trim();

    if (!name) {
        showToast('Please enter an item name', 'error');
        return;
    }

    try {
        const result = await apiCall('POST', '/api/add-item', {
            name, quantity,
            unit: unit || null,
            category,
            notes: notes || null,
        });

        showToast(result.message, 'success');
        document.getElementById('quick-add-form').reset();
        document.getElementById('item-category').value = 'Other';
        document.getElementById('item-quantity').value = '1';
        refreshPantryItems();

        // Re-focus for rapid entry
        nameInput.focus();
    } catch (error) { /* shown */ }
}

// ============================================================================
// Remove Item
// ============================================================================

async function removeItem(itemId) {
    const el = document.querySelector(`.grid-item[data-item-id="${itemId}"]`);
    if (el) {
        el.style.transition = 'all 0.25s ease';
        el.style.opacity = '0';
        el.style.transform = 'scale(0.92)';
    }

    try {
        const result = await apiCall('POST', `/api/remove-item/${itemId}`);
        showToast(result.message, 'success');
        setTimeout(() => refreshPantryItems(), 200);
    } catch (error) {
        if (el) { el.style.opacity = ''; el.style.transform = ''; }
    }
}

// ============================================================================
// Update Quantity
// ============================================================================

async function updateQuantity(itemId, delta) {
    const el = document.querySelector(`.grid-item[data-item-id="${itemId}"]`);
    const qtyEl = el ? el.querySelector('.qty-value') : null;

    if (!qtyEl) return;

    const currentQty = parseFloat(qtyEl.textContent) || 1;
    const newQty = Math.max(0.5, currentQty + delta);
    const display = newQty % 1 === 0 ? String(newQty) : newQty.toFixed(1);

    // Optimistic update
    qtyEl.textContent = display;

    // Pulse animation
    qtyEl.classList.add('qty-pulse');
    setTimeout(() => qtyEl.classList.remove('qty-pulse'), 300);

    try {
        await apiCall('POST', `/api/update-item/${itemId}`, { quantity: newQty });
    } catch (error) {
        // Revert on error
        const revert = currentQty % 1 === 0 ? String(currentQty) : currentQty.toFixed(1);
        qtyEl.textContent = revert;
    }
}

// ============================================================================
// Sort Items
// ============================================================================

function sortItems(sortBy) {
    currentSort = sortBy;
    const container = document.getElementById('pantry-items-container');
    const items = [...container.querySelectorAll('.grid-item')];

    if (items.length === 0) return;

    items.sort((a, b) => {
        switch (sortBy) {
            case 'name':
                return (a.dataset.name || '').localeCompare(b.dataset.name || '');
            case 'category': {
                const catA = a.dataset.category || 'Other';
                const catB = b.dataset.category || 'Other';
                return catA.localeCompare(catB) || (a.dataset.name || '').localeCompare(b.dataset.name || '');
            }
            case 'recent':
            default:
                return (parseInt(b.dataset.itemId) || 0) - (parseInt(a.dataset.itemId) || 0);
        }
    });

    items.forEach(item => container.appendChild(item));
}

// ============================================================================
// Refresh Items (Grid)
// ============================================================================

async function refreshPantryItems() {
    try {
        const response = await fetch('/api/pantry-items');
        const data = await response.json();
        const container = document.getElementById('pantry-items-container');
        const items = data.items;

        // Update count badge
        document.getElementById('item-count').textContent = items.length;

        if (items.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9h18v10a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><path d="M3 9l2.45-4.9A2 2 0 017.24 3h9.52a2 2 0 011.8 1.1L21 9"/></svg>
                    </div>
                    <p>Your pantry is empty</p>
                    <span class="empty-hint">Add items above or import from Instacart</span>
                </div>`;
            updateCategoryFilters({});
            return;
        }

        // Build grid items
        let html = '';
        items.forEach((item, index) => {
            const cat = item.category || 'Other';
            const rawQty = item.quantity || 1;
            const qtyDisplay = rawQty % 1 === 0 ? String(rawQty) : rawQty.toFixed(1);
            const unitDisplay = item.unit || '';

            html += `
                <div class="grid-item" data-item-id="${item.id}" data-category="${escapeHtml(cat)}" data-name="${escapeHtml(item.name)}" style="animation-delay: ${index * 0.02}s">
                    <div class="grid-item-top">
                        <span class="grid-item-name">${escapeHtml(item.name)}</span>
                        <button class="grid-item-remove" onclick="removeItem(${item.id})" title="Remove">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                        </button>
                    </div>
                    <div class="grid-item-bottom">
                        <div class="qty-controls">
                            <button class="qty-btn qty-minus" onclick="event.stopPropagation();updateQuantity(${item.id}, -0.5)" title="Decrease">&minus;</button>
                            <span class="qty-value">${qtyDisplay}</span>${unitDisplay ? `<span class="qty-unit">${escapeHtml(unitDisplay)}</span>` : ''}
                            <button class="qty-btn qty-plus" onclick="event.stopPropagation();updateQuantity(${item.id}, 0.5)" title="Increase">+</button>
                        </div>
                        <span class="grid-item-cat">${escapeHtml(cat)}</span>
                    </div>
                    ${item.notes && item.notes !== 'Imported from Instacart' ? `<div class="grid-item-notes">${escapeHtml(item.notes)}</div>` : ''}
                </div>`;
        });

        container.innerHTML = html;

        // Extract categories with counts and update filter chips
        const catCounts = {};
        items.forEach(i => {
            const c = i.category || 'Other';
            catCounts[c] = (catCounts[c] || 0) + 1;
        });
        updateCategoryFilters(catCounts);

        // Re-apply current filters and sort
        applyFilters();
        if (currentSort !== 'recent') sortItems(currentSort);
    } catch (error) {
        console.error('Failed to refresh pantry items:', error);
    }
}

// ============================================================================
// Category Filters (with counts)
// ============================================================================

function updateCategoryFilters(catCounts) {
    const container = document.getElementById('category-filters');
    const totalCount = Object.values(catCounts).reduce((a, b) => a + b, 0);

    let html = `<button class="filter-chip active" data-category="all">All <span class="chip-count">${totalCount}</span></button>`;

    const sortedCats = Object.keys(catCounts).sort();
    sortedCats.forEach(cat => {
        html += `<button class="filter-chip" data-category="${escapeHtml(cat)}">${escapeHtml(cat)} <span class="chip-count">${catCounts[cat]}</span></button>`;
    });
    container.innerHTML = html;

    // Bind click handlers
    container.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            container.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentFilter = chip.dataset.category;
            applyFilters();
        });
    });

    // Mark current filter as active
    const active = container.querySelector(`[data-category="${currentFilter}"]`);
    if (active) {
        container.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        active.classList.add('active');
    }

    // Check overflow for gradient mask
    if (typeof checkChipOverflow === 'function') checkChipOverflow();
}

// ============================================================================
// Import Instacart
// ============================================================================

async function importInstacart() {
    const text = document.getElementById('instacart-text').value.trim();
    if (!text) {
        showToast('Please paste Instacart order text', 'error');
        return;
    }

    const btn = document.querySelector('#instacart-form button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> Importing...';

    try {
        const result = await apiCall('POST', '/api/import-instacart', { text });
        showToast(result.message, 'success');
        document.getElementById('instacart-text').value = '';
        closeModal('import-modal');
        refreshPantryItems();
    } catch (error) { /* shown */ }
    finally {
        btn.disabled = false;
        btn.textContent = 'Import Items';
    }
}

// ============================================================================
// Clear Pantry
// ============================================================================

async function clearPantry() {
    if (!confirm('Clear ALL items from the pantry? This cannot be undone.')) return;

    try {
        const result = await apiCall('POST', '/api/clear-pantry');
        showToast(result.message, 'success');
        currentFilter = 'all';
        currentSearch = '';
        const searchInput = document.getElementById('pantry-search');
        if (searchInput) searchInput.value = '';
        const clearBtn = document.getElementById('search-clear');
        if (clearBtn) clearBtn.classList.add('hidden');
        refreshPantryItems();
    } catch (error) { /* shown */ }
}

// ============================================================================
// Screenshot Import
// ============================================================================

let selectedScreenshot = null;

function handleScreenshotSelect(file) {
    if (!file || !file.type.startsWith('image/')) {
        showToast('Please select an image file', 'error');
        return;
    }

    selectedScreenshot = file;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('screenshot-img').src = e.target.result;
        document.getElementById('screenshot-preview').classList.remove('hidden');
        document.getElementById('screenshot-upload-area').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function clearScreenshot() {
    selectedScreenshot = null;
    document.getElementById('screenshot-input').value = '';
    document.getElementById('screenshot-preview').classList.add('hidden');
    document.getElementById('screenshot-upload-area').style.display = 'flex';
}

async function importScreenshot() {
    if (!selectedScreenshot) {
        showToast('No screenshot selected', 'error');
        return;
    }

    const btn = document.getElementById('screenshot-import-btn');
    const loading = document.getElementById('screenshot-loading');
    const btnText = document.getElementById('screenshot-import-text');

    btn.disabled = true;
    loading.classList.remove('hidden');
    btnText.textContent = 'Reading items...';

    try {
        const formData = new FormData();
        formData.append('image', selectedScreenshot);

        const response = await fetch('/api/import-screenshot', {
            method: 'POST',
            body: formData
        });

        const json = await response.json();

        if (!response.ok) {
            throw new Error(json.error || `HTTP ${response.status}`);
        }

        showToast(json.message, 'success');
        closeModal('import-modal');
        clearScreenshot();
        refreshPantryItems();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        btn.disabled = false;
        loading.classList.add('hidden');
        btnText.textContent = 'Import from Screenshot';
    }
}

// ============================================================================
// Event Listeners
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    const quickAddForm = document.getElementById('quick-add-form');
    if (quickAddForm) {
        quickAddForm.addEventListener('submit', (e) => {
            e.preventDefault();
            addItem();
        });
    }

    const instacartForm = document.getElementById('instacart-form');
    if (instacartForm) {
        instacartForm.addEventListener('submit', (e) => {
            e.preventDefault();
            importInstacart();
        });
    }

    const clearPantryBtn = document.getElementById('clear-pantry-btn');
    if (clearPantryBtn) clearPantryBtn.addEventListener('click', clearPantry);

    // Search
    const searchInput = document.getElementById('pantry-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => searchItems(e.target.value));
    }

    const searchClearBtn = document.getElementById('search-clear');
    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', () => {
            clearSearch();
            document.getElementById('pantry-search').focus();
        });
    }

    // Sort
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => sortItems(e.target.value));
    }

    // Screenshot import
    const screenshotInput = document.getElementById('screenshot-input');
    if (screenshotInput) {
        screenshotInput.addEventListener('change', (e) => {
            if (e.target.files[0]) handleScreenshotSelect(e.target.files[0]);
        });
    }

    const screenshotImportBtn = document.getElementById('screenshot-import-btn');
    if (screenshotImportBtn) {
        screenshotImportBtn.addEventListener('click', importScreenshot);
    }

    // Initialize category filters from server-rendered items
    initCategoryFilters();

    // Focus add input
    setTimeout(() => {
        const nameInput = document.getElementById('item-name');
        if (nameInput) nameInput.focus();
    }, 100);
});

/**
 * Initialize category filters from existing DOM grid items
 */
function initCategoryFilters() {
    const items = document.querySelectorAll('.grid-item[data-category]');
    const catCounts = {};
    [...items].forEach(i => {
        const cat = i.dataset.category;
        catCounts[cat] = (catCounts[cat] || 0) + 1;
    });
    if (Object.keys(catCounts).length > 0) {
        updateCategoryFilters(catCounts);
    }
}
