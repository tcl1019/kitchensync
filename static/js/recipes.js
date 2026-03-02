/**
 * KitchenSync — Recipe Suggestions
 * Rich cards, preference chips, meal type filtering, Surprise Me,
 * Favorites, History, Cooking Mode, Provenance badges
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Preference State
// ============================================================================

let selectedTags = [];
let selectedMealType = 'all';

// ============================================================================
// Recipe Accumulation State
// ============================================================================

const MAX_VISIBLE_GENERATIONS = 3;
window.allRecipeGenerations = [];

const MEAL_GROUPS = {
    'breakfast': { label: 'Breakfast', order: 0 },
    'main':      { label: 'Lunch & Dinner', order: 1 },
    'side':      { label: 'Sides & Snacks', order: 2 },
    'snack':     { label: 'Sides & Snacks', order: 2 },
};

function groupRecipesByMealType(recipes) {
    const groups = {};
    recipes.forEach((recipe, index) => {
        const g = MEAL_GROUPS[recipe.meal_type || 'main'] || MEAL_GROUPS['main'];
        if (!groups[g.label]) groups[g.label] = { label: g.label, order: g.order, items: [] };
        groups[g.label].items.push({ recipe, index });
    });
    return Object.values(groups).sort((a, b) => a.order - b.order);
}

function setupPreferenceChips() {
    // Dietary / style chips (multi-select toggles)
    document.querySelectorAll('#pref-chips .pref-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const tag = chip.dataset.tag;
            chip.classList.toggle('active');
            if (chip.classList.contains('active')) {
                if (!selectedTags.includes(tag)) selectedTags.push(tag);
            } else {
                selectedTags = selectedTags.filter(t => t !== tag);
            }
        });
    });

    // Meal type pills (single-select)
    document.querySelectorAll('#pref-meal-types .pref-meal-type').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('#pref-meal-types .pref-meal-type').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            selectedMealType = pill.dataset.meal;
        });
    });
}

function buildPreferences() {
    const prefs = {};
    if (selectedTags.length > 0) prefs.tags = selectedTags;
    if (selectedMealType !== 'all') prefs.meal_types = [selectedMealType];
    return prefs;
}

// ============================================================================
// Favorites (localStorage)
// ============================================================================

function getFavorites() {
    try {
        return JSON.parse(localStorage.getItem('ks-favorites') || '[]');
    } catch { return []; }
}

function saveFavorites(favs) {
    localStorage.setItem('ks-favorites', JSON.stringify(favs));
}

function isFavorite(recipe) {
    const favs = getFavorites();
    return favs.some(f => f.name === recipe.name);
}

function toggleFavorite(recipe) {
    let favs = getFavorites();
    const idx = favs.findIndex(f => f.name === recipe.name);
    if (idx >= 0) {
        favs.splice(idx, 1);
    } else {
        favs.push({ ...recipe, savedAt: Date.now() });
    }
    saveFavorites(favs);
    return idx < 0; // true if now favorited
}

function toggleFavoriteCard(index) {
    if (!window.currentRecipes || !window.currentRecipes[index]) return;
    const recipe = window.currentRecipes[index];
    const nowFav = toggleFavorite(recipe);

    // Update all matching fav buttons across all grids
    const cards = document.querySelectorAll(`#recipes-container .recipe-card[data-name="${CSS.escape(recipe.name)}"]`);
    cards.forEach(card => {
        const btn = card.querySelector('.recipe-fav-btn');
        if (btn) btn.classList.toggle('active', nowFav);
    });

    showToast(nowFav ? 'Saved to favorites!' : 'Removed from favorites', nowFav ? 'success' : 'info');
}

function showRecipeFromGen(genIdx, recipeIdx) {
    const gen = window.allRecipeGenerations[genIdx];
    if (!gen || !gen.recipes[recipeIdx]) return;
    window.currentRecipes = gen.recipes;
    showRecipeDetail(recipeIdx);
}

function toggleFavoriteFromGen(genIdx, recipeIdx) {
    const gen = window.allRecipeGenerations[genIdx];
    if (!gen || !gen.recipes[recipeIdx]) return;
    window.currentRecipes = gen.recipes;
    toggleFavoriteCard(recipeIdx);
}

function addToGroceryFromGen(genIdx, recipeIdx) {
    const gen = window.allRecipeGenerations[genIdx];
    if (!gen || !gen.recipes[recipeIdx]) return;
    addMissingToGrocery(gen.recipes[recipeIdx]);
}

function toggleFavoriteModal() {
    if (!window.currentRecipe) return;
    const nowFav = toggleFavorite(window.currentRecipe);
    const btn = document.getElementById('recipe-modal-fav');
    if (btn) btn.classList.toggle('active', nowFav);
    showToast(nowFav ? 'Saved to favorites!' : 'Removed from favorites', nowFav ? 'success' : 'info');
}

// ============================================================================
// Recipe History (localStorage)
// ============================================================================

const MAX_HISTORY = 20;

function getRecipeHistory() {
    try {
        return JSON.parse(localStorage.getItem('ks-recipe-history') || '[]');
    } catch { return []; }
}

function addToHistory(recipes, prompt, preferences) {
    let history = getRecipeHistory();
    history.unshift({
        recipes,
        prompt: prompt || '',
        preferences: preferences || {},
        timestamp: Date.now(),
    });
    if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
    localStorage.setItem('ks-recipe-history', JSON.stringify(history));
}

function showRecipeHistory() {
    const container = document.getElementById('recipes-container');
    const history = getRecipeHistory();

    if (history.length === 0) {
        container.innerHTML = `
            <div class="recipes-hero">
                <div class="recipes-hero-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
                <h2>No History Yet</h2>
                <p>Generate some recipes and they'll show up here!</p>
            </div>`;
        return;
    }

    let html = `
        <div class="recipes-header">
            <h2>Recipe History</h2>
            <button class="btn-secondary" onclick="clearRecipeHistory()">Clear History</button>
        </div>`;

    history.forEach((entry, groupIdx) => {
        const ago = timeAgoShort(entry.timestamp);
        const label = entry.prompt ? `"${escapeHtml(entry.prompt)}"` : 'Generated recipes';

        html += `
            <div class="recipe-history-group">
                <div class="recipe-history-timestamp">
                    <span>${ago}</span>
                    <span class="recipe-history-label">${label}</span>
                </div>
                <div class="recipe-grid">`;

        entry.recipes.forEach((recipe, recipeIdx) => {
            const totalIngredients = recipe.ingredients ? recipe.ingredients.length : 0;
            const pantryCount = recipe.ingredients ? recipe.ingredients.filter(i => i.in_pantry).length : 0;
            const readiness = totalIngredients > 0 ? Math.round((pantryCount / totalIngredients) * 100) : 0;
            const mealType = recipe.meal_type || 'main';

            html += `
                <div class="recipe-card" onclick="showHistoryRecipeDetail(${groupIdx}, ${recipeIdx})" data-readiness="${readiness}">
                    ${recipe.thumbnail ? `<img class="recipe-card-thumb" src="${escapeHtml(recipe.thumbnail)}" alt="${escapeHtml(recipe.name)}" loading="lazy">` : ''}
                    <div class="recipe-card-meta">
                        <span class="meal-type-pill" data-type="${mealType}">${mealType}</span>
                        ${(recipe.source === 'themealdb' || recipe.source === 'api-ninjas') ? `<span class="recipe-source-badge recipe-source-real">Based on real recipe</span>` : `<span class="recipe-source-badge recipe-source-ai">AI Original</span>`}
                    </div>
                    <div class="recipe-name">${escapeHtml(recipe.name)}</div>
                    <div class="recipe-desc">${escapeHtml(recipe.description)}</div>
                </div>`;
        });

        html += '</div></div>';
    });

    container.innerHTML = html;
}

function showHistoryRecipeDetail(groupIdx, recipeIdx) {
    const history = getRecipeHistory();
    if (!history[groupIdx] || !history[groupIdx].recipes[recipeIdx]) return;
    window.currentRecipes = history[groupIdx].recipes;
    showRecipeDetail(recipeIdx);
}

function clearRecipeHistory() {
    localStorage.removeItem('ks-recipe-history');
    showRecipeHistory();
    showToast('History cleared', 'info');
}

function timeAgoShort(ts) {
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(ts).toLocaleDateString();
}

// ============================================================================
// Skeleton Loading
// ============================================================================

function showRecipeSkeletons() {
    const container = document.getElementById('recipes-container');
    const skeletonHtml = `
        <div id="recipe-skeleton-block">
            <div class="recipes-header">
                <h2>Generating recipes...</h2>
            </div>
            <div class="recipe-grid">
                ${[0,1,2,3].map(i => `
                    <div class="recipe-card skeleton" style="animation-delay: ${i * 0.1}s">
                        <div class="skeleton-line skeleton-title"></div>
                        <div class="skeleton-line skeleton-desc"></div>
                        <div class="skeleton-line skeleton-desc short"></div>
                        <div class="skeleton-line skeleton-meta"></div>
                    </div>
                `).join('')}
            </div>
        </div>`;

    if (window.allRecipeGenerations && window.allRecipeGenerations.length > 0) {
        // Prepend skeletons above existing generations
        container.insertAdjacentHTML('afterbegin', skeletonHtml);
    } else {
        container.innerHTML = skeletonHtml;
    }
}

// ============================================================================
// Suggest Recipes
// ============================================================================

async function suggestRecipes() {
    const btn = document.getElementById('suggest-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span> Generating...';
    }

    showRecipeSkeletons();

    const preferences = buildPreferences();
    const promptEl = document.getElementById('recipe-prompt');
    const prompt = promptEl ? promptEl.value.trim() : '';

    try {
        const result = await apiCall('POST', '/api/suggest-recipes', {
            preferences,
            prompt: prompt || undefined
        });
        // Accumulate: prepend new generation, cap at MAX
        window.allRecipeGenerations.unshift({
            recipes: result.recipes,
            timestamp: Date.now(),
            prompt: prompt || ''
        });
        if (window.allRecipeGenerations.length > MAX_VISIBLE_GENERATIONS) {
            window.allRecipeGenerations = window.allRecipeGenerations.slice(0, MAX_VISIBLE_GENERATIONS);
        }
        window.currentRecipes = result.recipes;
        displayAllGenerations();
        showToast(`Generated ${result.count} recipe suggestions!`, 'success');

        // Save to history
        addToHistory(result.recipes, prompt, preferences);

        // Auto-surprise if triggered from Surprise Me
        if (window.autoSurprise && result.recipes && result.recipes.length > 0) {
            window.autoSurprise = false;
            const idx = Math.floor(Math.random() * result.recipes.length);
            setTimeout(() => showRecipeDetail(idx), 400);
        }
    } catch (error) {
        const container = document.getElementById('recipes-container');
        container.innerHTML = `
            <div class="recipes-hero">
                <div class="recipes-hero-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c1.5 0 2.5 1 3 2 .5-1 1.5-2 3-2 2 0 4 1.5 4 4 0 3.5-3 6-7 9.5C11 12.5 8 9.5 8 6c0-2.5 2-4 4-4z"/><path d="M8 6c-2 0-4 1.5-4 4 0 3.5 3 6 7 9.5"/><line x1="2" y1="21" x2="22" y2="21"/></svg>
                </div>
                <p style="margin-bottom:1rem;">Could not generate recipes. Please try again.</p>
            </div>`;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Generate Recipes`;
        }
    }
}

// ============================================================================
// Surprise Me
// ============================================================================

function surpriseMe() {
    if (window.currentRecipes && window.currentRecipes.length > 0) {
        const idx = Math.floor(Math.random() * window.currentRecipes.length);
        showRecipeDetail(idx);
        showToast('Chef\'s choice!', 'info');
    } else {
        window.autoSurprise = true;
        suggestRecipes();
        showToast('Generating a surprise...', 'info');
    }
}

// ============================================================================
// Display Recipes — Rich Cards
// ============================================================================

function difficultyDots(level) {
    const map = { easy: 1, medium: 2, hard: 3 };
    const n = map[level] || 1;
    let html = '<span class="recipe-difficulty" title="' + (level || 'easy') + '">';
    for (let i = 1; i <= 3; i++) {
        html += `<span class="diff-dot${i <= n ? ' filled' : ''}"></span>`;
    }
    html += '</span>';
    return html;
}

function buildRecipeCardHTML(recipe, index, genIdx) {
    const totalIngredients = recipe.ingredients ? recipe.ingredients.length : 0;
    const pantryCount = recipe.ingredients ? recipe.ingredients.filter(i => i.in_pantry).length : 0;
    const toBuy = totalIngredients - pantryCount;
    const readiness = totalIngredients > 0 ? Math.round((pantryCount / totalIngredients) * 100) : 0;
    const mealType = recipe.meal_type || 'main';
    const cookTime = recipe.cook_time || '';
    const difficulty = recipe.difficulty || 'easy';
    const tags = recipe.tags || [];
    const isFav = isFavorite(recipe);
    const source = recipe.source || 'ai';
    const sourceName = recipe.source_name || '';
    const thumbnail = recipe.thumbnail || '';

    return `
        <div class="recipe-card" onclick="showRecipeFromGen(${genIdx}, ${index})" data-readiness="${readiness}" data-name="${escapeHtml(recipe.name)}" style="animation-delay: ${index * 0.06}s">
            ${thumbnail ? `<img class="recipe-card-thumb" src="${escapeHtml(thumbnail)}" alt="${escapeHtml(recipe.name)}" loading="lazy">` : ''}
            <button class="recipe-fav-btn ${isFav ? 'active' : ''}" onclick="event.stopPropagation(); toggleFavoriteFromGen(${genIdx}, ${index})" title="${isFav ? 'Remove from favorites' : 'Save recipe'}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
            </button>
            <div class="recipe-card-meta">
                <span class="meal-type-pill" data-type="${mealType}">${mealType}</span>
                ${cookTime ? `<span class="recipe-cook-time">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    ${escapeHtml(cookTime)}
                </span>` : ''}
                ${difficultyDots(difficulty)}
            </div>
            <div class="recipe-name">${escapeHtml(recipe.name)}</div>
            <div class="recipe-desc">${escapeHtml(recipe.description)}</div>
            ${(source === 'themealdb' || source === 'api-ninjas') && sourceName ? `<div class="recipe-source"><span class="recipe-source-badge recipe-source-real">Based on ${escapeHtml(sourceName)}</span></div>` : source === 'ai' ? `<div class="recipe-source"><span class="recipe-source-badge recipe-source-ai">AI Original</span></div>` : ''}
            ${tags.length > 0 ? `<div class="recipe-tags">${tags.map(t => `<span class="recipe-tag">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
            <div class="recipe-badges">
                <span class="recipe-pantry-badge">${pantryCount}/${totalIngredients} in pantry</span>
                ${toBuy > 0
                    ? `<span class="recipe-buy-badge">${toBuy} to buy</span>`
                    : '<span class="recipe-ready-badge">Ready to cook!</span>'}
                ${recipe.instructions ? `<span class="recipe-meta-steps">${recipe.instructions.length} steps</span>` : ''}
                ${toBuy > 0
                    ? `<button class="recipe-cart-btn" onclick="event.stopPropagation(); addToGroceryFromGen(${genIdx}, ${index})" title="Add ${toBuy} missing to grocery list">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                       </button>`
                    : ''}
            </div>
            <div class="recipe-readiness-bar">
                <div class="readiness-fill" style="width:${readiness}%" data-pct="${readiness}"></div>
            </div>
        </div>`;
}

function buildRecipeGroupHTML(recipes, genIdx) {
    if (selectedMealType !== 'all') {
        // Flat grid when filtering to single meal type
        let html = '<div class="recipe-grid">';
        recipes.forEach((recipe, idx) => { html += buildRecipeCardHTML(recipe, idx, genIdx); });
        html += '</div>';
        return html;
    }
    // Grouped view
    const groups = groupRecipesByMealType(recipes);
    let html = '';
    groups.forEach(group => {
        html += `<div class="recipe-meal-group">`;
        html += `<h3 class="recipe-group-header">${group.label}</h3>`;
        html += `<div class="recipe-grid">`;
        group.items.forEach(({ recipe, index }) => {
            html += buildRecipeCardHTML(recipe, index, genIdx);
        });
        html += `</div></div>`;
    });
    return html;
}

function displayAllGenerations() {
    const container = document.getElementById('recipes-container');
    const gens = window.allRecipeGenerations;

    if (!gens || gens.length === 0) {
        container.innerHTML = `
            <div class="recipes-hero">
                <p>No recipes generated. Try again!</p>
            </div>`;
        return;
    }

    let html = `
        <div class="recipes-header">
            <h2>Your Recipes</h2>
            <div class="recipes-header-actions">
                <button class="btn-secondary" onclick="suggestRecipes()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                    Regenerate
                </button>
            </div>
        </div>
        <div class="recipe-filter-bar" id="recipe-filter-bar">
            <button class="recipe-filter active" data-filter="all" onclick="filterRecipeCards('all')">All</button>
            <button class="recipe-filter" data-filter="ready" onclick="filterRecipeCards('ready')">Ready to Cook</button>
            <button class="recipe-filter" data-filter="saved" onclick="filterRecipeCards('saved')">Saved</button>
        </div>`;

    gens.forEach((gen, genIdx) => {
        if (genIdx > 0) {
            const ago = timeAgoShort(gen.timestamp);
            const label = gen.prompt ? escapeHtml(gen.prompt) : 'Previous';
            html += `<div class="generation-divider">
                <span class="generation-divider-label">${ago} &mdash; ${label}</span>
            </div>`;
        }
        html += buildRecipeGroupHTML(gen.recipes, genIdx);
    });

    container.innerHTML = html;
}

// Backward-compatible wrapper used by history view
function displayRecipes(recipes) {
    window.allRecipeGenerations = [{ recipes, timestamp: Date.now(), prompt: '' }];
    window.currentRecipes = recipes;
    displayAllGenerations();

    // Show saved recipes notice if favorites exist
    const favs = getFavorites();
    if (favs.length > 0) {
        const savedCount = recipes.filter(r => isFavorite(r)).length;
        if (savedCount > 0) {
            showToast(`${savedCount} saved recipe${savedCount > 1 ? 's' : ''} in results`, 'info');
        }
    }
}

// ============================================================================
// Post-Generation Filter (client-side)
// ============================================================================

function filterRecipeCards(filter) {
    // Update active filter button
    document.querySelectorAll('.recipe-filter').forEach(f => f.classList.remove('active'));
    const activeBtn = document.querySelector(`.recipe-filter[data-filter="${filter}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    // Show/hide cards
    const cards = document.querySelectorAll('#recipes-container .recipe-card');
    const favs = filter === 'saved' ? getFavorites() : [];
    cards.forEach(card => {
        if (filter === 'all') {
            card.style.display = '';
        } else if (filter === 'ready') {
            card.style.display = card.dataset.readiness === '100' ? '' : 'none';
        } else if (filter === 'saved') {
            const name = card.dataset.name;
            card.style.display = favs.some(f => f.name === name) ? '' : 'none';
        }
    });

    // Hide group headers when all cards in the group are hidden
    document.querySelectorAll('#recipes-container .recipe-meal-group').forEach(group => {
        const groupCards = group.querySelectorAll('.recipe-card');
        const anyVisible = Array.from(groupCards).some(c => c.style.display !== 'none');
        group.style.display = anyVisible ? '' : 'none';
    });
}

// ============================================================================
// Recipe Detail
// ============================================================================

function showRecipeDetail(index) {
    if (!window.currentRecipes || !window.currentRecipes[index]) return;
    const recipe = window.currentRecipes[index];

    document.getElementById('recipe-title').textContent = recipe.name;
    document.getElementById('recipe-description').textContent = recipe.description;

    // Source badge in modal
    const sourceBadge = document.getElementById('recipe-source-badge');
    if (sourceBadge) {
        if ((recipe.source === 'themealdb' || recipe.source === 'api-ninjas') && recipe.source_name) {
            sourceBadge.className = 'recipe-source-badge recipe-source-real';
            sourceBadge.textContent = `Based on ${recipe.source_name}`;
            sourceBadge.style.display = '';
        } else if (recipe.source === 'ai') {
            sourceBadge.className = 'recipe-source-badge recipe-source-ai';
            sourceBadge.textContent = 'AI Original';
            sourceBadge.style.display = '';
        } else {
            sourceBadge.style.display = 'none';
        }
    }

    // Favorite button state in modal
    const favBtn = document.getElementById('recipe-modal-fav');
    if (favBtn) favBtn.classList.toggle('active', isFavorite(recipe));

    // Ingredients
    const ingredientsList = document.getElementById('recipe-ingredients');
    let ingredientsHtml = '';
    if (recipe.ingredients) {
        recipe.ingredients.forEach((ing, ingIdx) => {
            const cls = ing.in_pantry ? 'ingredient-in-pantry' : 'ingredient-to-buy';
            const qty = ing.quantity && ing.unit ? `${ing.quantity} ${ing.unit}` : (ing.quantity || '');
            ingredientsHtml += `
                <li class="${cls}">
                    <strong>${escapeHtml(ing.name)}</strong>
                    ${qty ? `<span class="ingredient-qty">${qty}</span>` : ''}
                    ${!ing.in_pantry ? `<button class="btn-quick-add" onclick="event.stopPropagation();quickAddIngredient('${escapeHtml(ing.name).replace(/'/g, "\\'")}', '${escapeHtml(ing.quantity || '1').replace(/'/g, "\\'")}', '${escapeHtml(ing.unit || '').replace(/'/g, "\\'")}', this)" title="Add to pantry">+ Add</button>` : ''}
                </li>`;
        });
    }
    ingredientsList.innerHTML = ingredientsHtml;

    // Instructions
    const instructionsList = document.getElementById('recipe-instructions');
    let instructionsHtml = '';
    if (recipe.instructions) {
        recipe.instructions.forEach(step => {
            instructionsHtml += `<li>${escapeHtml(step)}</li>`;
        });
    }
    instructionsList.innerHTML = instructionsHtml;

    // Show/hide cooking button based on instructions
    const cookBtn = document.getElementById('start-cooking-btn');
    if (cookBtn) {
        cookBtn.style.display = recipe.instructions && recipe.instructions.length > 0 ? '' : 'none';
    }

    // Grocery list button in modal actions
    const modalActions = document.querySelector('.recipe-modal-actions');
    if (modalActions) {
        // Remove any existing grocery button
        const oldGrocBtn = modalActions.querySelector('.btn-add-grocery');
        if (oldGrocBtn) oldGrocBtn.remove();

        const missingCount = recipe.ingredients
            ? recipe.ingredients.filter(i => !i.in_pantry).length
            : 0;
        if (missingCount > 0) {
            const grocBtn = document.createElement('button');
            grocBtn.className = 'btn-secondary btn-add-grocery';
            grocBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg> Add ${missingCount} to Grocery List`;
            grocBtn.onclick = () => addMissingToGrocery(window.currentRecipe);
            modalActions.appendChild(grocBtn);
        }
    }

    // Shopping list button (reset each time)
    window.currentRecipe = recipe;
    const slContainer = document.getElementById('shopping-list-container');
    slContainer.innerHTML = '<button id="get-shopping-list-btn" class="btn-primary">Generate Shopping List</button>';
    document.getElementById('get-shopping-list-btn').onclick = () => generateShoppingList(recipe);

    openModal('recipe-modal');
}

// ============================================================================
// Cooking Mode
// ============================================================================

let cookingRecipe = null;
let cookingStepIndex = 0;

function startCookingMode() {
    if (!window.currentRecipe || !window.currentRecipe.instructions || window.currentRecipe.instructions.length === 0) return;
    cookingRecipe = window.currentRecipe;
    cookingStepIndex = 0;

    document.getElementById('cooking-mode-title').textContent = cookingRecipe.name;
    document.getElementById('cooking-mode').classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    renderCookingStep();
}

function exitCookingMode() {
    document.getElementById('cooking-mode').classList.add('hidden');
    document.body.style.overflow = '';
    cookingRecipe = null;
}

function cookingStep(delta) {
    if (!cookingRecipe) return;
    const newIdx = cookingStepIndex + delta;
    if (newIdx < 0 || newIdx >= cookingRecipe.instructions.length) return;
    cookingStepIndex = newIdx;
    renderCookingStep();
}

function renderCookingStep() {
    if (!cookingRecipe) return;
    const total = cookingRecipe.instructions.length;
    const step = cookingRecipe.instructions[cookingStepIndex];

    document.getElementById('cooking-step-label').textContent = `Step ${cookingStepIndex + 1} of ${total}`;
    document.getElementById('cooking-instruction').textContent = step;

    const pct = ((cookingStepIndex + 1) / total) * 100;
    document.getElementById('cooking-progress-fill').style.width = pct + '%';

    // Disable prev/next at boundaries
    const prevBtn = document.getElementById('cooking-prev');
    const nextBtn = document.getElementById('cooking-next');
    if (prevBtn) prevBtn.disabled = cookingStepIndex === 0;
    if (nextBtn) {
        if (cookingStepIndex === total - 1) {
            nextBtn.innerHTML = 'Done!';
            nextBtn.onclick = () => {
                exitCookingMode();
                showToast('Enjoy your meal!', 'success');
            };
        } else {
            nextBtn.innerHTML = 'Next <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';
            nextBtn.onclick = () => cookingStep(1);
        }
    }
}

// ============================================================================
// Shopping List
// ============================================================================

async function generateShoppingList(recipe) {
    const btn = document.getElementById('get-shopping-list-btn');
    const container = document.getElementById('shopping-list-container');

    btn.disabled = true;
    btn.textContent = 'Generating...';

    try {
        const result = await apiCall('POST', '/api/shopping-list', { recipe });

        if (result.missing_items && result.missing_items.length > 0) {
            let html = '<div class="shopping-list">';
            html += `<h4>${escapeHtml(result.recipe_name)} — Shopping List</h4>`;
            result.missing_items.forEach(item => {
                const qty = item.quantity && item.unit ? `${item.quantity} ${item.unit}` : (item.quantity || '');
                html += `
                    <div class="shopping-item">
                        <span class="shopping-item-name">${escapeHtml(item.name)}</span>
                        ${qty ? `<span class="shopping-item-qty">${qty}</span>` : ''}
                    </div>`;
            });
            html += '</div>';
            container.innerHTML = html;
            showToast(`${result.count} items to buy`, 'info');
        } else {
            container.innerHTML = '<div class="shopping-list"><p class="shopping-all-good">You have everything! No shopping needed.</p></div>';
            showToast('You have all the ingredients!', 'success');
        }
    } catch (error) { /* shown */ }
    finally {
        const retryBtn = container.querySelector('#get-shopping-list-btn');
        if (retryBtn) {
            retryBtn.disabled = false;
            retryBtn.textContent = 'Generate Shopping List';
        }
    }
}

// ============================================================================
// Quick Add Missing Ingredient to Pantry
// ============================================================================

async function quickAddIngredient(name, quantity, unit, btnEl) {
    // Disable button immediately
    if (btnEl) {
        btnEl.disabled = true;
        btnEl.textContent = 'Adding...';
    }

    try {
        const result = await apiCall('POST', '/api/add-item', {
            name: name,
            quantity: parseFloat(quantity) || 1,
            unit: unit || '',
            category: 'Other',
        });

        if (result.success) {
            // Update the ingredient in current recipe data
            if (window.currentRecipe && window.currentRecipe.ingredients) {
                const ing = window.currentRecipe.ingredients.find(i => i.name === name);
                if (ing) ing.in_pantry = true;
            }

            // Swap button for a checkmark
            if (btnEl) {
                const li = btnEl.closest('li');
                if (li) {
                    li.classList.remove('ingredient-to-buy');
                    li.classList.add('ingredient-in-pantry');
                }
                btnEl.textContent = '✓ Added';
                btnEl.classList.add('btn-quick-added');
            }

            showToast(`Added ${name} to pantry`, 'success');

            // Refresh pantry count in tab badge
            if (typeof refreshPantryItems === 'function') refreshPantryItems();
        }
    } catch (error) {
        if (btnEl) {
            btnEl.disabled = false;
            btnEl.textContent = '+ Add';
        }
        showToast('Failed to add item', 'error');
    }
}

// ============================================================================
// Event Listeners
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    setupPreferenceChips();

    const suggestBtn = document.getElementById('suggest-btn');
    if (suggestBtn) suggestBtn.addEventListener('click', suggestRecipes);

    const surpriseBtn = document.getElementById('surprise-btn');
    if (surpriseBtn) surpriseBtn.addEventListener('click', surpriseMe);

    // Keyboard shortcut: Enter in prompt textarea triggers generation
    const promptEl = document.getElementById('recipe-prompt');
    if (promptEl) {
        promptEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                suggestRecipes();
            }
        });
    }

    // Escape exits cooking mode
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !document.getElementById('cooking-mode').classList.contains('hidden')) {
            exitCookingMode();
        }
    });

    // Show saved recipes on initial load if favorites exist and no recipes generated
    const favs = getFavorites();
    if (favs.length > 0 && !window.currentRecipes) {
        showSavedRecipesHero();
    }
});

function showSavedRecipesHero() {
    const favs = getFavorites();
    if (favs.length === 0) return;

    const container = document.getElementById('recipes-container');
    let html = `
        <div class="recipes-hero">
            <div class="recipes-hero-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
            </div>
            <h2>Your Saved Recipes</h2>
            <p>Pick preferences and Generate, or browse your ${favs.length} saved recipe${favs.length > 1 ? 's' : ''}:</p>
        </div>
        <div class="recipe-grid" id="recipe-grid">`;

    // Set currentRecipes to favorites for click handling
    window.currentRecipes = favs;

    favs.forEach((recipe, index) => {
        const mealType = recipe.meal_type || 'main';
        const thumbnail = recipe.thumbnail || '';

        html += `
            <div class="recipe-card" onclick="showRecipeDetail(${index})" data-name="${escapeHtml(recipe.name)}" style="animation-delay: ${index * 0.06}s">
                ${thumbnail ? `<img class="recipe-card-thumb" src="${escapeHtml(thumbnail)}" alt="${escapeHtml(recipe.name)}" loading="lazy">` : ''}
                <button class="recipe-fav-btn active" onclick="event.stopPropagation(); removeFavoriteFromHero(${index})" title="Remove from favorites">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                </button>
                <div class="recipe-card-meta">
                    <span class="meal-type-pill" data-type="${mealType}">${mealType}</span>
                </div>
                <div class="recipe-name">${escapeHtml(recipe.name)}</div>
                <div class="recipe-desc">${escapeHtml(recipe.description)}</div>
            </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}

function removeFavoriteFromHero(index) {
    const favs = getFavorites();
    if (!favs[index]) return;
    toggleFavorite(favs[index]);
    showSavedRecipesHero();
    showToast('Removed from favorites', 'info');
}
