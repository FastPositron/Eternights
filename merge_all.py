import json
from pathlib import Path

prog_path = Path('C:/Users/sacke/eternights_rus/output/translations_progress.json')
with open(prog_path, encoding='utf-8') as f:
    merged = json.load(f)

before = len(merged)
errors = []

for p in sorted(Path('C:/Users/sacke/eternights_rus/output').glob('progress_0*.json')):
    try:
        with open(p, encoding='utf-8') as f:
            data = json.load(f)
        merged.update(data)
        print('OK', p.name, len(data))
    except Exception as e:
        errors.append(p.name)
        print('ERROR', p.name, str(e)[:80])

with open(prog_path, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print(f'\nTotal: {before} -> {len(merged)} (+{len(merged)-before})')
if errors:
    print('Bad files:', errors)
