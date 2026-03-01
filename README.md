# PantryPal

A Flask web app for household pantry inventory management and AI-powered recipe suggestions.

## Features

- **Shared Household Pantry** - Multiple people can add/remove items with name tracking
- **Quick Item Entry** - Add items with quantity, unit, category, and notes
- **Instacart Integration** - Paste Instacart order text to automatically import items
- **AI Recipe Suggestions** - Get creative recipe suggestions based on your pantry using Claude API
- **Shopping Lists** - See what you need to buy for suggested recipes
- **SQLite Database** - Simple local database storing pantry items with metadata
- **No Authentication** - Household trust model (just enter your name)

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone or download this repository

2. Navigate to the project directory:
   ```bash
   cd pantrypal
   ```

3. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file with your API key:
   ```bash
   cp .env.example .env
   ```

6. Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
   ```

   Get your API key from https://console.anthropic.com/account/keys

## Running the App

### Development

```bash
python app.py
```

The app will run on `http://localhost:5000`

### Production

Using Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Usage

### Adding Items

1. Enter item name, quantity, unit (optional), and category
2. Click "Add" to add to pantry
3. Items are attributed to whoever is currently logged in (no password)

### Importing from Instacart

1. Go to your Instacart order confirmation page
2. Copy the entire order details text
3. Paste into the "Import from Instacart" section
4. Click "Import Instacart Order"
5. The app will parse and add items automatically

### Getting Recipe Suggestions

1. Add items to your pantry
2. Click "Get Recipes" in the Recipe Suggestions panel
3. Click any recipe to see full details, ingredients, and instructions
4. Click "Generate Shopping List" to see missing ingredients

## API Endpoints

### Pantry Management

- `GET /` - Main dashboard
- `POST /api/add-item` - Add item to pantry
- `POST /api/remove-item/<id>` - Remove item from pantry
- `POST /api/update-item/<id>` - Update item quantity/notes
- `POST /api/import-instacart` - Parse and import Instacart order
- `GET /api/pantry-items` - Get all pantry items
- `GET /api/pantry-items-by-category` - Get items grouped by category
- `GET /api/pantry-summary` - Get pantry statistics
- `POST /api/clear-pantry` - Clear all items

### User Management

- `POST /api/set-user` - Set current user name

### Recipe Generation

- `POST /api/suggest-recipes` - Get AI-generated recipe suggestions
- `POST /api/shopping-list` - Get missing ingredients for a recipe

## Database

The app uses SQLite with a simple schema:

```sql
CREATE TABLE pantry_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 1,
    unit TEXT DEFAULT NULL,
    category TEXT DEFAULT 'Other',
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by TEXT NOT NULL,
    notes TEXT DEFAULT NULL
);
```

Database file: `pantrypal.db` (created automatically on first run)

## Project Structure

```
pantrypal/
├── app.py                 # Main Flask application
├── config.py              # Configuration and settings
├── database.py            # SQLite database operations
├── parsers.py             # Instacart text parsing
├── recipe_suggester.py    # Claude API recipe generation
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── README.md              # This file
├── templates/
│   ├── base.html          # Base template
│   └── index.html         # Main dashboard template
└── static/
    ├── css/
    │   └── style.css      # Stylesheet
    └── js/
        ├── app.js         # Main app JavaScript
        ├── pantry.js      # Pantry management scripts
        └── recipes.js     # Recipe handling scripts
```

## Configuration

Edit `config.py` or set environment variables:

- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)
- `FLASK_DEBUG` - Enable debug mode (default: False)
- `DATABASE_PATH` - Path to SQLite database (default: ./pantrypal.db)
- `MAX_RECIPES_SUGGESTIONS` - Number of recipes to suggest (default: 5)

## Instacart Parsing

The app uses two methods to parse Instacart orders:

1. **Regex-based parsing** - Fast pattern matching for common formats
2. **Claude AI fallback** - Uses Claude API for complex/unusual formats

The parser automatically infers item categories (Vegetables, Fruits, Dairy, Meat, Pantry, etc.)

## Recipe Generation

Recipes are generated using Claude 3.5 Sonnet with the following:

- 5 creative recipe suggestions at a time
- Ingredients marked as "in pantry" or "need to buy"
- Step-by-step cooking instructions
- JSON-formatted response for easy parsing

## Troubleshooting

### "ANTHROPIC_API_KEY not configured"

Make sure you've set your API key in the `.env` file. The key should start with `sk-ant-`.

### Instacart parsing returns no items

Try pasting a larger section of the order confirmation page, including item names and quantities.

### Recipe suggestions are generic

This is normal if your pantry has common items only. Add more specific ingredients for better suggestions.

### Database errors

Delete `pantrypal.db` and restart the app to reset the database.

## Future Enhancements

- User accounts with persistence
- Recipe ratings and favorites
- Nutritional information
- Meal planning calendar
- Grocery store price integration
- Recipe sharing with household members
- Mobile app

## License

MIT License - feel free to use and modify

## Support

For issues or questions, please check the code comments or create an issue.
