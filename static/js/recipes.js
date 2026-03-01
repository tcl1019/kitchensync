/**
 * KitchenSync — Recipe Suggestions
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// Skeleton Loading
// ============================================================================

function showRecipeSkeletons() {
    const container = document.getElementById('recipes-container');
    let html = `
        <div class="recipes-header">
            <h2>Generating recipes...</h2>
        </div>
        <div class="recipe-grid">`;

    for (let i = 0; i < 4; i++) {
        html += `
            <div class="recipe-card skeleton" style="animation-delay: ${i * 0.1}s">
                <div class="skeleton-line skeleton-title"></div>
                <div class="skeleton-line skeleton-desc"></div>
                <div class="skeleton-line skeleton-desc short"></div>
                <div class="skeleton-line skeleton-meta"></div>
            </div>`;
    }

    html += '</div>';
    container.innerHTML = html;
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

    try {
        const result = await apiCall('POST', '/api/suggest-recipes');
        displayRecipes(result.recipes);
        showToast(`Generated ${result.count} recipe suggestions!`, 'success');
    } catch (error) {
        const container = document.getElementById('recipes-container');
        container.innerHTML = `
            <div class="recipes-hero">
                <div class="recipes-hero-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c1.5 0 2.5 1 3 2 .5-1 1.5-2 3-2 2 0 4 1.5 4 4 0 3.5-3 6-7 9.5C11 12.5 8 9.5 8 6c0-2.5 2-4 4-4z"/><path d="M8 6c-2 0-4 1.5-4 4 0 3.5 3 6 7 9.5"/><line x1="2" y1="21" x2="22" y2="21"/></svg>
                </div>
                <p style="margin-bottom:1rem;">Could not generate recipes. Please try again.</p>
                <button id="suggest-btn" class="btn-primary btn-large" onclick="suggestRecipes()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    Try Again
                </button>
            </div>`;
    }
}

// ============================================================================
// Display Recipes
// ============================================================================

function displayRecipes(recipes) {
    const container = document.getElementById('recipes-container');

    if (!recipes || recipes.length === 0) {
        container.innerHTML = `
            <div class="recipes-hero">
                <p>No recipes generated. Try again!</p>
                <button id="suggest-btn" class="btn-primary btn-large" onclick="suggestRecipes()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    Generate Recipes
                </button>
            </div>`;
        return;
    }

    let html = `
        <div class="recipes-header">
            <h2>Your Recipes</h2>
            <button class="btn-secondary" onclick="suggestRecipes()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                Regenerate
            </button>
        </div>
        <div class="recipe-grid">`;

    recipes.forEach((recipe, index) => {
        const totalIngredients = recipe.ingredients ? recipe.ingredients.length : 0;
        const pantryCount = recipe.ingredients ? recipe.ingredients.filter(i => i.in_pantry).length : 0;
        const toBuy = totalIngredients - pantryCount;

        html += `
            <div class="recipe-card" onclick="showRecipeDetail(${index})" style="animation-delay: ${index * 0.06}s">
                <div class="recipe-name">${escapeHtml(recipe.name)}</div>
                <div class="recipe-desc">${escapeHtml(recipe.description)}</div>
                <div class="recipe-badges">
                    <span class="recipe-pantry-badge">${pantryCount}/${totalIngredients} in pantry</span>
                    ${toBuy > 0
                        ? `<span class="recipe-buy-badge">${toBuy} to buy</span>`
                        : '<span class="recipe-ready-badge">Ready to cook!</span>'}
                </div>
                <div class="recipe-meta">
                    ${recipe.instructions ? `<span>${recipe.instructions.length} steps</span>` : ''}
                </div>
            </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
    window.currentRecipes = recipes;
}

// ============================================================================
// Recipe Detail
// ============================================================================

function showRecipeDetail(index) {
    if (!window.currentRecipes || !window.currentRecipes[index]) return;
    const recipe = window.currentRecipes[index];

    document.getElementById('recipe-title').textContent = recipe.name;
    document.getElementById('recipe-description').textContent = recipe.description;

    // Ingredients
    const ingredientsList = document.getElementById('recipe-ingredients');
    let ingredientsHtml = '';
    if (recipe.ingredients) {
        recipe.ingredients.forEach(ing => {
            const cls = ing.in_pantry ? 'ingredient-in-pantry' : 'ingredient-to-buy';
            const qty = ing.quantity && ing.unit ? `${ing.quantity} ${ing.unit}` : (ing.quantity || '');
            ingredientsHtml += `
                <li class="${cls}">
                    <strong>${escapeHtml(ing.name)}</strong>
                    ${qty ? `<span class="ingredient-qty">${qty}</span>` : ''}
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

    // Shopping list button (reset each time)
    window.currentRecipe = recipe;
    const slContainer = document.getElementById('shopping-list-container');
    slContainer.innerHTML = '<button id="get-shopping-list-btn" class="btn-primary">Generate Shopping List</button>';
    document.getElementById('get-shopping-list-btn').onclick = () => generateShoppingList(recipe);

    openModal('recipe-modal');
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
// Event Listeners
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    const suggestBtn = document.getElementById('suggest-btn');
    if (suggestBtn) suggestBtn.addEventListener('click', suggestRecipes);
});
