"""
PantryPal: A Flask web app for household pantry inventory and recipe suggestions.
Main application file with all routes and logic.
"""

import os
import json
import base64
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file BEFORE any config imports
load_dotenv()

from flask import Flask, render_template, request, jsonify, session
from anthropic import Anthropic

from config import (
    DEBUG, TESTING, SECRET_KEY, DATABASE_PATH,
    ANTHROPIC_API_KEY, API_NINJAS_KEY, MAX_RECIPES_SUGGESTIONS
)
from database import Database
from parsers import InstacartParser, infer_unit
from recipe_suggester import RecipeSuggester
from recipe_api import MealDBClient, APINinjasClient


# Initialize Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['DEBUG'] = DEBUG
app.config['TESTING'] = TESTING

# Initialize database
db = Database(DATABASE_PATH)
db.init_db()  # Ensure tables exist (safe to call multiple times)

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
parser = InstacartParser(anthropic_client)
mealdb_client = MealDBClient()
ninjas_client = APINinjasClient(API_NINJAS_KEY) if API_NINJAS_KEY else None
recipe_suggester = RecipeSuggester(
    anthropic_client, MAX_RECIPES_SUGGESTIONS,
    mealdb_client=mealdb_client, ninjas_client=ninjas_client
)


# ============================================================================
# Utility Functions
# ============================================================================

def get_user_name():
    """Get the current user's name from session or cookie."""
    if 'user_name' not in session:
        session['user_name'] = request.cookies.get('user_name', 'Guest')
    return session['user_name']


def set_user_name(name: str):
    """Set the current user's name in session."""
    session['user_name'] = name


def ensure_api_key(f):
    """Decorator to ensure ANTHROPIC_API_KEY is configured."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ANTHROPIC_API_KEY:
            return jsonify({
                'error': 'ANTHROPIC_API_KEY not configured. Please set it in .env file.'
            }), 500
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Main dashboard showing pantry inventory and recipe suggestions."""
    user_name = get_user_name()
    pantry_items = db.get_all_items()
    summary = db.get_pantry_summary()

    return render_template(
        'index.html',
        user_name=user_name,
        items=pantry_items,
        summary=summary,
        total_items=len(pantry_items)
    )


@app.route('/api/set-user', methods=['POST'])
def set_user():
    """Set the current user's name."""
    data = request.get_json()
    name = data.get('name', 'Guest').strip()

    if not name or len(name) > 50:
        return jsonify({'error': 'Invalid name'}), 400

    set_user_name(name)
    return jsonify({'success': True, 'name': name})


@app.route('/api/add-item', methods=['POST'])
def add_item():
    """Add a single item to the pantry."""
    data = request.get_json()
    user_name = get_user_name()

    # Validate input
    name = data.get('name', '').strip()
    if not name or len(name) > 200:
        return jsonify({'error': 'Invalid item name'}), 400

    quantity = data.get('quantity', 1)
    try:
        quantity = float(quantity)
        if quantity <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid quantity'}), 400

    unit = (data.get('unit') or '').strip()
    if not unit:
        unit = infer_unit(name)
    category = (data.get('category') or 'Other').strip()
    notes = (data.get('notes') or '').strip() or None

    # Add to database
    item_id = db.add_item(
        name=name,
        quantity=quantity,
        unit=unit if unit else None,
        category=category,
        added_by=user_name,
        notes=notes
    )

    return jsonify({
        'success': True,
        'item_id': item_id,
        'message': f'Added {name} to pantry'
    }), 201


@app.route('/api/remove-item/<int:item_id>', methods=['POST'])
def remove_item(item_id):
    """Remove an item from the pantry."""
    item = db.get_item_by_id(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    success = db.remove_item(item_id)
    if success:
        return jsonify({
            'success': True,
            'message': f'Removed {item["name"]} from pantry'
        })
    else:
        return jsonify({'error': 'Failed to remove item'}), 500


@app.route('/api/update-item/<int:item_id>', methods=['POST'])
def update_item(item_id):
    """Update an existing pantry item."""
    item = db.get_item_by_id(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    data = request.get_json()

    # Validate quantity if provided
    quantity = data.get('quantity')
    if quantity is not None:
        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid quantity'}), 400

    unit = (data.get('unit') or '').strip() or None
    notes = (data.get('notes') or '').strip() or None

    success = db.update_item(item_id, quantity=quantity, unit=unit, notes=notes)

    if success:
        return jsonify({'success': True, 'message': 'Item updated'})
    else:
        return jsonify({'error': 'Failed to update item'}), 500


@app.route('/api/import-instacart', methods=['POST'])
def import_instacart():
    """
    Parse Instacart order text and add items to pantry.
    Expects JSON with 'text' field containing the order confirmation text.
    """
    data = request.get_json()
    text = data.get('text', '').strip()
    user_name = get_user_name()

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    if len(text) > 10000:
        return jsonify({'error': 'Text too long'}), 400

    # Parse items from text
    parsed_items = parser.parse_text(text)

    if not parsed_items:
        return jsonify({
            'error': 'Could not parse any items from the provided text. '
                     'Please check the format and try again.'
        }), 400

    # Add items to database (add_item handles duplicate accumulation)
    added_items = []
    for item_data in parsed_items:
        name = item_data.get('name', '').strip()
        quantity = item_data.get('quantity', 1)

        if not name:
            continue

        category = parser.infer_category(name)
        unit = infer_unit(name)

        item_id = db.add_item(
            name=name,
            quantity=quantity,
            unit=unit,
            category=category,
            added_by=user_name,
            notes='Imported from Instacart'
        )
        added_items.append({
            'id': item_id,
            'name': name,
            'quantity': quantity,
            'action': 'added'
        })

    return jsonify({
        'success': True,
        'count': len(added_items),
        'items': added_items,
        'message': f'Imported {len(added_items)} items from Instacart order'
    }), 201


@app.route('/api/import-screenshot', methods=['POST'])
@ensure_api_key
def import_screenshot():
    """
    Extract grocery items from a screenshot using Claude Vision.
    Accepts an image file upload and returns parsed items.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Validate file extension
    allowed_types = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                     'gif': 'image/gif', 'webp': 'image/webp', 'heic': 'image/heic'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_types:
        return jsonify({'error': f'Unsupported file type. Allowed: {", ".join(allowed_types)}'}), 400

    # Read and encode image
    image_data = file.read()
    if len(image_data) > 10 * 1024 * 1024:  # 10MB limit
        return jsonify({'error': 'Image too large (max 10MB)'}), 400

    media_type = allowed_types[ext]

    b64_image = base64.standard_b64encode(image_data).decode('utf-8')

    # Ask Claude to extract items from the screenshot
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": """Look at this screenshot of a grocery order (likely Instacart or similar).
Extract every grocery item you can see. For each item, provide:
- name: the product name (clean, without brand sizing info)
- quantity: how many (default 1 if not visible)
- unit: the most appropriate unit (e.g. "lbs", "oz", "gal", "ct", "bag", "box", "can", "loaf", "dozen"). Use null if unknown.
- category: one of Vegetables, Fruits, Dairy, Meat, Pantry, Frozen, Beverages, Other

Return ONLY a JSON array, no other text. Example:
[{"name": "Organic Bananas", "quantity": 2, "unit": "ct", "category": "Fruits"}, {"name": "Whole Milk", "quantity": 1, "unit": "gal", "category": "Dairy"}]

If you can't identify any grocery items, return an empty array: []"""
                    }
                ]
            }]
        )

        # Parse Claude's response
        result_text = response.content[0].text.strip()
        # Extract JSON from response (handle potential markdown code blocks)
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        parsed_items = json.loads(result_text)

        if not parsed_items:
            return jsonify({'error': 'No grocery items found in this image. Try a clearer screenshot.'}), 400

    except json.JSONDecodeError:
        return jsonify({'error': 'Could not parse items from image. Try a clearer screenshot.'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to analyze image: {str(e)}'}), 500

    # Add items to database
    user_name = get_user_name()
    added_items = []

    for item_data in parsed_items:
        name = item_data.get('name', '').strip()
        quantity = item_data.get('quantity', 1)
        category = item_data.get('category', 'Other')
        unit = item_data.get('unit') or infer_unit(name)

        if not name:
            continue

        try:
            quantity = max(1, int(float(quantity)))
        except (ValueError, TypeError):
            quantity = 1

        item_id = db.add_item(
            name=name, quantity=quantity, unit=unit,
            category=category, added_by=user_name,
            notes='Imported from screenshot'
        )
        added_items.append({'id': item_id, 'name': name,
                          'quantity': quantity, 'action': 'added'})

    return jsonify({
        'success': True,
        'count': len(added_items),
        'items': added_items,
        'message': f'Found and imported {len(added_items)} items from screenshot'
    }), 201


@app.route('/api/suggest-recipes', methods=['POST'])
@ensure_api_key
def suggest_recipes():
    """
    Generate recipe suggestions based on current pantry inventory.
    Uses Claude API to intelligently suggest recipes.
    Accepts optional preferences in POST body.
    """
    data = request.get_json() or {}
    preferences = data.get('preferences', {})
    user_prompt = (data.get('prompt', '') or '').strip() or None
    mode = data.get('mode', 'pantry')  # 'pantry' or 'discover'
    pantry_items = db.get_all_items()

    if not pantry_items and mode == 'pantry':
        return jsonify({
            'error': 'Your pantry is empty. Add some items first or try "Discover New" mode.'
        }), 400

    # Get recipe suggestions from Claude (with optional user prompt and MealDB grounding)
    recipes = recipe_suggester.suggest_recipes(
        pantry_items, preferences=preferences, user_prompt=user_prompt, mode=mode
    )

    if not recipes:
        return jsonify({
            'error': 'Could not generate recipe suggestions. Please try again.'
        }), 500

    return jsonify({
        'success': True,
        'recipes': recipes,
        'count': len(recipes)
    })


@app.route('/api/shopping-list', methods=['POST'])
def shopping_list():
    """
    Generate a shopping list for a recipe based on what's missing from pantry.
    Expects JSON with 'recipe' field containing the recipe dict.
    """
    data = request.get_json()
    recipe = data.get('recipe')

    if not recipe:
        return jsonify({'error': 'No recipe provided'}), 400

    pantry_items = db.get_all_items()
    missing = recipe_suggester.get_shopping_list(recipe, pantry_items)

    return jsonify({
        'success': True,
        'recipe_name': recipe.get('name', 'Recipe'),
        'missing_items': missing,
        'count': len(missing)
    })


@app.route('/api/pantry-summary', methods=['GET'])
def pantry_summary():
    """Get a summary of the pantry."""
    summary = db.get_pantry_summary()
    return jsonify(summary)


@app.route('/api/pantry-items', methods=['GET'])
def pantry_items_api():
    """Get all pantry items as JSON."""
    items = db.get_all_items()
    return jsonify({'items': items})


@app.route('/api/pantry-items-by-category', methods=['GET'])
def pantry_items_by_category():
    """Get pantry items grouped by category."""
    categorized = db.get_items_by_category()
    return jsonify(categorized)


@app.route('/api/clear-pantry', methods=['POST'])
def clear_pantry():
    """Clear all items from the pantry. Use with caution."""
    count = db.clear_pantry()
    return jsonify({
        'success': True,
        'cleared_count': count,
        'message': f'Cleared {count} items from pantry'
    })


# ============================================================================
# Error Handlers
# ============================================================================


# ============================================================================
# PWA Routes
# ============================================================================

@app.route('/manifest.json')
def manifest():
    """Serve the PWA manifest from the static directory."""
    return app.send_static_file('manifest.json')


@app.route('/offline.html')
def offline():
    """Serve the offline fallback page."""
    return app.send_static_file('offline.html')


@app.route('/share', methods=['GET', 'POST'])
def share_target():
    """Handle PWA Web Share Target.
    When users share text/URLs to KitchenSync from their phone,
    this route receives the shared data and opens the import modal
    with the text pre-filled.
    """
    shared_text = ''
    shared_url = ''

    if request.method == 'POST':
        shared_text = request.form.get('text', '')
        shared_url = request.form.get('url', '')
    else:
        shared_text = request.args.get('text', '')
        shared_url = request.args.get('url', '')

    # Combine text and URL if both present
    content = shared_text
    if shared_url and shared_url not in content:
        content = f"{content}\n{shared_url}".strip()

    # Render main page with shared content to pre-fill the import modal
    user_name = get_user_name()
    pantry_items = db.get_all_items()
    summary = db.get_pantry_summary()

    return render_template(
        'index.html',
        user_name=user_name,
        items=pantry_items,
        summary=summary,
        total_items=len(pantry_items),
        shared_text=content
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Context Processors
# ============================================================================

@app.context_processor
def inject_now():
    """Make datetime available in templates."""
    return {'now': datetime.now()}


CATEGORY_EMOJI = {
    'Vegetables': '\U0001F96C',
    'Fruits': '\U0001F34E',
    'Dairy': '\U0001F9C0',
    'Meat': '\U0001F969',
    'Pantry': '\U0001FAD9',
    'Frozen': '\U0001F9CA',
    'Beverages': '\U0001F964',
    'Other': '\U0001F4E6',
}


@app.context_processor
def inject_category_helpers():
    """Provide category_emoji() function to templates."""
    def category_emoji(cat):
        return CATEGORY_EMOJI.get(cat or 'Other', '\U0001F4E6')
    return {'category_emoji': category_emoji}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    # Run Flask development server
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG,
        use_reloader=True
    )
