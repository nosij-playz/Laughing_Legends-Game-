import json

# Read your data.json file
with open('data.json', 'r', encoding='utf-8') as f:
    game_data = json.load(f)

# Create new dictionary with .jpg keys
new_game_data = {}
for key, value in game_data.items():
    if key.startswith('LAUGH/'):
        # Extract number and convert to .jpg
        number = key.split('/')[1].split('.')[0]
        new_key = f"LAUGH/{number}.jpg"
        new_game_data[new_key] = value
        print(f"Converted: {key} -> {new_key}")
    else:
        new_game_data[key] = value

# Write back to file
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(new_game_data, f, indent=2, ensure_ascii=False)

print("✅ All keys converted to .jpg format!")