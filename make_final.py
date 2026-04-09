"""
Сборка финального dialogues_ru.json из файла прогресса переводов.
Запускать после каждой пачки переводов чтобы посмотреть статус.
"""
import json
from pathlib import Path

INPUT_PATH  = Path("C:/Users/sacke/eternights_rus/output/dialogues_en.json")
PROGRESS_PATH = Path("C:/Users/sacke/eternights_rus/output/translations_progress.json")
OUTPUT_PATH = Path("C:/Users/sacke/eternights_rus/output/dialogues_ru.json")

with open(INPUT_PATH, encoding='utf-8') as f:
    en_strings = json.load(f)

translations = {}
if PROGRESS_PATH.exists():
    with open(PROGRESS_PATH, encoding='utf-8') as f:
        translations = json.load(f)

def normalize(s):
    """Нормализация апострофов/кавычек для сравнения ключей."""
    return (s.replace('\u2019', "'").replace('\u2018', "'")
             .replace('\u201c', '"').replace('\u201d', '"'))

# Строим lookup с нормализованными ключами
norm_translations = {}
for k, v in translations.items():
    norm_translations[normalize(k)] = v

ru_strings = []
untranslated = 0
for s in en_strings:
    norm_s = normalize(s)
    if s in translations:
        ru_strings.append(translations[s])
    elif norm_s in norm_translations:
        ru_strings.append(norm_translations[norm_s])
    else:
        ru_strings.append(s)  # оставляем английский как заглушку
        untranslated += 1

translated = len(en_strings) - untranslated
print(f"Прогресс: {translated}/{len(en_strings)} ({100*translated//len(en_strings)}%)")
print(f"Осталось: {untranslated}")

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(ru_strings, f, ensure_ascii=False, indent=2)
print(f"Записано: {OUTPUT_PATH}")
