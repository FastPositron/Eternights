"""
Patch dialogues in gamemanager bundle.
Replace German text in "de" fields with Russian.
Uses complete translation dict + handles dots/ellipsis.
Bundle already patched (TextTable+Dropdown), works on top.
"""
import UnityPy
import struct
import re
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BUNDLE = Path("C:/Program Files (x86)/Steam/steamapps/common/Eternights/Eternights_Data/StreamingAssets/aa/StandaloneWindows64/gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle")
TRANSLATIONS_PATH = Path("C:/Users/sacke/eternights_rus/output/existing_translations.json")

DB_PID = -5833716775174085199

with open(TRANSLATIONS_PATH, encoding='utf-8') as f:
    translation = json.load(f)

def normalize(s):
    return (s.replace('\u2019', "'").replace('\u2018', "'")
             .replace('\u201c', '"').replace('\u201d', '"'))

print(f"Translation dict: {len(translation)} pairs")

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
               'SET NAME HERE'}

def get_translation(en_value):
    """Get RU translation, or handle dots/ellipsis."""
    ru = translation.get(en_value) or translation.get(normalize(en_value))
    if ru:
        return ru
    # Handle dots/ellipsis: replace U+2026 with ... and normalize
    stripped = en_value.strip()
    if stripped and all(c in '.\u2026 \n\t' for c in stripped):
        return en_value.replace('\u2026', '...')
    return None

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
        ru = get_translation(en_value)
        if not ru:
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
        new_value_bytes = pack_unity_str(ru)
        replacements.append((abs_value_start, after_value, new_value_bytes))
    if not replacements:
        return None, 0
    replacements.sort(key=lambda x: -x[0])
    result = bytearray(data)
    for old_start, old_end, new_bytes in replacements:
        result[old_start:old_end] = new_bytes
    return bytes(result), len(replacements)

print(f"Loading bundle...")
env = UnityPy.load(str(BUNDLE))

for obj in env.objects:
    if obj.path_id == DB_PID:
        raw = obj.get_raw_data()
        print(f"DB_Dialogue_Eternight: raw={len(raw):,}")

        new_raw, n = patch_de_fields(raw)
        if new_raw and n > 0:
            obj.set_raw_data(new_raw)
            print(f"Replaced: {n} de->ru fields")
            print(f"Size: {len(raw):,} -> {len(new_raw):,}")
        else:
            print("Nothing replaced!")
        break

print("Saving bundle...")
try:
    saved = env.file.save(packer="lz4")
except:
    saved = env.file.save()
with open(BUNDLE, 'wb') as f:
    f.write(saved)
print(f"Done! {len(saved):,} bytes")

# Update catalog CRC
import base64
CATALOG = Path("C:/Program Files (x86)/Steam/steamapps/common/Eternights/Eternights_Data/StreamingAssets/aa/catalog.json")
CATALOG_BACKUP = Path("C:/Users/sacke/eternights_rus/backup_clean/catalog.json")

# Restore clean catalog first, then patch
import shutil
shutil.copy2(CATALOG_BACKUP, CATALOG)

with open(CATALOG, encoding='utf-8') as f:
    cat = json.load(f)

raw_extra = bytearray(base64.b64decode(cat['m_ExtraDataString']))
target_utf16 = '2a1ab4181e2e1d6bed81737aeb159efc'.encode('utf-16-le')
hash_idx = raw_extra.find(target_utf16)

# Find the JSON block around this hash
json_start = raw_extra.rfind(b'{\x00', 0, hash_idx)
json_end = raw_extra.find(b'}\x00', hash_idx)
old_json_bytes = raw_extra[json_start:json_end+2]
old_json_str = old_json_bytes.decode('utf-16-le')
entry = json.loads(old_json_str)

print(f"Old CRC: {entry['m_Crc']}")
print(f"Old size: {entry['m_BundleSize']}")

entry['m_Crc'] = 0
entry['m_BundleSize'] = len(saved)

new_json_str = json.dumps(entry, separators=(',', ':'))
new_json_bytes = new_json_str.encode('utf-16-le')
old_len = len(old_json_bytes)
new_len = len(new_json_bytes)

if new_len < old_len:
    diff = old_len - new_len
    spaces_needed = diff // 2
    # Add spaces after colons and commas to pad
    new_json_str_padded = new_json_str[:-1] + ' ' * spaces_needed + '}'
    new_json_bytes = new_json_str_padded.encode('utf-16-le')
    print(f"Added {spaces_needed} padding spaces")
elif new_len > old_len:
    print(f"WARNING: new JSON longer by {new_len - old_len} bytes!")
    entry.pop('m_ClearOtherCachedVersionsWhenLoaded', None)
    new_json_str = json.dumps(entry, separators=(',', ':'))
    new_json_bytes = new_json_str.encode('utf-16-le')
    new_len = len(new_json_bytes)
    if new_len < old_len:
        diff = old_len - new_len
        spaces_needed = diff // 2
        new_json_str_padded = new_json_str[:-1] + ' ' * spaces_needed + '}'
        new_json_bytes = new_json_str_padded.encode('utf-16-le')

assert len(new_json_bytes) == old_len, f"Length mismatch: {len(new_json_bytes)} != {old_len}"
raw_extra[json_start:json_start+old_len] = new_json_bytes

cat['m_ExtraDataString'] = base64.b64encode(bytes(raw_extra)).decode('ascii')
with open(CATALOG, 'w', encoding='utf-8') as f:
    json.dump(cat, f, separators=(',', ':'))
print(f"catalog.json updated! CRC=0, size={len(saved)}")
