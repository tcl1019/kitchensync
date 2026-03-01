# PantryPal - Quick Start Guide

Get up and running with PantryPal in 5 minutes.

## 1. Get Your API Key

Visit https://console.anthropic.com/account/keys and create or copy your API key.

## 2. Setup (Choose One)

### Option A: Using the run script (Linux/Mac)

```bash
cd /path/to/pantrypal
./run.sh
```

The script will:
- Create a virtual environment
- Install dependencies
- Create .env file from template
- Start the server

Then edit `.env` and add your API key.

### Option B: Manual Setup

```bash
# Navigate to project
cd /path/to/pantrypal

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your API key
nano .env  # or use your favorite editor
```

### Option C: Using Docker (future option)

```bash
docker build -t pantrypal .
docker run -p 5000:5000 -e ANTHROPIC_API_KEY=your-key pantrypal
```

## 3. Start the App

### Development Mode
```bash
python app.py
```

You'll see:
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

### Production Mode
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 4. Open in Browser

Go to **http://localhost:5000**

You should see:
- Navigation bar with "🥘 PantryPal" logo
- Left panel: Your Pantry with add form
- Right panel: Recipe Suggestions
- Both empty at first

## 5. First Steps

### Add Your First Item

1. Enter "Chicken Breast" in the item name field
2. Set quantity to 2
3. Set unit to "lbs"
4. Select category "Meat"
5. Click "Add"
6. See it appear in your pantry!

### Add More Items

Add these items to build up your pantry:
- Rice (2, cups, Pantry)
- Broccoli (1, head, Vegetables)
- Garlic (1, bulb, Pantry)
- Olive Oil (1, bottle, Pantry)
- Milk (1, quart, Dairy)
- Eggs (12, count, Dairy)

### Get Recipe Suggestions

1. Click "Get Recipes" button
2. Wait 2-4 seconds (Claude is thinking!)
3. See 5 recipe suggestions appear
4. Click any recipe to see:
   - Full description
   - Complete ingredient list
   - Step-by-step instructions
   - Which ingredients you have
5. Click "Generate Shopping List" to see what to buy

### Try Instacart Import

1. Find any Instacart order confirmation email or page
2. Copy the entire order details (items and quantities)
3. Paste into "Paste your Instacart order" textarea
4. Click "Import Instacart Order"
5. Watch items automatically appear in your pantry!

### Change Your Name

1. Click your current name in top right
2. Enter your name (e.g., "Alice", "Bob", etc.)
3. Click "Save"
4. Your name will be tracked for items you add

## Common Tasks

### Remove an Item
Click the "Remove" button next to any item

### Clear Everything
Scroll down and click "Clear All Items" (be careful!)

### Update Item Quantity
(Feature for future enhancement - currently requires removal + re-add)

### See Who Added What
Each item shows "Added by [name]" - helps track household contributions

### Export Your Pantry
(Currently not available - use browser DevTools or Database)

## Troubleshooting

### "ANTHROPIC_API_KEY not configured"

**Problem**: App shows this error when trying to get recipes

**Solution**: 
1. Check your `.env` file has the API key
2. Make sure it starts with `sk-ant-`
3. Restart the app after adding the key

### "Could not parse any items from text"

**Problem**: Instacart import fails

**Solution**:
1. Make sure you're pasting full order text (not just item names)
2. Include quantities if available
3. Try a larger portion of the order confirmation

### "Port 5000 is already in use"

**Problem**: Another app is using the port

**Solution**:
```bash
# Use a different port
python -c "from app import app; app.run(port=5001)"
```

Or kill the other process:
```bash
# Linux/Mac
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
# Then: taskkill /PID <PID> /F
```

### Recipe suggestions are bland

**Problem**: Claude isn't generating creative recipes

**Reason**: You might have very common items only

**Solution**:
- Add more specific/international ingredients
- Try unusual ingredient combinations
- Run again - Claude varies its suggestions

### Database issues

**Problem**: "database is locked" or items not saving

**Solution**:
```bash
# Stop the app
# Delete the database
rm pantrypal.db

# Restart the app - fresh database is created
python app.py
```

## Development Tips

### Enable Debug Mode

Edit `config.py` or set environment variable:
```bash
export FLASK_DEBUG=True
python app.py
```

Features:
- Auto-reload on code changes
- Interactive debugger on errors
- Detailed error pages

### Check Database Directly

```bash
# Access SQLite database
sqlite3 pantrypal.db

# List tables
.tables

# See all pantry items
SELECT * FROM pantry_items;

# See item count
SELECT COUNT(*) FROM pantry_items;

# Exit
.quit
```

### Monitor API Calls

Open browser Developer Tools (F12):
1. Go to Network tab
2. Perform actions (add item, get recipes, etc.)
3. See each API call with request/response
4. Check Console for JavaScript errors

### Test API Endpoints Directly

Using curl:

```bash
# Add item
curl -X POST http://localhost:5000/api/add-item \
  -H "Content-Type: application/json" \
  -d '{"name":"Apple","quantity":3,"category":"Fruits","added_by":"Alice"}'

# Get all items
curl http://localhost:5000/api/pantry-items

# Get recipes
curl -X POST http://localhost:5000/api/suggest-recipes \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Next Steps

1. **Explore Features**: Add more items, try different recipes
2. **Customize**: Edit `config.py` to change defaults
3. **Learn More**: Read `README.md` for full documentation
4. **Understand Design**: Check `ARCHITECTURE.md` for technical details
5. **Extend**: Add new features like ratings, favorites, etc.

## File Locations

Quick reference for important files:

- **Main app**: `app.py`
- **Configuration**: `config.py`
- **Database**: `pantrypal.db` (auto-created)
- **Frontend**: `templates/index.html`
- **Styles**: `static/css/style.css`
- **API key**: `.env` (hidden, don't share!)

## Getting Help

If something isn't working:

1. Check the browser console (F12 → Console tab)
2. Look at Flask console output (your terminal)
3. Check `.env` has API key
4. Try deleting `pantrypal.db` and starting fresh
5. Read the README.md for more details

## Tips for Best Results

1. **Use complete Instacart text** - Full order confirmation pages work best
2. **Add diverse ingredients** - Claude suggests better with variety
3. **Be specific with categories** - Helps organize pantry
4. **Add notes** - "2 lbs grass-fed" vs just "2 lbs"
5. **Check generated recipes** - Claude sometimes needs guidance
6. **Share wisely** - Household trust model means everyone can see/edit

## Production Deployment

When you're ready to deploy:

```bash
# Use gunicorn (production WSGI server)
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Set secure secret key
export SECRET_KEY=very-long-random-secure-string

# Use environment variables for all settings
export FLASK_DEBUG=False
export DATABASE_PATH=/var/lib/pantrypal/pantrypal.db
```

---

**Happy cooking!** 🍳

For detailed documentation, see `README.md` and `ARCHITECTURE.md`
