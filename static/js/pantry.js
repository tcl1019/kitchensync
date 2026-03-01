/**
 * KitchenSync — Pantry Management
 */

let currentFilter = 'all';
let currentSort = 'recent';
let currentSearch = '';

// ============================================================================
// Category Meta (emoji + CSS variable mapping)
// ============================================================================

const CATEGORY_META = {
    'Vegetables': { emoji: '\u{1F96C}', cssVar: 'vegetables' },
    'Fruits':     { emoji: '\u{1F34E}', cssVar: 'fruits' },
    'Dairy':      { emoji: '\u{1F9C0}', cssVar: 'dairy' },
    'Meat':       { emoji: '\u{1F969}', cssVar: 'meat' },
    'Pantry':     { emoji: '\u{1FAD9}', cssVar: 'pantry' },
    'Frozen':     { emoji: '\u{1F9CA}', cssVar: 'frozen' },
    'Beverages':  { emoji: '\u{1F964}', cssVar: 'beverages' },
    'Other':      { emoji: '\u{1F4E6}', cssVar: 'other' },
};

function getCategoryEmoji(cat) {
    return (CATEGORY_META[cat] || CATEGORY_META['Other']).emoji;
}

function getCategoryCssVar(cat) {
    return (CATEGORY_META[cat] || CATEGORY_META['Other']).cssVar;
}

// ============================================================================
// Unit Suggestions (mirrors Python UNIT_HINTS)
// ============================================================================

const UNIT_SUGGESTIONS = {
    // Liquids
    'milk': 'gal', 'juice': 'oz', 'water': 'gal', 'soda': 'L',
    'wine': 'bottle', 'beer': 'pack', 'broth': 'oz', 'stock': 'oz',
    'oil': 'oz', 'vinegar': 'oz', 'cream': 'oz', 'lemonade': 'oz',
    // Produce by weight
    'chicken': 'lbs', 'beef': 'lbs', 'pork': 'lbs', 'turkey': 'lbs',
    'salmon': 'lbs', 'fish': 'lbs', 'steak': 'lbs', 'ground': 'lbs',
    'lamb': 'lbs', 'cheese': 'oz', 'deli': 'lbs', 'bacon': 'oz',
    // Produce by count
    'banana': 'ct', 'apple': 'ct', 'orange': 'ct', 'lemon': 'ct',
    'lime': 'ct', 'avocado': 'ct', 'peach': 'ct', 'pear': 'ct',
    'egg': 'dozen', 'onion': 'ct', 'pepper': 'ct', 'potato': 'ct',
    'tomato': 'ct', 'cucumber': 'ct', 'garlic': 'ct', 'mango': 'ct',
    // Packaged
    'cereal': 'box', 'chips': 'bag', 'crackers': 'box', 'cookies': 'box',
    'granola': 'bag', 'nuts': 'bag', 'rice': 'bag', 'pasta': 'box',
    'flour': 'bag', 'sugar': 'bag', 'fries': 'bag',
    // Canned
    'beans': 'can', 'soup': 'can', 'tuna': 'can', 'corn': 'can',
    'coconut milk': 'can',
    // Bread/baked
    'bread': 'loaf', 'bagel': 'pack', 'tortilla': 'pack', 'bun': 'pack',
    'muffin': 'pack', 'roll': 'pack', 'cinnamon roll': 'pack',
    // Spices
    'cinnamon': 'oz', 'salt': 'oz', 'paprika': 'oz',
    'cumin': 'oz', 'oregano': 'oz', 'basil': 'oz',
};

function suggestUnit(itemName) {
    const nameLower = itemName.toLowerCase();
    for (const [keyword, unit] of Object.entries(UNIT_SUGGESTIONS)) {
        if (nameLower.includes(keyword)) return unit;
    }
    return null;
}

// ============================================================================
// Time Ago Utility
// ============================================================================

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHr / 24);
    const diffWeek = Math.floor(diffDay / 7);

    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    if (diffWeek < 5) return `${diffWeek}w ago`;

    // Older than ~1 month: show short date
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[date.getMonth()]} ${date.getDate()}`;
}

function renderDates() {
    document.querySelectorAll('.grid-item-date[data-date]').forEach(el => {
        const dateStr = el.dataset.date;
        if (dateStr) {
            el.textContent = timeAgo(dateStr);
        }
    });
}

// ============================================================================
// Helpers
// ============================================================================

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

        // Collapse details panel and reset unit suggestion
        const details = document.getElementById('add-details');
        const toggle = document.getElementById('toggle-details');
        if (details && !details.classList.contains('hidden')) {
            details.classList.add('hidden');
            if (toggle) toggle.textContent = 'More options';
        }

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
            default: {
                // Use date_added if available, fallback to item ID
                const dateA = a.dataset.date || '';
                const dateB = b.dataset.date || '';
                if (dateA && dateB) return dateB.localeCompare(dateA);
                return (parseInt(b.dataset.itemId) || 0) - (parseInt(a.dataset.itemId) || 0);
            }
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
                    <div class="empty-icon-large">\u{1F9FA}</div>
                    <p class="empty-title">Your pantry is empty</p>
                    <span class="empty-hint">Add your first item above, or tap <strong>Import</strong> to bulk-add from a grocery order</span>
                </div>`;
            updateCategoryFilters({});
            return;
        }

        // Build grid items (must match Jinja template structure)
        let html = '';
        items.forEach((item, index) => {
            const cat = item.category || 'Other';
            const cssVar = getCategoryCssVar(cat);
            const emoji = getCategoryEmoji(cat);
            const rawQty = item.quantity || 1;
            const qtyDisplay = rawQty % 1 === 0 ? String(rawQty) : rawQty.toFixed(1);
            const unitDisplay = item.unit || '';
            const dateAdded = item.date_added || '';
            const showNotes = item.notes && item.notes !== 'Imported from Instacart' && item.notes !== 'Imported from screenshot';

            html += `
                <div class="grid-item" data-item-id="${item.id}" data-category="${escapeHtml(cat)}" data-name="${escapeHtml(item.name)}" data-date="${escapeHtml(dateAdded)}" style="--cat-color: var(--cat-${cssVar}); --cat-color-muted: var(--cat-${cssVar}-muted); animation-delay: ${index * 0.02}s">
                    <div class="grid-item-top">
                        <div class="grid-item-title-row">
                            <span class="grid-item-emoji">${emoji}</span>
                            <span class="grid-item-name">${escapeHtml(item.name)}</span>
                        </div>
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
                    ${showNotes ? `<div class="grid-item-notes">${escapeHtml(item.notes)}</div>` : ''}
                    <div class="grid-item-date" data-date="${escapeHtml(dateAdded)}"></div>
                </div>`;
        });

        container.innerHTML = html;

        // Render relative dates
        renderDates();

        // Re-apply view toggle after DOM rebuild
        applyView(currentView);

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
// Category Filters (with emoji + colors + counts)
// ============================================================================

function updateCategoryFilters(catCounts) {
    const container = document.getElementById('category-filters');
    const totalCount = Object.values(catCounts).reduce((a, b) => a + b, 0);

    let html = `<button class="filter-chip active" data-category="all">All <span class="chip-count">${totalCount}</span></button>`;

    const sortedCats = Object.keys(catCounts).sort();
    sortedCats.forEach(cat => {
        const meta = CATEGORY_META[cat] || CATEGORY_META['Other'];
        const catColor = `var(--cat-${meta.cssVar})`;
        const catColorMuted = `var(--cat-${meta.cssVar}-muted)`;
        html += `<button class="filter-chip" data-category="${escapeHtml(cat)}" style="--chip-color: ${catColor}; --chip-color-muted: ${catColorMuted}">${meta.emoji} ${escapeHtml(cat)} <span class="chip-count">${catCounts[cat]}</span></button>`;
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
// Multi-Screenshot Import
// ============================================================================

let selectedScreenshots = [];

function handleScreenshotSelect(files) {
    if (!files || files.length === 0) return;

    for (const file of files) {
        if (!file.type.startsWith('image/')) {
            showToast(`Skipped "${file.name}" — not an image`, 'error');
            continue;
        }
        selectedScreenshots.push(file);
    }

    if (selectedScreenshots.length === 0) {
        showToast('Please select image files', 'error');
        return;
    }

    renderScreenshotThumbnails();
    document.getElementById('screenshot-preview').classList.remove('hidden');
}

function renderScreenshotThumbnails() {
    const thumbContainer = document.getElementById('screenshot-thumbnails');
    thumbContainer.innerHTML = '';

    selectedScreenshots.forEach((file, idx) => {
        const thumb = document.createElement('div');
        thumb.className = 'screenshot-thumb';

        const img = document.createElement('img');
        img.alt = file.name;
        const reader = new FileReader();
        reader.onload = (e) => { img.src = e.target.result; };
        reader.readAsDataURL(file);

        const removeBtn = document.createElement('button');
        removeBtn.className = 'screenshot-thumb-remove';
        removeBtn.innerHTML = '&times;';
        removeBtn.title = 'Remove';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            selectedScreenshots.splice(idx, 1);
            if (selectedScreenshots.length === 0) {
                clearScreenshots();
            } else {
                renderScreenshotThumbnails();
            }
        };

        thumb.appendChild(img);
        thumb.appendChild(removeBtn);
        thumbContainer.appendChild(thumb);
    });

    // Update import button text
    const btnText = document.getElementById('screenshot-import-text');
    if (btnText) {
        btnText.textContent = selectedScreenshots.length === 1
            ? 'Import from Screenshot'
            : `Import from ${selectedScreenshots.length} Screenshots`;
    }
}

function clearScreenshots() {
    selectedScreenshots = [];
    const input = document.getElementById('screenshot-input');
    if (input) input.value = '';
    document.getElementById('screenshot-preview').classList.add('hidden');
    document.getElementById('screenshot-thumbnails').innerHTML = '';

    // Hide progress
    const progress = document.getElementById('screenshot-progress');
    if (progress) progress.classList.add('hidden');
}

async function importScreenshots() {
    if (selectedScreenshots.length === 0) {
        showToast('No screenshots selected', 'error');
        return;
    }

    const btn = document.getElementById('screenshot-import-btn');
    const loading = document.getElementById('screenshot-loading');
    const btnText = document.getElementById('screenshot-import-text');
    const progressContainer = document.getElementById('screenshot-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    btn.disabled = true;
    loading.classList.remove('hidden');
    progressContainer.classList.remove('hidden');

    let totalItemsFound = 0;
    const totalFiles = selectedScreenshots.length;

    for (let i = 0; i < totalFiles; i++) {
        const file = selectedScreenshots[i];
        const pct = ((i) / totalFiles) * 100;
        progressFill.style.width = pct + '%';
        progressText.textContent = `Processing ${i + 1} of ${totalFiles}...`;
        btnText.textContent = `Reading image ${i + 1}/${totalFiles}...`;

        try {
            const formData = new FormData();
            formData.append('image', file);

            const response = await fetch('/api/import-screenshot', {
                method: 'POST',
                body: formData
            });

            const json = await response.json();

            if (response.ok) {
                // Extract count from message like "Imported 5 items from screenshot"
                const match = (json.message || '').match(/(\d+)\s*item/);
                if (match) totalItemsFound += parseInt(match[1]);
            } else {
                showToast(`Image ${i + 1}: ${json.error || 'Failed'}`, 'error');
            }
        } catch (error) {
            showToast(`Image ${i + 1}: ${error.message}`, 'error');
        }
    }

    // Complete
    progressFill.style.width = '100%';
    progressText.textContent = 'Done!';

    if (totalItemsFound > 0) {
        const msg = totalFiles === 1
            ? `Imported ${totalItemsFound} items from screenshot`
            : `Found ${totalItemsFound} items across ${totalFiles} screenshots`;
        showToast(msg, 'success');
    } else {
        showToast('No grocery items found in the screenshots', 'error');
    }

    setTimeout(() => {
        closeModal('import-modal');
        clearScreenshots();
        refreshPantryItems();

        btn.disabled = false;
        loading.classList.add('hidden');
        btnText.textContent = 'Import from Screenshots';
        progressContainer.classList.add('hidden');
        progressFill.style.width = '0%';
    }, 600);
}

// ============================================================================
// Unit Suggestion on Item Name Input
// ============================================================================

function setupUnitSuggestion() {
    const nameInput = document.getElementById('item-name');
    const unitInput = document.getElementById('item-unit');
    const details = document.getElementById('add-details');
    const toggle = document.getElementById('toggle-details');

    if (!nameInput || !unitInput) return;

    let lastSuggested = '';

    nameInput.addEventListener('input', () => {
        const name = nameInput.value.trim();
        const suggested = suggestUnit(name);

        if (suggested && suggested !== lastSuggested) {
            // Only auto-fill if unit field is empty or still has previous suggestion
            if (!unitInput.value || unitInput.value === lastSuggested) {
                unitInput.value = suggested;
                lastSuggested = suggested;

                // Auto-expand "More options" if hidden so user sees the unit
                if (details && details.classList.contains('hidden')) {
                    details.classList.remove('hidden');
                    if (toggle) toggle.textContent = 'Less options';
                }
            }
        } else if (!suggested && unitInput.value === lastSuggested) {
            // Clear suggestion if name no longer matches
            unitInput.value = '';
            lastSuggested = '';
        }
    });
}

// ============================================================================
// View Toggle (Grid / List)
// ============================================================================

let currentView = localStorage.getItem('ks-pantry-view') || 'grid';

function setupViewToggle() {
    const container = document.getElementById('view-toggle');
    if (!container) return;

    // Apply saved view on load
    applyView(currentView);

    container.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            if (view === currentView) return;
            currentView = view;
            localStorage.setItem('ks-pantry-view', view);
            applyView(view);
        });
    });
}

function applyView(view) {
    const grid = document.getElementById('pantry-items-container');
    if (grid) {
        grid.classList.toggle('list-view', view === 'list');
    }

    // Update active button
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });
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

    // Multi-screenshot import
    const screenshotInput = document.getElementById('screenshot-input');
    if (screenshotInput) {
        screenshotInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleScreenshotSelect(e.target.files);
            }
        });
    }

    const screenshotImportBtn = document.getElementById('screenshot-import-btn');
    if (screenshotImportBtn) {
        screenshotImportBtn.addEventListener('click', importScreenshots);
    }

    // Initialize category filters from server-rendered items
    initCategoryFilters();

    // Render dates on server-rendered items
    renderDates();

    // Setup unit auto-suggestion
    setupUnitSuggestion();

    // Setup view toggle (grid/list)
    setupViewToggle();

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
