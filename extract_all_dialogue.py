"""
Полное извлечение диалогов из resources.assets
Структура Pixel Crushers: "Dialogue Text" → значение → "CustomFieldType_Text" → ...
"""

import struct
import re
import json
import csv
from pathlib import Path

OUTPUT_DIR = Path("C:/Users/sacke/eternights_rus/output")

with open("C:/Program Files (x86)/Steam/steamapps/common/Eternights/Eternights_Data/resources.assets", 'rb') as f:
    data = f.read()

def read_unity_string_at(data, pos):
    """Читаем Unity-строку по позиции: [4-byte len][string][padding to 4]"""
    if pos + 4 > len(data):
        return None, pos
    length = struct.unpack_from('<I', data, pos)[0]
    if length > 10000 or length == 0:
        return None, pos
    end = pos + 4 + length
    if end > len(data):
        return None, pos
    try:
        s = data[pos+4:end].decode('utf-8')
        # Выравнивание до 4 байт
        padded_end = pos + 4 + ((length + 3) & ~3)
        return s, padded_end
    except:
        return None, pos

def extract_strings_sequence(data, start_pos, count=5):
    """Читаем последовательность Unity строк начиная с позиции"""
    pos = start_pos
    result = []
    for _ in range(count):
        s, new_pos = read_unity_string_at(data, pos)
        if s is None:
            break
        result.append(s)
        pos = new_pos
    return result

# Ищем "Dialogue Text" и извлекаем следующую строку
print("Извлекаем диалоги...")
dialogues = []
skip_set = {'', 'CustomFieldType_Text', 'CustomFieldType_Files', 'CustomFieldType_Number',
            'CustomFieldType_Boolean', 'Parenthetical', 'Audio Files', 'Sequence',
            'Response Menu Sequence', '[]', 'Dialogue Text', 'Actor', 'Conversant',
            'Title', 'Description', 'IsRoot', 'IsGroup', 'NodeColor', 'conditionsString',
            'userScript', 'onExecute', 'falseConditionAction', 'nodeColor'}

# Паттерн поиска: строка "Dialogue Text" в Unity-формате
DT_BYTES = b'\x0d\x00\x00\x00Dialogue Text'  # длина 13 = \x0d
for m in re.finditer(b'\x0d\x00\x00\x00Dialogue Text', data):
    pos = m.end()
    # Выравнивание
    pad = (4 - (13 % 4)) % 4  # 13 % 4 = 1, pad = 3
    pos += pad

    # Читаем следующую строку — это должно быть значение диалога
    value, next_pos = read_unity_string_at(data, pos)
    if value and value not in skip_set and len(value) > 0:
        # Проверяем что следующая строка — CustomFieldType_Text
        next_str, _ = read_unity_string_at(data, next_pos)
        dialogues.append({
            'text': value,
            'has_type': next_str == 'CustomFieldType_Text'
        })

print(f"Найдено диалоговых записей: {len(dialogues)}")
confirmed = [d for d in dialogues if d['has_type']]
print(f"Подтверждённых (с CustomFieldType_Text): {len(confirmed)}")

print("\nПримеры:")
for d in confirmed[:20]:
    print(f"  {d['text'][:100]}")

# Ищем также actor-conversation-dialogue структуру
# Сначала найдём все названия разговоров
print("\n\n=== Поиск разговоров ===")
conversations = []
for m in re.finditer(rb'\x05\x00\x00\x00Title', data):
    pos = m.end()
    # пропускаем padding (Title = 5 bytes, pad = 3)
    pos += 3
    title_val, next_pos = read_unity_string_at(data, pos)
    if title_val and '/' in title_val and len(title_val) < 100:
        conversations.append(title_val)

print(f"Названий разговоров с '/': {len(conversations)}")
for c in conversations[:20]:
    print(f"  {c}")

# Сохраняем результаты
all_texts = [d['text'] for d in confirmed]

# CSV для перевода
csv_path = OUTPUT_DIR / "dialogue_to_translate.csv"
with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['id', 'en', 'ru'])
    writer.writeheader()
    for i, text in enumerate(all_texts):
        writer.writerow({'id': i, 'en': text, 'ru': ''})

print(f"\nСохранено {len(all_texts)} строк в {csv_path}")

# Также JSON
json_path = OUTPUT_DIR / "dialogues_en.json"
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(all_texts, f, ensure_ascii=False, indent=2)
print(f"JSON: {json_path}")
