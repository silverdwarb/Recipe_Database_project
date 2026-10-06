# ==========================================
# scraper_config.py
# ==========================================

# --- Website Settings ---
BASE_URL = "https://www.cookwell.com"
SITEMAP_URL = f"{BASE_URL}/server-sitemap.xml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
}

# --- Scraper Settings ---
OUTPUT_CSV = "cookwell_recipes.csv"
MAX_RECIPES = 10000  # Change this to 1000 when you are ready to go big!
MIN_DELAY = 10
MAX_DELAY = 20

# --- Filtering Rules ---
FLAVOR_WORDS = ['SOUR', 'CRISPY', 'CHEWY', 'SALTY', 'SWEET', 'SPICY', 'TANGY', 'RICH', 'FRESH', 'UMAMI', 'CRUNCHY', 'FAT', 'CREAMY', 'COLOR', 'PUNGENT','ASTRINGENT', 'UNCTUOUS' ]

NAV_JUNK = [
    'One Pot Recipes', 'Asian Eats', 'All Recipes', 'Spice lovers',
    'RECIPES', 'FUNDAMENTALS', 'OUR APP', 'NEWSLETTER', 
    'RECOMMENDED GEAR', 'CONTACT', 'YouTube', 'Instagram', 'TikTok', 'Twitter',
    'CUTTING BOARD', 'PINTEREST', 'SHARE', 'PRINT', 'SAVE', 'RATE', 'SUBSCRIBE'
]