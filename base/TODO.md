# Eternights Русификатор — Что осталось сделать

## Контекст
Переводы готовы (6325 диалогов + 781 UI строка). Нужно ИНЖЕКТИРОВАТЬ их в файлы игры.

Игра имеет 10 языков (EN, JA, KR, ES, FR, IT, PT, ZH_CHS, ZH_CHT, DE). Русский = 11-й.

## Файлы проекта
- Рабочая папка: `C:\Users\sacke\eternights_rus\`
- База знаний: `C:\Users\sacke\eternights_rus\base\` (architecture.md, translation.md, patching.md, issues.md)
- Переводы диалогов: `output\dialogues_ru.json` (6325 строк, 100%)
- Переводы UI: `output\GameText_Ru.json` (269 строк — СТАРЫЙ формат, нужно пересобрать под TextTable)
- Извлечённые TextTable: `output\tt_GameText_Menu.json`, `tt_GameText_Skills.json` и т.д. (9 файлов)
- Python: `C:\Users\sacke\AppData\Local\Programs\Python\Python311\python.exe`
- UnityPy 1.25.0 установлен

## Задача 1: UI текст (TextTable система)

### Что это
9 ассетов `GameText_*` в бандле `gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle`:
- GameText_Menu (182 поля)
- GameText_Skills (289 полей)  
- GameText_Tutorial (78 полей)
- GameText_Achievement (52 поля)
- GameText_CharacterName (48 полей)
- GameText_Texts (46 полей)
- GameText_SurvivalItems (37 полей)
- GameText_Location (33 поля)
- GameText_PersonalityTest (16 полей)
**Итого: 781 строк для перевода**

### Формат TextTable
```json
{
  "m_languageKeys": ["Default", "es", "ja", "kr", "zh_CHT", "zh_CHS", "de", "it", "fr", "pt"],
  "m_languageValues": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  "m_fieldValues": [
    {
      "m_fieldName": "yesText",
      "m_keys": [0, 1, 3, 2, 4, 5, 6, 7, 8, 9],
      "m_values": ["Yes", "Sí", "네", "はい", "是", "是", "Ja", "Sì", "Oui", "Sim"]
    }
  ]
}
```

### Что нужно сделать
1. Перевести 781 EN строку на русский (Default/[0] = English)
2. В каждом из 9 ассетов:
   - Добавить `"ru"` в `m_languageKeys`
   - Добавить `10` в `m_languageValues`
   - В каждом элементе `m_fieldValues`: добавить `10` в `m_keys` и русский перевод в `m_values`
   - Обновить `m_nextLanguageID` на 11
3. Записать обратно в бандл через UnityPy (save_typetree + file.save)
4. **ВАЖНО**: при save() бандл раздувается (LZ4→uncompressed). Нужно или `save(packer="lz4")` или другой подход

### Извлечённые файлы для перевода
`output/tt_GameText_Menu.json`, `tt_GameText_Tutorial.json`, `tt_GameText_Texts.json` (остальные 6 не извлечены — скрипт `extract_all_gametext.py` извлекает все)

---

## Задача 2: Диалоги (Pixel Crushers в resources.assets)

### Что это
6325 уникальных диалоговых строк в `Eternights_Data/resources.assets`.
Переводы уже готовы: `output/dialogues_en.json` + `output/dialogues_ru.json` (100%).

### Формат хранения
Каждая диалоговая запись в binary:
```
[4-byte len]["Dialogue Text"][3 pad][4-byte len][EN value][pad]
  [4 bytes: type=0][4-byte len]["CustomFieldType_Text"][pad][4-byte field_id]
[4-byte len]["ja"][1 pad][4-byte len][JP value][pad]
  [4 bytes: type=4][4-byte len]["CustomFieldType_Localization"][pad][4-byte field_id???]
[4-byte len]["de"][2 pad][4-byte len][DE value][pad]
  [4 bytes: type=4][4-byte len]["CustomFieldType_Localization"][pad]
[4-byte len]["it"][2 pad][4-byte len][IT value][pad]
  ...
```

Все 10261 записей "Dialogue Text" в range 67,237,808 - 87,997,328 (абс. offset).

### Что нужно сделать
1. Для каждой записи "Dialogue Text" в resources.assets:
   - Прочитать EN текст
   - Найти RU перевод в `dialogues_ru.json`
   - ВСТАВИТЬ новое поле `"ru"` + RU текст + `CustomFieldType_Localization` ПОСЛЕ последнего языка
2. Это binary INSERT → размер файла растёт → нужно обновить Unity SerializedFile object table
3. Использовать UnityPy: `obj.get_raw_data()` → вставить RU поля → `obj.set_raw_data()` → `env.file.save()`

### Важные детали
- resources.assets = Unity SerializedFile v22, data_offset=223216, 9055 объектов
- Диалоги в 1 большом объекте (около pid 9000+)
- `obj.set_raw_data()` + `env.file.save()` автоматически обновляет object table
- Нормализация апострофов: игра использует U+2019 (`'`), переводы — U+0027 (`'`). Скрипт `make_final.py` нормализует

---

## Задача 3: Дропдаун языков

Нужно добавить "Русский" (или "Russian") в дропдаун выбора языка в настройках. Скорее всего это:
- Список в каком-то UI ассете или скрипте
- Или автоматически строится из `m_languageKeys` (тогда добавление "ru" в TextTable автоматом добавит)
- Требует исследования — где хранится список языков для UI dropdown

---

## Задача 4: Шрифт (кириллица)

Текущий шрифт: NotoSansKR SDF LOCALIZED (Bold/Regular/Thin) — содержит латиницу + CJK.
Кириллицы НЕТ → русский текст будет кракозябрами.

Нужно:
- Добавить Cyrillic glyphs (U+0400-U+04FF) в TMPro SDF атлас
- Варианты: Unity Font Asset Creator, UABEA, ручной патч atlas texture
- Шрифт NotoSans УЖЕ поддерживает кириллицу в .ttf/.otf — нужно только сгенерировать SDF atlas

Каталог шрифтов (из catalog.json):
```
Font/NotoSans/Localized/JA/NotoSansJP-*.ttf
Font/NotoSans/Localized/KR/NotoSansKR-*.otf
Font/NotoSans/Localized/SC/NotoSansSC-*.otf
Font/NotoSans/Localized/TC/NotoSansTC-*.otf
```

---

## Порядок выполнения
1. **Задача 2** (диалоги) — самая сложная, binary insert
2. **Задача 1** (UI TextTable) — проще, через UnityPy type tree
3. **Задача 3** (дропдаун) — зависит от исследования
4. **Задача 4** (шрифт) — нужна для отображения кириллицы

## Бэкапы
Всегда бэкапить в `C:\Users\sacke\eternights_rus\backup\` перед патчем!
Оригиналы уже восстановлены (после неудачного первого патча).
