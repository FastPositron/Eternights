# Архитектура файлов игры Eternights

## Движок
- Unity 2022.3.62f1
- Addressables (бандлы в StreamingAssets)
- Pixel Crushers Dialogue System (диалоги)
- TextMeshPro (шрифты)

## КРИТИЧНО: Две папки с бандлами!

Игра имеет ДВЕ копии бандлов в разных папках:
- `aa/StandaloneWindows64/` ← **ИГРА ГРУЗИТ ОТСЮДА** (RuntimePath)
- `aa/Windows/StandaloneWindows64/` ← дубли, игра НЕ использует

**ВСЕГДА патчить файлы в `aa/StandaloneWindows64/`!**

## Addressables catalog.json и CRC

**Файл**: `Eternights_Data/StreamingAssets/aa/catalog.json`

Каталог содержит CRC-чексуммы для каждого бандла в поле `m_ExtraDataString`:
- Формат: base64 → бинарные записи → внутри каждой UTF-16LE JSON
- Каждая запись: `{"m_Hash":"...","m_Crc":ЧИСЛО,"m_BundleSize":ЧИСЛО,...}`
- **Если CRC не совпадает — игра НЕ грузит бандл (чёрный экран)**

### Как патчить CRC:
1. base64 decode `m_ExtraDataString`
2. Найти нужный хэш в UTF-16LE: `'2a1ab4...'.encode('utf-16-le')`
3. Заменить CRC на 0 (обнуление = отключить проверку), **побайтово с сохранением длины**
4. Обновить `m_BundleSize` на новый размер файла (тоже побайтово, кол-во цифр должно совпадать)
5. base64 encode обратно
6. **НЕ МЕНЯТЬ общую длину бинарных данных!** Если JSON стал короче — добавить пробелы перед `}`

### Подход "Вариант А" (рабочий):
Вместо добавления нового языка (ограничение в C# коде на 10 языков) — **подменяем немецкий (de, индекс 9) на русский**. Dropdown: "German" → "Russian", содержимое "de" полей заменяем на русский текст.

## Система локализации

### UI текст — TextTable система
Ассеты `GameText_*` в бандле `gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle`:
- Формат: `m_languageKeys` (["Default","es","ja","kr",...]) + `m_languageValues` ([0,1,2,3,...])
- Каждое поле: `m_fieldName` + `m_keys` (lang IDs) + `m_values` (переводы)
- 10 языков: Default(EN)=0, es=1, ja=2, kr=3, zh_CHT=4, zh_CHS=5, **de=6**, it=7, fr=8, pt=9
- **de (value=6) подменяется на русский**

9 ассетов GameText_*:
- GameText_Menu (180 полей)
- GameText_Skills (289 полей)
- GameText_Tutorial (78 полей)
- GameText_Achievement (52 поля)
- GameText_CharacterName (48 полей)
- GameText_Texts (46 полей)
- GameText_SurvivalItems (37 полей)
- GameText_Location (33 поля)
- GameText_PersonalityTest (16 полей)
**Итого: 779 строк**

### Диалоги — Pixel Crushers в ДВУХ местах!

**ВАЖНО:** Диалоги хранятся в ДВУХ файлах:
1. `resources.assets` — pid=8475, один большой MonoBehaviour
2. **`gamemanager bundle`** — объект `DB_Dialogue_Eternight` (pid=-5833716775174085199, ~20MB raw) — **ЭТО ОСНОВНОЙ!**

Каждая диалоговая запись в binary:
```
[4-byte len]["Dialogue Text"][3 pad][4-byte len][EN value][pad]
  [type=0]["CustomFieldType_Text"]
["de"][2 pad][4-byte len][DE value][pad]
  [type=4]["CustomFieldType_Localization"]
["it"][2 pad][4-byte len][IT value][pad]
  ...
```

Патч: находим паттерн `\x02\x00\x00\x00de\x00\x00` в регионе каждого Dialogue Text, заменяем значение после него на русский перевод. Замены применяются от конца к началу (чтобы не сбивать офсеты).

### Dropdown языков
- TMP_Dropdown pid=1226886224836449939 в gamemanager bundle
- m_Options: 10 элементов, индекс 9 = "German" → заменяем на "Russian"
- C# код (UIPlayerLanguagesSettings) маппит индекс 9 → "de", поэтому добавить 11-й язык нельзя без патча DLL

### Шрифты
- TextMeshPro SDF атлас — NotoSansKR
- **Кириллица отображается нормально** (шрифт уже поддерживает!)
- Отдельный патч шрифтов НЕ нужен

## Структура файлов для патча

### Правильные пути (ИГРА ГРУЗИТ ЭТИ ФАЙЛЫ):
```
Eternights_Data/resources.assets
Eternights_Data/StreamingAssets/aa/StandaloneWindows64/gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle
Eternights_Data/StreamingAssets/aa/catalog.json
```

### Бэкапы чистых файлов:
```
C:\Users\sacke\eternights_rus\backup_clean\resources.assets
C:\Users\sacke\eternights_rus\backup_clean\gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle
C:\Users\sacke\eternights_rus\backup_clean\catalog.json
```

## Python окружение
- Python 3.11: `C:\Users\sacke\AppData\Local\Programs\Python\Python311\python.exe`
- UnityPy 1.25.0 установлен
- sys.stdout.reconfigure(encoding='utf-8') — обязательно в каждом скрипте
