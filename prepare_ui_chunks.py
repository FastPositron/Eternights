"""
Prepare UI translation chunks for agents.
"""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('output/ui_need_translation.json', encoding='utf-8') as f:
    items = json.load(f)  # list of [key, en_value]

# Filter out "SP 1".."SP 7" type strings (don't need translation)
filtered = []
for key, val in items:
    v = val.strip()
    # Skip SP N patterns, single words that are names
    if v.startswith('SP ') and v[3:].isdigit():
        continue
    filtered.append({"key": key, "en": val})

print(f"Total to translate: {len(filtered)}")

# Split into chunks of 150
chunk_size = 155
chunks = []
for i in range(0, len(filtered), chunk_size):
    chunk = filtered[i:i+chunk_size]
    chunks.append(chunk)

for i, chunk in enumerate(chunks):
    chunk_data = {
        "chunk_id": i + 1,
        "strings": [{"idx": j, "key": chunk[j]["key"], "en": chunk[j]["en"]}
                     for j in range(len(chunk))]
    }
    path = f'output/chunks_en/ui_chunk_{i+1:03d}.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(chunk_data, f, ensure_ascii=False, indent=2)
    print(f"  {path}: {len(chunk)} strings")

print(f"\nTotal chunks: {len(chunks)}")
