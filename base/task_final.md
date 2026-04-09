# Task Final: Собрать инсталлятор русификатора

## Цель
Один .exe файл (~30-50 МБ), который устанавливает русский перевод в Eternights.
Пользователю не нужен Python или другие зависимости.

## Что должен делать инсталлятор

### Кнопка "Установить"
1. Автоматически найти папку игры через Steam (реестр Windows или стандартные пути)
2. Создать бэкап оригинальных файлов (если ещё нет)
3. Пропатчить 3 файла:
   - `resources.assets` — заменить "de" поля диалогов на русский (необязательно, диалоги дублируются в бандле)
   - `aa/StandaloneWindows64/gamemanager_...bundle` — TextTable (UI) + Dropdown + DB_Dialogue_Eternight
   - `aa/catalog.json` — обнулить CRC и обновить размер бандла
4. Показать результат: сколько строк заменено

### Кнопка "Удалить"
1. Восстановить оригинальные файлы из бэкапа
2. Удалить бэкап

## Технологии
- **PyInstaller** — упаковка в .exe (`pyinstaller --onefile install_rus.py`)
- **UnityPy** — чтение/запись Unity бандлов и assets
- **tkinter** — простой GUI (кнопки, прогресс-бар, лог)
- Перевод данные (JSON) вшиты прямо в .exe

## Файлы для вшивания
- `output/dialogues_en.json` — 6325 EN строк
- `output/dialogues_ru.json` — 6325 RU строк
- `output/ui_strings_ru.json` — 781 UI строк

## Логика патча (из рабочих скриптов)
- `patch_final.py` — патч resources.assets + TextTable + Dropdown + catalog
- `patch_dialogues_bundle.py` — патч DB_Dialogue_Eternight в бандле

## Важные детали
- Патчить `aa/StandaloneWindows64/` (НЕ `aa/Windows/StandaloneWindows64/`)
- CRC в catalog.json: побайтовая замена в UTF-16LE внутри base64 ExtraDataString
- JSON padding: пробелы после `,` и `:` для сохранения длины (НЕ перед `}`)
- Подход "Вариант А": подмена немецкого (de, индекс 9) на русский
- Dropdown: "German" → "Russian"
- DB_Dialogue_Eternight pid=-5833716775174085199 в gamemanager бандле

## Покрытие перевода (текущее)
- Диалоги: 7100/9234 (77%) — остальные останутся на немецком
- UI: 779/781 (99.7%)
- Непереведённые строки в основном: точки, анимации, дубли

## Распространение
- GitHub (релиз с .exe)
- Steam Community Guide с ссылкой
- Nexus Mods (опционально)
