"""
Build complete translation dictionary for ALL bundle dialogue entries.
Combines existing translations + new translations for the 615 missing.
Outputs: output/existing_translations.json (dict {en: ru})
"""
import UnityPy
import struct
import re
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BUNDLE = Path("C:/Users/sacke/eternights_rus/backup_clean/gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle")
DB_PID = -5833716775174085199

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
        s = data[pos+4:end].decode('utf-8')
        padded = pos + 4 + ((length + 3) & ~3)
        return s, padded
    except:
        return None, pos

DT_PATTERN = b'\x0d\x00\x00\x00Dialogue Text'
DE_PATTERN = b'\x02\x00\x00\x00de\x00\x00'

# Load existing translations
with open('output/dialogues_en.json', encoding='utf-8') as f:
    old_en = json.load(f)
with open('output/dialogues_ru.json', encoding='utf-8') as f:
    old_ru = json.load(f)

def normalize(s):
    return (s.replace('\u2019', "'").replace('\u2018', "'")
             .replace('\u201c', '"').replace('\u201d', '"'))

existing_ru = {}
for en, ru in zip(old_en, old_ru):
    if en != ru:
        existing_ru[en] = ru
        existing_ru[normalize(en)] = ru

# NEW translations for the 615 missing strings
new_translations = {
    # Player choices
    "[Rest]": "[Отдохнуть]",
    "[Walk around]": "[Осмотреться]",
    "[Train with Sia]": "[Тренироваться с Сией]",
    "[Train with Yohan]": "[Тренироваться с Ёханом]",
    "[Spend Time]": "[Провести время]",
    "[Scavenge]": "[Искать припасы]",
    "[Pull out tentacle]": "[Вытащить щупальце]",
    "[Make confused face] ": "[Скорчить растерянное лицо]",
    "[Heavy breathing]": "[Тяжёлое дыхание]",
    "[Vomit sounds]": "[Звуки рвоты]",
    "*Takes a deep breath*": "*Глубоко вздыхает*",
    "*Cackles*": "*Злобно хохочет*",
    "[ Fart ]": "[Пук]",

    # Exclamations
    "DRONE LADY!": "ДРОН-ЛЕДИ!",
    "AAAAHHHHHHHHHH!": "АААААААААААА!",
    "BREAKS OVER!": "ПЕРЕРЫВ ОКОНЧЕН!",
    "GOOD.": "ХОРОШО.",
    "Ugh...": "Угх...",
    "100%!": "100%!",

    # Phrases
    "Molecule Warriors!": "Молекулярные Воины!",
    "Molecule Warriors?": "Молекулярные Воины?",
    "Molecule Warrior\u2026": "Молекулярный Воин...",
    "Molecule Warriors 2!": "Молекулярные Воины 2!",
    "<i>Tentacles Weekly</i>.": "<i>Еженедельник Щупалец</i>.",

    # Elongated speech
    "I\u2026mmmm Euuuuuuuuuunnnji.": "Я... Ынджиииииии.",
    "I\u2026mmmm Euuuuuuuuuunnnji": "Я... Ынджиииииии",
    "Beeeeeelliiiiievvveeee": "Вееееериииииии",

    # Variable-only (keep as-is)
    "[var=PLAYER_NAME].": "[var=PLAYER_NAME].",
    "[var=TEAM_NAME].": "[var=TEAM_NAME].",

    # Garbled/special text (keep as-is)
    "[em2]no\u0229\u023a\u0230\u023a\u023c no\u0229\u023a\u023a[/em2]": "[em2]no\u0229\u023a\u0230\u023a\u023c no\u0229\u023a\u023a[/em2]",
    "[em2]\u0230\u023a\u023c no\u0229\u023a\u023a[/em2]": "[em2]\u0230\u023a\u023c no\u0229\u023a\u023a[/em2]",
    "C\u00be\u00f0\u00be\u00ee: \u2026": "C\u00be\u00f0\u00be\u00ee: ...",
    "C\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00ee": "C\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00eeC\u00be\u00f0\u00be\u00ee",

    # Context from DE translation
    "[var=PLAYER_NAME], now it's your \u2026": "[var=PLAYER_NAME], теперь твоя...",
    "630": "630 часов.",

    # ??? strings (translated from DE context)
    "???....??....": "Надо... защитить...",
    "??...?..?..?.....???": "Здесь... так опасно... снаружи...",
    "???! ???! ???! ???! ???! ???!": "ЗАЩИТИТЬ! ЗАЩИТИТЬ! ЗАЩИТИТЬ! ЗАЩИТИТЬ! ЗАЩИТИТЬ!",

    # Technical/debug (keep as-is)
    "BTA9.": "BTA9.",
    "eeee": "eeee",
    "next": "next",
    "secret ending yuna": "secret ending yuna",
    "secret ending min": "secret ending min",
    "secret ending sia": "secret ending sia",
    "secret ending yohan": "secret ending yohan",
    "post- Ending": "post- Ending",
    "reset dialogue panel": "Блин... ниже всякого достоинства...",
    "[var=PLAYER_NAME] has a transforming arm.": "У [var=PLAYER_NAME] трансформирующаяся рука.",
}

# Merge all
for en, ru in new_translations.items():
    existing_ru[en] = ru
    existing_ru[normalize(en)] = ru

# Handle dots/ellipsis: any EN that is pure dots/punctuation → normalize to "..."
# We'll handle this in the patch script instead

# Save complete dictionary
print(f"Total translation pairs: {len(existing_ru)}")
with open('output/existing_translations.json', 'w', encoding='utf-8') as f:
    json.dump(existing_ru, f, ensure_ascii=False, indent=2)
print("Saved to output/existing_translations.json")

# Verify coverage against bundle
env = UnityPy.load(str(BUNDLE))
for obj in env.objects:
    if obj.path_id == DB_PID:
        raw = bytes(obj.get_raw_data())
        dt_matches = list(re.finditer(DT_PATTERN, raw))

        covered = 0
        uncovered_real = []
        total_with_de = 0

        for i, m in enumerate(dt_matches):
            dt_end = m.end()
            pad = (4 - 13 % 4) % 4
            value_pos = dt_end + pad
            en_value, _ = read_unity_str(raw, value_pos)
            if not en_value:
                continue

            next_dt = dt_matches[i+1].start() if i+1 < len(dt_matches) else len(raw)
            region = raw[m.start():next_dt]
            de_pos = region.find(DE_PATTERN)
            if de_pos == -1:
                continue
            abs_de_val = m.start() + de_pos + 8
            de_value, _ = read_unity_str(raw, abs_de_val)
            if not de_value or not de_value.strip():
                continue

            total_with_de += 1
            ru = existing_ru.get(en_value) or existing_ru.get(normalize(en_value))

            # For dots/ellipsis, we'll handle in patch
            stripped = en_value.strip()
            is_dots = all(c in '.…?! \n\t' for c in stripped) if stripped else True

            if ru:
                covered += 1
            elif is_dots:
                covered += 1  # will be handled as "..."
            else:
                uncovered_real.append((en_value, de_value))

        print(f"\nBundle coverage:")
        print(f"Total with DE: {total_with_de}")
        print(f"Covered (has RU or dots): {covered}")
        print(f"Still uncovered: {len(uncovered_real)}")
        if uncovered_real:
            print("\nUncovered:")
            for en, de in uncovered_real:
                print(f"  EN: {en[:80]}")
                print(f"  DE: {de[:80]}")
                print()
        break
