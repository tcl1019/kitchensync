"""
Recipe API integrations for grounding suggestions in real data.
- TheMealDB: free API (test key "1"), has thumbnails, structured data
- API Ninjas: keyed API, broader recipe coverage, needs normalization
"""

import os
import re
import requests
from typing import List, Dict, Optional


MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"
NINJAS_BASE = "https://api.api-ninjas.com/v1/recipe"

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


class APINinjasClient:
    """Client for API Ninjas Recipe API."""

    def __init__(self, api_key: str, timeout: int = 5):
        self.api_key = api_key
        self.timeout = timeout

    def search_recipes(self, query: str) -> List[Dict]:
        """Search recipes by query string. Returns normalized list."""
        if not self.api_key:
            return []
        try:
            resp = requests.get(
                NINJAS_BASE,
                params={"query": query},
                headers={"X-Api-Key": self.api_key},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            raw_list = resp.json()
            if not isinstance(raw_list, list):
                return []
            return [self._normalize(r) for r in raw_list if self._is_home_scale(r)]
        except Exception as e:
            print(f"API Ninjas search error: {e}")
            return []

    def _is_home_scale(self, raw: Dict) -> bool:
        """Filter out industrial-scale recipes (e.g. 100 servings)."""
        servings = raw.get("servings", "")
        match = re.search(r'(\d+)', str(servings))
        if match and int(match.group(1)) > 12:
            return False
        return True

    def _normalize(self, raw: Dict) -> Dict:
        """Normalize API Ninjas response to app format."""
        title = self._title_case(raw.get("title", ""))
        ingredients = self._parse_ingredients(raw.get("ingredients", ""))
        instructions = self._clean_instructions(raw.get("instructions", ""))
        servings = raw.get("servings", "")

        return {
            "name": title,
            "ingredients": ingredients,
            "instructions": instructions,
            "servings": servings,
            "source": "api-ninjas",
        }

    def _title_case(self, text: str) -> str:
        """Fix ALL CAPS or weird casing to proper title case."""
        if not text:
            return ""
        # If mostly uppercase, convert to title case
        if sum(1 for c in text if c.isupper()) > len(text) * 0.5:
            return text.title()
        return text

    def _parse_ingredients(self, raw: str) -> List[Dict]:
        """Parse pipe-delimited ingredient string into structured list."""
        if not raw:
            return []
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        ingredients = []
        for part in parts:
            # Skip section headers like "** Package Together **"
            if part.startswith('**') or part.startswith('--'):
                continue
            # Fix ALL CAPS
            if sum(1 for c in part if c.isupper()) > len(part) * 0.5:
                part = part.title()
            # Try to split "2 cups Flour" or "1/2 c Flour" into quantity/unit/name
            match = re.match(
                r'^([\d/\.\s]+(?:\d+/\d+)?)\s+'          # quantity (digits, fractions)
                r'(cups?|c|tb|tbs|tbsp|ts|tsp|oz|lb|lbs|pt|qt|gal|ml|'
                r'cloves?|slices?|cans?|pkg|pcs?|pieces?|pinch|dash|bunch|heads?)\s+'
                r'(.+)',
                part, re.IGNORECASE
            )
            if match:
                qty = match.group(1).strip()
                unit = (match.group(2) or "").strip()
                name = match.group(3).strip().rstrip(';,.')
                ingredients.append({"name": name, "measure": f"{qty} {unit}".strip()})
            else:
                # Try just quantity + name (no unit)
                match2 = re.match(r'^([\d/\.]+)\s+(.+)', part)
                if match2:
                    qty = match2.group(1).strip()
                    name = match2.group(2).strip().rstrip(';,.')
                    ingredients.append({"name": name, "measure": qty})
                else:
                    ingredients.append({"name": part.rstrip(';,.'), "measure": ""})
        return ingredients

    def _clean_instructions(self, raw: str) -> str:
        """Clean up ALL CAPS instructions and normalize whitespace."""
        if not raw:
            return ""
        text = raw
        # Fix ALL CAPS
        if sum(1 for c in text if c.isupper()) > len(text) * 0.4:
            # Sentence case: capitalize first letter of each sentence
            sentences = re.split(r'(?<=[.!?])\s+', text.lower())
            text = " ".join(s.capitalize() for s in sentences)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def fetch_grounding_recipes(
        self,
        pantry_items: List[Dict],
        max_queries: int = 3,
        max_recipes: int = 5,
    ) -> List[Dict]:
        """
        Search API Ninjas with pantry-derived queries.
        Returns normalized recipes for Claude grounding.
        """
        if not pantry_items or not self.api_key:
            return []

        # Extract search terms using the same keyword map as MealDB
        search_terms = []
        seen = set()
        for item in pantry_items:
            name = item.get("name", "").strip()
            if not name:
                continue
            name_lower = name.lower()
            for keyword in INGREDIENT_KEYWORDS:
                if keyword in name_lower and keyword not in seen:
                    seen.add(keyword)
                    search_terms.append(keyword)

        # Prioritize proteins
        PROTEIN_KEYS = {'chicken', 'turkey', 'beef', 'pork', 'lamb', 'salmon',
                        'shrimp', 'tuna', 'bacon', 'sausage', 'ham', 'steak',
                        'egg', 'eggs', 'thigh', 'breast', 'drumstick', 'wing', 'mince'}
        proteins = [t for t in search_terms if t in PROTEIN_KEYS]
        others = [t for t in search_terms if t not in PROTEIN_KEYS]
        queries = (proteins + others)[:max_queries]

        if not queries:
            return []

        print(f"API Ninjas search queries: {queries}")

        seen_names = set()
        results = []
        for q in queries:
            recipes = self.search_recipes(q)
            for r in recipes:
                norm_name = r["name"].lower()
                if norm_name not in seen_names:
                    seen_names.add(norm_name)
                    results.append(r)
                    if len(results) >= max_recipes:
                        break
            if len(results) >= max_recipes:
                break

        print(f"API Ninjas found {len(results)} recipes")
        return results
