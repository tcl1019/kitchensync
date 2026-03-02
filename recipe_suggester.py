"""
Recipe suggestion module for KitchenSync.
Uses Claude API to suggest recipes based on pantry inventory.
Optionally grounded with real recipes from TheMealDB.
"""

import os
import json
import re
from typing import List, Dict, Optional
from anthropic import Anthropic


class RecipeSuggester:
    """Generate recipe suggestions using Claude API."""

    def __init__(self, client: Anthropic, max_suggestions: int = 5, mealdb_client=None):
        """Initialize the recipe suggester with Anthropic client."""
        self.client = client
        self.max_suggestions = max_suggestions
        self.mealdb_client = mealdb_client

    def suggest_recipes(self, pantry_items: List[Dict],
                        preferences: Optional[Dict] = None,
                        user_prompt: Optional[str] = None) -> List[Dict]:
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

        Returns:
            List of recipe dicts with name, description, meal_type, cook_time,
            difficulty, tags, ingredients, instructions, source, source_name, thumbnail
        """
        if not pantry_items:
            return []

        # Check if API key is available
        if not os.getenv('ANTHROPIC_API_KEY') or not self.client:
            return []

        preferences = preferences or {}

        # Format pantry inventory for Claude
        inventory_text = self._format_inventory(pantry_items)

        # Build preference instructions
        pref_lines = self._build_preference_instructions(preferences)

        # Build user prompt section
        user_prompt_section = ""
        if user_prompt:
            user_prompt_section = f"\nUSER REQUEST: {user_prompt}\nHonor this request while using pantry items where possible.\n"

        # Fetch grounding recipes from MealDB
        grounding_section = ""
        if self.mealdb_client:
            grounding_section = self._build_grounding_section(pantry_items)

        count = preferences.get('count', self.max_suggestions)

        prompt = f"""You are a practical home cook, not a fancy chef. Given this pantry, suggest {count} realistic meals or snacks.

RULES:
- Each recipe is ONE dish, not a dish + random side.
- Suggest normal meals real people actually cook and search for online: stir fry, pasta, tacos, fried rice, quesadillas, soup, sandwiches, wraps, salads, etc.
- Use 3-4 pantry items per recipe. You do NOT need to use every item — and you SHOULD NOT force weird combos just to use more items.
- Prioritize perishables (meat, dairy, produce) over shelf-stable stuff
- Under 30 min active cooking
- 0-2 extra ingredients to buy (basic spices don't count)
- Simple names only: "Turkey Tacos" not "Seasoned Ground Turkey Fiesta Wraps"
- Include a MIX of meal types: some full meals, some quick snacks, some sides — unless the user specifies otherwise
- For snacks: can be as simple as 1-2 ingredients (e.g. "Apple & Peanut Butter", "Cheese Plate")

FLAVOR SANITY CHECK — CRITICAL:
- ONLY suggest ingredient combinations that are well-established in real cooking. If you wouldn't find it on a normal recipe blog, don't suggest it.
- NEVER combine sweet fruits (banana, clementine, mango, berries) with cured/savory meats (bacon, sausage, ham) UNLESS it's a widely known pairing (e.g. prosciutto + melon, pork + apple, Hawaiian pizza).
- NEVER invent bizarre fusion dishes. "Bacon Wrapped Banana" is NOT a real recipe people make. Neither is "Bacon & Clementines."
- Ask yourself: "Would a normal person see this recipe name and think 'yeah that sounds good'?" If the answer is no, don't suggest it.
- When in doubt, stick to classic comfort food and simple staples. Boring but tasty beats creative but disgusting.
{pref_lines}{user_prompt_section}{grounding_section}
PANTRY INVENTORY:
{inventory_text}

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
      "source": "themealdb or ai",
      "source_name": "Original recipe name if adapted from a reference, otherwise empty string",
      "thumbnail": "thumbnail URL if from a reference recipe, otherwise empty string",
      "ingredients": [
        {{"name": "ingredient", "quantity": "amount", "unit": "unit", "in_pantry": true}},
        {{"name": "ingredient", "quantity": "amount", "unit": "unit", "in_pantry": false}}
      ],
      "instructions": ["Step 1", "Step 2", "Step 3"]
    }}
  ]
}}"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=3000,
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
        """Fetch and format MealDB recipes as reference material for the Claude prompt."""
        try:
            grounding_recipes = self.mealdb_client.fetch_grounding_recipes(pantry_items)
        except Exception as e:
            print(f"MealDB grounding fetch error: {e}")
            return ""

        if not grounding_recipes:
            return ""

        lines = [
            "\nREFERENCE RECIPES (real recipes from a database — adapt these or use as inspiration):",
            "If you base a recipe on one of these, keep the original name, set source to 'themealdb',",
            "set source_name to the original recipe name, and include the thumbnail URL.",
            "You may also create original recipes (set source to 'ai').\n",
        ]

        for r in grounding_recipes:
            ing_list = ", ".join(i["name"] for i in r.get("ingredients", [])[:8])
            lines.append(f"- {r['name']} ({r.get('area', 'Unknown')} {r.get('category', '')})")
            lines.append(f"  Ingredients: {ing_list}")
            if r.get("thumbnail"):
                lines.append(f"  Thumbnail: {r['thumbnail']}")
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

        max_time = preferences.get('max_cook_time')
        if max_time:
            lines.append(f"- ALL recipes must be under {max_time} minutes active cooking time")

        if lines:
            return "\nPREFERENCES:\n" + "\n".join(lines) + "\n"
        return ""

    def _format_inventory(self, items: List[Dict]) -> str:
        """Format pantry items for Claude prompt."""
        if not items:
            return "Empty pantry"

        lines = []
        for item in items:
            name = item.get('name', 'Unknown')
            qty = item.get('quantity', 1)
            unit = item.get('unit', '')

            if unit:
                lines.append(f"- {name}: {qty} {unit}")
            else:
                lines.append(f"- {name}: {qty}")

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
