"""
Merge UI translation chunks back into ui_strings_ru.json.
"""
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('output/ui_strings_ru.json', encoding='utf-8') as f:
    ui_ru = json.load(f)

updated = 0
for i in [1, 2]:
    path = f'output/chunks_ru/ui_chunk_{i:03d}.json'
    with open(path, encoding='utf-8') as f:
        chunk = json.load(f)
    for t in chunk['translations']:
        key = t['key']
        ru = t['ru']
        if key in ui_ru:
            if ui_ru[key] != ru:
                ui_ru[key] = ru
                updated += 1

with open('output/ui_strings_ru.json', 'w', encoding='utf-8') as f:
    json.dump(ui_ru, f, ensure_ascii=False, indent=2)

# Verify coverage
with open('output/ui_strings_en.json', encoding='utf-8') as f:
    ui_en = json.load(f)

translated = sum(1 for k in ui_en if ui_en[k] != ui_ru.get(k, ui_en[k]))
print(f"Updated: {updated} strings")
print(f"Total translated: {translated}/{len(ui_en)}")

# Show remaining untranslated
remaining = [(k, ui_en[k]) for k in ui_en if ui_en[k] == ui_ru.get(k, ui_en[k])]
print(f"Still en==ru: {len(remaining)}")
for k, v in remaining[:20]:
    print(f"  {k}: {v[:60]}")
