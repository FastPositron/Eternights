"""
Extract ALL dialogue strings from DB_Dialogue_Eternight in gamemanager bundle.
Target: ~9234 real strings (excluding empty, dots, animations).
"""
import UnityPy
import struct
import re
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BUNDLE = Path("C:/Users/sacke/eternights_rus/backup_clean/gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle")
OUTPUT = Path("C:/Users/sacke/eternights_rus/output/bundle_dialogues_en.json")
DB_PID = -5833716775174085199

def read_unity_str(data, pos):
    if pos + 4 > len(data):
        return None, pos
    length = struct.unpack_from('<I', data, pos)[0]
    if length > 200000 or length == 0:
        return None, pos
    end = pos + 4 + length
    if end > len(data):
        return None, pos
    try:
        s = data[pos+4:end].decode('utf-8')
        padded = pos + 4 + ((length + 3) & ~3)
        return s, padded
    except:
        return None, pos

DT_PATTERN = b'\x0d\x00\x00\x00Dialogue Text'

# Values to skip - not real dialogue
SKIP_VALUES = {
    '', '.', '..', '...', '....',
    'delay + animation only', 'Dim In Only', 'Dim Out Only', ' Dim Out Only',
    'SET NAME HERE', '[var=PLAYER_NAME].', '[var=PLAYER_NAME]',
}

def is_real_dialogue(s):
    """Check if string is a real dialogue line worth translating."""
    if not s or s in SKIP_VALUES:
        return False
    s_stripped = s.strip()
    if not s_stripped:
        return False
    # Skip pure punctuation/dots
    if all(c in '.!? ' for c in s_stripped):
        return False
    # Skip pure animation/delay markers
    if s_stripped.startswith('delay') and 'animation' in s_stripped:
        return False
    return True

print(f"Loading bundle: {BUNDLE}")
env = UnityPy.load(str(BUNDLE))

for obj in env.objects:
    if obj.path_id == DB_PID:
        raw = obj.get_raw_data()
        print(f"DB_Dialogue_Eternight: {len(raw):,} bytes")

        data = bytes(raw)
        all_strings = []

        for m in re.finditer(DT_PATTERN, data):
            dt_end = m.end()
            pad_after_dt = (4 - 13 % 4) % 4  # 3
            value_pos = dt_end + pad_after_dt

            en_value, next_pos = read_unity_str(data, value_pos)
            if en_value is not None and is_real_dialogue(en_value):
                all_strings.append(en_value)

        print(f"Total real dialogue strings: {len(all_strings)}")

        # Save
        with open(OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(all_strings, f, ensure_ascii=False, indent=2)
        print(f"Saved to {OUTPUT}")

        # Stats
        print(f"\nFirst 5:")
        for s in all_strings[:5]:
            print(f"  {s[:100]}")
        print(f"\nLast 5:")
        for s in all_strings[-5:]:
            print(f"  {s[:100]}")
        break
