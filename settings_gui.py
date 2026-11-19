"""
Модуль графического интерфейса настроек LAMZU Battery & Polling Rate Monitor.
Глубокая черная тема (AMOLED Dark), нативная тёмная панель Windows 11/10,
стильные карточки настроек, поддержка номера карты Яндекс Банка и копирование в буфер.
"""

import os
import sys
import ctypes
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable

from config import load_config, save_config

DEFAULT_GITHUB_URL = "https://github.com/nikchudinovich-del"

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

def format_card_number(raw_num: str) -> str:
    """Форматирует номер карты блоками по 4 цифры."""
    clean = "".join(c for c in raw_num if c.isdigit())
    if not clean:
        clean = "2204311017900938"
    return " ".join(clean[i:i+4] for i in range(0, len(clean), 4))

def show_donation_dialog(parent=None, cfg: dict = None, on_save_callback: Optional[Callable[[dict], None]] = None):
    """Окно поддержки / пожертвований с номером банковской карты и кнопкой копирования."""
    if cfg is None:
        cfg = load_config()

    is_standalone = False
    if parent is None:
        dlg = tk.Tk()
        is_standalone = True
    else:
        dlg = tk.Toplevel(parent)
        dlg.transient(parent)
        dlg.grab_set()

    dlg.title("Поддержать автора проекта")
    dlg.geometry("480x360")
    dlg.resizable(False, False)
    dlg.configure(bg="#08090d")

    enable_dark_title_bar(dlg)
    ico = get_icon_path()
    if ico:
        try:
            dlg.iconbitmap(ico)
        except Exception:
            pass

    dlg.update_idletasks()
    if parent is not None:
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 240
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 180
    else:
        x = (dlg.winfo_screenwidth() // 2) - 240
        y = (dlg.winfo_screenheight() // 2) - 180
    dlg.geometry(f"480x360+{x}+{y}")

    # Заголовок
    header = tk.Frame(dlg, bg="#08090d", padx=24, pady=16)
    header.pack(fill=tk.X)

    tk.Label(
        header,
        text="Поддержка разработчика",
        font=("Segoe UI", 14, "bold"),
        fg="#ff3b69",
        bg="#08090d"
    ).pack(anchor="w")

    tk.Label(
        header,
        text="Если приложение полезно для вас, вы можете поддержать автора\nлюбой суммой по номеру карты через СБП:",
        font=("Segoe UI", 9),
        fg="#858da3",
        bg="#08090d",
        justify="left"
    ).pack(anchor="w", pady=(4, 0))

    # Виртуальная банковская карта (Cyber Black Card)
    card_frame = tk.Frame(dlg, bg="#11141d", padx=18, pady=14, highlightbackground="#222738", highlightthickness=1)
    card_frame.pack(fill=tk.X, padx=24, pady=(0, 14))

    card_head = tk.Frame(card_frame, bg="#11141d")
    card_head.pack(fill=tk.X)

    tk.Label(
        card_head,
        text="ЯНДЕКС БАНК (СБП)",
        font=("Segoe UI", 8, "bold"),
        fg="#00e6a0",
        bg="#11141d"
    ).pack(side=tk.LEFT)

    tk.Label(
        card_head,
        text="● Перевод без комиссии",
        font=("Segoe UI", 8),
        fg="#6a7287",
        bg="#11141d"
    ).pack(side=tk.RIGHT)

    raw_card = cfg.get("card_number", "2204 3110 1790 0938").strip() or "2204 3110 1790 0938"
    display_card = format_card_number(raw_card)

    card_num_lbl = tk.Label(
        card_frame,
        text=display_card,
        font=("Consolas", 16, "bold"),
        fg="#ffffff",
        bg="#11141d",
        pady=8
    )
    card_num_lbl.pack(anchor="w")

    holder_text = "Банк: Яндекс Банк (СБП)"
    tk.Label(
        card_frame,
        text=holder_text,
        font=("Segoe UI", 9, "bold"),
        fg="#8e97ad",
        bg="#11141d"
    ).pack(anchor="w")

    # Статус копирования
    copy_status_lbl = tk.Label(dlg, text="", font=("Segoe UI", 9, "bold"), fg="#00f09a", bg="#08090d")
    copy_status_lbl.pack(pady=(0, 4))

    def on_copy_card():
        clean_num = "".join(c for c in raw_card if c.isdigit()) or "2204311017900938"
        dlg.clipboard_clear()
        dlg.clipboard_append(clean_num)
        copy_status_lbl.config(text="✔ Номер карты Яндекс Банка скопирован в буфер обмена!")
        copy_btn.config(text="✔ Скопировано!", bg="#00c880")
        dlg.after(2500, lambda: (
            copy_status_lbl.config(text=""),
            copy_btn.config(text="Скопировать номер карты", bg="#ff3366")
        ))

    actions_frame = tk.Frame(dlg, bg="#08090d", padx=24)
    actions_frame.pack(fill=tk.X)

    copy_btn = tk.Button(
        actions_frame,
        text="Скопировать номер карты",
        font=("Segoe UI", 10, "bold"),
        fg="#ffffff",
        bg="#ff3366",
        activebackground="#e02454",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=18,
        pady=8,
        command=on_copy_card
    )
    copy_btn.pack(fill=tk.X)

    # Разделитель и кнопка закрытия
    sep = tk.Frame(dlg, bg="#181c26", height=1)
    sep.pack(fill=tk.X, padx=24, pady=(16, 12))

    footer = tk.Frame(dlg, bg="#08090d", padx=24)
    footer.pack(fill=tk.X)

    tk.Label(
        footer,
        text="Спасибо за поддержку развития проекта!",
        font=("Segoe UI", 8),
        fg="#596075",
        bg="#08090d"
    ).pack(side=tk.LEFT)

    close_btn = tk.Button(
        footer,
        text="Закрыть",
        font=("Segoe UI", 9, "bold"),
        fg="#090a0f",
        bg="#00e6a0",
        activebackground="#00c88c",
        relief="flat",
        cursor="hand2",
        padx=16,
        pady=5,
        command=dlg.destroy
    )
    close_btn.pack(side=tk.RIGHT)

    if is_standalone:
        dlg.mainloop()

def show_settings_dialog(on_saved_callback: Optional[Callable[[dict], None]] = None, apply_stage_callback: Optional[Callable[[int], None]] = None):
    """Главное окно настроек в глубокой черной теме (AMOLED Dark)."""
    root = tk.Tk()
    root.title("LAMZU Maya X — Настройки и реквизиты")
    root.geometry("560x660")
    root.resizable(False, False)
    root.configure(bg="#08090d")

    ico = get_icon_path()
    if ico:
        try:
            root.iconbitmap(ico)
        except Exception:
            pass

    enable_dark_title_bar(root)

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 280
    y = (root.winfo_screenheight() // 2) - 330
    root.geometry(f"560x660+{x}+{y}")

    cfg = load_config()

    # --- ШАПКА ОКНА ---
    header = tk.Frame(root, bg="#08090d")
    header.pack(fill=tk.X, padx=22, pady=(14, 8))

    title_frame = tk.Frame(header, bg="#08090d")
    title_frame.pack(fill=tk.X)

    tk.Label(
        title_frame,
        text="LAMZU Maya X Control",
        font=("Segoe UI", 14, "bold"),
        fg="#ffffff",
        bg="#08090d"
    ).pack(side=tk.LEFT)

    status_badge = tk.Label(
        title_frame,
        text=" 8K Dongle Active ",
        font=("Segoe UI", 8, "bold"),
        fg="#00f09a",
        bg="#0e241b",
        padx=7,
        pady=2
    )
    status_badge.pack(side=tk.RIGHT)

    tk.Label(
        header,
        text="Циклическое переключение частоты кнопкой снизу мыши и оптимизация отклика",
        font=("Segoe UI", 9),
        fg="#72798e",
        bg="#08090d"
    ).pack(anchor="w", pady=(2, 0))

    # Контейнер карточек
    content = tk.Frame(root, bg="#08090d")
    content.pack(fill=tk.BOTH, expand=True, padx=22, pady=(0, 6))

    # ==================== КАРТОЧКА 1: ЭТАП 1 ====================
    c1 = tk.Frame(content, bg="#0f1118", padx=12, pady=8, highlightbackground="#1d212e", highlightthickness=1)
    c1.pack(fill=tk.X, pady=(0, 6))

    c1_head = tk.Frame(c1, bg="#0f1118")
    c1_head.pack(fill=tk.X, pady=(0, 4))

    tk.Label(
        c1_head,
        text=" 1 ",
        font=("Segoe UI", 9, "bold"),
        fg="#090a0f",
        bg="#00f09a",
        padx=4,
        pady=1
    ).pack(side=tk.LEFT, padx=(0, 8))

    tk.Label(
        c1_head,
        text="1-е нажатие: Киберспортивный режим (High-Speed)",
        font=("Segoe UI", 9, "bold"),
        fg="#00f09a",
        bg="#0f1118"
    ).pack(side=tk.LEFT)

    s1_rate_var = tk.IntVar(value=cfg.get("stage1_rate", 2000))
    s1_opt = tk.Frame(c1, bg="#0f1118")
    s1_opt.pack(fill=tk.X)

    tk.Label(s1_opt, text="Частота опроса:", font=("Segoe UI", 9), fg="#939ba8", bg="#0f1118").pack(side=tk.LEFT, padx=(0, 10))
    for r in [1000, 2000, 4000, 8000]:
        tk.Radiobutton(
            s1_opt,
            text=f"{r} Гц",
            value=r,
            variable=s1_rate_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#0f1118",
            selectcolor="#06070a",
            activebackground="#0f1118",
            activeforeground="#00f09a",
            highlightthickness=0,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

    # ==================== КАРТОЧКА 2: ЭТАП 2 ====================
    c2 = tk.Frame(content, bg="#0f1118", padx=12, pady=8, highlightbackground="#1d212e", highlightthickness=1)
    c2.pack(fill=tk.X, pady=(0, 6))

    c2_head = tk.Frame(c2, bg="#0f1118")
    c2_head.pack(fill=tk.X, pady=(0, 4))

    tk.Label(
        c2_head,
        text=" 2 ",
        font=("Segoe UI", 9, "bold"),
        fg="#090a0f",
        bg="#00b4ff",
        padx=4,
        pady=1
    ).pack(side=tk.LEFT, padx=(0, 8))

    tk.Label(
        c2_head,
        text="2-е нажатие: Экстремальный режим (20K FPS)",
        font=("Segoe UI", 9, "bold"),
        fg="#00b4ff",
        bg="#0f1118"
    ).pack(side=tk.LEFT)

    s2_rate_var = tk.IntVar(value=cfg.get("stage2_rate", 4000))
    s2_opt = tk.Frame(c2, bg="#0f1118")
    s2_opt.pack(fill=tk.X)

    tk.Label(s2_opt, text="Частота опроса:", font=("Segoe UI", 9), fg="#939ba8", bg="#0f1118").pack(side=tk.LEFT, padx=(0, 10))
    for r in [2000, 4000, 8000]:
        tk.Radiobutton(
            s2_opt,
            text=f"{r} Гц",
            value=r,
            variable=s2_rate_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#0f1118",
            selectcolor="#06070a",
            activebackground="#0f1118",
            activeforeground="#00b4ff",
            highlightthickness=0,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

    # ==================== КАРТОЧКА 3: ЭТАП 3 ====================
    c3 = tk.Frame(content, bg="#0f1118", padx=12, pady=8, highlightbackground="#1d212e", highlightthickness=1)
    c3.pack(fill=tk.X, pady=(0, 6))

    c3_head = tk.Frame(c3, bg="#0f1118")
    c3_head.pack(fill=tk.X, pady=(0, 4))

    tk.Label(
        c3_head,
        text=" 3 ",
        font=("Segoe UI", 9, "bold"),
        fg="#ffffff",
        bg="#373c4d",
        padx=4,
        pady=1
    ).pack(side=tk.LEFT, padx=(0, 8))

    tk.Label(
        c3_head,
        text="3-е нажатие: Обычный режим (Выключение)",
        font=("Segoe UI", 9, "bold"),
        fg="#c9cfdf",
        bg="#0f1118"
    ).pack(side=tk.LEFT)

    s0_rate_var = tk.IntVar(value=cfg.get("stage0_rate", 1000))
    s0_opt = tk.Frame(c3, bg="#0f1118")
    s0_opt.pack(fill=tk.X)

    tk.Label(s0_opt, text="Частота опроса:", font=("Segoe UI", 9), fg="#939ba8", bg="#0f1118").pack(side=tk.LEFT, padx=(0, 10))
    for r in [500, 1000, 2000]:
        tk.Radiobutton(
            s0_opt,
            text=f"{r} Гц",
            value=r,
            variable=s0_rate_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#0f1118",
            selectcolor="#06070a",
            activebackground="#0f1118",
            activeforeground="#00f09a",
            highlightthickness=0,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

    # ==================== КАРТОЧКА 4: ОПТИМИЗАЦИЯ В ИГРАХ ====================
    c_perf = tk.Frame(content, bg="#0f1118", padx=12, pady=8, highlightbackground="#1d212e", highlightthickness=1)
    c_perf.pack(fill=tk.X, pady=(0, 6))

    tk.Label(
        c_perf,
        text="Оптимизация производительности и отклика",
        font=("Segoe UI", 9, "bold"),
        fg="#ffb82e",
        bg="#0f1118"
    ).pack(anchor="w", pady=(0, 2))

    pause_game_var = tk.BooleanVar(value=cfg.get("pause_in_game", True))
    tk.Checkbutton(
        c_perf,
        text="Отключать опрос в играх (0% задержек и нагрузки, авто-опрос при Alt-Tab)",
        variable=pause_game_var,
        font=("Segoe UI", 9),
        fg="#d8dde8",
        bg="#0f1118",
        selectcolor="#06070a",
        activebackground="#0f1118",
        activeforeground="#00f09a",
        highlightthickness=0,
        cursor="hand2"
    ).pack(anchor="w", pady=(1, 2))

    int_frame = tk.Frame(c_perf, bg="#0f1118")
    int_frame.pack(fill=tk.X, pady=(1, 2))

    tk.Label(int_frame, text="Интервал обновления:", font=("Segoe UI", 9), fg="#939ba8", bg="#0f1118").pack(side=tk.LEFT, padx=(0, 10))
    poll_int_var = tk.IntVar(value=cfg.get("poll_interval", 30))
    for sec in [30, 60, 120]:
        tk.Radiobutton(
            int_frame,
            text=f"{sec} сек",
            value=sec,
            variable=poll_int_var,
            font=("Segoe UI", 9),
            fg="#ffffff",
            bg="#0f1118",
            selectcolor="#06070a",
            activebackground="#0f1118",
            activeforeground="#00f09a",
            highlightthickness=0,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

    notify_var = tk.BooleanVar(value=cfg.get("notify_on_switch", True))
    tk.Checkbutton(
        c_perf,
        text="Всплывающее уведомление Windows при переключении режима",
        variable=notify_var,
        font=("Segoe UI", 9),
        fg="#d8dde8",
        bg="#0f1118",
        selectcolor="#06070a",
        activebackground="#0f1118",
        activeforeground="#00f09a",
        highlightthickness=0,
        cursor="hand2"
    ).pack(anchor="w", pady=(1, 0))

    # ==================== КАРТОЧКА 5: РЕКВИЗИТЫ ДЛЯ ДОНАТОВ ====================
    c_donate = tk.Frame(content, bg="#0f1118", padx=12, pady=8, highlightbackground="#1d212e", highlightthickness=1)
    c_donate.pack(fill=tk.X, pady=(0, 6))

    don_head = tk.Frame(c_donate, bg="#0f1118")
    don_head.pack(fill=tk.X, pady=(0, 4))

    tk.Label(
        don_head,
        text="Реквизиты для поддержки автора (Донаты)",
        font=("Segoe UI", 9, "bold"),
        fg="#ff3b69",
        bg="#0f1118"
    ).pack(side=tk.LEFT)

    tk.Label(
        don_head,
        text="Яндекс Банк (СБП)",
        font=("Segoe UI", 8, "bold"),
        fg="#00e6a0",
        bg="#0f1118"
    ).pack(side=tk.RIGHT)

    # 1. Поле: Номер карты
    f_card = tk.Frame(c_donate, bg="#0f1118")
    f_card.pack(fill=tk.X, pady=(2, 2))

    tk.Label(
        f_card,
        text="Номер вашей карты:",
        font=("Segoe UI", 8, "bold"),
        fg="#c8cedb",
        bg="#0f1118",
        width=18,
        anchor="w"
    ).pack(side=tk.LEFT)

    card_num_var = tk.StringVar(value=cfg.get("card_number", "2204 3110 1790 0938"))
    card_entry = tk.Entry(
        f_card,
        textvariable=card_num_var,
        font=("Consolas", 10, "bold"),
        fg="#00f09a",
        bg="#171924",
        insertbackground="#00f09a",
        relief="flat",
        highlightbackground="#242838",
        highlightthickness=1
    )
    card_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

    # 2. Поле: Банк / Получатель (СБП)
    f_holder = tk.Frame(c_donate, bg="#0f1118")
    f_holder.pack(fill=tk.X, pady=(2, 2))

    tk.Label(
        f_holder,
        text="Банк / Получатель:",
        font=("Segoe UI", 8, "bold"),
        fg="#c8cedb",
        bg="#0f1118",
        width=18,
        anchor="w"
    ).pack(side=tk.LEFT)

    holder_var = tk.StringVar(value=cfg.get("card_holder", "Яндекс Банк (СБП)"))
    holder_entry = tk.Entry(
        f_holder,
        textvariable=holder_var,
        font=("Segoe UI", 9),
        fg="#ffffff",
        bg="#171924",
        insertbackground="#00f09a",
        relief="flat",
        highlightbackground="#242838",
        highlightthickness=1
    )
    holder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

    # ==================== НИЖНЯЯ ПАНЕЛЬ ====================
    footer = tk.Frame(root, bg="#08090d")
    footer.pack(fill=tk.X, padx=22, pady=(0, 14))

    # Левая сторона: Донат и GitHub
    left_actions = tk.Frame(footer, bg="#08090d")
    left_actions.pack(side=tk.LEFT)

    def on_preview_donation():
        temp_cfg = dict(cfg)
        temp_cfg["card_number"] = card_num_var.get().strip()
        temp_cfg["card_holder"] = holder_var.get().strip()
        show_donation_dialog(root, temp_cfg)

    def on_github_click():
        u = cfg.get("github_url", DEFAULT_GITHUB_URL)
        webbrowser.open(u)

    donate_btn = tk.Button(
        left_actions,
        text="Поддержать автора",
        font=("Segoe UI", 9, "bold"),
        fg="#ffffff",
        bg="#ff3366",
        activebackground="#d62252",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=10,
        pady=5,
        command=on_preview_donation
    )
    donate_btn.pack(side=tk.LEFT, padx=(0, 8))

    github_btn = tk.Button(
        left_actions,
        text="GitHub",
        font=("Segoe UI", 9),
        fg="#b5bac9",
        bg="#161822",
        activebackground="#222636",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=10,
        pady=5,
        command=on_github_click
    )
    github_btn.pack(side=tk.LEFT)

    # Правая сторона: Сохранить и Отмена
    right_actions = tk.Frame(footer, bg="#08090d")
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
            "card_number": card_num_var.get().strip(),
            "card_holder": holder_var.get().strip(),
            "github_url": DEFAULT_GITHUB_URL
        })
        save_config(new_cfg)
        if on_saved_callback:
            on_saved_callback(new_cfg)
        root.destroy()

    cancel_btn = tk.Button(
        right_actions,
        text="Отмена",
        font=("Segoe UI", 9),
        fg="#858da3",
        bg="#161822",
        activebackground="#222636",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=12,
        pady=5,
        command=root.destroy
    )
    cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

    save_btn = tk.Button(
        right_actions,
        text="Сохранить",
        font=("Segoe UI", 9, "bold"),
        fg="#08090d",
        bg="#00f09a",
        activebackground="#00c880",
        relief="flat",
        cursor="hand2",
        padx=16,
        pady=5,
        command=on_save
    )
    save_btn.pack(side=tk.RIGHT)

    root.mainloop()

if __name__ == "__main__":
    show_settings_dialog()
