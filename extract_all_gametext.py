"""Извлекаем ВСЕ GameText_* ассеты из gamemanager бандла в отдельные JSON"""
import UnityPy
import json
from pathlib import Path

BUNDLES_DIR = Path("C:/Program Files (x86)/Steam/steamapps/common/Eternights/Eternights_Data/StreamingAssets/aa/Windows/StandaloneWindows64")
OUT = Path("C:/Users/sacke/eternights_rus/output")

bundle_path = BUNDLES_DIR / "gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle"
env = UnityPy.load(str(bundle_path))

total_fields = 0
assets = {}

for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        data = obj.read()
        name = getattr(data, 'm_Name', '') or ''
        if not name.startswith('GameText_'):
            continue
        if 'm_languageKeys' not in [a for a in dir(data)]:
            # Try type tree
            tree = obj.read_typetree()
            if 'm_languageKeys' not in tree:
                continue
        else:
            tree = obj.read_typetree()

        fv = tree.get('m_fieldValues', [])
        n = len(fv)
        total_fields += n

        # Save full JSON
        out_path = OUT / f"tt_{name}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)

        # Show summary
        langs = tree.get('m_languageKeys', [])
        print(f"{name}: {n} fields, langs={langs}")

        # Show first 3 field names
        for field in fv[:3]:
            fn = field.get('m_fieldName', '?')
            en = field['m_values'][0] if field.get('m_values') else '?'
            print(f"  {fn}: {en[:60]}")

        assets[name] = n
    except Exception as e:
        pass

print(f"\nTotal: {sum(assets.values())} fields across {len(assets)} assets")
print("Assets:", json.dumps(assets, indent=2))
