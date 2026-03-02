/**
 * KitchenSync — Grocery List
 * Ephemeral shopping list with localStorage persistence,
 * recipe integration, and Instacart export.
 */

const GROCERY_STORAGE_KEY = 'ks-grocery-list';

// ============================================================================
// Data Layer (localStorage CRUD)
// ============================================================================

function getGroceryList() {
    try {
        return JSON.parse(localStorage.getItem(GROCERY_STORAGE_KEY) || '[]');
    } catch { return []; }
}

function saveGroceryList(list) {
    localStorage.setItem(GROCERY_STORAGE_KEY, JSON.stringify(list));
    updateGroceryBadge();
}

function addGroceryItem(name, quantity, unit, source) {
    const list = getGroceryList();
    const existing = list.find(i => i.name.toLowerCase() === name.trim().toLowerCase());
    if (existing) {
        if (source && existing.source && !existing.source.includes(source)) {
            existing.source += ', ' + source;
        }
        if (quantity) existing.quantity = quantity;
        if (unit) existing.unit = unit;
    } else {
        list.push({
            id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
            name: name.trim(),
            quantity: quantity || '',
            unit: unit || '',
            checked: false,
            source: source || '',
            addedAt: Date.now(),
        });
    }
    saveGroceryList(list);
    renderGroceryList();
}

function removeGroceryItem(itemId) {
    let list = getGroceryList();
    list = list.filter(i => i.id !== itemId);
    saveGroceryList(list);
    renderGroceryList();
}

function toggleGroceryItem(itemId) {
    const list = getGroceryList();
    const item = list.find(i => i.id === itemId);
    if (item) item.checked = !item.checked;
    saveGroceryList(list);
    renderGroceryList();
}

function clearCheckedItems() {
    let list = getGroceryList();
    const count = list.filter(i => i.checked).length;
    list = list.filter(i => !i.checked);
    saveGroceryList(list);
    renderGroceryList();
    showToast(`Removed ${count} checked item${count !== 1 ? 's' : ''}`, 'info');
}

function clearAllGroceryItems() {
    const list = getGroceryList();
    if (list.length === 0) return;
    if (!confirm('Clear the entire grocery list?')) return;
    saveGroceryList([]);
    renderGroceryList();
    showToast('Grocery list cleared', 'info');
}

// ============================================================================
// Recipe Integration
// ============================================================================

function addMissingToGrocery(recipe) {
    if (!recipe || !recipe.ingredients) return;
    const missing = recipe.ingredients.filter(i => !i.in_pantry);
    if (missing.length === 0) {
        showToast('All ingredients already in pantry!', 'success');
        return;
    }
    missing.forEach(ing => {
        addGroceryItem(
            ing.name,
            ing.quantity || '',
            ing.unit || '',
            recipe.name
        );
    });
    showToast(`Added ${missing.length} item${missing.length !== 1 ? 's' : ''} to grocery list`, 'success');
    updateGroceryBadge();
}

// ============================================================================
// Render
// ============================================================================

function renderGroceryList() {
    const container = document.getElementById('grocery-list-container');
    const actions = document.getElementById('grocery-actions');
    if (!container) return;

    const list = getGroceryList();

    if (list.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon-large" style="font-size:3rem;">&#x1F6D2;</div>
                <p class="empty-title">Your grocery list is empty</p>
                <span class="empty-hint">Add items above, or tap the cart icon on recipe cards to add missing ingredients</span>
            </div>`;
        if (actions) actions.style.display = 'none';
        return;
    }

    // Sort: unchecked first, then by addedAt
    const sorted = [...list].sort((a, b) => {
        if (a.checked !== b.checked) return a.checked ? 1 : -1;
        return a.addedAt - b.addedAt;
    });

    let html = '<div class="grocery-items">';
    sorted.forEach(item => {
        const qtyDisplay = item.quantity
            ? escapeHtml(String(item.quantity)) + (item.unit ? ' ' + escapeHtml(item.unit) : '')
            : '';
        const nameEncoded = encodeURIComponent(item.name);

        html += `
            <div class="grocery-item ${item.checked ? 'grocery-item-checked' : ''}" data-id="${item.id}">
                <label class="grocery-checkbox-label">
                    <input type="checkbox" class="grocery-checkbox" ${item.checked ? 'checked' : ''}
                           onchange="toggleGroceryItem('${item.id}')">
                    <span class="grocery-checkmark"></span>
                </label>
                <div class="grocery-item-info">
                    <a class="grocery-item-name" href="https://www.instacart.com/store/search/${nameEncoded}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Search on Instacart">${escapeHtml(item.name)}</a>
                    ${qtyDisplay ? `<span class="grocery-item-qty">${qtyDisplay}</span>` : ''}
                </div>
                ${item.source ? `<span class="grocery-item-source" title="${escapeHtml(item.source)}">${escapeHtml(item.source)}</span>` : ''}
                <button class="grocery-item-remove" onclick="removeGroceryItem('${item.id}')" title="Remove">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>`;
    });
    html += '</div>';
    container.innerHTML = html;

    // Update action bar
    const checkedCount = list.filter(i => i.checked).length;
    const uncheckedCount = list.length - checkedCount;

    if (actions) {
        actions.style.display = 'flex';
        const summary = document.getElementById('grocery-summary');
        if (summary) {
            summary.textContent = uncheckedCount + ' to buy' + (checkedCount > 0 ? ', ' + checkedCount + ' done' : '');
        }
        const clearCheckedBtn = document.getElementById('grocery-clear-checked');
        if (clearCheckedBtn) {
            clearCheckedBtn.style.display = checkedCount > 0 ? '' : 'none';
        }
    }

    updateGroceryBadge();
}

// ============================================================================
// Badge
// ============================================================================

function updateGroceryBadge() {
    const badge = document.getElementById('grocery-count');
    if (!badge) return;
    const list = getGroceryList();
    const unchecked = list.filter(i => !i.checked).length;
    badge.textContent = unchecked;
    badge.style.display = unchecked > 0 ? '' : 'none';
}

// ============================================================================
// Instacart Export
// ============================================================================

function copyForInstacart() {
    const list = getGroceryList().filter(i => !i.checked);
    if (list.length === 0) {
        showToast('No items to copy', 'error');
        return;
    }

    const lines = list.map(item => {
        let line = '- ';
        if (item.quantity) {
            line += item.quantity;
            if (item.unit) line += ' ' + item.unit;
            line += ' ';
        }
        line += item.name;
        return line;
    });

    const text = lines.join('\n');

    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied ' + list.length + ' items to clipboard!', 'success');
    }).catch(() => {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Copied ' + list.length + ' items to clipboard!', 'success');
    });
}

// ============================================================================
// Event Listeners
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Manual add form
    const form = document.getElementById('grocery-add-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const nameInput = document.getElementById('grocery-item-name');
            const qtyInput = document.getElementById('grocery-item-qty');
            const name = nameInput.value.trim();
            if (!name) return;
            addGroceryItem(name, qtyInput.value.trim(), '', '');
            nameInput.value = '';
            qtyInput.value = '';
            nameInput.focus();
        });
    }

    // Action buttons
    const clearCheckedBtn = document.getElementById('grocery-clear-checked');
    if (clearCheckedBtn) clearCheckedBtn.addEventListener('click', clearCheckedItems);

    const clearAllBtn = document.getElementById('grocery-clear-all');
    if (clearAllBtn) clearAllBtn.addEventListener('click', clearAllGroceryItems);

    const copyBtn = document.getElementById('grocery-copy-instacart');
    if (copyBtn) copyBtn.addEventListener('click', copyForInstacart);

    // Initial render
    renderGroceryList();
    updateGroceryBadge();
});
