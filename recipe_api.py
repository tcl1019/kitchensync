"""
TheMealDB integration for grounding recipe suggestions in real data.
Free API — no signup needed (test key "1").
"""

import re
import requests
from typing import List, Dict, Optional


MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"

# Priority for picking search ingredients (perishables first)
CATEGORY_PRIORITY = {
    'Meat': 0,
    'Dairy': 1,
    'Vegetables': 2,
    'Fruits': 3,
    'Frozen': 4,
    'Pantry': 5,
    'Beverages': 6,
    'Other': 7,
}

# Common keywords that map to MealDB ingredient names
# Handles long grocery store names → simple ingredient
INGREDIENT_KEYWORDS = {
    'bacon': 'Bacon', 'turkey': 'Turkey Mince', 'chicken': 'Chicken',
    'beef': 'Beef', 'pork': 'Pork', 'salmon': 'Salmon', 'shrimp': 'Shrimp',
    'egg': 'Eggs', 'eggs': 'Eggs', 'milk': 'Milk', 'cheese': 'Cheese',
    'butter': 'Butter', 'cream': 'Cream', 'rice': 'Rice', 'pasta': 'Pasta',
    'potato': 'Potatoes', 'potatoes': 'Potatoes', 'tomato': 'Tomatoes',
    'tomatoes': 'Tomatoes', 'onion': 'Onion', 'garlic': 'Garlic',
    'lettuce': 'Lettuce', 'spinach': 'Spinach', 'broccoli': 'Broccoli',
    'carrot': 'Carrots', 'carrots': 'Carrots', 'pepper': 'Pepper',
    'mushroom': 'Mushrooms', 'mushrooms': 'Mushrooms', 'avocado': 'Avocado',
    'lemon': 'Lemon', 'lime': 'Lime', 'banana': 'Bananas',
    'sausage': 'Sausages', 'ham': 'Ham', 'tuna': 'Tuna',
    'lamb': 'Lamb', 'steak': 'Steak', 'mince': 'Minced Beef',
    'thigh': 'Chicken Thighs', 'breast': 'Chicken Breast',
    'drumstick': 'Chicken drumsticks', 'wing': 'Chicken Wings',
}


class MealDBClient:
    """Client for TheMealDB free API."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def search_by_ingredient(self, ingredient: str) -> List[Dict]:
        """Search recipes by a single ingredient. Returns simplified list."""
        try:
            resp = requests.get(
                f"{MEALDB_BASE}/filter.php",
                params={"i": ingredient},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            meals = data.get("meals") or []
            return [
                {
                    "id": m["idMeal"],
                    "name": m["strMeal"],
                    "thumbnail": m.get("strMealThumb", ""),
                }
                for m in meals
            ]
        except Exception as e:
            print(f"MealDB search_by_ingredient error: {e}")
            return []

    def get_recipe_detail(self, meal_id: str) -> Optional[Dict]:
        """Get full recipe details by MealDB ID."""
        try:
            resp = requests.get(
                f"{MEALDB_BASE}/lookup.php",
                params={"i": meal_id},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            meals = data.get("meals") or []
            if not meals:
                return None
            return self._normalize_recipe(meals[0])
        except Exception as e:
            print(f"MealDB get_recipe_detail error: {e}")
            return None

    def search_by_name(self, query: str) -> List[Dict]:
        """Search recipes by name (for natural language prompt support)."""
        try:
            resp = requests.get(
                f"{MEALDB_BASE}/search.php",
                params={"s": query},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            meals = data.get("meals") or []
            return [self._normalize_recipe(m) for m in meals[:6]]
        except Exception as e:
            print(f"MealDB search_by_name error: {e}")
            return []

    def _normalize_recipe(self, raw: Dict) -> Dict:
        """Normalize MealDB response to app format."""
        ingredients = []
        for i in range(1, 21):
            name = (raw.get(f"strIngredient{i}") or "").strip()
            measure = (raw.get(f"strMeasure{i}") or "").strip()
            if name:
                ingredients.append({"name": name, "measure": measure})

        return {
            "id": raw.get("idMeal", ""),
            "name": raw.get("strMeal", ""),
            "category": raw.get("strCategory", ""),
            "area": raw.get("strArea", ""),
            "instructions": raw.get("strInstructions", ""),
            "ingredients": ingredients,
            "thumbnail": raw.get("strMealThumb", ""),
            "source_url": raw.get("strSource", ""),
        }

    def _extract_search_term(self, item_name: str) -> Optional[str]:
        """
        Extract the best MealDB search term from a grocery item name.
        e.g. "Greenfield Natural Meat Co. Applewood Smoked Uncured Bacon" → "Bacon"
        e.g. "Kroger® 85/15 Fresh Ground Turkey Tray 1 LB" → "Turkey Mince"
        """
        name_lower = item_name.lower()
        # Check each keyword against the full item name
        for keyword, mealdb_name in INGREDIENT_KEYWORDS.items():
            if keyword in name_lower:
                return mealdb_name
        return None

    def fetch_grounding_recipes(
        self,
        pantry_items: List[Dict],
        max_search_terms: int = 4,
        max_recipes: int = 8,
    ) -> List[Dict]:
        """
        Given pantry items, extract ingredient keywords, search MealDB,
        and return up to max_recipes unique detailed results.
        """
        if not pantry_items:
            return []

        # Extract ALL possible search terms, then pick the best ones
        all_terms = []
        seen_terms = set()
        for item in pantry_items:
            name = item.get("name", "").strip()
            if not name:
                continue
            term = self._extract_search_term(name)
            if term and term.lower() not in seen_terms:
                seen_terms.add(term.lower())
                all_terms.append(term)

        # Prioritize proteins/meats (better recipe anchors) over dairy/pantry
        PROTEIN_TERMS = {'chicken', 'chicken thighs', 'chicken breast', 'chicken drumsticks',
                         'chicken wings', 'turkey mince', 'turkey', 'beef', 'minced beef',
                         'pork', 'lamb', 'salmon', 'shrimp', 'tuna', 'bacon', 'sausages',
                         'ham', 'steak', 'eggs'}
        proteins = [t for t in all_terms if t.lower() in PROTEIN_TERMS]
        others = [t for t in all_terms if t.lower() not in PROTEIN_TERMS]
        search_terms = (proteins + others)[:max_search_terms]

        if not search_terms:
            return []

        print(f"MealDB search terms: {search_terms}")

        # Search MealDB for each ingredient, collect unique meal IDs
        seen_ids = set()
        candidates = []
        for term in search_terms:
            results = self.search_by_ingredient(term)
            for r in results:
                if r["id"] not in seen_ids and len(candidates) < max_recipes * 2:
                    seen_ids.add(r["id"])
                    candidates.append(r)

        if not candidates:
            return []

        print(f"MealDB found {len(candidates)} candidate recipes")

        # Get full details for top candidates (limit API calls)
        detailed = []
        for candidate in candidates[:max_recipes]:
            detail = self.get_recipe_detail(candidate["id"])
            if detail:
                detailed.append(detail)

        return detailed
