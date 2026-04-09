# Система перевода диалогов

## Файлы переводов
- `output/dialogues_en.json` — 6325 уникальных EN строк (список)
- `output/dialogues_ru.json` — 6325 RU строк (список, same order)
- `output/translations_progress.json` — словарь {en: ru} для отслеживания

## Чанки
- `chunks/chunk_001.json` .. `chunk_064.json` — по 100 строк каждый
- `write_chunk001-009.py` — ручные переводы первых 9 чанков
- `output/progress_010.json` .. `progress_064.json` — агентские переводы

## Сборка финала
```bash
python make_final.py
# → output/dialogues_ru.json (100%, 6325/6325)
```

## Мёрж прогресса
```bash
python merge_all.py
# Добавляет все progress_0NN.json в translations_progress.json
```

## ВАЖНАЯ ПРОБЛЕМА: апострофы
- Игра (`dialogues_en.json`) использует УМНЫЕ апострофы: `'` (U+2019)
- Ручные переводы (write_chunk*.py) используют ПРЯМЫЕ: `'` (U+0027)
- РЕШЕНИЕ: `make_final.py` нормализует оба к прямым перед сравнением
- НЕ менять логику нормализации!

## Характеры персонажей (для новых переводов)
- Чани: "чувак" (ВСЕГДА для dude), разговорный, энергичный
- Юна: тёплая, грамотная, без пафоса
- Ария/Люкс: формальная, театральная, старомодная
- Лина: резкая, саркастичная
- Умбра: холодная, повелительная

## Термины
| EN | RU |
|----|----|
| The Stone | Камень |
| Architects | Архитекторы |
| Lux | Люкс |
| Umbra | Умбра |
| wall | стена |
| infected | заражённые |

## Как добавить пропущенные строки
Если `make_final.py` показывает < 100%, создать:
```python
# add_missing.py
import json
from pathlib import Path
prog_path = Path('output/translations_progress.json')
with open(prog_path, encoding='utf-8') as f:
    t = json.load(f)
t["EN string"] = "RU перевод"
with open(prog_path, 'w', encoding='utf-8') as f:
    json.dump(t, f, ensure_ascii=False, indent=2)
```
Потом запустить `make_final.py`.
