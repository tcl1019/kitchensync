"""
Recipe suggestion module for KitchenSync.
Uses Claude API to suggest recipes based on pantry inventory.
Optionally grounded with real recipes from TheMealDB.
"""

import os
import json
import re
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from anthropic import Anthropic


class RecipeSuggester:
    """Generate recipe suggestions using Claude API."""

    def __init__(self, client: Anthropic, max_suggestions: int = 5,
                 mealdb_client=None, ninjas_client=None):
        """Initialize the recipe suggester with Anthropic client."""
        self.client = client
        self.max_suggestions = max_suggestions
        self.mealdb_client = mealdb_client
        self.ninjas_client = ninjas_client

    def suggest_recipes(self, pantry_items: List[Dict],
                        preferences: Optional[Dict] = None,
                        user_prompt: Optional[str] = None,
                        mode: str = 'pantry') -> List[Dict]:
        """
        Suggest recipes based on available pantry items and user preferences.

        Args:
            pantry_items: List of dicts with 'name', 'quantity', 'unit' keys
            preferences: Optional dict with:
                - tags: list of strings like ["low-carb", "high-protein"]
                - meal_types: list like ["snack", "main"]
                - max_cook_time: int in minutes
                - count: int number of recipes to generate
            user_prompt: Optional free-text describing what the user wants
            mode: 'pantry' (build from pantry) or 'discover' (popular recipes, pantry optional)

        Returns:
            List of recipe dicts with name, description, meal_type, cook_time,
            difficulty, tags, ingredients, instructions, source, source_name, thumbnail
        """
        if not pantry_items and mode == 'pantry':
            return []

        # Check if API key is available
        if not os.getenv('ANTHROPIC_API_KEY') or not self.client:
            return []

        preferences = preferences or {}

        # Format pantry inventory for Claude
        inventory_text = self._format_inventory(pantry_items) if pantry_items else ""

        # Build preference instructions
        pref_lines = self._build_preference_instructions(preferences)

        # Build user prompt section
        user_prompt_section = ""
        if user_prompt:
            if mode == 'discover':
                user_prompt_section = f"\nUSER REQUEST: {user_prompt}\nHonor this request — suggest great recipes regardless of pantry.\n"
            else:
                user_prompt_section = f"\nUSER REQUEST: {user_prompt}\nHonor this request while using pantry items where possible.\n"

        # Fetch grounding recipes from APIs (with tight timeout to avoid
        # eating into Claude API time budget)
        grounding_section = self._build_grounding_section(pantry_items) if pantry_items else ""

        count = min(preferences.get('count', self.max_suggestions), 3)

        # Build mode-specific prompt sections
        if mode == 'discover':
            intro_line = f"You are a confident, flavor-forward home cook who makes restaurant-quality food without fuss. Suggest {count} popular, crave-worthy recipes that real people love to cook at home."
            rules_block = """RULES:
- Each recipe is ONE dish, not a dish + random side.
- Suggest popular meals real people actually cook and search for online: stir fry, pasta, tacos, fried rice, quesadillas, soup, sandwiches, wraps, salads, stews, curries, etc.
- Recipes should be crowd-pleasers — think AllRecipes top-rated, Tasty viral, or food blog favorites.
- Under 45 min active cooking preferred, up to 60 min OK for special dishes.
- Simple names only: "Chicken Tikka Masala" not "Aromatic Spiced Yogurt-Marinated Chicken Masala"
- Include a MIX of meal types: some full meals, some quick snacks, some sides — unless the user specifies otherwise
- For snacks: can be as simple as 1-2 ingredients (e.g. "Apple & Peanut Butter", "Cheese Plate")"""
            if inventory_text:
                pantry_block = f"""
PANTRY REFERENCE (the user has these items — mark matching ingredients as in_pantry: true):
{inventory_text}
For ingredients NOT in the pantry above, set in_pantry: false. The user will add them to their grocery list."""
            else:
                pantry_block = "\nThe user has no pantry items. Mark ALL ingredients as in_pantry: false."
        else:
            intro_line = f"You are a confident, flavor-forward home cook who makes restaurant-quality food without fuss. Given this pantry, suggest {count} realistic meals or snacks."
            rules_block = """RULES:
- Each recipe is ONE dish, not a dish + random side.
- Suggest normal meals real people actually cook and search for online: stir fry, pasta, tacos, fried rice, quesadillas, soup, sandwiches, wraps, salads, etc.
- Use 2-5 pantry items per recipe. You do NOT need to use every item — and you SHOULD NOT force weird combos just to use more items.
- Prioritize perishables (meat, dairy, produce) over shelf-stable stuff
- Under 30 min active cooking
- 0-2 extra ingredients to buy (staples above don't count)
- Simple names only: "Turkey Tacos" not "Seasoned Ground Turkey Fiesta Wraps"
- Include a MIX of meal types: some full meals, some quick snacks, some sides — unless the user specifies otherwise
- For snacks: can be as simple as 1-2 ingredients (e.g. "Apple & Peanut Butter", "Cheese Plate")"""
            pantry_block = f"""
PANTRY INVENTORY (all items below are in_pantry: true — do NOT list them as "to buy"):
{inventory_text}"""

        prompt = f"""{intro_line}

ASSUMED KITCHEN STAPLES (do NOT list these as "to buy" — assume every kitchen has them):
Salt, black pepper, olive oil, vegetable oil, butter, garlic powder, onion powder, paprika,
cumin, chili powder, oregano, Italian seasoning, soy sauce, vinegar, flour, sugar, baking
powder, ketchup, mustard, mayo. Mark these as in_pantry: true when used.

{rules_block}

RECIPE INSTRUCTIONS — keep them concise but complete:
- 4-6 steps for mains, 2-4 for snacks/sides. Combine related actions into single steps.
- Include key temps and times but don't over-explain basic techniques.
- Keep each step to 1-2 sentences max.
- Use 6-10 ingredients per main dish. Keep it simple.

FLAVOR RULES:
- Brown meats well, deglaze pans, season at every stage, finish with acid.
- Specify exact spice amounts. Toast spices in oil.
- Only suggest recipes you'd find on AllRecipes or Tasty — no weird combos.
- Never combine meat + sweet fruit except: pork+apple, prosciutto+melon, chicken+cranberry, ham+pineapple.
- When pantry has incompatible items, use them in SEPARATE recipes.
{pref_lines}{user_prompt_section}{grounding_section}{pantry_block}

IMPORTANT: Return ONLY raw JSON. No markdown, no ```json fences, no text before/after.
{{"recipes": [
  {{"name": "Short Name", "description": "1 sentence", "meal_type": "main|snack|side|breakfast",
    "cook_time": "10 min", "difficulty": "easy|medium|hard", "tags": ["quick"],
    "source": "ai", "source_name": "", "thumbnail": "",
    "ingredients": [{{"name": "x", "quantity": "1", "unit": "cup", "in_pantry": true}}],
    "instructions": ["Step 1 with temps/times.", "Step 2.", "Step 3."]}}
]}}"""

        try:
            # Use a dedicated client with no retries to prevent the SDK from
            # sleeping inside the worker (which blocks gunicorn heartbeats and
            # causes SIGKILL). Timeout is 25s to leave room for grounding calls
            # within gunicorn's overall worker timeout.
            no_retry_client = Anthropic(
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                max_retries=0,
                timeout=25.0,
            )
            message = no_retry_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system="You are a recipe JSON generator. Return ONLY valid raw JSON — never use markdown code fences, never include text outside the JSON object. Be concise: 1-2 sentences per instruction step, 6-8 ingredients per recipe.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Detect truncated responses
            if message.stop_reason == 'max_tokens':
                print(f"Warning: response truncated (stop_reason=max_tokens)")

            # Strip markdown code fences if present (handles truncated responses
            # where closing ``` may be missing)
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                # Remove opening fence line (e.g. "```json\n")
                first_newline = cleaned.find('\n')
                if first_newline != -1:
                    cleaned = cleaned[first_newline + 1:]
                # Remove closing fence if present
                if cleaned.rstrip().endswith('```'):
                    cleaned = cleaned.rstrip()[:-3]
                cleaned = cleaned.strip()

            # Parse JSON response
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as e:
                # Always attempt repair — response may be truncated by
                # max_tokens, timeout, or other reasons
                print(f"JSON parse failed ({message.stop_reason}), attempting repair: {e}")
                data = self._repair_truncated_json(cleaned)
                if not data:
                    print(f"Could not repair JSON. First 200 chars: {cleaned[:200]}")
                    return []

            recipes = data.get('recipes', [])

            # Apply defensive defaults for any missing fields
            for recipe in recipes:
                recipe.setdefault('meal_type', 'main')
                recipe.setdefault('cook_time', '')
                recipe.setdefault('difficulty', 'easy')
                recipe.setdefault('tags', [])
                recipe.setdefault('ingredients', [])
                recipe.setdefault('instructions', [])
                recipe.setdefault('source', 'ai')
                recipe.setdefault('source_name', '')
                recipe.setdefault('thumbnail', '')

            return recipes[:count]

        except Exception as e:
            print(f"Claude API error: {e}")
            return []

    def _repair_truncated_json(self, text: str) -> Optional[Dict]:
        """Attempt to salvage complete recipes from a truncated JSON response.

        When the response is cut off, the JSON is incomplete. This method walks
        through the recipes array tracking brace depth to find complete recipe
        objects, skipping the final truncated one.
        """
        # Find the start of the recipes array
        arr_match = re.search(r'"recipes"\s*:\s*\[', text)
        if not arr_match:
            return None

        pos = arr_match.end()
        recipes = []

        # Walk through finding complete top-level objects in the array
        while pos < len(text):
            # Skip whitespace and commas
            while pos < len(text) and text[pos] in ' \t\n\r,':
                pos += 1
            if pos >= len(text) or text[pos] != '{':
                break

            # Track brace depth to find the end of this object
            start = pos
            depth = 0
            in_string = False
            escape_next = False
            found_end = False

            for i in range(start, len(text)):
                c = text[i]
                if escape_next:
                    escape_next = False
                    continue
                if c == '\\' and in_string:
                    escape_next = True
                    continue
                if c == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        # Found a complete object
                        obj_text = text[start:i + 1]
                        try:
                            obj = json.loads(obj_text)
                            if isinstance(obj, dict) and 'name' in obj:
                                recipes.append(obj)
                        except json.JSONDecodeError:
                            pass
                        pos = i + 1
                        found_end = True
                        break
            if not found_end:
                # Ran out of text — this object was truncated
                break

        if recipes:
            print(f"Salvaged {len(recipes)} complete recipes from truncated response")
            return {"recipes": recipes}
        return None

    def _build_grounding_section(self, pantry_items: List[Dict]) -> str:
        """Fetch and format recipes from MealDB + API Ninjas as reference material."""
        mealdb_recipes = []
        ninjas_recipes = []

        # Fetch from both APIs in parallel for speed
        futures = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            if self.mealdb_client:
                futures['mealdb'] = executor.submit(
                    self.mealdb_client.fetch_grounding_recipes, pantry_items)
            if self.ninjas_client:
                futures['ninjas'] = executor.submit(
                    self.ninjas_client.fetch_grounding_recipes, pantry_items)
            for key, future in futures.items():
                try:
                    result = future.result(timeout=5)
                    if key == 'mealdb':
                        mealdb_recipes = result
                    else:
                        ninjas_recipes = result
                except Exception as e:
                    print(f"{key} grounding fetch error: {e}")

        if not mealdb_recipes and not ninjas_recipes:
            return ""

        # Score and filter MealDB recipes by pantry relevance
        pantry_keywords = set()
        for item in pantry_items:
            for word in item.get('name', '').lower().split():
                if len(word) > 3:
                    pantry_keywords.add(word)

        def relevance_score(recipe):
            """Score how relevant a recipe is to our pantry."""
            ing_names = " ".join(i.get("name", "").lower() for i in recipe.get("ingredients", []))
            recipe_name = recipe.get("name", "").lower()
            text = ing_names + " " + recipe_name
            return sum(1 for kw in pantry_keywords if kw in text)

        # Skip obscure cuisines, score by relevance, take top 3
        SKIP_AREAS = {'Japanese', 'Chinese', 'Vietnamese', 'Thai', 'Indian',
                      'Moroccan', 'Turkish', 'Egyptian', 'Tunisian', 'Croatian',
                      'Malaysian', 'Filipino', 'Kenyan'}
        candidates = [r for r in mealdb_recipes if r.get('area', '') not in SKIP_AREAS]
        candidates.sort(key=relevance_score, reverse=True)
        filtered_mealdb = candidates[:3]

        all_refs = filtered_mealdb + ninjas_recipes[:2]  # Cap total references
        if not all_refs:
            return ""

        must_use = min(len(all_refs), 2)

        lines = [
            f"\nREFERENCE RECIPES (adapt at least {must_use} from these, rest can be original):",
            "For adapted recipes: set source_name to the original recipe name below, copy source and thumbnail values.",
            "For original recipes: set source='ai', source_name='', thumbnail=''.\n",
        ]

        for r in filtered_mealdb:
            ing_list = ", ".join(i["name"] for i in r.get("ingredients", [])[:5])
            thumb = r.get('thumbnail', '')
            lines.append(f"- {r['name']}: {ing_list} (source='themealdb', source_name='{r['name']}', thumbnail='{thumb}')")

        for r in ninjas_recipes[:2]:
            ing_list = ", ".join(i["name"] for i in r.get("ingredients", [])[:5])
            lines.append(f"- {r['name']}: {ing_list} (source='api-ninjas', source_name='{r['name']}')")

        return "\n".join(lines)

    def _build_preference_instructions(self, preferences: Dict) -> str:
        """Build conditional preference lines for the Claude prompt."""
        lines = []

        tags = preferences.get('tags', [])
        if tags:
            tag_str = ', '.join(tags)
            lines.append(f"- USER PREFERENCES: Focus on {tag_str} recipes")

        meal_types = preferences.get('meal_types', [])
        if meal_types:
            if meal_types == ['snack']:
                lines.append("- Focus on SNACKS and quick bites — simple 1-3 ingredient items")
            elif meal_types == ['main']:
                lines.append("- Focus on full MEALS — proper dinner/lunch dishes")
            elif meal_types == ['side']:
                lines.append("- Focus on SIDE dishes — things that complement a main")
            else:
                types_str = ', '.join(meal_types)
                lines.append(f"- Include a mix of these meal types: {types_str}")

        if not meal_types:
            lines.append("- Include at least 1 breakfast recipe and at least 1 main dish. Fill remaining slots with a mix of mains, sides, or snacks.")

        max_time = preferences.get('max_cook_time')
        if max_time:
            lines.append(f"- ALL recipes must be under {max_time} minutes active cooking time")

        if lines:
            return "\nPREFERENCES:\n" + "\n".join(lines) + "\n"
        return ""

    def _simplify_name(self, name: str) -> str:
        """Simplify long grocery store names for the Claude prompt.
        e.g. 'Greenfield Natural Meat Co. Applewood Smoked Uncured Bacon' → 'Applewood Smoked Bacon'
        e.g. 'Kroger® 85/15 Fresh Ground Turkey Tray 1 LB' → 'Ground Turkey'
        """
        import re
        # Remove brand prefixes and suffixes
        s = name
        # Remove common brand patterns: "Brand® ...", "Brand's® ..."
        s = re.sub(r'^[\w\s\.&\']+®\s*', '', s)
        # Remove size/weight suffixes like "1 LB", "16 oz", "Tray", "Bag"
        s = re.sub(r'\b\d+(\.\d+)?\s*(LB|lb|oz|OZ|ct|CT|pk|PK|gal|GAL|ml|ML|L)\b', '', s)
        s = re.sub(r'\b(Tray|Bag|Box|Can|Pack|Bundle|Pouch|Bottle|Jug)\b', '', s, flags=re.IGNORECASE)
        # Remove "Brand Name" prefixes (words before the food)
        # Common brand indicators
        brand_words = ['kroger', 'roundy', 'greenfield', 'natural', 'meat', 'co.', 'co',
                       'simply', 'birds', 'eye', 'voila!', 'voila', 'wow', 'bao', 'celsius',
                       'heineken', 'carnation', 'old', 'fashioned', 'select', 'sara', 'lee',
                       'sunsweet', 'dole', 'del', 'monte', 'great', 'value']
        words = s.split()
        # Strip leading brand words
        while words and words[0].lower().rstrip('®.,') in brand_words:
            words.pop(0)
        s = ' '.join(words).strip()
        # Remove trailing commas, clean up whitespace
        s = re.sub(r'\s+', ' ', s).strip().rstrip(',')
        return s if len(s) > 2 else name

    def _format_inventory(self, items: List[Dict]) -> str:
        """Format pantry items for Claude prompt with simplified names."""
        if not items:
            return "Empty pantry"

        lines = []
        for item in items:
            name = item.get('name', 'Unknown')
            simple = self._simplify_name(name)
            qty = item.get('quantity', 1)
            unit = item.get('unit', '')

            if unit:
                lines.append(f"- {simple}: {qty} {unit}")
            else:
                lines.append(f"- {simple}: {qty}")

        return '\n'.join(lines)

    def get_shopping_list(self, recipe: Dict, pantry_items: List[Dict]) -> List[Dict]:
        """
        Given a recipe and pantry inventory, return what needs to be bought.

        Args:
            recipe: Recipe dict with 'ingredients' list
            pantry_items: List of pantry items

        Returns:
            List of missing ingredients
        """
        # Create a lowercase map of pantry items for matching
        pantry_names = {item['name'].lower() for item in pantry_items}

        missing = []
        if 'ingredients' in recipe:
            for ingredient in recipe['ingredients']:
                if not ingredient.get('in_pantry', False):
                    name = ingredient.get('name', '')
                    if name.lower() not in pantry_names:
                        missing.append({
                            'name': name,
                            'quantity': ingredient.get('quantity', ''),
                            'unit': ingredient.get('unit', ''),
                            'notes': f"Needed for {recipe.get('name', 'recipe')}"
                        })

        return missing
