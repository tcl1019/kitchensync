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

        # Fetch grounding recipes from APIs
        grounding_section = self._build_grounding_section(pantry_items) if pantry_items else ""

        count = preferences.get('count', self.max_suggestions)

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

RECIPE COMPLETENESS — CRITICAL:
- Instructions must be DETAILED and COMPLETE. A real person should be able to cook the dish from your instructions alone.
- Each step should include specific temperatures, times, and techniques. NOT just "Cook the chicken" — instead "Heat olive oil in a large skillet over medium-high heat. Season chicken thighs with salt, pepper, and paprika. Cook 5-6 minutes per side until golden brown and internal temp reaches 165°F."
- Include 5-8 steps for main dishes. 3-5 steps for simple snacks/sides.
- Include prep steps (chopping, seasoning) and finishing steps (garnish, rest, plate).

FLAVOR EXCELLENCE — make every recipe crave-worthy:
- Brown and sear meats HARD. Use the fond — deglaze the pan with broth, wine, or vinegar.
- Season at EVERY stage: salt the pasta water, season before searing, adjust at the end.
- Finish dishes with acid: a squeeze of lemon, splash of vinegar, or dollop of sour cream brightens everything.
- Use aromatics aggressively: garlic, ginger, shallots, fresh herbs are the backbone of flavor.
- Specify exact spice combos, not just "add spices." Example: "1 tsp smoked paprika, 1/2 tsp cumin, pinch of cayenne."
- Toast dry spices in oil before adding liquid — this blooms their flavor.
- Think: "Would this recipe get 4+ stars on AllRecipes?" If the flavor profile is bland, fix it.

FLAVOR SANITY CHECK — CRITICAL (violations will be rejected):
- ONLY suggest recipes you could find on AllRecipes, Tasty, or a normal food blog.
- ABSOLUTELY NEVER combine: bacon + banana, bacon + clementine, bacon + mango, sausage + fruit, meat + sweet fruit.
- The ONLY acceptable meat + fruit pairings are: pork + apple, prosciutto + melon, chicken + cranberry, ham + pineapple.
- Do NOT wrap random things in bacon. "Bacon Wrapped Turkey" is not a home recipe. Use bacon in sandwiches, pasta, eggs, salads, burgers, or soups.
- Every recipe must pass this test: "Could I google this recipe name and find it on a real cooking website?" If no, don't suggest it.
- When the pantry has incompatible items (e.g. bacon AND bananas), use them in SEPARATE recipes, not together.
{pref_lines}{user_prompt_section}{grounding_section}{pantry_block}

Return valid JSON only (no markdown, no code fences, no explanation):
{{
  "recipes": [
    {{
      "name": "Simple recipe name",
      "description": "1 sentence — what it is and why it works with this pantry",
      "meal_type": "main|snack|side|breakfast",
      "cook_time": "10 min",
      "difficulty": "easy|medium|hard",
      "tags": ["low-carb", "quick"],
      "source": "themealdb or api-ninjas or ai",
      "source_name": "Original recipe name if adapted from a reference, otherwise empty string",
      "thumbnail": "thumbnail URL if from a reference recipe, otherwise empty string",
      "ingredients": [
        {{"name": "ingredient", "quantity": "amount", "unit": "unit", "in_pantry": true}},
        {{"name": "ingredient", "quantity": "amount", "unit": "unit", "in_pantry": false}}
      ],
      "instructions": ["Detailed step 1 with temps/times", "Detailed step 2", "...5-8 steps for mains"]
    }}
  ]
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                timeout=90.0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Strip markdown code fences if present
            cleaned = response_text.strip()
            fence_match = re.match(r'^```\w*\s*\n(.*?)```\s*$', cleaned, re.DOTALL)
            if fence_match:
                cleaned = fence_match.group(1).strip()
            else:
                cleaned = cleaned.strip()

            # Parse JSON response
            try:
                data = json.loads(cleaned)
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
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Response: {response_text}")
                return []

        except Exception as e:
            print(f"Claude API error: {e}")
            return []

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
                    result = future.result(timeout=12)
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

        # Skip obscure cuisines, score by relevance, take top 5
        SKIP_AREAS = {'Japanese', 'Chinese', 'Vietnamese', 'Thai', 'Indian',
                      'Moroccan', 'Turkish', 'Egyptian', 'Tunisian', 'Croatian',
                      'Malaysian', 'Filipino', 'Kenyan'}
        candidates = [r for r in mealdb_recipes if r.get('area', '') not in SKIP_AREAS]
        candidates.sort(key=relevance_score, reverse=True)
        filtered_mealdb = candidates[:5]

        all_refs = filtered_mealdb + ninjas_recipes[:3]  # Cap total references
        if not all_refs:
            return ""

        must_use = min(len(all_refs), 3)

        lines = [
            f"\nREFERENCE RECIPES — MANDATORY (you MUST base at least {must_use} of your {self.max_suggestions} recipes on these):",
            f"Your FIRST {must_use} recipes in the JSON array MUST be adapted from these references.",
            "Simplify the recipe name if it's too fancy (e.g. 'Bubble & Squeak' → 'Bacon Potato Hash').",
            "Adapt them to use pantry items. Set source/source_name/thumbnail as shown below.",
            f"Only the remaining {self.max_suggestions - must_use} slots can be AI originals (source='ai').\n",
        ]

        for r in filtered_mealdb:
            ing_list = ", ".join(i["name"] for i in r.get("ingredients", [])[:8])
            lines.append(f"- {r['name']} ({r.get('area', 'Unknown')} {r.get('category', '')})")
            lines.append(f"  Ingredients: {ing_list}")
            if r.get("thumbnail"):
                lines.append(f"  Thumbnail: {r['thumbnail']}")
            lines.append(f"  → Set source='themealdb', source_name='{r['name']}', thumbnail='{r.get('thumbnail', '')}'")
            lines.append("")

        for r in ninjas_recipes[:3]:
            ing_list = ", ".join(i["name"] for i in r.get("ingredients", [])[:8])
            lines.append(f"- {r['name']} (Servings: {r.get('servings', 'unknown')})")
            lines.append(f"  Ingredients: {ing_list}")
            lines.append(f"  → Set source='api-ninjas', source_name='{r['name']}', thumbnail=''")
            lines.append("")

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
