"""
Финальный патч: подмена немецкого (de) на русский.
Правильные пути. Корректный пересчёт CRC в catalog.json.
"""
import UnityPy
import struct
import re
import json
import shutil
import zlib
import base64
import sys
import os
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path("C:/Program Files (x86)/Steam/steamapps/common/Eternights/Eternights_Data")
RESOURCES = BASE / "resources.assets"
BUNDLE = BASE / "StreamingAssets/aa/StandaloneWindows64/gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle"
CATALOG = BASE / "StreamingAssets/aa/catalog.json"

BACKUP = Path("C:/Users/sacke/eternights_rus/backup_clean")
DATA = Path("C:/Users/sacke/eternights_rus/output")

EN_PATH = DATA / "dialogues_en.json"
RU_PATH = DATA / "dialogues_ru.json"
TRANSLATIONS_PATH = DATA / "existing_translations.json"
UI_RU_PATH = DATA / "ui_strings_ru.json"

DROPDOWN_PID = 1226886224836449939

# =====================================================
# RESTORE FROM CLEAN BACKUPS
# =====================================================
print("Восстанавливаем чистые файлы...")
shutil.copy2(BACKUP / "resources.assets", RESOURCES)
shutil.copy2(BACKUP / BUNDLE.name, BUNDLE)
shutil.copy2(BACKUP / "catalog.json", CATALOG)
print("  OK")

# =====================================================
# LOAD TRANSLATIONS
# =====================================================
with open(EN_PATH, encoding='utf-8') as f:
    en_strings = json.load(f)
with open(RU_PATH, encoding='utf-8') as f:
    ru_strings = json.load(f)
with open(TRANSLATIONS_PATH, encoding='utf-8') as f:
    translation = json.load(f)
with open(UI_RU_PATH, encoding='utf-8') as f:
    ui_ru_all = json.load(f)

def normalize(s):
    return (s.replace('\u2019', "'").replace('\u2018', "'")
             .replace('\u201c', '"').replace('\u201d', '"'))

# Also add pairs from old files
for en, ru in zip(en_strings, ru_strings):
    if en != ru:
        translation.setdefault(en, ru)
        translation.setdefault(normalize(en), ru)

ui_index = {}
for key, val in ui_ru_all.items():
    file_part, field = key.split('::', 1)
    ui_index.setdefault(file_part, {})[field] = val

print(f"Диалоги: {len(translation)} пар")
print(f"UI: {sum(len(v) for v in ui_index.values())} строк")

# =====================================================
# PART 1: PATCH resources.assets
# =====================================================
print("\n" + "="*50)
print("ЧАСТЬ 1: Диалоги (resources.assets)")
print("="*50)

def pack_unity_str(s):
    b = s.encode('utf-8')
    pad = (4 - len(b) % 4) % 4
    return struct.pack('<I', len(b)) + b + b'\x00' * pad

def read_unity_str(data, pos):
    if pos + 4 > len(data):
        return None, pos
    length = struct.unpack_from('<I', data, pos)[0]
    if length > 200000:
        return None, pos
    end = pos + 4 + length
    if end > len(data):
        return None, pos
    try:
        s = bytes(data[pos+4:end]).decode('utf-8')
        padded = pos + 4 + ((length + 3) & ~3)
        return s, padded
    except:
        return None, pos

DT_PATTERN = b'\x0d\x00\x00\x00Dialogue Text'
DE_PATTERN = b'\x02\x00\x00\x00de\x00\x00'
SKIP_VALUES = {'', 'delay + animation only', 'Dim In Only', ' Dim Out Only', 'Dim Out Only',
               'SET NAME HERE', '[var=PLAYER_NAME].', '[var=PLAYER_NAME]'}

def patch_de_fields(raw_bytes):
    data = bytes(raw_bytes)
    if DT_PATTERN not in data:
        return None, 0
    replacements = []
    for m in re.finditer(DT_PATTERN, data):
        dt_end = m.end()
        pad_after_dt = (4 - 13 % 4) % 4
        value_pos = dt_end + pad_after_dt
        en_value, _ = read_unity_str(data, value_pos)
        if en_value is None or en_value in SKIP_VALUES:
            continue
        ru = translation.get(en_value) or translation.get(normalize(en_value))
        if not ru:
            # Handle dots/ellipsis
            stripped = en_value.strip()
            if stripped and all(c in '.\u2026 \n\t' for c in stripped):
                ru = en_value.replace('\u2026', '...')
            else:
                continue
        next_dt = data.find(DT_PATTERN, m.end())
        if next_dt == -1:
            next_dt = len(data)
        region = data[m.start():next_dt]
        de_pos = region.find(DE_PATTERN)
        if de_pos == -1:
            continue
        abs_value_start = m.start() + de_pos + 8
        de_value, after_value = read_unity_str(data, abs_value_start)
        if de_value is None:
            continue
        old_value_bytes = data[abs_value_start:after_value]
        new_value_bytes = pack_unity_str(ru)
        replacements.append((abs_value_start, after_value, new_value_bytes))
    if not replacements:
        return None, 0
    replacements.sort(key=lambda x: -x[0])
    result = bytearray(data)
    for old_start, old_end, new_bytes in replacements:
        result[old_start:old_end] = new_bytes
    return bytes(result), len(replacements)

env_res = UnityPy.load(str(RESOURCES))
sf = env_res.file
total_objs = len(sf.objects)
patched_count = 0
total_replacements = 0

for i, (path_id, obj) in enumerate(sf.objects.items()):
    if i % 2000 == 0:
        print(f"  {i}/{total_objs} (patched: {patched_count}, replaced: {total_replacements})...")
    try:
        raw = obj.get_raw_data()
        if not raw or DT_PATTERN not in raw:
            continue
        new_raw, n = patch_de_fields(raw)
        if new_raw and n > 0:
            obj.set_raw_data(new_raw)
            patched_count += 1
            total_replacements += n
    except:
        pass

print(f"Заменено: {total_replacements} полей de→ru в {patched_count} объектах")

new_data = env_res.file.save()
with open(RESOURCES, 'wb') as f:
    f.write(new_data)
print(f"Сохранено: {len(new_data):,} байт")

# =====================================================
# PART 2: PATCH gamemanager bundle
# =====================================================
print("\n" + "="*50)
print("ЧАСТЬ 2: TextTable + Dropdown (bundle)")
print("="*50)

env = UnityPy.load(str(BUNDLE))

# TextTable
tt_patched = 0
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        d = obj.read()
        name = getattr(d, 'm_Name', '') or ''
        if not name.startswith('GameText_') or name not in ui_index:
            continue
        ru_fields = ui_index[name]
        tree = obj.read_typetree()
        lang_keys = tree.get('m_languageKeys', [])
        if 'de' not in lang_keys:
            continue
        de_key_idx = lang_keys.index('de')
        de_lang_val = tree['m_languageValues'][de_key_idx]
        fields_patched = 0
        for field in tree.get('m_fieldValues', []):
            fname = field.get('m_fieldName', '')
            if fname in ru_fields and de_lang_val in field['m_keys']:
                idx = field['m_keys'].index(de_lang_val)
                field['m_values'][idx] = ru_fields[fname]
                fields_patched += 1
        if fields_patched > 0:
            obj.save_typetree(tree)
            tt_patched += 1
            print(f"  {name}: {fields_patched} полей")
    except Exception as e:
        print(f"  ERROR: {e}")

print(f"TextTable: {tt_patched} ассетов")

# Dropdown
for obj in env.objects:
    if obj.path_id == DROPDOWN_PID:
        tree = obj.read_typetree()
        for opt in tree['m_Options']['m_Options']:
            if opt['m_Text'] == 'German':
                opt['m_Text'] = 'Russian'
        obj.save_typetree(tree)
        print(f"Dropdown: German → Russian")
        print(f"  {[o['m_Text'] for o in tree['m_Options']['m_Options']]}")
        break

# Save bundle
print("Сохраняем бандл...")
try:
    saved = env.file.save(packer="lz4")
except:
    saved = env.file.save()
with open(BUNDLE, 'wb') as f:
    f.write(saved)
new_bundle_size = len(saved)
print(f"Сохранено: {new_bundle_size:,} байт")

# =====================================================
# PART 3: FIX catalog.json CRC
# =====================================================
print("\n" + "="*50)
print("ЧАСТЬ 3: catalog.json CRC")
print("="*50)

with open(CATALOG, encoding='utf-8') as f:
    cat = json.load(f)

raw = bytearray(base64.b64decode(cat['m_ExtraDataString']))

# Find gamemanager entry
target_hash = '2a1ab4181e2e1d6bed81737aeb159efc'
target_utf16 = target_hash.encode('utf-16-le')
hash_idx = raw.find(target_utf16)
print(f"Hash найден на позиции: {hash_idx}")

# Find the JSON block
json_start = raw.rfind(b'{\x00', 0, hash_idx)
json_end = raw.find(b'}\x00', hash_idx)
old_json_bytes = raw[json_start:json_end+2]
old_json_str = old_json_bytes.decode('utf-16-le')
entry = json.loads(old_json_str)

print(f"Старый CRC: {entry['m_Crc']}")
print(f"Старый размер: {entry['m_BundleSize']}")

# Disable CRC check by setting to 0 and update size
entry['m_Crc'] = 0
entry['m_BundleSize'] = new_bundle_size

# Build new JSON with EXACT same byte length
new_json_str = json.dumps(entry, separators=(',', ':'))

# Encode to UTF-16LE
new_json_bytes = new_json_str.encode('utf-16-le')
old_len = len(old_json_bytes)
new_len = len(new_json_bytes)

if new_len < old_len:
    # Need to pad - add spaces before closing brace
    # In UTF-16LE, space = \x20\x00
    diff = old_len - new_len
    spaces_needed = diff // 2
    # Insert spaces before the last }
    # Remove closing }, add spaces, add } back
    new_json_str_padded = new_json_str[:-1] + ' ' * spaces_needed + '}'
    new_json_bytes = new_json_str_padded.encode('utf-16-le')
    print(f"Добавлено {spaces_needed} пробелов для выравнивания")
elif new_len > old_len:
    print(f"ОШИБКА: новый JSON длиннее на {new_len - old_len} байт!")
    # Try to shorten by removing m_ClearOtherCachedVersionsWhenLoaded
    entry.pop('m_ClearOtherCachedVersionsWhenLoaded', None)
    new_json_str = json.dumps(entry, separators=(',', ':'))
    new_json_bytes = new_json_str.encode('utf-16-le')
    new_len = len(new_json_bytes)
    if new_len < old_len:
        diff = old_len - new_len
        spaces_needed = diff // 2
        new_json_str_padded = new_json_str[:-1] + ' ' * spaces_needed + '}'
        new_json_bytes = new_json_str_padded.encode('utf-16-le')
        print(f"Укоротил JSON, добавлено {spaces_needed} пробелов")

print(f"Байты JSON: old={old_len}, new={len(new_json_bytes)}")
assert len(new_json_bytes) == old_len, f"Length mismatch: {len(new_json_bytes)} != {old_len}"

# Replace in raw
raw[json_start:json_start+old_len] = new_json_bytes

# Verify
verify_str = raw[json_start:json_start+old_len].decode('utf-16-le')
print(f"Проверка: {verify_str.strip()}")

# Save
cat['m_ExtraDataString'] = base64.b64encode(bytes(raw)).decode('ascii')
with open(CATALOG, 'w', encoding='utf-8') as f:
    json.dump(cat, f, separators=(',', ':'))
print("catalog.json сохранён!")

print("\n" + "="*50)
print("ГОТОВО! Выбери 'Russian' в настройках игры.")
print("="*50)
