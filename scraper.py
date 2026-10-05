# ==========================================
# scraper.py
# ==========================================
import requests
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from scraper_config import HEADERS, SITEMAP_URL, FLAVOR_WORDS, NAV_JUNK

def get_all_recipe_urls():
    print(f"Fetching sitemap from {SITEMAP_URL} ...")
    response = requests.get(SITEMAP_URL, headers=HEADERS)
    
    if response.status_code != 200:
        print("ERROR: Could not fetch sitemap.")
        return []

    root = ET.fromstring(response.content)
    urls = []
    namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    for url in root.findall('sm:url', namespace):
        loc = url.find('sm:loc', namespace).text
        if '/recipe/' in loc:
            urls.append(loc)
            
    print(f"Found {len(urls)} recipe URLs in the sitemap.")
    return urls

def scrape_single_recipe(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Title
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"
    
    # Ingredients
    all_lis = soup.find_all('li')
    leaf_lis = [li for li in all_lis if not li.find('li')]
    valid_lis = [li for li in leaf_lis if not li.find_parent(['footer', 'nav', 'aside'])]
    
    flavor_pattern = re.compile(r'\b(' + '|'.join(FLAVOR_WORDS) + r')\b', re.IGNORECASE)
    
    ingredients = []
    for li in valid_lis:
        text = li.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        text = flavor_pattern.sub('', text).strip()
        text = re.sub(r'\s+,', ',', text)
        text = re.sub(r',\s*$', '', text)
        
        if text.endswith('.') and len(text) > 40: continue
        if text.startswith(('If ', 'Full ', 'Different ', 'Keep ', 'Note:', 'Tip:', 'Pro tip:', 'Add ', 'Stir ')): continue
        if any(word.lower() in text.lower() for word in NAV_JUNK): continue
        
        if text and len(text) > 2:
            ingredients.append(text)

    # Instructions
    step_headings = soup.find_all(lambda tag: tag.name in ['h2', 'h3', 'h4', 'h5'] and re.search(r'Step \d+', tag.get_text()))
    instructions = []
    
    if step_headings:
        for heading in step_headings:
            heading_text = heading.get_text(separator=' ', strip=True)
            step_text = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']: break
                text = sibling.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)
                if text: step_text.append(text)
            instructions.append(f"{heading_text}: {' '.join(step_text)}")

    return {
        "url": url,
        "title": title,
        "ingredients": " | ".join(ingredients),
        "instructions": " || ".join(instructions)
    }