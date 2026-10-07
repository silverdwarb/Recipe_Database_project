import pandas as pd

print("Loading existing CSV...")
df = pd.read_csv('cookwell_recipes.csv')

print("Applying targeted regex fixes...")

# The regex r'low-(?![a-zA-Z])' means:
# Match "low-" ONLY if it is NOT followed by a letter.
# This catches "low- " or "low-" at the end of a string.
# It safely IGNORES "low-moisture" or "low-sodium".
df['Ingredients'] = df['Ingredients'].str.replace(r'low-(?![a-zA-Z])', 'low fat', regex=True)

# Save to a NEW file so your original data is safe
output_file = 'cookwell_recipes_fixed.csv'
df.to_csv(output_file, index=False)

print(f"SUCCESS! Saved fixed data to {output_file}")