import pandas as pd
import re
from collections import Counter

print("Loading data...")
df = pd.read_csv('cookwell_recipes_fixed.csv')

ingredient_counts = Counter()

SHORTLIST = ['salt', 'water', 'neutral oil', 'cooking oil', 'cilantro', 'eggs'] 

TYPO_FIXES = {
    'hoison': 'hoisin',
    'monterrey jack': 'monterey jack',
    'handul': 'handful',
    'scallion': 'scallions' # Optional: merge singular/plural
}

NUCLEAR_JUNK = [
    'protocol', 'of choice', 'protein carb', 'leftover', 'optional',
]

JUNK_PHRASES = [
    'lunch in under', 'start cooking healthy', 'easy weeknight meals', 
    'mexican eats', 'favorite sandwiches', 'easy ingredient swaps', 
    'cheese lovers', 'using up ground meat', 'cooking with homemade broth', 
    'creating healthy meals', 'fridge cleanout time', 'breakfast & brunch',
    'one pot recipes', 'asian eats', 'all recipes', 'spice lovers',
    'recommended gear', 'our app', 'newsletter', 'contact', 'youtube', 
    'instagram', 'tiktok', 'twitter', 'cutting board', 'pinterest',
    'help us update our food photography', 'cooking through a stack of corn tortillas',
    'using up bread', 'experimenting with onions & alliums', 'cooking with vegetables', 'forward', 'mexico city classics',
    'scrap meals', 'our best burgers', 'flavor profile switch up', 'the protein carb swap protocol', 'fast food dupes',
    'fry in batches to ensure even oil temps',
    'store in the fridge for several weeks',
    'classic ridges shape: press the gnocchi into the back of a fork and roll it away',
    'once cooled they should be and crumbly',
    'mix & match to your preference',
    'set the chicken aside to rest before dicing into cubes for filling the enchiladas',
    'check out the video for rolling tips',
    'scramble the egg into a wide bowl and then add a handful of panko breadcrumbs into another plate or container',
    'feel free to add whatever else you might like to your sauce now (siracha',
    'see the video for a visual guide',
    'portion and roll out right away',
    'bonus points: add in the oil from the anchovy tin for extra flavor!',
    'remove when cooked to your desired temperature. for medium well',
    'this sauce can be kept in the refrigerator to use for other sandwiches & wraps',
    'this can be done in advance',
    'you can also use baking spray here',
    'so long as the shrimp are peeled',
    'extra sauce can be frozen',
    'pasta salads',
    'our top tostadas',
    'kebabs of the world',
    'nyc street food classics',
    'master the breakfast taco elements',
    'short pasta of choice',
    'best pizzas',
    'meals to impress',
    'adding acidity',
    'spice profile switch up',
    'our best braised meats',
    'our top tacos',
    'best of stir frying',
    'weeknight pasta',
    'golden brown &',
    'the protein carb swap protocol',
    'protein carb swap',
    'tomato season',
    "let's get baking",
    'food frameworks',
    'pantry meals',
    'fried cutlets of the world',
    'meal prep',
    'street eats',
    'using up eggs',
    'satisfying salads',
    'soup season',
    'thanksgiving dinner',
    'meze dips & spreads',
    'high protein baked potatoes',
    'the weeknight chopped cheese series',
    'perfect the pad see ew stir fry',
    'using gochujang',
    'cooking with rice',
    'drain and set aside',
    'boil & drain the pasta',
    'gather dressing components',
    'chop any vegetables',
    'enjoy with toppings of choice',
    'garnish with basil and enjoy',
    'repeat with remaining sandwiches',
    'leave as is',
    'adjust if needed',
    'for less spice',
    'for a bonus treat',
    'check out the video for rolling tips',
    'see the video for a visual guide',
    'then',
    'while those develop some',
    'meanwhile'
]

MEASUREMENT_WORDS = [
    'to taste', 'a sprinkle', 'a drizzle', 'as needed', 'optional', 'g', 'kg', 'ml', 'l', 
    'cup', 'cups', 'tbsp', 'tsp', 'oz', 'lb', 'lbs', 'pinch', 'cloves', 'clove', 'a spoonful',
    'spoonful', 'spoonfuls', 'part', 'parts', 'a splash', 'a squeeze', 'a sprig', 'lb', 'lbs', 'equal amount',
    'enough to cover', 'enough to coat', 'a heaping', 'a few', 'a handful', 'handful', 'slices',
    'a', 'large', 'small', 'medium', 'extra', 'heaping', 'full', 'g', 'or',
    'can', 'pack', 'packet', 'box', 'bag', 'knob', 'dollop', 'squirt', 'sprinkle', 'stick', 'to coat', 'serving', 'servings',

]

print("Counting and normalizing ingredients...")
for index, row in df.iterrows():
    ingredients_str = str(row['Ingredients'])
    raw_ingredients = ingredients_str.split(' | ')

    # 1. Clean all ingredients for THIS specific recipe first
    cleaned_for_this_recipe = []

    for ing in raw_ingredients:

        clean = ing.strip().lower()

        # NUCLEAR CHECK
        if any(junk in clean for junk in NUCLEAR_JUNK):
            continue

        is_shortlist = False
        for item in SHORTLIST:
            pattern = r'\b' + item.replace(' ', r'\s+') + r'\b'
            if re.search(pattern, clean):
                cleaned_for_this_recipe.append(item) 
                is_shortlist = True
                break

        # If we found a match, skip ALL the other cleaning steps and move to the next ingredient!
        if is_shortlist:
            continue
        
        # A. Junk phrase check
        if any(junk in clean for junk in JUNK_PHRASES):
            continue

        if re.search(r'\bdishes\b', clean): continue
        if re.search(r'\bmicrowave\b', clean): continue
        if re.search(r'\bper\b', clean): continue
        

        # 1. Nuke invisible unicode characters (zero-width spaces, etc.)
        clean = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', clean)
        
        # 2. Delete "for" and everything after it IMMEDIATELY
        clean = re.sub(r'\s*\bfor\b.*', '', clean).strip()
        
        # ==========================================



    
        clean = clean.split(',')[0].strip()
        clean = re.sub(r'\d+', '', clean).strip()
        
        for word in MEASUREMENT_WORDS:
            clean = re.sub(r'\b' + word + r'\b', '', clean).strip()
            
        clean = clean.replace('/', ' ').replace('-', ' ').replace('~', '').strip().replace('%','').strip()
        clean = clean.replace('"', '').replace('”', '').replace('“', '').strip()      
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = clean.rstrip(',. ')

        if clean in TYPO_FIXES:
            clean = TYPO_FIXES[clean]

        words = clean.split()
        if len(words) > 1 and words[-1] == words[-2]:
            clean = " ".join(words[:-1])

        words = clean.split()
        if len(words) > 2 and words[0] == words[-1]:
            clean = " ".join(words[:-1])

        if clean and len(clean) > 2 and not clean.isspace():
            cleaned_for_this_recipe.append(clean)

    # ==========================================
    # 2. THE MAGIC FIX: Remove duplicates for THIS recipe only!
    # This instantly fixes the mobile/desktop HTML duplicate issue!
    # ==========================================
    unique_ingredients = list(set(cleaned_for_this_recipe))

    # 3. Add to the global counter
    for item in unique_ingredients:
        ingredient_counts[item] += 1

# Save to CSV
# Convert to DataFrame and sort
counts_df = pd.DataFrame(ingredient_counts.items(), columns=['Ingredient', 'Count'])
counts_df = counts_df.sort_values(by='Count', ascending=False)

output_file = 'buildvis.csv'

# 1. Save the main, clean data first
counts_df.to_csv(output_file, index=False)


print(f"SUCCESS! Saved {len(counts_df)} unique ingredients to {output_file}")

