# ==========================================
# main.py
# ==========================================
import time
import csv
import random
from scraper import get_all_recipe_urls, scrape_single_recipe
from scraper_config import MAX_RECIPES, MIN_DELAY, MAX_DELAY, OUTPUT_CSV

if __name__ == "__main__":
    urls = get_all_recipe_urls()
    
    if not urls:
        print("No URLs found. Exiting.")
    else:
        urls_to_scrape = urls[:MAX_RECIPES]
        print(f"Starting scrape of {len(urls_to_scrape)} recipes...\n")
        
        with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            if csvfile.tell() == 0:
                writer.writerow(["URL", "Title", "Ingredients", "Instructions"])

            for i, url in enumerate(urls_to_scrape):
                print(f"[{i+1}/{len(urls_to_scrape)}] Scraping: {url}")
                
                try:
                    data = scrape_single_recipe(url)
                    if data:
                        writer.writerow([data["url"], data["title"], data["ingredients"], data["instructions"]])
                        print(f"  -> Saved: {data['title']}")
                    else:
                        print("  -> Failed to load page.")
                except Exception as e:
                    print(f"  -> ERROR: {e}")

                wait_time = random.uniform(MIN_DELAY, MAX_DELAY)
                print(f"  -> Waiting {wait_time:.1f} seconds before next request...")
                time.sleep(wait_time)

        print(f"\nDONE! Data saved to {OUTPUT_CSV}")