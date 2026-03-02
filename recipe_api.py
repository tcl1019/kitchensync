"""
TheMealDB integration for grounding recipe suggestions in real data.
Free API — no signup needed (test key "1").
"""

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

    def fetch_grounding_recipes(
        self,
        pantry_items: List[Dict],
        max_ingredients: int = 3,
        max_recipes: int = 6,
    ) -> List[Dict]:
        """
        Given pantry items, pick the top perishable ingredients,
        search MealDB for each, and return up to max_recipes unique detailed results.
        """
        if not pantry_items:
            return []

        # Sort by category priority (perishables first)
        sorted_items = sorted(
            pantry_items,
            key=lambda x: CATEGORY_PRIORITY.get(x.get("category", "Other"), 7),
        )

        # Pick top N ingredient names
        search_terms = []
        for item in sorted_items:
            name = item.get("name", "").strip()
            if name and len(search_terms) < max_ingredients:
                # Use just the first word for better MealDB matching
                # e.g. "ground turkey" -> "turkey", "chicken breast" -> "chicken"
                simple_name = name.split()[-1] if len(name.split()) > 1 else name
                search_terms.append(simple_name.lower())

        if not search_terms:
            return []

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

        # Get full details for top candidates (limit API calls)
        detailed = []
        for candidate in candidates[:max_recipes]:
            detail = self.get_recipe_detail(candidate["id"])
            if detail:
                detailed.append(detail)

        return detailed
