"""
Parser module for PantryPal.
Handles parsing of Instacart orders and other text formats.
"""

import os
import re
import json
from typing import List, Dict, Tuple, Any
from anthropic import Anthropic


class InstacartParser:
    """Parse Instacart order history text to extract items."""

    # Format 1: "Item Name | qty: N" (from bookmarklet)
    BOOKMARKLET_PATTERN = re.compile(
        r'^([^|]+?)\s*\|\s*qty:\s*(\d+(?:\.\d+)?)\s*$',
        re.MULTILINE | re.IGNORECASE
    )

    # Format 2: "Item Name Qty: X" or "Item Name Quantity: X"
    ITEM_PATTERN = re.compile(
        r'(?:^|\n)\s*([^0-9\n]+?)\s+(?:Qty|Quantity):\s*(\d+(?:\.\d+)?)',
        re.MULTILINE | re.IGNORECASE
    )

    # Format 3: Raw Instacart page text - "Item Name$X.XX • eachQuantity: N"
    # This pattern looks for text starting with capital letter up to a dollar sign
    RAW_INSTACART_PATTERN = re.compile(
        r'([A-Z][^\$\n]+?)\$[\d.]+\s*(?:•\s*each)?Quantity:\s*(\d+(?:\.\d+)?)',
        re.MULTILINE | re.IGNORECASE
    )

    # Format 4: "Item Name × X"
    ALT_ITEM_PATTERN = re.compile(
        r'([^×\n]+?)\s*×\s*(\d+(?:\.\d+)?)',
        re.MULTILINE
    )

    # Price pattern to help identify items
    PRICE_PATTERN = re.compile(r'\$[\d.]+')

    def __init__(self, client: Anthropic):
        """Initialize parser with Anthropic client for fallback parsing."""
        self.client = client

    def parse_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse Instacart order text to extract items.
        Supports multiple formats:
        1. "Item Name | qty: N" (bookmarklet format)
        2. "Item Name Qty: X" (standard format)
        3. "Item Name$X.XX • eachQuantity: N" (raw page text)
        4. "Item Name × X" (alternative format)
        
        Returns list of dicts with 'name' and 'quantity' keys.
        """
        items = []

        # Try regex-based parsing first (multiple patterns in order)
        items = self._parse_with_regex(text)

        # If regex found little/nothing, use Claude as fallback
        if len(items) < 1:
            items = self._parse_with_claude(text)

        return items

    def _clean_item_name(self, name: str) -> str:
        """Clean up item names by removing common artifacts."""
        name = name.strip()
        
        # Remove leading artifacts like "Replaced (1)", "Found (31)", etc.
        name = re.sub(r'^(?:Replaced|Found|Substituted)\s*\(\d+\)', '', name).strip()
        
        # Remove common status prefixes
        name = re.sub(r'^(?:Current|Original|Price):', '', name).strip()
        
        return name

    def _parse_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Parse using regex patterns in order of specificity."""
        items = []
        seen = set()

        # Try bookmarklet format first (most specific)
        for match in self.BOOKMARKLET_PATTERN.finditer(text):
            name = self._clean_item_name(match.group(1))
            qty = float(match.group(2))

            if name and name.lower() not in seen and len(name) > 2:
                items.append({'name': name, 'quantity': qty})
                seen.add(name.lower())

        # If successful, return early
        if items:
            return items

        # Try raw Instacart format (concatenated text without line breaks)
        for match in self.RAW_INSTACART_PATTERN.finditer(text):
            name = self._clean_item_name(match.group(1))
            qty = float(match.group(2))

            if name and name.lower() not in seen and len(name) > 2:
                items.append({'name': name, 'quantity': qty})
                seen.add(name.lower())

        if items:
            return items

        # Try standard format
        for match in self.ITEM_PATTERN.finditer(text):
            name = self._clean_item_name(match.group(1))
            qty = float(match.group(2))

            if name and name.lower() not in seen and len(name) > 2:
                items.append({'name': name, 'quantity': qty})
                seen.add(name.lower())

        if items:
            return items

        # Try alternative format
        for match in self.ALT_ITEM_PATTERN.finditer(text):
            name = self._clean_item_name(match.group(1))
            qty = float(match.group(2))

            # Filter out common non-items
            if name and len(name) > 2 and name.lower() not in seen:
                items.append({'name': name, 'quantity': qty})
                seen.add(name.lower())

        return items

    def _parse_with_claude(self, text: str) -> List[Dict[str, Any]]:
        """
        Use Claude to intelligently parse the text as a fallback.
        This is useful for varied Instacart formats.
        """
        # Check if API key is available
        if not os.getenv('ANTHROPIC_API_KEY') or not self.client:
            return []

        prompt = f"""You are an expert at parsing grocery order confirmations.
Extract the list of items from this Instacart order text. 
For each item, identify the product name and quantity.

Text:
{text}

Return a JSON array of objects with 'name' and 'quantity' keys.
Example: [
  {{"name": "Bananas", "quantity": 1}},
  {{"name": "Milk", "quantity": 2}}
]

Only return valid JSON, nothing else."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Extract JSON from response
            try:
                items = json.loads(response_text)
                # Validate structure
                if isinstance(items, list):
                    valid_items = []
                    for item in items:
                        if isinstance(item, dict) and 'name' in item:
                            qty = item.get('quantity', 1)
                            if not isinstance(qty, (int, float)):
                                try:
                                    qty = float(qty)
                                except (ValueError, TypeError):
                                    qty = 1
                            valid_items.append({
                                'name': str(item['name']).strip(),
                                'quantity': float(qty)
                            })
                    return valid_items
            except json.JSONDecodeError:
                return []

        except Exception as e:
            print(f"Claude parsing error: {e}")
            return []

    def infer_category(self, item_name: str) -> str:
        """
        Infer category from item name using simple heuristics.
        Returns one of: Vegetables, Fruits, Dairy, Meat, Pantry, Other
        """
        name_lower = item_name.lower()

        # Vegetable keywords
        vegetables = ['broccoli', 'spinach', 'lettuce', 'carrot', 'onion', 'garlic',
                      'tomato', 'pepper', 'cucumber', 'celery', 'potato', 'asparagus',
                      'kale', 'cabbage', 'zucchini', 'squash', 'bean', 'pea']
        if any(v in name_lower for v in vegetables):
            return 'Vegetables'

        # Fruit keywords
        fruits = ['apple', 'banana', 'orange', 'grape', 'strawberry', 'blueberry',
                  'mango', 'pineapple', 'lemon', 'lime', 'peach', 'pear', 'watermelon',
                  'cherry', 'raspberry', 'avocado']
        if any(f in name_lower for f in fruits):
            return 'Fruits'

        # Dairy keywords
        dairy = ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'ice cream']
        if any(d in name_lower for d in dairy):
            return 'Dairy'

        # Meat keywords
        meat = ['chicken', 'beef', 'pork', 'turkey', 'lamb', 'fish', 'salmon',
                'steak', 'bacon', 'sausage', 'ground']
        if any(m in name_lower for m in meat):
            return 'Meat'

        # Pantry keywords (grains, oils, spices, etc.)
        pantry = ['rice', 'pasta', 'bread', 'flour', 'sugar', 'salt', 'oil', 'vinegar',
                  'sauce', 'spice', 'herb', 'cereal', 'granola', 'bean', 'lentil',
                  'nuts', 'coffee', 'tea', 'chocolate', 'cinnamon', 'pepper']
        if any(p in name_lower for p in pantry):
            return 'Pantry'

        return 'Other'
