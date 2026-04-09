"""
Eternights Russian Translation Installer
GUI installer that patches game files to add Russian language.
"""
import sys
import os
import json
import struct
import re
import shutil
import base64
import threading
import winreg
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox

# =====================================================
# CONSTANTS
# =====================================================
APP_TITLE = "Eternights - Русификатор"
APP_VERSION = "1.0"
BUNDLE_NAME = "gamemanager_assets_all_2a1ab4181e2e1d6bed81737aeb159efc.bundle"
BUNDLE_HASH = "2a1ab4181e2e1d6bed81737aeb159efc"
DB_PID = -5833716775174085199
DROPDOWN_PID = 1226886224836449939
BACKUP_DIR_NAME = "_rus_backup"

DT_PATTERN = b'\x0d\x00\x00\x00Dialogue Text'
DE_PATTERN = b'\x02\x00\x00\x00de\x00\x00'
SKIP_VALUES = {'', 'delay + animation only', 'Dim In Only', ' Dim Out Only',
               'Dim Out Only', 'SET NAME HERE'}

# =====================================================
# LOAD TRANSLATION DATA (embedded or from files)
# =====================================================
def get_data_path():
    """Get path to data files (works both in dev and PyInstaller)."""
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS) / "data"
    return Path(__file__).parent / "translations"

def load_translations():
    dp = get_data_path()
    with open(dp / "dialogues.json", encoding='utf-8') as f:
        translations = json.load(f)
    with open(dp / "ui_ru.json", encoding='utf-8') as f:
        ui_ru = json.load(f)
    return translations, ui_ru

# =====================================================
# FIND GAME
# =====================================================
def find_steam_library_folders():
    """Find all Steam library folders from libraryfolders.vdf."""
    folders = []
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
        winreg.CloseKey(key)
    except Exception:
        steam_path = Path("C:/Program Files (x86)/Steam")

    if not steam_path.exists():
        return folders

    folders.append(steam_path / "steamapps")

    vdf = steam_path / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        try:
            text = vdf.read_text(encoding='utf-8')
            for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                p = Path(m.group(1)) / "steamapps"
                if p.exists() and p not in folders:
                    folders.append(p)
        except Exception:
            pass
    return folders

def find_game_path():
    """Auto-detect Eternights install path."""
    for lib in find_steam_library_folders():
        game = lib / "common" / "Eternights"
        if (game / "Eternights_Data").exists():
            return game
    return None

# =====================================================
# UNITY HELPERS
# =====================================================
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
    except Exception:
        return None, pos

def normalize(s):
    return (s.replace('\u2019', "'").replace('\u2018', "'")
             .replace('\u201c', '"').replace('\u201d', '"'))

def get_translation(en_value, translations):
    """Get RU translation or handle dots/ellipsis."""
    ru = translations.get(en_value) or translations.get(normalize(en_value))
    if ru:
        return ru
    stripped = en_value.strip()
    if stripped and all(c in '.\u2026 \n\t' for c in stripped):
        return en_value.replace('\u2026', '...')
    return None

# =====================================================
# PATCH FUNCTIONS
# =====================================================
def patch_de_fields(raw_bytes, translations):
    """Patch DE fields in raw Unity data with Russian translations."""
    data = bytes(raw_bytes)
    if DT_PATTERN not in data:
        return None, 0
    replacements = []
    for m in re.finditer(DT_PATTERN, data):
        dt_end = m.end()
        pad = (4 - 13 % 4) % 4
        value_pos = dt_end + pad
        en_value, _ = read_unity_str(data, value_pos)
        if en_value is None or en_value in SKIP_VALUES:
            continue
        ru = get_translation(en_value, translations)
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

def patch_catalog_crc(catalog_path, bundle_hash, new_bundle_size):
    """Zero out CRC and update bundle size in catalog.json."""
    with open(catalog_path, encoding='utf-8') as f:
        cat = json.load(f)

    raw = bytearray(base64.b64decode(cat['m_ExtraDataString']))
    target_utf16 = bundle_hash.encode('utf-16-le')
    hash_idx = raw.find(target_utf16)
    if hash_idx == -1:
        raise RuntimeError("Bundle hash not found in catalog!")

    json_start = raw.rfind(b'{\x00', 0, hash_idx)
    json_end = raw.find(b'}\x00', hash_idx)
    old_json_bytes = raw[json_start:json_end + 2]
    old_json_str = old_json_bytes.decode('utf-16-le')
    entry = json.loads(old_json_str)

    entry['m_Crc'] = 0
    entry['m_BundleSize'] = new_bundle_size

    new_json_str = json.dumps(entry, separators=(',', ':'))
    new_json_bytes = new_json_str.encode('utf-16-le')
    old_len = len(old_json_bytes)
    new_len = len(new_json_bytes)

    if new_len < old_len:
        spaces = (old_len - new_len) // 2
        new_json_str = new_json_str[:-1] + ' ' * spaces + '}'
        new_json_bytes = new_json_str.encode('utf-16-le')
    elif new_len > old_len:
        entry.pop('m_ClearOtherCachedVersionsWhenLoaded', None)
        new_json_str = json.dumps(entry, separators=(',', ':'))
        new_json_bytes = new_json_str.encode('utf-16-le')
        new_len = len(new_json_bytes)
        if new_len < old_len:
            spaces = (old_len - new_len) // 2
            new_json_str = new_json_str[:-1] + ' ' * spaces + '}'
            new_json_bytes = new_json_str.encode('utf-16-le')

    if len(new_json_bytes) != old_len:
        raise RuntimeError(f"Catalog JSON length mismatch: {len(new_json_bytes)} != {old_len}")

    raw[json_start:json_start + old_len] = new_json_bytes
    cat['m_ExtraDataString'] = base64.b64encode(bytes(raw)).decode('ascii')

    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(cat, f, separators=(',', ':'))

# =====================================================
# MAIN INSTALL / UNINSTALL
# =====================================================
def do_install(game_path, log_fn, progress_fn):
    """Run the full installation."""
    import UnityPy

    translations, ui_ru = load_translations()
    log_fn(f"Загружено {len(translations)} переводов диалогов")
    log_fn(f"Загружено {len(ui_ru)} UI строк")

    base = game_path / "Eternights_Data"
    resources = base / "resources.assets"
    bundle = base / "StreamingAssets" / "aa" / "StandaloneWindows64" / BUNDLE_NAME
    catalog = base / "StreamingAssets" / "aa" / "catalog.json"

    for f in [resources, bundle, catalog]:
        if not f.exists():
            raise FileNotFoundError(f"Файл не найден: {f}")

    # Backup
    backup_dir = game_path / BACKUP_DIR_NAME
    if not backup_dir.exists():
        log_fn("Создаю бэкап оригинальных файлов...")
        backup_dir.mkdir(parents=True)
        shutil.copy2(resources, backup_dir / resources.name)
        shutil.copy2(bundle, backup_dir / bundle.name)
        shutil.copy2(catalog, backup_dir / catalog.name)
        log_fn("Бэкап создан")
    else:
        log_fn("Бэкап уже существует, восстанавливаю чистые файлы...")
        shutil.copy2(backup_dir / resources.name, resources)
        shutil.copy2(backup_dir / bundle.name, bundle)
        shutil.copy2(backup_dir / catalog.name, catalog)
        log_fn("Чистые файлы восстановлены")

    progress_fn(10)

    # --- PART 1: resources.assets ---
    log_fn("\n[1/3] Патчу resources.assets...")
    env_res = UnityPy.load(str(resources))
    sf = env_res.file
    total_objs = len(sf.objects)
    res_replacements = 0
    res_patched = 0

    for i, (pid, obj) in enumerate(sf.objects.items()):
        try:
            raw = obj.get_raw_data()
            if not raw or DT_PATTERN not in raw:
                continue
            new_raw, n = patch_de_fields(raw, translations)
            if new_raw and n > 0:
                obj.set_raw_data(new_raw)
                res_patched += 1
                res_replacements += n
        except Exception:
            pass

    new_data = env_res.file.save()
    with open(resources, 'wb') as f:
        f.write(new_data)
    log_fn(f"  resources.assets: {res_replacements} замен в {res_patched} объектах")
    progress_fn(30)

    # --- PART 2: gamemanager bundle ---
    log_fn("\n[2/3] Патчу бандл (UI + Dropdown + Диалоги)...")
    env = UnityPy.load(str(bundle))

    # TextTable
    ui_index = {}
    for key, val in ui_ru.items():
        parts = key.split('::', 1)
        if len(parts) == 2:
            ui_index.setdefault(parts[0], {})[parts[1]] = val

    tt_fields = 0
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            d = obj.read()
            name = getattr(d, 'm_Name', '') or ''
            if not name.startswith('GameText_') or name not in ui_index:
                continue
            ru_fields = ui_index[name]
            tree = obj.read_typetree()
            lang_keys = tree.get('m_languageKeys', [])
            if 'de' not in lang_keys:
                continue
            de_key_idx = lang_keys.index('de')
            de_lang_val = tree['m_languageValues'][de_key_idx]
            for field in tree.get('m_fieldValues', []):
                fname = field.get('m_fieldName', '')
                if fname in ru_fields and de_lang_val in field['m_keys']:
                    idx = field['m_keys'].index(de_lang_val)
                    field['m_values'][idx] = ru_fields[fname]
                    tt_fields += 1
            obj.save_typetree(tree)
        except Exception:
            pass

    log_fn(f"  TextTable: {tt_fields} UI строк")
    progress_fn(50)

    # Dropdown
    for obj in env.objects:
        if obj.path_id == DROPDOWN_PID:
            tree = obj.read_typetree()
            for opt in tree['m_Options']['m_Options']:
                if opt['m_Text'] == 'German':
                    opt['m_Text'] = 'Russian'
            obj.save_typetree(tree)
            log_fn("  Dropdown: German -> Russian")
            break

    # Dialogues in bundle
    bundle_replacements = 0
    for obj in env.objects:
        if obj.path_id == DB_PID:
            raw = obj.get_raw_data()
            new_raw, n = patch_de_fields(raw, translations)
            if new_raw and n > 0:
                obj.set_raw_data(new_raw)
                bundle_replacements = n
            break

    log_fn(f"  Диалоги в бандле: {bundle_replacements} замен")
    progress_fn(70)

    # Save bundle
    log_fn("  Сохраняю бандл...")
    try:
        saved = env.file.save(packer="lz4")
    except Exception:
        saved = env.file.save()
    with open(bundle, 'wb') as f:
        f.write(saved)
    new_bundle_size = len(saved)
    log_fn(f"  Бандл: {new_bundle_size:,} байт")
    progress_fn(85)

    # --- PART 3: catalog.json ---
    log_fn("\n[3/3] Обновляю catalog.json...")
    patch_catalog_crc(catalog, BUNDLE_HASH, new_bundle_size)
    log_fn("  CRC обнулён, размер обновлён")
    progress_fn(100)

    total = res_replacements + tt_fields + bundle_replacements
    log_fn(f"\n{'='*40}")
    log_fn(f"ГОТОВО! Всего {total} замен.")
    log_fn(f"Запусти игру и выбери 'German' в настройках языка (он заменён на русский).")

def do_uninstall(game_path, log_fn, progress_fn):
    """Restore original files from backup."""
    base = game_path / "Eternights_Data"
    resources = base / "resources.assets"
    bundle = base / "StreamingAssets" / "aa" / "StandaloneWindows64" / BUNDLE_NAME
    catalog = base / "StreamingAssets" / "aa" / "catalog.json"
    backup_dir = game_path / BACKUP_DIR_NAME

    if not backup_dir.exists():
        raise FileNotFoundError("Бэкап не найден! Возможно, русификатор не был установлен.")

    log_fn("Восстанавливаю оригинальные файлы...")
    progress_fn(20)
    shutil.copy2(backup_dir / resources.name, resources)
    progress_fn(50)
    shutil.copy2(backup_dir / bundle.name, bundle)
    progress_fn(80)
    shutil.copy2(backup_dir / catalog.name, catalog)
    progress_fn(90)

    shutil.rmtree(backup_dir)
    progress_fn(100)
    log_fn("Оригинальные файлы восстановлены!")
    log_fn("Бэкап удалён.")

# =====================================================
# GUI
# =====================================================
class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("620x480")
        self.root.resizable(False, False)

        # Try to set icon
        try:
            self.root.iconbitmap(default='')
        except Exception:
            pass

        self.game_path = None
        self.working = False

        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        # Header
        hdr = Frame(self.root, pady=10)
        hdr.pack(fill=X)
        Label(hdr, text=APP_TITLE, font=("Segoe UI", 16, "bold")).pack()
        Label(hdr, text="Подмена немецкого языка на русский",
              font=("Segoe UI", 9)).pack()

        # Path frame
        pf = LabelFrame(self.root, text="Папка игры", padx=10, pady=5)
        pf.pack(fill=X, padx=10)

        self.path_var = StringVar()
        Entry(pf, textvariable=self.path_var, width=60,
              font=("Segoe UI", 9)).pack(side=LEFT, fill=X, expand=True)
        Button(pf, text="Обзор...", command=self._browse).pack(side=RIGHT, padx=(5, 0))

        # Buttons
        bf = Frame(self.root, pady=10)
        bf.pack()
        self.btn_install = Button(bf, text="Установить", width=18, height=2,
                                  font=("Segoe UI", 10, "bold"),
                                  bg="#4CAF50", fg="white",
                                  command=self._on_install)
        self.btn_install.pack(side=LEFT, padx=10)

        self.btn_uninstall = Button(bf, text="Удалить", width=18, height=2,
                                    font=("Segoe UI", 10),
                                    command=self._on_uninstall)
        self.btn_uninstall.pack(side=LEFT, padx=10)

        # Progress
        self.progress = ttk.Progressbar(self.root, length=580, mode='determinate')
        self.progress.pack(padx=20, pady=(0, 5))

        # Log
        lf = LabelFrame(self.root, text="Лог", padx=5, pady=5)
        lf.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_text = Text(lf, height=12, font=("Consolas", 9),
                             state=DISABLED, wrap=WORD)
        sb = Scrollbar(lf, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        self.log_text.pack(fill=BOTH, expand=True)

    def _auto_detect(self):
        path = find_game_path()
        if path:
            self.game_path = path
            self.path_var.set(str(path))
            self.log("Игра найдена автоматически: " + str(path))
        else:
            self.log("Игра не найдена. Укажи папку вручную.")

    def _browse(self):
        d = filedialog.askdirectory(title="Выбери папку Eternights")
        if d:
            p = Path(d)
            if (p / "Eternights_Data").exists():
                self.game_path = p
                self.path_var.set(str(p))
                self.log(f"Выбрано: {p}")
            else:
                messagebox.showerror("Ошибка",
                    "В этой папке нет Eternights_Data.\nВыбери корневую папку игры.")

    def log(self, msg):
        self.log_text.configure(state=NORMAL)
        self.log_text.insert(END, msg + "\n")
        self.log_text.see(END)
        self.log_text.configure(state=DISABLED)

    def set_progress(self, val):
        self.progress['value'] = val

    def _set_buttons(self, enabled):
        state = NORMAL if enabled else DISABLED
        self.btn_install.configure(state=state)
        self.btn_uninstall.configure(state=state)
        self.working = not enabled

    def _on_install(self):
        if not self._validate_path():
            return
        self._set_buttons(False)
        self.progress['value'] = 0

        def run():
            try:
                def log_fn(msg):
                    self.root.after(0, self.log, msg)
                def progress_fn(val):
                    self.root.after(0, self.set_progress, val)
                do_install(self.game_path, log_fn, progress_fn)
            except Exception as e:
                self.root.after(0, self.log, f"\nОШИБКА: {e}")
                self.root.after(0, messagebox.showerror, "Ошибка", str(e))
            finally:
                self.root.after(0, self._set_buttons, True)

        threading.Thread(target=run, daemon=True).start()

    def _on_uninstall(self):
        if not self._validate_path():
            return
        self._set_buttons(False)
        self.progress['value'] = 0

        def run():
            try:
                def log_fn(msg):
                    self.root.after(0, self.log, msg)
                def progress_fn(val):
                    self.root.after(0, self.set_progress, val)
                do_uninstall(self.game_path, log_fn, progress_fn)
            except Exception as e:
                self.root.after(0, self.log, f"\nОШИБКА: {e}")
                self.root.after(0, messagebox.showerror, "Ошибка", str(e))
            finally:
                self.root.after(0, self._set_buttons, True)

        threading.Thread(target=run, daemon=True).start()

    def _validate_path(self):
        p = self.path_var.get().strip()
        if not p:
            messagebox.showwarning("Внимание", "Укажи папку игры!")
            return False
        gp = Path(p)
        if not (gp / "Eternights_Data").exists():
            messagebox.showerror("Ошибка", "Eternights_Data не найдена в указанной папке.")
            return False
        self.game_path = gp
        return True

def main():
    root = Tk()
    app = InstallerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
