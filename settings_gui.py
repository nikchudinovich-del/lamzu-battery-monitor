"""
Модуль графического интерфейса настроек LAMZU Battery Monitor.
Стильная тёмная тема, поддержка темной панели заголовка Windows 11/10,
карточный дизайн без сбоев шрифтов и эмодзи, кнопки поддержки (донат) и GitHub.
"""

import os
import sys
import ctypes
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable

from config import load_config, save_config

DEFAULT_DONATION_URL = "https://www.donationalerts.com/"
DEFAULT_GITHUB_URL = "https://github.com/"

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

def get_icon_path():
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base_dir, "app_icon.ico")
    if os.path.exists(p):
        return p
    scratch_p = r"C:\Users\NikCh\.gemini\antigravity\scratch\lamzu_battery_tray\app_icon.ico"
    return scratch_p if os.path.exists(scratch_p) else None

def show_donation_dialog(parent, current_url: str, on_save_url: Callable[[str], None]):
    """Окно поддержки / пожертвований с возможностью настроить ссылку."""
    dlg = tk.Toplevel(parent)
    dlg.title("Поддержка автора / Донат")
    dlg.geometry("460x280")
    dlg.resizable(False, False)
    dlg.configure(bg="#11131a")
    dlg.transient(parent)
    dlg.grab_set()

    enable_dark_title_bar(dlg)
    ico = get_icon_path()
    if ico:
        try:
            dlg.iconbitmap(ico)
        except Exception:
            pass

    dlg.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - 230
    y = parent.winfo_y() + (parent.winfo_height() // 2) - 140
    dlg.geometry(f"460x280+{x}+{y}")

    # Заголовок
    tk.Label(
        dlg,
        text="Поддержка разработки",
        font=("Segoe UI", 12, "bold"),
        fg="#ff4a6e",
        bg="#11131a"
    ).pack(pady=(18, 4))

    tk.Label(
        dlg,
        text="Если приложение оказалось полезным, вы можете поддержать автора\nили указать свою собственную ссылку для сбора средств:",
        font=("Segoe UI", 9),
        fg="#8f96a8",
        bg="#11131a",
        justify="center"
    ).pack(pady=(0, 14))

    # Поле ссылки
    entry_frame = tk.Frame(dlg, bg="#11131a", padx=24)
    entry_frame.pack(fill=tk.X)

    tk.Label(
        entry_frame,
        text="Ссылка для донатов (Boosty, DonationAlerts, ЮMoney, SBP и т.д.):",
        font=("Segoe UI", 8, "bold"),
        fg="#c8cdd9",
        bg="#11131a"
    ).pack(anchor="w", pady=(0, 4))

    url_var = tk.StringVar(value=current_url or DEFAULT_DONATION_URL)
    url_entry = tk.Entry(
        entry_frame,
        textvariable=url_var,
        font=("Segoe UI", 9),
        fg="#ffffff",
        bg="#1b1e2a",
        insertbackground="#00e6a0",
        relief="flat",
        highlightbackground="#2d3246",
        highlightthickness=1
    )
    url_entry.pack(fill=tk.X, ipady=4)

    # Кнопки
    btn_box = tk.Frame(dlg, bg="#11131a", padx=24)
    btn_box.pack(fill=tk.X, pady=(20, 0))

    def open_link():
        u = url_var.get().strip()
        if u:
            if not u.startswith("http://") and not u.startswith("https://"):
                u = "https://" + u
            webbrowser.open(u)

    def save_and_close():
        u = url_var.get().strip()
        on_save_url(u)
        dlg.destroy()

    open_btn = tk.Button(
        btn_box,
        text="Открыть в браузере",
        font=("Segoe UI", 9, "bold"),
        fg="#ffffff",
        bg="#ff3366",
        activebackground="#e02454",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=12,
        pady=5,
        command=open_link
    )
    open_btn.pack(side=tk.LEFT)

    save_btn = tk.Button(
        btn_box,
        text="Сохранить ссылку",
        font=("Segoe UI", 9, "bold"),
        fg="#090b10",
        bg="#00e6a0",
        activebackground="#00c88c",
        relief="flat",
        cursor="hand2",
        padx=12,
        pady=5,
        command=save_and_close
    )
    save_btn.pack(side=tk.RIGHT)

def show_settings_dialog(on_saved_callback: Optional[Callable[[dict], None]] = None, apply_stage_callback: Optional[Callable[[int], None]] = None):
    root = tk.Tk()
    root.title("LAMZU Maya X — Настройки и производительность")
    root.geometry("540x620")
    root.resizable(False, False)
    root.configure(bg="#0d0f15")

    ico = get_icon_path()
    if ico:
        try:
            root.iconbitmap(ico)
        except Exception:
            pass

    enable_dark_title_bar(root)

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 270
    y = (root.winfo_screenheight() // 2) - 310
    root.geometry(f"540x620+{x}+{y}")

    cfg = load_config()

    # --- ШАПКА ---
    header = tk.Frame(root, bg="#0d0f15")
    header.pack(fill=tk.X, padx=22, pady=(16, 10))

    title_frame = tk.Frame(header, bg="#0d0f15")
    title_frame.pack(fill=tk.X)

    tk.Label(
        title_frame,
        text="LAMZU Maya X Control",
        font=("Segoe UI", 14, "bold"),
        fg="#ffffff",
        bg="#0d0f15"
    ).pack(side=tk.LEFT)

    status_badge = tk.Label(
        title_frame,
        text=" 8K Dongle Active ",
        font=("Segoe UI", 8, "bold"),
        fg="#00e6a0",
        bg="#122b22",
        padx=6,
        pady=2
    )
    status_badge.pack(side=tk.RIGHT)

    tk.Label(
        header,
        text="Циклическое переключение кнопки снизу мыши и оптимизация отклика",
        font=("Segoe UI", 9),
        fg="#788094",
        bg="#0d0f15"
    ).pack(anchor="w", pady=(2, 0))

    # Главный контейнер карточек
    content = tk.Frame(root, bg="#0d0f15")
    content.pack(fill=tk.BOTH, expand=True, padx=22, pady=(0, 10))

    # ==================== КАРТОЧКА 1 ====================
    c1 = tk.Frame(content, bg="#151822", padx=14, pady=10, highlightbackground="#222636", highlightthickness=1)
    c1.pack(fill=tk.X, pady=(0, 8))

    c1_head = tk.Frame(c1, bg="#151822")
    c1_head.pack(fill=tk.X, pady=(0, 6))

    tk.Label(
        c1_head,
        text=" 1 ",
        font=("Segoe UI", 9, "bold"),
        fg="#090b10",
        bg="#00e6a0",
        padx=4,
        pady=1
    ).pack(side=tk.LEFT, padx=(0, 8))

    tk.Label(
        c1_head,
        text="1-е нажатие: Киберспортивный режим (High-Speed)",
        font=("Segoe UI", 9, "bold"),
        fg="#00e6a0",
        bg="#151822"
    ).pack(side=tk.LEFT)

    s1_rate_var = tk.IntVar(value=cfg.get("stage1_rate", 2000))
    s1_opt = tk.Frame(c1, bg="#151822")
    s1_opt.pack(fill=tk.X)

    tk.Label(s1_opt, text="Частота опроса:", font=("Segoe UI", 9), fg="#9ca3b5", bg="#151822").pack(side=tk.LEFT, padx=(0, 12))
    for r in [1000, 2000, 4000, 8000]:
        rb = tk.Radiobutton(
            s1_opt,
            text=f"{r} Гц",
            value=r,
            variable=s1_rate_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#151822",
            selectcolor="#090b10",
            activebackground="#151822",
            activeforeground="#00e6a0",
            highlightthickness=0,
            cursor="hand2"
        )
        rb.pack(side=tk.LEFT, padx=(0, 10))

    # ==================== КАРТОЧКА 2 ====================
    c2 = tk.Frame(content, bg="#151822", padx=14, pady=10, highlightbackground="#222636", highlightthickness=1)
    c2.pack(fill=tk.X, pady=(0, 8))

    c2_head = tk.Frame(c2, bg="#151822")
    c2_head.pack(fill=tk.X, pady=(0, 6))

    tk.Label(
        c2_head,
        text=" 2 ",
        font=("Segoe UI", 9, "bold"),
        fg="#090b10",
        bg="#00b4ff",
        padx=4,
        pady=1
    ).pack(side=tk.LEFT, padx=(0, 8))

    tk.Label(
        c2_head,
        text="2-е нажатие: Экстремальный режим (20K FPS)",
        font=("Segoe UI", 9, "bold"),
        fg="#00b4ff",
        bg="#151822"
    ).pack(side=tk.LEFT)

    s2_rate_var = tk.IntVar(value=cfg.get("stage2_rate", 4000))
    s2_opt = tk.Frame(c2, bg="#151822")
    s2_opt.pack(fill=tk.X)

    tk.Label(s2_opt, text="Частота опроса:", font=("Segoe UI", 9), fg="#9ca3b5", bg="#151822").pack(side=tk.LEFT, padx=(0, 12))
    for r in [2000, 4000, 8000]:
        rb = tk.Radiobutton(
            s2_opt,
            text=f"{r} Гц",
            value=r,
            variable=s2_rate_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#151822",
            selectcolor="#090b10",
            activebackground="#151822",
            activeforeground="#00b4ff",
            highlightthickness=0,
            cursor="hand2"
        )
        rb.pack(side=tk.LEFT, padx=(0, 10))

    # ==================== КАРТОЧКА 3 ====================
    c3 = tk.Frame(content, bg="#151822", padx=14, pady=10, highlightbackground="#222636", highlightthickness=1)
    c3.pack(fill=tk.X, pady=(0, 8))

    c3_head = tk.Frame(c3, bg="#151822")
    c3_head.pack(fill=tk.X, pady=(0, 6))

    tk.Label(
        c3_head,
        text=" 3 ",
        font=("Segoe UI", 9, "bold"),
        fg="#ffffff",
        bg="#3d4357",
        padx=4,
        pady=1
    ).pack(side=tk.LEFT, padx=(0, 8))

    tk.Label(
        c3_head,
        text="3-е нажатие: Обычный режим (Выключение)",
        font=("Segoe UI", 9, "bold"),
        fg="#d0d5e3",
        bg="#151822"
    ).pack(side=tk.LEFT)

    s0_rate_var = tk.IntVar(value=cfg.get("stage0_rate", 1000))
    s0_opt = tk.Frame(c3, bg="#151822")
    s0_opt.pack(fill=tk.X)

    tk.Label(s0_opt, text="Частота опроса:", font=("Segoe UI", 9), fg="#9ca3b5", bg="#151822").pack(side=tk.LEFT, padx=(0, 12))
    for r in [500, 1000, 2000]:
        rb = tk.Radiobutton(
            s0_opt,
            text=f"{r} Гц",
            value=r,
            variable=s0_rate_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#151822",
            selectcolor="#090b10",
            activebackground="#151822",
            activeforeground="#00e6a0",
            highlightthickness=0,
            cursor="hand2"
        )
        rb.pack(side=tk.LEFT, padx=(0, 10))

    # ==================== КАРТОЧКА ОПТИМИЗАЦИИ ====================
    c_perf = tk.Frame(content, bg="#151822", padx=14, pady=10, highlightbackground="#222636", highlightthickness=1)
    c_perf.pack(fill=tk.X, pady=(0, 10))

    tk.Label(
        c_perf,
        text="Оптимизация производительности в играх",
        font=("Segoe UI", 9, "bold"),
        fg="#ffc83b",
        bg="#151822"
    ).pack(anchor="w", pady=(0, 4))

    pause_game_var = tk.BooleanVar(value=cfg.get("pause_in_game", True))
    tk.Checkbutton(
        c_perf,
        text="Отключать опрос в играх (0% задержек и нагрузки, авто-опрос при Alt-Tab)",
        variable=pause_game_var,
        font=("Segoe UI", 9),
        fg="#e1e5f0",
        bg="#151822",
        selectcolor="#090b10",
        activebackground="#151822",
        activeforeground="#00e6a0",
        highlightthickness=0,
        cursor="hand2"
    ).pack(anchor="w", pady=(1, 3))

    int_frame = tk.Frame(c_perf, bg="#151822")
    int_frame.pack(fill=tk.X, pady=(2, 4))

    tk.Label(int_frame, text="Интервал обновления:", font=("Segoe UI", 9), fg="#9ca3b5", bg="#151822").pack(side=tk.LEFT, padx=(0, 12))
    poll_int_var = tk.IntVar(value=cfg.get("poll_interval", 30))
    for sec in [30, 60, 120]:
        tk.Radiobutton(
            int_frame,
            text=f"{sec} сек",
            value=sec,
            variable=poll_int_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#151822",
            selectcolor="#090b10",
            activebackground="#151822",
            activeforeground="#00e6a0",
            highlightthickness=0,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

    notify_var = tk.BooleanVar(value=cfg.get("notify_on_switch", True))
    tk.Checkbutton(
        c_perf,
        text="Всплывающее уведомление Windows при переключении режима",
        variable=notify_var,
        font=("Segoe UI", 9),
        fg="#e1e5f0",
        bg="#151822",
        selectcolor="#090b10",
        activebackground="#151822",
        activeforeground="#00e6a0",
        highlightthickness=0,
        cursor="hand2"
    ).pack(anchor="w", pady=(1, 0))

    # ==================== НИЖНЯЯ ПАНЕЛЬ ====================
    footer = tk.Frame(root, bg="#0d0f15")
    footer.pack(fill=tk.X, padx=22, pady=(0, 16))

    # Левая сторона: Донат и GitHub
    left_actions = tk.Frame(footer, bg="#0d0f15")
    left_actions.pack(side=tk.LEFT)

    current_donation_url = cfg.get("donation_url", DEFAULT_DONATION_URL)

    def on_donation_click():
        show_donation_dialog(root, current_donation_url, on_update_donation_url)

    def on_update_donation_url(new_url):
        nonlocal current_donation_url
        current_donation_url = new_url
        cfg["donation_url"] = new_url
        save_config(cfg)

    def on_github_click():
        u = cfg.get("github_url", DEFAULT_GITHUB_URL)
        webbrowser.open(u)

    donate_btn = tk.Button(
        left_actions,
        text="♥ Поддержать",
        font=("Segoe UI", 9, "bold"),
        fg="#ffffff",
        bg="#e02454",
        activebackground="#c71b46",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=10,
        pady=5,
        command=on_donation_click
    )
    donate_btn.pack(side=tk.LEFT, padx=(0, 8))

    github_btn = tk.Button(
        left_actions,
        text="GitHub",
        font=("Segoe UI", 9),
        fg="#c4c9d9",
        bg="#1c202d",
        activebackground="#2a3043",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=10,
        pady=5,
        command=on_github_click
    )
    github_btn.pack(side=tk.LEFT)

    # Правая сторона: Сохранить и Отмена
    right_actions = tk.Frame(footer, bg="#0d0f15")
    right_actions.pack(side=tk.RIGHT)

    def on_save():
        new_cfg = dict(cfg)
        new_cfg.update({
            "stage1_rate": s1_rate_var.get(),
            "stage1_mode": "high_speed",
            "stage2_rate": s2_rate_var.get(),
            "stage2_mode": "20k",
            "stage0_rate": s0_rate_var.get(),
            "stage0_mode": "normal",
            "pause_in_game": pause_game_var.get(),
            "poll_interval": poll_int_var.get(),
            "auto_sync_button": True,
            "notify_on_switch": notify_var.get(),
            "donation_url": current_donation_url
        })
        save_config(new_cfg)
        if on_saved_callback:
            on_saved_callback(new_cfg)
        root.destroy()

    save_btn = tk.Button(
        right_actions,
        text="Сохранить",
        font=("Segoe UI", 9, "bold"),
        fg="#090b10",
        bg="#00e6a0",
        activebackground="#00c88c",
        relief="flat",
        cursor="hand2",
        padx=16,
        pady=5,
        command=on_save
    )
    save_btn.pack(side=tk.RIGHT)

    cancel_btn = tk.Button(
        right_actions,
        text="Отмена",
        font=("Segoe UI", 9),
        fg="#8f96a8",
        bg="#151822",
        activebackground="#222636",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=12,
        pady=5,
        command=root.destroy
    )
    cancel_btn.pack(side=tk.RIGHT, padx=(0, 8))

    root.mainloop()

if __name__ == "__main__":
    show_settings_dialog()
