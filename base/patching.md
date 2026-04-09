# Как патчить файлы игры

## Порядок действий

1. **Переводы готовы** (✅ сделано):
   - `output/dialogues_ru.json` — 6325/6325 (100%)
   - `output/GameText_Ru.json` — 269 UI строк (нужно проверить)

2. **Патч GameText бандла** (UI строки):
   ```bash
   python patch_gametext.py
   ```
   - Ищет MonoBehaviour m_Name="GameText_En" во ВСЕХ бандлах
   - Заменяет sections.entries.value на русские из GameText_Ru.json
   - Бэкап → `backup/` перед изменением
   - ЕСЛИ не найден: проверить все бандлы на "GameText" в имени

3. **Патч диалогов** (resources.assets):
   ```bash
   python patch_dialogues_v2.py
   ```
   - UnityPy: get_raw_data() → binary replace → set_raw_data()
   - env.file.save() — автоматически обновляет object table
   - Бэкап → `backup/resources.assets` (90MB!) перед запуском
   - Занимает несколько минут (9055 объектов)

4. **Шрифт** (❌ не начато):
   - Найти TMPro SDF атлас для кириллицы
   - Возможно нужен UABEA или Font Asset Creator
   - Цель: добавить Cyrillic glyphs в существующий шрифт игры

## Бэкапы
Все бэкапы в `backup/`:
```
backup/resources.assets          ← оригинальный (90MB)
backup/defaultlocalgroup_*.bundle ← бандл с GameText
```

## Проверка
После патча запустить игру и проверить:
- Меню и UI: должны быть по-русски
- Диалоги: должны быть по-русски
- Если кракозябры: проблема со шрифтом (нет кириллицы в TMPro atlas)

## Откат
Если что-то пошло не так:
```bash
# Копируем из backup обратно в игру
Copy-Item backup/resources.assets "C:/Program Files (x86)/Steam/steamapps/common/Eternights/Eternights_Data/resources.assets"
```

## Технические детали

### Unity SerializedFile v22 (resources.assets)
- data_offset = 223,216 байт
- Диалоги: абс. офсеты 67M-88M
- 9055 объектов всего
- Каждый диалог — отдельный объект ~50-200 байт
- UnityPy 1.25.0 умеет:
  - `obj.get_raw_data()` — читать сырые байты объекта
  - `obj.set_raw_data(bytes)` — записывать новые байты
  - `env.file.save()` — сохранять весь файл с обновлённым object table

### Pixel Crushers Binary Format
Паттерн для поиска:
```python
b'\x0d\x00\x00\x00Dialogue Text'  # 13-байтная строка "Dialogue Text"
# далее 3 байта padding (13 % 4 = 1, pad = 3)
# далее [4-byte LE len][value bytes][padding to 4]
```

### GameText Bundle Format
Структура JSON:
```json
{
  "sections": [
    {
      "name": " GameText_04_EnglishTutorialSection",
      "entries": [
        {"key": 27, "value": " Translation here..."}
      ]
    }
  ]
}
```
