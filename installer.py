"""
Полностью автоматический графический установщик для LAMZU Battery Monitor.
- Запускается в стильной тёмной теме (AMOLED Black).
- Автоматически выполняет установку без необходимости нажимать кнопку «Установить».
- Копирует файлы, настраивает автозагрузку с Windows, создает ярлык на Рабочем столе.
- Мгновенно запускает приложение в трее и автоматически закрывается.
"""

import os
import sys
import shutil
import winreg
import ctypes
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "LamzuBatteryTray"
DISPLAY_NAME = "LAMZU Battery Monitor"
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL_REG_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"

def enable_dark_title_bar(window):
    """Включает нативную тёмную тему для заголовка окна Windows 10/11."""
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
        val = ctypes.c_int(1)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(val), ctypes.sizeof(val)
        )
        if res != 0:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1, ctypes.byref(val), ctypes.sizeof(val)
            )
    except Exception:
        pass

def get_bundle_dir():
    """Возвращает каталог с распакованными файлами инсталлятора."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_install_dir():
    local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    return os.path.join(local_appdata, "Programs", APP_NAME)

def kill_running_app():
    try:
        subprocess.run(["taskkill", "/f", "/im", f"{APP_NAME}.exe"], capture_output=True)
    except Exception:
        pass

def create_windows_shortcut(target_exe, shortcut_path, icon_path, description):
    vbs_script = f'''
Set WshShell = CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut("{shortcut_path}")
Shortcut.TargetPath = "{target_exe}"
Shortcut.WorkingDirectory = "{os.path.dirname(target_exe)}"
Shortcut.IconLocation = "{icon_path},0"
Shortcut.Description = "{description}"
Shortcut.Save
'''
    temp_vbs = os.path.join(os.environ.get("TEMP", "."), "_create_shortcut.vbs")
    try:
        with open(temp_vbs, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        subprocess.run(["cscript.exe", "//nologo", temp_vbs], capture_output=True)
    finally:
        if os.path.exists(temp_vbs):
            try:
                os.remove(temp_vbs)
            except OSError:
                pass

def perform_install(progress_callback=None):
    """Выполняет полную автоматическую установку."""
    def log(msg, step):
        if progress_callback:
            progress_callback(msg, step)
        time.sleep(0.08)

    log("Остановка предыдущих копий...", 15)
    kill_running_app()

    install_dir = get_install_dir()
    os.makedirs(install_dir, exist_ok=True)
    bundle_dir = get_bundle_dir()

    log("Копирование файлов программы...", 40)
    source_exe = os.path.join(bundle_dir, f"{APP_NAME}.exe")
    dest_exe = os.path.join(install_dir, f"{APP_NAME}.exe")

    if not os.path.exists(source_exe):
        scratch_exe = r"C:\Users\NikCh\.gemini\antigravity\scratch\lamzu_battery_tray\LamzuBatteryTray.exe"
        if os.path.exists(scratch_exe):
            source_exe = scratch_exe

    shutil.copy2(source_exe, dest_exe)

    source_ico = os.path.join(bundle_dir, "app_icon.ico")
    dest_ico = os.path.join(install_dir, "app_icon.ico")
    if not os.path.exists(source_ico):
        scratch_ico = r"C:\Users\NikCh\.gemini\antigravity\scratch\lamzu_battery_tray\app_icon.ico"
        if os.path.exists(scratch_ico):
            source_ico = scratch_ico

    if os.path.exists(source_ico):
        shutil.copy2(source_ico, dest_ico)

    # Копирование конфига с реквизитами
    source_cfg = os.path.join(bundle_dir, "config.json")
    if not os.path.exists(source_cfg):
        scratch_cfg = r"C:\Users\NikCh\.gemini\antigravity\scratch\lamzu_battery_tray\config.json"
        if os.path.exists(scratch_cfg):
            source_cfg = scratch_cfg

    dest_cfg = os.path.join(install_dir, "config.json")
    if os.path.exists(source_cfg):
        try:
            if not os.path.exists(dest_cfg):
                shutil.copy2(source_cfg, dest_cfg)
            else:
                import json
                with open(dest_cfg, "r", encoding="utf-8") as f:
                    curr_c = json.load(f)
                curr_c["card_number"] = "2204 3110 1790 0938"
                curr_c["card_holder"] = "Яндекс Банк (СБП)"
                curr_c["github_url"] = "https://github.com/nikchudinovich-del/lamzu-battery-monitor"
                curr_c.pop("profile_id", None)
                with open(dest_cfg, "w", encoding="utf-8") as f:
                    json.dump(curr_c, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    log("Настройка автозагрузки Windows...", 70)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{dest_exe}"')

    log("Создание ярлыков на Рабочем столе...", 85)
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    desktop_lnk = os.path.join(desktop, f"{DISPLAY_NAME}.lnk")
    create_windows_shortcut(dest_exe, desktop_lnk, dest_ico, DISPLAY_NAME)

    start_menu = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs')
    if os.path.exists(start_menu):
        start_lnk = os.path.join(start_menu, f"{DISPLAY_NAME}.lnk")
        create_windows_shortcut(dest_exe, start_lnk, dest_ico, DISPLAY_NAME)

    # Деинсталлятор
    uninstall_bat = os.path.join(install_dir, "Uninstall.bat")
    with open(uninstall_bat, "w", encoding="cp1251", errors="ignore") as f:
        f.write(f'''@echo off
chcp 1251 > nul
taskkill /f /im {APP_NAME}.exe > nul 2>&1
reg delete "HKCU\\{RUN_REG_KEY}" /v {APP_NAME} /f > nul 2>&1
del /f /q "{desktop_lnk}" > nul 2>&1
echo Программа {DISPLAY_NAME} успешно удалена.
pause
''')

    log("Запуск приложения в трее...", 95)
    try:
        os.startfile(dest_exe)
    except Exception:
        subprocess.Popen(
            [dest_exe],
            cwd=install_dir,
            creationflags=0x00000008 | 0x00000200,
            close_fds=True
        )

    log("Установка успешно завершена!", 100)
    return True

class AutoInstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Установка LAMZU Battery Monitor")
        self.root.geometry("450x240")
        self.root.resizable(False, False)
        self.root.configure(bg="#08090d")

        enable_dark_title_bar(root)

        bundle_dir = get_bundle_dir()
        ico = os.path.join(bundle_dir, "app_icon.ico")
        if os.path.exists(ico):
            try:
                root.iconbitmap(ico)
            except Exception:
                pass

        self.center_window()

        # Шапка
        header = tk.Frame(root, bg="#08090d", padx=24, pady=16)
        header.pack(fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="LAMZU Battery Monitor",
            font=("Segoe UI", 14, "bold"),
            fg="#00f09a",
            bg="#08090d"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header,
            text="Автоматическая установка и запуск в трее...",
            font=("Segoe UI", 9),
            fg="#788094",
            bg="#08090d"
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Статус
        self.status_lbl = tk.Label(
            root,
            text="Подготовка к установке...",
            font=("Segoe UI", 9, "bold"),
            fg="#e1e6f2",
            bg="#08090d"
        )
        self.status_lbl.pack(anchor="w", padx=24, pady=(10, 6))

        # Стиль прогрессбара
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Auto.Horizontal.TProgressbar",
            foreground='#00f09a',
            background='#00f09a',
            troughcolor='#151822',
            bordercolor='#08090d',
            lightcolor='#00f09a',
            darkcolor='#00f09a'
        )

        self.progress = ttk.Progressbar(
            root,
            orient="horizontal",
            length=402,
            mode="determinate",
            style="Auto.Horizontal.TProgressbar"
        )
        self.progress.pack(padx=24, pady=(0, 14))

        # Нижняя подсказка
        self.footer_lbl = tk.Label(
            root,
            text="Пожалуйста, подождите, всё происходит автоматически...",
            font=("Segoe UI", 8),
            fg="#596075",
            bg="#08090d"
        )
        self.footer_lbl.pack(anchor="w", padx=24)

        # Автоматический старт установки через 200 мс после отрисовки окна
        self.root.after(200, self.start_auto_install)

    def center_window(self):
        self.root.update_idletasks()
        w = 450
        h = 240
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def update_progress(self, msg, val):
        self.status_lbl.config(text=msg)
        self.progress["value"] = val
        self.root.update_idletasks()

    def start_auto_install(self):
        def worker():
            try:
                perform_install(self.update_progress)
                self.root.after(0, self.on_success)
            except Exception as e:
                self.root.after(0, lambda: self.on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def on_success(self):
        self.status_lbl.config(text="✔ Установка завершена! Значок активен в трее.", fg="#00f09a")
        self.footer_lbl.config(text="Окно закроется автоматически через секунду...")
        # Автоматическое закрытие окна через 1.2 секунды
        self.root.after(1200, self.root.destroy)

    def on_error(self, err):
        self.status_lbl.config(text=f"Ошибка: {err}", fg="#ff4d4d")
        messagebox.showerror("Ошибка установки", f"Не удалось завершить установку:\n{err}")

def main():
    if "--silent" in sys.argv:
        perform_install()
        return

    root = tk.Tk()
    app = AutoInstallerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
