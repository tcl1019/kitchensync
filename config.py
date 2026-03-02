"""
Configuration module for PantryPal.
Loads environment variables and sets defaults.
"""

import os
from pathlib import Path

# Get the base directory
BASE_DIR = Path(__file__).parent

# Flask configuration
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
TESTING = os.getenv('FLASK_TESTING', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'pantrypal.db'))

# Anthropic API configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# API Ninjas configuration
API_NINJAS_KEY = os.getenv('API_NINJAS_KEY', '')

# App configuration
ITEMS_PER_PAGE = 20
MAX_RECIPES_SUGGESTIONS = 5

# Database schema version
DB_VERSION = 1
