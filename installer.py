"""
Графический установщик для LAMZU Battery Monitor.
Устанавливает приложение, добавляет в автозагрузку Windows,
создает ярлыки на Рабочем столе и в меню Пуск, и сразу запускает в трее.
"""

import os
import sys
import shutil
import winreg
import ctypes
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "LamzuBatteryTray"
DISPLAY_NAME = "LAMZU Battery Monitor"
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
UNINSTALL_REG_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"

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
    """Выполняет полную установку и настройку."""
    def log(msg, step):
        if progress_callback:
            progress_callback(msg, step)

    log("Остановка предыдущих копий...", 15)
    kill_running_app()

    install_dir = get_install_dir()
    os.makedirs(install_dir, exist_ok=True)
    bundle_dir = get_bundle_dir()

    log("Копирование файлов программы...", 40)
    source_exe = os.path.join(bundle_dir, f"{APP_NAME}.exe")
    dest_exe = os.path.join(install_dir, f"{APP_NAME}.exe")

    if not os.path.exists(source_exe):
        # Fallback если запущен из исходников
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

    log("Добавление в автозагрузку Windows...", 65)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{dest_exe}"')

    log("Создание ярлыков...", 80)
    # 1. Рабочий стол
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    desktop_lnk = os.path.join(desktop, f"{DISPLAY_NAME}.lnk")
    create_windows_shortcut(dest_exe, desktop_lnk, dest_ico, DISPLAY_NAME)

    # 2. Меню Пуск
    start_menu = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs')
    if os.path.exists(start_menu):
        start_lnk = os.path.join(start_menu, f"{DISPLAY_NAME}.lnk")
        create_windows_shortcut(dest_exe, start_lnk, dest_ico, DISPLAY_NAME)

    # Создаем скрипт деинсталляции
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
    subprocess.Popen([dest_exe], cwd=install_dir)

    log("Готово!", 100)
    return True

class InstallerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Установка LAMZU Battery Monitor")
        self.root.geometry("480x360")
        self.root.resizable(False, False)
        self.root.configure(bg="#15171e")

        # Центрирование окна
        self.center_window()

        # Заголовок
        header_frame = tk.Frame(root, bg="#15171e")
        header_frame.pack(fill=tk.X, padx=24, pady=(24, 12))

        title_lbl = tk.Label(
            header_frame,
            text="LAMZU Battery Monitor",
            font=("Segoe UI", 16, "bold"),
            fg="#00e6a0",
            bg="#15171e"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Индикатор заряда вашей мышки в трее Windows",
            font=("Segoe UI", 10),
            fg="#8c92a4",
            bg="#15171e"
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Карточка с информацией
        card = tk.Frame(root, bg="#1f222d", padx=16, pady=14, relief="flat", highlightbackground="#2d3242", highlightthickness=1)
        card.pack(fill=tk.X, padx=24, pady=10)

        features = [
            "✔  Опрос заряда мыши каждую 1 минуту",
            "✔  Отображение процента и молнии зарядки в трее",
            "✔  Автозапуск при старте Windows",
            "✔  Ярлык на Рабочем столе и в меню «Пуск»",
        ]

        for feat in features:
            f_lbl = tk.Label(card, text=feat, font=("Segoe UI", 9), fg="#e1e4ea", bg="#1f222d")
            f_lbl.pack(anchor="w", pady=2)

        # Статус и прогресс
        self.status_lbl = tk.Label(
            root,
            text="Нажмите «Установить» для начала автоматической установки",
            font=("Segoe UI", 9),
            fg="#9ba3b8",
            bg="#15171e"
        )
        self.status_lbl.pack(fill=tk.X, padx=24, pady=(16, 6))

        # Стиль прогрессбара
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Custom.Horizontal.TProgressbar", foreground='#00e6a0', background='#00e6a0', troughcolor='#202430', bordercolor='#15171e', lightcolor='#00e6a0', darkcolor='#00e6a0')

        self.progress = ttk.Progressbar(root, orient="horizontal", length=432, mode="determinate", style="Custom.Horizontal.TProgressbar")
        self.progress.pack(padx=24, pady=(0, 20))

        # Кнопки
        btn_frame = tk.Frame(root, bg="#15171e")
        btn_frame.pack(fill=tk.X, padx=24, pady=(0, 20))

        self.install_btn = tk.Button(
            btn_frame,
            text="Установить сейчас",
            font=("Segoe UI", 10, "bold"),
            fg="#0b0d12",
            bg="#00e6a0",
            activeforeground="#0b0d12",
            activebackground="#00c88c",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.start_install
        )
        self.install_btn.pack(side=tk.RIGHT)

        self.close_btn = tk.Button(
            btn_frame,
            text="Отмена",
            font=("Segoe UI", 10),
            fg="#8c92a4",
            bg="#232733",
            activeforeground="#ffffff",
            activebackground="#2e3342",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.root.destroy
        )
        self.close_btn.pack(side=tk.RIGHT, padx=(0, 10))

    def center_window(self):
        self.root.update_idletasks()
        w = 480
        h = 360
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def update_progress(self, msg, val):
        self.status_lbl.config(text=msg)
        self.progress["value"] = val
        self.root.update_idletasks()

    def start_install(self):
        self.install_btn.config(state=tk.DISABLED, text="Установка...")
        self.close_btn.config(state=tk.DISABLED)

        def worker():
            try:
                perform_install(self.update_progress)
                self.root.after(0, self.on_success)
            except Exception as e:
                self.root.after(0, lambda: self.on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def on_success(self):
        self.status_lbl.config(text="✔ Установка завершена! Программа запущена в трее.", fg="#00e6a0")
        self.install_btn.config(state=tk.NORMAL, text="Готово", command=self.root.destroy, bg="#00e6a0")
        self.close_btn.pack_forget()

    def on_error(self, err):
        self.status_lbl.config(text=f"Ошибка: {err}", fg="#ff4d4d")
        messagebox.showerror("Ошибка установки", f"Не удалось завершить установку:\n{err}")
        self.install_btn.config(state=tk.NORMAL, text="Повторить")
        self.close_btn.config(state=tk.NORMAL)

def main():
    if "--silent" in sys.argv:
        perform_install()
        return

    root = tk.Tk()
    app = InstallerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
