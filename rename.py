import webview
import os
import json
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import requests
import sys
import subprocess
import time
from threading import Thread

# --- НАСТРОЙКИ ОБНОВЛЕНИЙ ---
VERSION = "1.2.0" 
GITHUB_REPO = "koteey/renamer" # Укажи свой репозиторий здесь!
# ----------------------------

APP_NAME = "RenamerApp_kote"
SETTINGS_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), APP_NAME)
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')
PHOTO_EXTENSIONS = ['webp', 'png', 'jpeg', 'jpg', 'gif', 'tiff', 'psd', 'bmp']

class Api:
    def __init__(self):
        self.last_action_history = []
        self._ensure_settings_dir()
        # Тихая проверка обновления в отдельном потоке
        Thread(target=self._silent_update_check, daemon=True).start()

    def _ensure_settings_dir(self):
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR)

    def _silent_update_check(self):
        """Фоновая загрузка обновления без уведомлений"""
        try:
            exe_path = sys.executable
            temp_exe = exe_path + ".new"
            
            # Если обновление уже скачано (с прошлого раза) - применяем
            if os.path.exists(temp_exe):
                self._apply_hotfix(exe_path, temp_exe)
                return

            # Проверка новой версии на GitHub
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data['tag_name'].replace('v', '')
                
                if latest_version != VERSION:
                    assets = data.get('assets', [])
                    for asset in assets:
                        if asset['name'].endswith('.exe'):
                            # Качаем тихо
                            r = requests.get(asset['browser_download_url'], stream=True)
                            with open(temp_exe, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            break
        except: pass

    def _apply_hotfix(self, exe_path, temp_exe):
        """Замена файла через батник"""
        try:
            bat_path = os.path.join(SETTINGS_DIR, "hotfix.bat")
            with open(bat_path, "w") as f:
                f.write(f'@echo off\ntimeout /t 1 /nobreak > nul\ndel "{exe_path}"\nmove "{temp_exe}" "{exe_path}"\nstart "" "{exe_path}"\ndel "%~f0"')
            subprocess.Popen([bat_path], shell=True)
            os._exit(0)
        except: pass

    def save_settings(self, settings):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except: pass

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {
            "current_theme": "pink", 
            "custom_themes": [],
            "last_folder": "",
            "last_mode": "photo",
            "last_old_ext": "",
            "last_new_ext": "webp"
        }

    def select_folder(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder_selected = filedialog.askdirectory()
        root.destroy()
        return folder_selected

    def convert_image(self, source_path, dest_path, target_ext):
        try:
            with Image.open(source_path) as img:
                if target_ext.lower() in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.save(dest_path)
            return True
        except: return False

    def rename_logic(self, folder_path, new_ext, mode, old_ext_filter=None):
        if not folder_path or not os.path.exists(folder_path):
            return {"status": "error", "message": "Путь не найден!"}
        
        new_ext = new_ext.strip().replace('.', '').lower()
        if not new_ext:
            return {"status": "error", "message": "Укажите формат!"}

        self.last_action_history = []
        count, errors = 0, 0
        
        try:
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            for filename in files:
                name, current_ext = os.path.splitext(filename)
                cur_ext_clean = current_ext.replace('.', '').lower()

                if mode == 'photo' and cur_ext_clean not in PHOTO_EXTENSIONS: continue
                if old_ext_filter and cur_ext_clean != old_ext_filter.strip().replace('.', '').lower(): continue

                old_path = os.path.normpath(os.path.join(folder_path, filename))
                new_path = os.path.normpath(os.path.join(folder_path, f"{name}.{new_ext}"))

                if old_path == new_path: continue

                if cur_ext_clean in PHOTO_EXTENSIONS or new_ext in PHOTO_EXTENSIONS:
                    if self.convert_image(old_path, new_path, new_ext):
                        os.remove(old_path)
                        self.last_action_history.append((new_path, old_path))
                        count += 1
                    else: errors += 1
                else:
                    os.rename(old_path, new_path)
                    self.last_action_history.append((new_path, old_path))
                    count += 1
            
            return {"status": "success", "message": f"Готово! Обработано: {count}", "can_undo": len(self.last_action_history) > 0}
        except Exception as e:
            return {"status": "error", "message": f"Ошибка: {str(e)}"}

    def undo_rename(self):
        if not self.last_action_history: return {"status": "error", "message": "Нечего отменять!"}
        undone = 0
        try:
            for cur, orig in self.last_action_history:
                if os.path.exists(cur):
                    os.rename(cur, orig)
                    undone += 1
            self.last_action_history = []
            return {"status": "success", "message": f"Откат: {undone} файлов"}
        except: return {"status": "error", "message": "Ошибка при откате"}

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        :root {{
            --bg: linear-gradient(135deg, #2b0314 0%, #630202 100%);
            --container: rgba(0, 0, 0, 0.6);
            --text: #ffffff;
            --accent: #ff2e63;
            --input-bg: rgba(255, 255, 255, 0.1);
            --panel-bg: #1a1a1a;
        }}
        body.white-theme {{
            --bg: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            --container: rgba(255, 255, 255, 0.9);
            --text: #333;
            --accent: #2d5cf7;
            --input-bg: rgba(0, 0, 0, 0.05);
            --panel-bg: #ffffff;
        }}
        body.black-theme {{
            --bg: #000000;
            --container: #111111;
            --text: #eeeeee;
            --accent: #555555;
            --input-bg: #222222;
            --panel-bg: #111111;
        }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: var(--bg); color: var(--text);
            height: 100vh; margin: 0;
            display: flex; justify-content: center; align-items: center;
            transition: background 0.5s; overflow: hidden;
        }}
        .container {{
            background: var(--container); padding: 25px; border-radius: 20px;
            width: 380px; backdrop-filter: blur(20px);
            box-shadow: 0 15px 50px rgba(0,0,0,0.8);
            border: 1px solid rgba(255,255,255,0.1);
            position: relative; z-index: 1;
        }}
        .v-tag {{ position: absolute; bottom: 8px; right: 12px; font-size: 9px; opacity: 0.3; }}
        .theme-switches {{ display: flex; gap: 8px; margin-bottom: 20px; justify-content: center; }}
        .theme-btn {{ 
            width: 26px; height: 26px; border-radius: 50%; cursor: pointer; 
            border: 2px solid white; display: flex; align-items: center; justify-content: center;
            transition: 0.2s;
        }}
        .theme-btn:hover {{ transform: scale(1.1); }}
        .mode-switcher {{
            display: flex; background: var(--input-bg); border-radius: 12px; 
            margin-bottom: 20px; padding: 4px;
        }}
        .mode-btn {{
            flex: 1; padding: 10px; text-align: center; cursor: pointer;
            border-radius: 8px; font-size: 0.85em; font-weight: bold; transition: 0.3s; opacity: 0.5;
        }}
        .mode-btn.active {{ background: var(--accent); color: white; opacity: 1; }}
        h2 {{ text-align: center; margin: 0 0 20px 0; font-size: 1.4em; }}
        .group {{ margin-bottom: 15px; }}
        label {{ display: block; font-size: 0.75em; margin-bottom: 6px; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; }}
        
        input, select {{
            width: 100%; padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);
            background: var(--panel-bg); color: var(--text); box-sizing: border-box;
            outline: none; font-size: 0.95em;
        }}
        select option {{ background: var(--panel-bg); color: var(--text); }}
        
        button {{ cursor: pointer; border: none; border-radius: 10px; transition: 0.2s; font-weight: bold; }}
        .btn-small {{ padding: 7px 15px; font-size: 0.75em; background: var(--accent); color: white; margin-top: 6px; }}
        .btn-main {{ width: 100%; padding: 15px; background: var(--accent); color: white; margin-top: 10px; font-size: 1em; }}
        .btn-undo {{ width: 100%; padding: 12px; background: rgba(255, 204, 0, 0.1); color: #ffcc00; margin-top: 12px; display: none; border: 1px dashed #ffcc00; }}
        
        #status {{ text-align: center; margin-top: 15px; font-size: 0.9em; font-weight: 500; min-height: 1.2em; }}

        /* ПАНЕЛЬ ТЕМЫ (FIXED) */
        #themePicker {{
            display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); border-radius: 20px; z-index: 100;
            flex-direction: column; justify-content: center; align-items: center; padding: 30px; box-sizing: border-box;
        }}
        .picker-row {{ display: flex; justify-content: space-between; width: 100%; align-items: center; margin-bottom: 20px; }}
        .color-input {{ width: 45px; height: 45px; padding: 0; border: 2px solid #fff; border-radius: 50%; cursor: pointer; }}
    </style>
</head>
<body id="body">
    <div class="container">
        <div class="v-tag">v.{VERSION}</div>

        <div id="themePicker">
            <h3 style="color: #fff; margin-bottom: 30px;">Свой стиль</h3>
            <div class="picker-row">
                <span>Цвет кнопок:</span>
                <input type="color" id="pickAccent" class="color-input" value="#ff2e63">
            </div>
            <div class="picker-row">
                <span>Фон:</span>
                <input type="color" id="pickBg" class="color-input" value="#2b0314">
            </div>
            <button class="btn-main" onclick="confirmTheme()">СОХРАНИТЬ</button>
            <button class="btn-small" style="background: #333; margin-top: 15px;" onclick="togglePicker(false)">ОТМЕНА</button>
        </div>

        <div class="theme-switches" id="themeList">
            <div class="theme-btn" style="background: #630202;" onclick="setTheme('pink')"></div>
            <div class="theme-btn" style="background: #fff;" onclick="setTheme('white')"></div>
            <div class="theme-btn" style="background: #000;" onclick="setTheme('black')"></div>
            <div class="theme-btn" style="background: #444; color: white;" onclick="togglePicker(true)">+</div>
        </div>

        <div class="mode-switcher">
            <div id="mode-photo" class="mode-btn active" onclick="setMode('photo')">ФОТО</div>
            <div id="mode-normal" class="mode-btn" onclick="setMode('normal')">ОБЫЧНЫЙ</div>
        </div>

        <h2 id="title">Загрузка...</h2>
        
        <div class="group">
            <label>Папка с файлами</label>
            <input type="text" id="folderPath" readonly placeholder="Выберите путь...">
            <button class="btn-small" onclick="selectFolder()">ОБЗОР</button>
        </div>

        <div class="group">
            <label>Найти формат</label>
            <div id="oldExtContainer"></div>
        </div>

        <div class="group">
            <label>В какой формат</label>
            <div id="newExtContainer"></div>
        </div>

        <button class="btn-main" onclick="run(false)">КОНВЕРТИРОВАТЬ ВСЁ</button>
        <button class="btn-main" style="background: transparent; border: 2px solid var(--accent);" onclick="run(true)">ТОЛЬКО ФИЛЬТР</button>
        
        <button id="undoBtn" class="btn-undo" onclick="undo()">↩ ОТМЕНИТЬ ИЗМЕНЕНИЯ</button>
        <div id="status"></div>
    </div>

    <script>
        let currentMode = 'photo';
        let customThemes = [];
        let currentThemeId = 'pink';
        const photoExts = {PHOTO_EXTENSIONS};

        window.addEventListener('pywebviewready', async () => {{
            const s = await pywebview.api.load_settings();
            customThemes = s.custom_themes || [];
            document.getElementById('folderPath').value = s.last_folder || '';
            
            renderCustomThemes();
            setMode(s.last_mode || 'photo');
            setTheme(s.current_theme || 'pink');

            setTimeout(() => {{
                if (document.getElementById('oldExt')) document.getElementById('oldExt').value = s.last_old_ext || '';
                if (document.getElementById('newExt')) document.getElementById('newExt').value = s.last_new_ext || 'webp';
            }}, 50);
        }});

        function setMode(mode) {{
            currentMode = mode;
            document.getElementById('mode-photo').classList.toggle('active', mode === 'photo');
            document.getElementById('mode-normal').classList.toggle('active', mode === 'normal');
            document.getElementById('title').innerText = mode === 'photo' ? 'Фото-Конвертер' : 'Переименователь';
            
            const oldCont = document.getElementById('oldExtContainer');
            const newCont = document.getElementById('newExtContainer');

            if (mode === 'photo') {{
                let options = photoExts.map(x => `<option value="${{x}}">${{x}}</option>`).join('');
                oldCont.innerHTML = `<select id="oldExt"><option value="">(Все фото)</option>${{options}}</select>`;
                newCont.innerHTML = `<select id="newExt">${{options}}</select>`;
            }} else {{
                oldCont.innerHTML = `<input type="text" id="oldExt" placeholder="Напр: txt">`;
                newCont.innerHTML = `<input type="text" id="newExt" placeholder="Напр: png">`;
            }}
            saveAll();
        }}

        function setTheme(id) {{
            const b = document.getElementById('body');
            currentThemeId = id;
            b.className = ''; b.style.background = ''; b.style.setProperty('--accent', '');
            
            const custom = customThemes.find(t => t.id === id);
            if (custom) {{
                b.style.background = custom.bg;
                b.style.setProperty('--accent', custom.accent);
            }} else if (id !== 'pink') {{
                b.classList.add(id + '-theme');
            }}
            saveAll();
        }}

        function togglePicker(show) {{ document.getElementById('themePicker').style.display = show ? 'flex' : 'none'; }}

        async function confirmTheme() {{
            const acc = document.getElementById('pickAccent').value;
            const bg = document.getElementById('pickBg').value;
            const nid = 'c_' + Date.now();
            customThemes.push({{ id: nid, accent: acc, bg: bg }});
            renderCustomThemes();
            setTheme(nid);
            togglePicker(false);
        }}

        function renderCustomThemes() {{
            const list = document.getElementById('themeList');
            while(list.children.length > 4) list.removeChild(list.children[3]);
            customThemes.forEach(t => {{
                const d = document.createElement('div');
                d.className = 'theme-btn';
                d.style.background = t.accent;
                d.onclick = () => setTheme(t.id);
                d.oncontextmenu = (e) => {{
                    e.preventDefault();
                    customThemes = customThemes.filter(x => x.id !== t.id);
                    renderCustomThemes(); setTheme('pink');
                }};
                list.insertBefore(d, list.lastElementChild);
            }});
        }}

        async function saveAll() {{
            const folder = document.getElementById('folderPath').value;
            const oldVal = document.getElementById('oldExt') ? document.getElementById('oldExt').value : '';
            const newVal = document.getElementById('newExt') ? document.getElementById('newExt').value : '';
            
            await pywebview.api.save_settings({{
                current_theme: currentThemeId,
                custom_themes: customThemes,
                last_folder: folder,
                last_mode: currentMode,
                last_old_ext: oldVal,
                last_new_ext: newVal
            }});
        }}

        async function selectFolder() {{
            const path = await pywebview.api.select_folder();
            if (path) {{ document.getElementById('folderPath').value = path; saveAll(); }}
        }}

        async function run(useFilter) {{
            const folder = document.getElementById('folderPath').value;
            const newEx = document.getElementById('newExt').value;
            const oldEx = document.getElementById('oldExt').value;
            const status = document.getElementById('status');
            
            status.innerText = "В процессе...";
            const res = await pywebview.api.rename_logic(folder, newEx, currentMode, useFilter ? oldEx : null);
            
            status.innerText = res.message;
            status.style.color = res.status === 'success' ? '#00ff88' : '#ff4d4d';
            document.getElementById('undoBtn').style.display = res.can_undo ? 'block' : 'none';
            saveAll();
        }}

        async function undo() {{
            const res = await pywebview.api.undo_rename();
            document.getElementById('status').innerText = res.message;
            document.getElementById('undoBtn').style.display = 'none';
        }}
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    api = Api()
    webview.create_window('Renamer PRO v.' + VERSION, html=html_content, js_api=api, width=440, height=750)
    webview.start()