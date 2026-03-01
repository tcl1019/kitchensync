"""
Recipe suggestion module for PantryPal.
Uses Claude API to suggest recipes based on pantry inventory.
"""

import os
import json
import re
from typing import List, Dict, Optional
from anthropic import Anthropic


class RecipeSuggester:
    """Generate recipe suggestions using Claude API."""

    def __init__(self, client: Anthropic, max_suggestions: int = 5):
        """Initialize the recipe suggester with Anthropic client."""
        self.client = client
        self.max_suggestions = max_suggestions

    def suggest_recipes(self, pantry_items: List[Dict]) -> List[Dict]:
        """
        Suggest recipes based on available pantry items.
        
        Args:
            pantry_items: List of dicts with 'name', 'quantity', 'unit' keys
            
        Returns:
            List of recipe dicts with name, description, ingredients, and instructions
        """
        if not pantry_items:
            return []

        # Check if API key is available
        if not os.getenv('ANTHROPIC_API_KEY') or not self.client:
            return []

        # Format pantry inventory for Claude
        inventory_text = self._format_inventory(pantry_items)

        prompt = f"""You are a practical home cook, not a fancy chef. Given this pantry, suggest {self.max_suggestions} realistic weeknight meals.

RULES:
- Each recipe is ONE dish, not a dish + random side. "BLT with chicken salad on the side" is two meals crammed together — don't do that.
- Suggest normal meals real people google: stir fry, pasta, tacos, fried rice, quesadillas, soup, etc.
- Use 3-4 pantry items per recipe. You do NOT need to use every item — it's fine to leave things unused.
- Prioritize perishables (meat, dairy, produce) over shelf-stable stuff
- Under 30 min active cooking
- 0-2 extra ingredients to buy (basic spices don't count)
- Simple names only: "Turkey Tacos" not "Seasoned Ground Turkey Fiesta Wraps"

PANTRY INVENTORY:
{inventory_text}

Return valid JSON only (no markdown, no code fences, no explanation):
{{
  "recipes": [
    {{
      "name": "Simple recipe name",
      "description": "1 sentence — what it is and why it works with this pantry",
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
                return recipes[:self.max_suggestions]
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Response: {response_text}")
                return []

        except Exception as e:
            print(f"Claude API error: {e}")
            return []

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
