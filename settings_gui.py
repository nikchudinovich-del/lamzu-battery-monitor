"""
Модуль графического интерфейса LAMZU Control Center & Performance Suite.
Полный функционал оригинального ПО:
- Аппаратная оптимизация PAW3950 · 8K Nordic (Active Safe Profile)
- 20K FPS, High-Speed / Competition Mode, Motion Sync
- Debounce Time (0-20 мс)
- Сетка этапов DPI (1-5 этапов), выбор активного этапа, X-Y Split, RGB цвет каждого этапа
- Polling Rate (125, 250, 500, 1000, 2000, 4000, 8000 Гц)
- Ripple Control, Angle Snap, Angle Tune (-30°..+30°)
- Высота отрыва (LOD 0.7, 1.0, 2.0 мм), Тайм-аут сна (10с..30мин)
- Factory Reset
- Встроенный Polling Rate Tester в реальном времени (Live Hz Benchmark)
- Монитор здоровья батареи и оценка времени игры
- Game Optimizer (0% задержек в играх)
- Защищенные реквизиты автора Яндекс Банк (СБП) и кнопка GitHub
- АВТОМАТИЧЕСКОЕ ПРИМЕНЕНИЕ (AUTO-APPLY) на лету без кнопки «Сохранить»!
"""

import os
import sys
import time
import ctypes
import threading
import webbrowser
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser

from config import load_config, save_config, CARD_NUMBER, CARD_HOLDER, GITHUB_URL
from lamzu_battery import (
    get_mouse_polling_rate, set_mouse_polling_rate,
    get_mouse_hyper_mode, set_mouse_hyper_mode,
    get_mouse_tracking_mode, set_mouse_tracking_mode,
    get_mouse_lod, set_mouse_lod,
    get_mouse_sleep_time, set_mouse_sleep_time,
    get_mouse_dpi, set_mouse_dpi,
    get_mouse_led_color, set_mouse_led_color,
    get_mouse_debounce, set_mouse_debounce,
    get_mouse_motion_sync, set_mouse_motion_sync,
    get_mouse_ripple_control, set_mouse_ripple_control,
    get_mouse_angle_snap, set_mouse_angle_snap,
    get_mouse_angle_tune, set_mouse_angle_tune,
    get_mouse_dpi_detailed, set_mouse_full_dpi,
    factory_reset_mouse, query_aurora_battery, get_control_device_path
)

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

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def format_card_number(raw_num: str) -> str:
    clean = "".join(c for c in raw_num if c.isdigit())
    if not clean:
        clean = "2204311017900938"
    return " ".join(clean[i:i+4] for i in range(0, len(clean), 4))

def show_donation_dialog(parent=None, cfg: dict = None):
    """Окно поддержки / пожертвований с фиксированным номером карты Яндекс Банка автора и кнопкой копирования."""
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
        text="Если приложение полезно для вас, вы можете отблагодарить автора\nлюбой суммой по номеру карты через СБП:",
        font=("Segoe UI", 9),
        fg="#858da3",
        bg="#08090d",
        justify="left"
    ).pack(anchor="w", pady=(4, 0))

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

    raw_card = CARD_NUMBER
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

    holder_text = f"Банк: {CARD_HOLDER}"
    tk.Label(
        card_frame,
        text=holder_text,
        font=("Segoe UI", 9, "bold"),
        fg="#8e97ad",
        bg="#11141d"
    ).pack(anchor="w")

    copy_status_lbl = tk.Label(dlg, text="", font=("Segoe UI", 9, "bold"), fg="#00f09a", bg="#08090d")
    copy_status_lbl.pack(pady=(0, 4))

    def on_copy_card():
        clean_num = "".join(c for c in raw_card if c.isdigit())
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

class LamzuControlSuiteGUI:
    def __init__(self, root, on_change_callback: Optional[Callable[[str, Any], None]] = None):
        self.root = root
        self.on_change_callback = on_change_callback
        self.root.title("LAMZU Maya X — Control Center & Performance Suite")
        self.root.geometry("1060x720")
        self.root.minsize(980, 640)
        self.root.configure(bg="#07080c")

        enable_dark_title_bar(root)
        ico = get_icon_path()
        if ico:
            try:
                root.iconbitmap(ico)
            except Exception:
                pass

        self.cfg = load_config()
        self.active_tab = "performance"
        self._slider_job = None
        self._dpi_apply_timer = None
        self.stage_cards = []
        self.stage_val_labels = []
        self.stage_title_labels = []
        self.stage_top_rows = []

        # Состояние тестера герцовки
        self.tester_active = False
        self.hz_history = []
        self.last_mouse_time = None
        self.peak_hz = 0
        self.avg_hz = 0
        self.live_hz = 0

        # Считываем текущее аппаратное состояние с мыши
        self.read_live_mouse_state()

        # Построение UI
        self.create_header()
        self.create_navigation()

        self.container = tk.Frame(self.root, bg="#07080c")
        self.container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(6, 6))

        self.create_footer()

        # Показываем вкладку по умолчанию
        self.switch_tab("performance")

    def read_live_mouse_state(self):
        """Считывает текущие аппаратные параметры мыши."""
        try:
            dpi_info = get_mouse_dpi_detailed()
            if dpi_info:
                self.cfg["active_dpi_stage"] = dpi_info.get("active_index", self.cfg.get("active_dpi_stage", 2))
                self.cfg["xy_split"] = dpi_info.get("xy_split", False)
                if dpi_info.get("stages"):
                    self.cfg["dpi_stages"] = dpi_info["stages"]
                    self.cfg["stage_count"] = len(dpi_info["stages"])

            d_rate = get_mouse_polling_rate()
            if d_rate: self.cfg["polling_rate"] = d_rate
            else: self.cfg["polling_rate"] = 1000

            d_deb = get_mouse_debounce()
            if d_deb is not None: self.cfg["debounce_time"] = d_deb

            d_ms = get_mouse_motion_sync()
            if d_ms is not None: self.cfg["motion_sync"] = d_ms

            d_rc = get_mouse_ripple_control()
            if d_rc is not None: self.cfg["ripple_control"] = d_rc

            d_as = get_mouse_angle_snap()
            if d_as is not None: self.cfg["angle_snap"] = d_as

            d_at = get_mouse_angle_tune()
            if d_at is not None: self.cfg["angle_tune"] = d_at

            d_lod = get_mouse_lod()
            if d_lod is not None: self.cfg["mouse_lod"] = d_lod

            d_sl = get_mouse_sleep_time()
            if d_sl is not None: self.cfg["mouse_sleep_time"] = d_sl

            d_hyp = get_mouse_hyper_mode()
            if d_hyp is not None: self.cfg["hyper_mode"] = (d_hyp == 1)

            d_tr = get_mouse_tracking_mode()
            if d_tr is not None: self.cfg["tracking_20k"] = (d_tr == 1)

        except Exception:
            pass

    # =========================================================================
    # AUTO-APPLY SYSTEM (МГНОВЕННОЕ АВТОМАТИЧЕСКОЕ ПРИМЕНЕНИЕ)
    # =========================================================================
    def auto_apply(self, param_name: str, setter_func: Callable, *args):
        """Мгновенно применяет настройку к мыши в фоне и сохраняет конфиг."""
        def worker():
            try:
                setter_func(*args)
            except Exception as e:
                print(f"Error applying {param_name}: {e}")

        threading.Thread(target=worker, daemon=True).start()
        save_config(self.cfg)
        self.show_toast(f"✔ Применено: {param_name}")

        if self.on_change_callback:
            try:
                self.on_change_callback(param_name, args[0] if args else None)
            except Exception:
                pass

    def show_toast(self, text: str):
        now_time = datetime.now().strftime("%H:%M:%S")
        self.toast_lbl.config(text=f"[{now_time}] {text}", fg="#00f09a")
        self.root.after(3000, lambda: self.toast_lbl.config(text="Все изменения применяются мгновенно на лету", fg="#4e5870"))

    # =========================================================================
    # HEADER & NAVIGATION
    # =========================================================================
    def create_header(self):
        header = tk.Frame(self.root, bg="#07080c", padx=20, pady=12)
        header.pack(fill=tk.X)

        left = tk.Frame(header, bg="#07080c")
        left.pack(side=tk.LEFT)

        tk.Label(
            left,
            text="LAMZU",
            font=("Segoe UI", 16, "bold"),
            fg="#00f09a",
            bg="#07080c"
        ).pack(side=tk.LEFT)

        tk.Label(
            left,
            text=" Maya X Control Studio",
            font=("Segoe UI", 14),
            fg="#ffffff",
            bg="#07080c"
        ).pack(side=tk.LEFT)

        # Аппаратный статус сенсора
        hw_badge = tk.Frame(left, bg="#11141e", padx=10, pady=3, highlightbackground="#222838", highlightthickness=1)
        hw_badge.pack(side=tk.LEFT, padx=(18, 0))

        tk.Label(hw_badge, text="PAW3950 · 8K NORDIC", font=("Segoe UI", 8, "bold"), fg="#00f09a", bg="#11141e").pack(side=tk.LEFT)

        # Правая часть шапки: Батарея и Статус
        right = tk.Frame(header, bg="#07080c")
        right.pack(side=tk.RIGHT)

        # Плашка 20K FPS
        self.fps_badge = tk.Label(
            right,
            text=" 20K FPS: ВКЛ " if self.cfg.get("tracking_20k") else " 20K FPS: ВЫКЛ ",
            font=("Segoe UI", 8, "bold"),
            fg="#c084fc" if self.cfg.get("tracking_20k") else "#5a6275",
            bg="#1d152b" if self.cfg.get("tracking_20k") else "#12141c",
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.fps_badge.pack(side=tk.LEFT, padx=(0, 10))
        self.fps_badge.bind("<Button-1>", lambda e: self.toggle_20k_fps())

        # Плашка батареи
        self.bat_frame = tk.Frame(right, bg="#10131c", padx=10, pady=3, highlightbackground="#1e2433", highlightthickness=1)
        self.bat_frame.pack(side=tk.LEFT)

        self.bat_lbl = tk.Label(
            self.bat_frame,
            text="🔋 Батарея: ...%",
            font=("Segoe UI", 9, "bold"),
            fg="#00f09a",
            bg="#10131c"
        )
        self.bat_lbl.pack(side=tk.LEFT)

        self.update_header_battery()

    def update_header_battery(self):
        def worker():
            p = get_control_device_path()
            if p:
                res = query_aurora_battery(p)
                if res:
                    bat, st = res
                    st_str = "⚡ Зарядка" if st == 1 else "Разряжается"
                    color = "#00f09a" if bat > 25 else "#ff4d6d"
                    self.root.after(0, lambda: self.bat_lbl.config(
                        text=f"🔋 {bat}% ({st_str})",
                        fg=color
                    ))
        threading.Thread(target=worker, daemon=True).start()

    def toggle_20k_fps(self):
        cur = not self.cfg.get("tracking_20k", False)
        self.cfg["tracking_20k"] = cur
        self.fps_badge.config(
            text=" 20K FPS: ВКЛ " if cur else " 20K FPS: ВЫКЛ ",
            fg="#c084fc" if cur else "#5a6275",
            bg="#1d152b" if cur else "#12141c"
        )
        self.auto_apply("Режим 20K FPS", set_mouse_tracking_mode, cur)

    def create_navigation(self):
        nav = tk.Frame(self.root, bg="#07080c", padx=20)
        nav.pack(fill=tk.X)

        self.tab_buttons = {}
        tabs = [
            ("performance", "⚡ ПРОИЗВОДИТЕЛЬНОСТЬ (DPI & Частота)"),
            ("customize", "🖱 КАСТОМИЗАЦИЯ & СЕНСОР"),
            ("tools", "📈 ТЕСТЕР ГЕРЦОВКИ & ИНСТРУМЕНТЫ"),
            ("support", "💖 РАЗРАБОТЧИК & ДОНАТЫ")
        ]

        for tab_id, tab_title in tabs:
            btn = tk.Button(
                nav,
                text=tab_title,
                font=("Segoe UI", 9, "bold"),
                fg="#737e96",
                bg="#0d1017",
                activebackground="#141824",
                activeforeground="#ffffff",
                relief="flat",
                cursor="hand2",
                padx=16,
                pady=8,
                command=lambda t=tab_id: self.switch_tab(t)
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self.tab_buttons[tab_id] = btn

    def switch_tab(self, tab_id: str):
        self.active_tab = tab_id
        for t, btn in self.tab_buttons.items():
            if t == tab_id:
                btn.config(bg="#181e2e", fg="#00f09a", highlightbackground="#00f09a", highlightthickness=1)
            else:
                btn.config(bg="#0d1017", fg="#737e96", highlightthickness=0)

        for w in self.container.winfo_children():
            w.destroy()

        if tab_id == "performance":
            self.render_performance_tab()
        elif tab_id == "customize":
            self.render_customize_tab()
        elif tab_id == "tools":
            self.render_tools_tab()
        elif tab_id == "support":
            self.render_support_tab()

    def reload_all_tabs(self):
        self.read_live_mouse_state()
        self.switch_tab(self.active_tab)

    # =========================================================================
    # TAB 1: ПРОИЗВОДИТЕЛЬНОСТЬ (PERFORMANCE)
    # =========================================================================
    def render_performance_tab(self):
        panes = tk.Frame(self.container, bg="#07080c")
        panes.pack(fill=tk.BOTH, expand=True)

        left_col = tk.Frame(panes, bg="#07080c")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        right_col = tk.Frame(panes, bg="#07080c")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # --- КАРТОЧКА 1: ЧАСТОТА ОПРОСА (POLLING RATE) ---
        c_rate = tk.Frame(left_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_rate.pack(fill=tk.X, pady=(0, 10))

        tk.Label(c_rate, text="Частота опроса (Polling Rate)", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_rate, text="Частота обновления позиции мыши в секунду (Гц):", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        rates = [500, 1000, 2000, 4000, 8000]
        cur_rate = self.cfg.get("polling_rate", 1000)
        self.rate_var = tk.IntVar(value=cur_rate)

        r_row = tk.Frame(c_rate, bg="#0f121a")
        r_row.pack(fill=tk.X)

        for hz in rates:
            color = "#00f09a" if hz <= 1000 else ("#00b4ff" if hz <= 2000 else "#a855f7")
            btn = tk.Radiobutton(
                r_row,
                text=f"{hz} Гц",
                value=hz,
                variable=self.rate_var,
                font=("Segoe UI", 9, "bold"),
                fg="#ffffff",
                bg="#171b26",
                selectcolor=color,
                indicatoron=False,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
                command=self.on_rate_changed
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # --- КАРТОЧКА 2: СЕТКА ЭТАПОВ DPI ---
        c_dpi = tk.Frame(left_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_dpi.pack(fill=tk.BOTH, expand=True)

        dpi_head = tk.Frame(c_dpi, bg="#0f121a")
        dpi_head.pack(fill=tk.X, pady=(0, 6))

        tk.Label(dpi_head, text="Сетка этапов DPI", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(side=tk.LEFT)

        # Переключатель X-Y Split
        self.xy_split_var = tk.BooleanVar(value=self.cfg.get("xy_split", False))
        tk.Checkbutton(
            dpi_head,
            text="Раздельный X-Y DPI",
            variable=self.xy_split_var,
            font=("Segoe UI", 9),
            fg="#9aa3b5",
            bg="#0f121a",
            selectcolor="#07080c",
            activebackground="#0f121a",
            activeforeground="#00f09a",
            highlightthickness=0,
            cursor="hand2",
            command=self.on_xy_split_toggled
        ).pack(side=tk.RIGHT)

        stages = self.cfg.get("dpi_stages", [
            {"x": 800, "y": 800, "color": [255, 51, 102]},
            {"x": 1200, "y": 1200, "color": [0, 240, 154]},
            {"x": 1600, "y": 1600, "color": [0, 180, 255]},
            {"x": 2400, "y": 2400, "color": [168, 85, 247]},
            {"x": 3200, "y": 3200, "color": [255, 184, 46]}
        ])
        active_idx = self.cfg.get("active_dpi_stage", 2)

        # Карточки этапов
        self.stage_cards_frame = tk.Frame(c_dpi, bg="#0f121a")
        self.stage_cards_frame.pack(fill=tk.X, pady=(4, 10))

        self.stage_cards = []
        self.stage_val_labels = []
        self.stage_title_labels = []
        self.stage_top_rows = []
        for idx, s in enumerate(stages):
            is_active = (idx == active_idx)
            card = tk.Frame(
                self.stage_cards_frame,
                bg="#1c2130" if is_active else "#12151f",
                padx=8,
                pady=6,
                highlightbackground="#ff3366" if is_active else "#222738",
                highlightthickness=2 if is_active else 1,
                cursor="hand2"
            )
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
            self.stage_cards.append(card)

            top_row = tk.Frame(card, bg=card["bg"])
            top_row.pack(fill=tk.X)
            self.stage_top_rows.append(top_row)

            # Цветовой индикатор этапа
            c_rgb = s.get("color", [0, 240, 154])
            hex_c = rgb_to_hex(*c_rgb)
            swatch = tk.Label(top_row, text="  ", bg=hex_c, font=("Segoe UI", 4), cursor="hand2")
            swatch.pack(side=tk.LEFT)
            swatch.bind("<Button-1>", lambda e, i=idx: self.pick_stage_color(i))

            lbl_title = tk.Label(top_row, text=f" Этап {idx+1}", font=("Segoe UI", 8, "bold"), fg="#ffffff" if is_active else "#717a8e", bg=card["bg"])
            lbl_title.pack(side=tk.LEFT)
            self.stage_title_labels.append(lbl_title)

            dpi_val_str = f"{s['x']}" if not self.xy_split_var.get() else f"X:{s['x']}\nY:{s['y']}"
            val_lbl = tk.Label(card, text=dpi_val_str, font=("Segoe UI", 10, "bold"), fg="#ff3366" if is_active else "#b5bdcf", bg=card["bg"])
            val_lbl.pack(pady=(4, 0))
            self.stage_val_labels.append(val_lbl)

            card.bind("<Button-1>", lambda e, i=idx: self.select_dpi_stage(i))
            top_row.bind("<Button-1>", lambda e, i=idx: self.select_dpi_stage(i))
            lbl_title.bind("<Button-1>", lambda e, i=idx: self.select_dpi_stage(i))
            val_lbl.bind("<Button-1>", lambda e, i=idx: self.select_dpi_stage(i))

        # Ползунок регулировки DPI активного этапа
        cur_stage = stages[active_idx] if active_idx < len(stages) else stages[0]
        sl_box = tk.Frame(c_dpi, bg="#0f121a")
        sl_box.pack(fill=tk.X, pady=(6, 0))

        self.dpi_heading_lbl = tk.Label(
            sl_box,
            text=f"Регулировка DPI для активного этапа {active_idx + 1} ({cur_stage['x']} DPI):",
            font=("Segoe UI", 9, "bold"),
            fg="#e1e7f5",
            bg="#0f121a"
        )
        self.dpi_heading_lbl.pack(anchor="w")

        # X DPI Slider
        x_row = tk.Frame(sl_box, bg="#0f121a")
        x_row.pack(fill=tk.X, pady=(4, 2))
        tk.Label(x_row, text="X DPI:", font=("Segoe UI", 9, "bold"), fg="#ff3366", bg="#0f121a", width=6, anchor="w").pack(side=tk.LEFT)
        self.dpi_x_scale = ttk.Scale(
            x_row,
            from_=100,
            to=30000,
            value=cur_stage['x'],
            orient=tk.HORIZONTAL,
            command=self.on_x_slider_change
        )
        self.dpi_x_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self.dpi_x_lbl = tk.Label(x_row, text=f"{cur_stage['x']}", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#0f121a", width=6)
        self.dpi_x_lbl.pack(side=tk.RIGHT)
        self.dpi_x_scale.bind("<ButtonRelease-1>", lambda e: self.flush_dpi_apply_now())

        # Y DPI Slider (виден только при X-Y Split)
        self.y_row = tk.Frame(sl_box, bg="#0f121a")
        if self.xy_split_var.get():
            self.y_row.pack(fill=tk.X, pady=(2, 2))
        tk.Label(self.y_row, text="Y DPI:", font=("Segoe UI", 9, "bold"), fg="#00b4ff", bg="#0f121a", width=6, anchor="w").pack(side=tk.LEFT)
        self.dpi_y_scale = ttk.Scale(
            self.y_row,
            from_=100,
            to=30000,
            value=cur_stage['y'],
            orient=tk.HORIZONTAL,
            command=self.on_y_slider_change
        )
        self.dpi_y_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self.dpi_y_lbl = tk.Label(self.y_row, text=f"{cur_stage['y']}", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#0f121a", width=6)
        self.dpi_y_lbl.pack(side=tk.RIGHT)
        self.dpi_y_scale.bind("<ButtonRelease-1>", lambda e: self.flush_dpi_apply_now())

        # Быстрые пресеты
        presets_row = tk.Frame(c_dpi, bg="#0f121a")
        presets_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(presets_row, text="Пресеты:", font=("Segoe UI", 8), fg="#717a8e", bg="#0f121a").pack(side=tk.LEFT, padx=(0, 6))
        for p_val in [400, 800, 1200, 1600, 2400, 3200, 6400]:
            btn = tk.Button(
                presets_row, text=f"{p_val}", font=("Segoe UI", 8),
                fg="#b5bdcf", bg="#191c26", activebackground="#2a3042", relief="flat", padx=6, pady=1, cursor="hand2",
                command=lambda v=p_val: self.apply_quick_preset_dpi(v)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # --- КАРТОЧКА 3: ВЫСОТА ОТРЫВА (LOD) & ВРЕМЯ СНА ---
        c_lod_sleep = tk.Frame(right_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_lod_sleep.pack(fill=tk.X, pady=(0, 10))

        # LOD
        tk.Label(c_lod_sleep, text="Высота отрыва (Lift-off Distance)", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_lod_sleep, text="Расстояние от коврика, на котором сенсор перестает считывать:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 6))

        lod_row = tk.Frame(c_lod_sleep, bg="#0f121a")
        lod_row.pack(fill=tk.X, pady=(0, 12))
        self.lod_var = tk.DoubleVar(value=self.cfg.get("mouse_lod", 1.0))
        for lod_v, lod_name in [(0.7, "0.7 мм (Low)"), (1.0, "1.0 мм (Default)"), (2.0, "2.0 мм (High)")]:
            tk.Radiobutton(
                lod_row, text=lod_name, value=lod_v, variable=self.lod_var,
                font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#171b26", selectcolor="#00f09a",
                indicatoron=False, relief="flat", cursor="hand2", padx=10, pady=5,
                command=self.on_lod_changed
            ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Сон
        tk.Label(c_lod_sleep, text="Тайм-аут спящего режима", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_lod_sleep, text="Время бездействия мыши до перехода в режим энергосбережения:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 6))

        sleep_row = tk.Frame(c_lod_sleep, bg="#0f121a")
        sleep_row.pack(fill=tk.X)
        self.sleep_var = tk.IntVar(value=self.cfg.get("mouse_sleep_time", 60))
        for sec_v, sec_name in [(10, "10 с"), (30, "30 с"), (60, "1 мин"), (300, "5 мин"), (600, "10 мин"), (1800, "30 мин")]:
            tk.Radiobutton(
                sleep_row, text=sec_name, value=sec_v, variable=self.sleep_var,
                font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#171b26", selectcolor="#00b4ff",
                indicatoron=False, relief="flat", cursor="hand2", padx=4, pady=4,
                command=self.on_sleep_changed
            ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # --- КАРТОЧКА 4: ТОЧНЫЕ НАСТРОЙКИ СЕНСОРА (ANGLE SNAP, RIPPLE, TUNE) ---
        c_sens = tk.Frame(right_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_sens.pack(fill=tk.BOTH, expand=True)

        tk.Label(c_sens, text="Аппаратная коррекция сенсора", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w", pady=(0, 6))

        # Checkboxes
        self.ripple_var = tk.BooleanVar(value=self.cfg.get("ripple_control", False))
        tk.Checkbutton(
            c_sens,
            text="Ripple Control (сглаживание микро-джиттера на высоких DPI >5000)",
            variable=self.ripple_var,
            font=("Segoe UI", 9), fg="#e1e6f2", bg="#0f121a", selectcolor="#07080c",
            activebackground="#0f121a", activeforeground="#00f09a", highlightthickness=0, cursor="hand2",
            command=self.on_ripple_changed
        ).pack(anchor="w", pady=2)

        self.snap_var = tk.BooleanVar(value=self.cfg.get("angle_snap", False))
        tk.Checkbutton(
            c_sens,
            text="Angle Snap (аппаратная доводка прямых линий)",
            variable=self.snap_var,
            font=("Segoe UI", 9), fg="#e1e6f2", bg="#0f121a", selectcolor="#07080c",
            activebackground="#0f121a", activeforeground="#00f09a", highlightthickness=0, cursor="hand2",
            command=self.on_snap_changed
        ).pack(anchor="w", pady=2)

        # Angle Tune (-30..+30)
        tune_box = tk.Frame(c_sens, bg="#0f121a")
        tune_box.pack(fill=tk.X, pady=(10, 0))

        tk.Label(tune_box, text="Angle Tune (угол доворота сенсора):", font=("Segoe UI", 9, "bold"), fg="#e1e6f2", bg="#0f121a").pack(anchor="w")
        tk.Label(tune_box, text="Компенсирует наклонный хват мыши в руке (-30° до +30°):", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 4))

        t_row = tk.Frame(tune_box, bg="#0f121a")
        t_row.pack(fill=tk.X)

        self.angle_scale = ttk.Scale(t_row, from_=-30, to=30, value=self.cfg.get("angle_tune", 0), orient=tk.HORIZONTAL)
        self.angle_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.angle_lbl = tk.Label(t_row, text=f"{self.cfg.get('angle_tune', 0)}°", font=("Segoe UI", 9, "bold"), fg="#00f09a", bg="#0f121a", width=4)
        self.angle_lbl.pack(side=tk.LEFT)

        reset_angle_btn = tk.Button(
            t_row, text="0° Сброс", font=("Segoe UI", 8),
            fg="#b5bdcf", bg="#191c26", activebackground="#2a3042", relief="flat", padx=6, pady=2, cursor="hand2",
            command=self.reset_angle_tune
        )
        reset_angle_btn.pack(side=tk.RIGHT)

        self.angle_scale.bind("<Motion>", lambda e: self.angle_lbl.config(text=f"{int(round(self.angle_scale.get()))}°"))
        self.angle_scale.bind("<ButtonRelease-1>", self.on_angle_tune_release)

    # Handlers for Tab 1
    def on_rate_changed(self):
        hz = self.rate_var.get()
        self.cfg["polling_rate"] = hz
        self.auto_apply(f"Частота {hz} Гц", set_mouse_polling_rate, hz)

    def on_xy_split_toggled(self):
        split = self.xy_split_var.get()
        self.cfg["xy_split"] = split
        self.save_and_sync_dpi_stages(f"X-Y Split: {'ВКЛ' if split else 'ВЫКЛ'}")
        self.switch_tab("performance")

    def on_x_slider_change(self, val_str):
        val = int(round(float(val_str) / 50.0) * 50)
        val = max(100, min(30000, val))
        self.dpi_x_lbl.config(text=str(val))
        act_idx = self.cfg.get("active_dpi_stage", 0)
        stages = self.cfg.get("dpi_stages", [])
        if act_idx < len(stages):
            stages[act_idx]["x"] = val
            if not self.xy_split_var.get():
                stages[act_idx]["y"] = val
                self.dpi_y_scale.set(val)
                self.dpi_y_lbl.config(text=str(val))
        self.cfg["current_dpi"] = val

        if hasattr(self, "dpi_heading_lbl"):
            self.dpi_heading_lbl.config(text=f"Регулировка DPI для активного этапа {act_idx + 1} ({val} DPI):")
        if act_idx < len(self.stage_val_labels):
            txt = str(val) if not self.xy_split_var.get() else f"X:{val}\nY:{stages[act_idx].get('y', val)}"
            self.stage_val_labels[act_idx].config(text=txt)

        if self._dpi_apply_timer:
            self.root.after_cancel(self._dpi_apply_timer)
        self._dpi_apply_timer = self.root.after(80, self.flush_dpi_apply_now)

    def on_y_slider_change(self, val_str):
        val = int(round(float(val_str) / 50.0) * 50)
        val = max(100, min(30000, val))
        self.dpi_y_lbl.config(text=str(val))
        act_idx = self.cfg.get("active_dpi_stage", 0)
        stages = self.cfg.get("dpi_stages", [])
        if act_idx < len(stages):
            stages[act_idx]["y"] = val
        if act_idx < len(self.stage_val_labels):
            self.stage_val_labels[act_idx].config(text=f"X:{stages[act_idx].get('x', val)}\nY:{val}")

        if self._dpi_apply_timer:
            self.root.after_cancel(self._dpi_apply_timer)
        self._dpi_apply_timer = self.root.after(80, self.flush_dpi_apply_now)

    def flush_dpi_apply_now(self):
        if self._dpi_apply_timer:
            self.root.after_cancel(self._dpi_apply_timer)
            self._dpi_apply_timer = None
        stages = self.cfg.get("dpi_stages", [])
        act_idx = self.cfg.get("active_dpi_stage", 0)
        split = self.xy_split_var.get()
        cur_val = self.cfg.get("current_dpi", 800)
        self.auto_apply(f"DPI {cur_val}", set_mouse_full_dpi, stages, act_idx, split)

    def select_dpi_stage(self, stage_idx: int):
        stages = self.cfg.get("dpi_stages", [])
        if stage_idx >= len(stages):
            return
        self.cfg["active_dpi_stage"] = stage_idx
        cur_x = stages[stage_idx]["x"]
        cur_y = stages[stage_idx].get("y", cur_x)
        self.cfg["current_dpi"] = cur_x

        # Обновляем визуальное выделение карточек без мерцания и перерисовки всей вкладки
        for idx, card in enumerate(self.stage_cards):
            is_act = (idx == stage_idx)
            card.config(
                bg="#1c2130" if is_act else "#12151f",
                highlightbackground="#ff3366" if is_act else "#222738",
                highlightthickness=2 if is_act else 1
            )
            if idx < len(self.stage_top_rows):
                self.stage_top_rows[idx].config(bg="#1c2130" if is_act else "#12151f")
            if idx < len(self.stage_title_labels):
                self.stage_title_labels[idx].config(
                    bg="#1c2130" if is_act else "#12151f",
                    fg="#ffffff" if is_act else "#717a8e"
                )
            if idx < len(self.stage_val_labels):
                self.stage_val_labels[idx].config(
                    bg="#1c2130" if is_act else "#12151f",
                    fg="#ff3366" if is_act else "#b5bdcf"
                )

        if hasattr(self, "dpi_heading_lbl"):
            self.dpi_heading_lbl.config(text=f"Регулировка DPI для активного этапа {stage_idx + 1} ({cur_x} DPI):")
        if hasattr(self, "dpi_x_scale"):
            self.dpi_x_scale.set(cur_x)
            self.dpi_x_lbl.config(text=str(cur_x))
        if hasattr(self, "dpi_y_scale"):
            self.dpi_y_scale.set(cur_y)
            self.dpi_y_lbl.config(text=str(cur_y))

        split = self.xy_split_var.get()
        self.auto_apply(f"Этап {stage_idx + 1} ({cur_x} DPI)", set_mouse_full_dpi, stages, stage_idx, split)

    def apply_quick_preset_dpi(self, dpi_val: int):
        act_idx = self.cfg.get("active_dpi_stage", 0)
        stages = self.cfg.get("dpi_stages", [])
        if act_idx < len(stages):
            stages[act_idx]["x"] = dpi_val
            if not self.xy_split_var.get():
                stages[act_idx]["y"] = dpi_val
        self.cfg["current_dpi"] = dpi_val

        if hasattr(self, "dpi_heading_lbl"):
            self.dpi_heading_lbl.config(text=f"Регулировка DPI для активного этапа {act_idx + 1} ({dpi_val} DPI):")
        if hasattr(self, "dpi_x_scale"):
            self.dpi_x_scale.set(dpi_val)
            self.dpi_x_lbl.config(text=str(dpi_val))
        if hasattr(self, "dpi_y_scale") and not self.xy_split_var.get():
            self.dpi_y_scale.set(dpi_val)
            self.dpi_y_lbl.config(text=str(dpi_val))

        if act_idx < len(self.stage_val_labels):
            txt = str(dpi_val) if not self.xy_split_var.get() else f"X:{dpi_val}\nY:{stages[act_idx].get('y', dpi_val)}"
            self.stage_val_labels[act_idx].config(text=txt)

        split = self.xy_split_var.get()
        self.auto_apply(f"DPI: {dpi_val}", set_mouse_full_dpi, stages, act_idx, split)

    def pick_stage_color(self, stage_idx: int):
        stages = self.cfg.get("dpi_stages", [])
        if stage_idx >= len(stages): return
        cur_c = stages[stage_idx].get("color", [0, 240, 154])
        initial_hex = rgb_to_hex(*cur_c)
        chosen = colorchooser.askcolor(initial_hex, title=f"Цвет подсветки этапа {stage_idx + 1}")
        if chosen and chosen[0]:
            rgb = [int(chosen[0][0]), int(chosen[0][1]), int(chosen[0][2])]
            stages[stage_idx]["color"] = rgb
            self.save_and_sync_dpi_stages(f"Цвет этапа {stage_idx + 1}")
            self.switch_tab("performance")

    def save_and_sync_dpi_stages(self, desc: str):
        stages = self.cfg.get("dpi_stages", [])
        act_idx = self.cfg.get("active_dpi_stage", 0)
        split = self.cfg.get("xy_split", False)
        self.auto_apply(desc, set_mouse_full_dpi, stages, act_idx, split)

    def on_lod_changed(self):
        lod = self.lod_var.get()
        self.cfg["mouse_lod"] = lod
        self.auto_apply(f"LOD {lod} мм", set_mouse_lod, lod)

    def on_sleep_changed(self):
        sec = self.sleep_var.get()
        self.cfg["mouse_sleep_time"] = sec
        lbl = f"{sec} с" if sec < 60 else f"{sec // 60} мин"
        self.auto_apply(f"Время сна: {lbl}", set_mouse_sleep_time, sec)

    def on_ripple_changed(self):
        val = self.ripple_var.get()
        self.cfg["ripple_control"] = val
        self.auto_apply(f"Ripple Control: {'ВКЛ' if val else 'ВЫКЛ'}", set_mouse_ripple_control, val)

    def on_snap_changed(self):
        val = self.snap_var.get()
        self.cfg["angle_snap"] = val
        self.auto_apply(f"Angle Snap: {'ВКЛ' if val else 'ВЫКЛ'}", set_mouse_angle_snap, val)

    def reset_angle_tune(self):
        self.angle_scale.set(0)
        self.angle_lbl.config(text="0°")
        self.cfg["angle_tune"] = 0
        self.auto_apply("Angle Tune: 0°", set_mouse_angle_tune, 0)

    def on_angle_tune_release(self, e):
        angle = int(round(self.angle_scale.get()))
        self.angle_lbl.config(text=f"{angle}°")
        self.cfg["angle_tune"] = angle
        self.auto_apply(f"Angle Tune: {angle}°", set_mouse_angle_tune, angle)

    # =========================================================================
    # TAB 2: КАСТОМИЗАЦИЯ & СЕНСОР (CUSTOMIZE)
    # =========================================================================
    def render_customize_tab(self):
        panes = tk.Frame(self.container, bg="#07080c")
        panes.pack(fill=tk.BOTH, expand=True)

        left_col = tk.Frame(panes, bg="#07080c")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        right_col = tk.Frame(panes, bg="#07080c")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # --- КАРТОЧКА 1: КИБЕРСПОРТИВНЫЕ РЕЖИМЫ ---
        c_modes = tk.Frame(left_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_modes.pack(fill=tk.X, pady=(0, 10))

        tk.Label(c_modes, text="Режимы производительности сенсора", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_modes, text="Аппаратные режимы контроллера Nordic и сенсора PixArt 3950:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        # High-Speed / Competition Mode
        self.hyp_var = tk.BooleanVar(value=self.cfg.get("hyper_mode", False))
        tk.Checkbutton(
            c_modes,
            text="👑 High-Speed / Competition Mode (максимальный отклик радиоканала)",
            variable=self.hyp_var,
            font=("Segoe UI", 9, "bold"), fg="#00f09a", bg="#0f121a", selectcolor="#07080c",
            activebackground="#0f121a", activeforeground="#00f09a", highlightthickness=0, cursor="hand2",
            command=self.on_hyper_toggled
        ).pack(anchor="w", pady=4)

        # 20K FPS Mode
        self.tr_var = tk.BooleanVar(value=self.cfg.get("tracking_20k", False))
        tk.Checkbutton(
            c_modes,
            text="⚡ 20K FPS Mode (высокочастотное считывание матрицы сенсора)",
            variable=self.tr_var,
            font=("Segoe UI", 9, "bold"), fg="#c084fc", bg="#0f121a", selectcolor="#07080c",
            activebackground="#0f121a", activeforeground="#c084fc", highlightthickness=0, cursor="hand2",
            command=self.on_20k_toggled
        ).pack(anchor="w", pady=4)

        # Motion Sync
        self.ms_var = tk.BooleanVar(value=self.cfg.get("motion_sync", True))
        tk.Checkbutton(
            c_modes,
            text="🔄 Motion Sync (аппаратная синхронизация пакетов с USB SOF)",
            variable=self.ms_var,
            font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#0f121a", selectcolor="#07080c",
            activebackground="#0f121a", activeforeground="#38bdf8", highlightthickness=0, cursor="hand2",
            command=self.on_motion_sync_toggled
        ).pack(anchor="w", pady=4)

        # --- КАРТОЧКА 2: DEBOUNCE TIME ---
        c_deb = tk.Frame(left_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_deb.pack(fill=tk.BOTH, expand=True)

        tk.Label(c_deb, text="Задержка защиты от дабл-клика (Debounce Time)", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_deb, text="Минимальное время устранения дребезга контактов микропереключателей:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        deb_cur = self.cfg.get("debounce_time", 0)
        self.deb_lbl = tk.Label(c_deb, text=f"{deb_cur} мс", font=("Segoe UI", 18, "bold"), fg="#00f09a" if deb_cur == 0 else "#ffffff", bg="#0f121a")
        self.deb_lbl.pack(pady=4)

        # Stepper buttons
        deb_row = tk.Frame(c_deb, bg="#0f121a")
        deb_row.pack(fill=tk.X, pady=(4, 8))

        deb_presets = [0, 1, 2, 4, 8, 12, 16, 20]
        for d_val in deb_presets:
            btn = tk.Button(
                deb_row, text=f"{d_val}мс", font=("Segoe UI", 8, "bold"),
                fg="#ffffff" if d_val == deb_cur else "#838ea6",
                bg="#1a2030" if d_val == deb_cur else "#131620",
                activebackground="#2a3044", relief="flat", padx=5, pady=4, cursor="hand2",
                command=lambda v=d_val: self.apply_debounce(v)
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # --- КАРТОЧКА 3: ЦВЕТ СВЕТОДИОДА МЫШИ (LED RGB) ---
        c_led = tk.Frame(right_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_led.pack(fill=tk.X, pady=(0, 10))

        tk.Label(c_led, text="Цвет индикатора мыши (LED RGB)", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_led, text="Цвет светодиодного индикатора на корпусе мыши:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        cur_c = tuple(self.cfg.get("led_color", [0, 240, 154]))
        hex_cur = rgb_to_hex(*cur_c)

        led_preview_row = tk.Frame(c_led, bg="#0f121a")
        led_preview_row.pack(fill=tk.X, pady=(2, 8))

        self.led_swatch = tk.Label(led_preview_row, text="       ", bg=hex_cur, relief="flat", padx=10, pady=4)
        self.led_swatch.pack(side=tk.LEFT, padx=(0, 10))

        custom_btn = tk.Button(
            led_preview_row, text="🎨 Выбрать свой оттенок...", font=("Segoe UI", 9, "bold"),
            fg="#ffffff", bg="#1f2638", activebackground="#2c364e", relief="flat", padx=12, pady=4, cursor="hand2",
            command=self.on_pick_custom_led
        )
        custom_btn.pack(side=tk.LEFT)

        # Готовые пресеты цветов
        led_row = tk.Frame(c_led, bg="#0f121a")
        led_row.pack(fill=tk.X)

        presets = [
            ("Изумруд", 0, 240, 154),
            ("Циан", 0, 180, 255),
            ("Фиолет", 168, 85, 247),
            ("Красный", 255, 51, 102),
            ("Янтарь", 255, 184, 46),
            ("Белый", 255, 255, 255)
        ]
        for name, r, g, b in presets:
            b_hex = rgb_to_hex(r, g, b)
            btn = tk.Button(
                led_row, text=name, font=("Segoe UI", 8),
                fg="#000000" if (r+g+b)>450 else "#ffffff",
                bg=b_hex, activebackground=b_hex, relief="flat", padx=6, pady=2, cursor="hand2",
                command=lambda vr=r, vg=g, vb=b: self.apply_led_preset(vr, vg, vb)
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # --- КАРТОЧКА 4: НАЗНАЧЕНИЕ КНОПОК И СБРОС ---
        c_btns = tk.Frame(right_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_btns.pack(fill=tk.BOTH, expand=True)

        tk.Label(c_btns, text="Кнопки мыши & Заводской сброс", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_btns, text="Текущая раскладка физических кнопок LAMZU Maya X:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        btn_grid = tk.Frame(c_btns, bg="#0f121a")
        btn_grid.pack(fill=tk.X, pady=(0, 10))

        labels = [
            ("Кнопка 1 (Left):", "Левый клик (Left Click)"),
            ("Кнопка 2 (Right):", "Правый клик (Right Click)"),
            ("Кнопка 3 (Middle):", "Колёсико мыши (Wheel Click)"),
            ("Кнопка 4 (Forward):", "Вперёд (Browser Forward)"),
            ("Кнопка 5 (Back):", "Назад (Browser Back)"),
            ("Кнопка 6 (Bottom):", "3-этапный переключатель герцовки")
        ]
        for k_lbl, v_lbl in labels:
            row = tk.Frame(btn_grid, bg="#0f121a")
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=k_lbl, font=("Segoe UI", 8, "bold"), fg="#717a8e", bg="#0f121a", width=16, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=v_lbl, font=("Segoe UI", 8), fg="#b5bdcf", bg="#0f121a").pack(side=tk.LEFT)

        # Кнопка Factory Reset
        reset_frame = tk.Frame(c_btns, bg="#0f121a")
        reset_frame.pack(fill=tk.X, pady=(8, 0))

        factory_btn = tk.Button(
            reset_frame,
            text="🔄 Заводской сброс мыши (Factory Reset)",
            font=("Segoe UI", 9, "bold"),
            fg="#ff4d6d",
            bg="#211218",
            activebackground="#331922",
            activeforeground="#ff4d6d",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.on_factory_reset_click
        )
        factory_btn.pack(fill=tk.X)

    # Handlers for Tab 2
    def on_hyper_toggled(self):
        val = self.hyp_var.get()
        self.cfg["hyper_mode"] = val
        self.auto_apply(f"High-Speed Mode: {'ВКЛ' if val else 'ВЫКЛ'}", set_mouse_hyper_mode, val)

    def on_20k_toggled(self):
        val = self.tr_var.get()
        self.cfg["tracking_20k"] = val
        self.fps_badge.config(
            text=" 20K FPS: ВКЛ " if val else " 20K FPS: ВЫКЛ ",
            fg="#c084fc" if val else "#5a6275",
            bg="#1d152b" if val else "#12141c"
        )
        self.auto_apply(f"20K FPS Mode: {'ВКЛ' if val else 'ВЫКЛ'}", set_mouse_tracking_mode, val)

    def on_motion_sync_toggled(self):
        val = self.ms_var.get()
        self.cfg["motion_sync"] = val
        self.auto_apply(f"Motion Sync: {'ВКЛ' if val else 'ВЫКЛ'}", set_mouse_motion_sync, val)

    def apply_debounce(self, ms: int):
        self.cfg["debounce_time"] = ms
        self.deb_lbl.config(text=f"{ms} мс", fg="#00f09a" if ms == 0 else "#ffffff")
        self.auto_apply(f"Debounce: {ms} мс", set_mouse_debounce, ms)
        self.switch_tab("customize")

    def on_pick_custom_led(self):
        cur_c = tuple(self.cfg.get("led_color", [0, 240, 154]))
        initial_hex = rgb_to_hex(*cur_c)
        chosen = colorchooser.askcolor(initial_hex, title="Выберите цвет подсветки мыши")
        if chosen and chosen[0]:
            r, g, b = int(chosen[0][0]), int(chosen[0][1]), int(chosen[0][2])
            self.apply_led_preset(r, g, b)

    def apply_led_preset(self, r: int, g: int, b: int):
        self.cfg["led_color"] = [r, g, b]
        hex_c = rgb_to_hex(r, g, b)
        self.led_swatch.config(bg=hex_c)
        self.auto_apply("Цвет светодиода", set_mouse_led_color, r, g, b)

    def on_factory_reset_click(self):
        if messagebox.askyesno("Заводской сброс", "Сбросить все аппаратные параметры мыши LAMZU до заводских настроек?"):
            self.auto_apply("Заводской сброс", factory_reset_mouse)
            self.root.after(500, self.reload_all_tabs)

    # =========================================================================
    # TAB 3: ТЕСТЕР ГЕРЦОВКИ & ИНСТРУМЕНТЫ (TOOLS & TESTER)
    # =========================================================================
    def render_tools_tab(self):
        panes = tk.Frame(self.container, bg="#07080c")
        panes.pack(fill=tk.BOTH, expand=True)

        left_col = tk.Frame(panes, bg="#07080c")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        right_col = tk.Frame(panes, bg="#07080c")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # --- КАРТОЧКА 1: POLLING RATE TESTER (LIVE HZ BENCHMARK) ---
        c_test = tk.Frame(left_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_test.pack(fill=tk.BOTH, expand=True)

        tk.Label(c_test, text="⚡ Тестер частоты опроса (Live Polling Rate Tester)", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_test, text="Двигайте курсор мыши внутри поля ниже, чтобы измерить реальную герцовку в реальном времени:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        # Цифровые показатели
        stats_row = tk.Frame(c_test, bg="#0f121a")
        stats_row.pack(fill=tk.X, pady=(0, 8))

        # Текущая
        f_cur = tk.Frame(stats_row, bg="#141824", padx=10, pady=6)
        f_cur.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Label(f_cur, text="ТЕКУЩАЯ:", font=("Segoe UI", 7, "bold"), fg="#6e788e", bg="#141824").pack()
        self.lbl_live_hz = tk.Label(f_cur, text="0 Гц", font=("Segoe UI", 16, "bold"), fg="#00f09a", bg="#141824")
        self.lbl_live_hz.pack()

        # Пиковая
        f_peak = tk.Frame(stats_row, bg="#141824", padx=10, pady=6)
        f_peak.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Label(f_peak, text="ПИКОВАЯ:", font=("Segoe UI", 7, "bold"), fg="#6e788e", bg="#141824").pack()
        self.lbl_peak_hz = tk.Label(f_peak, text="0 Гц", font=("Segoe UI", 16, "bold"), fg="#00b4ff", bg="#141824")
        self.lbl_peak_hz.pack()

        # Средняя
        f_avg = tk.Frame(stats_row, bg="#141824", padx=10, pady=6)
        f_avg.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Label(f_avg, text="СРЕДНЯЯ:", font=("Segoe UI", 7, "bold"), fg="#6e788e", bg="#141824").pack()
        self.lbl_avg_hz = tk.Label(f_avg, text="0 Гц", font=("Segoe UI", 16, "bold"), fg="#c084fc", bg="#141824")
        self.lbl_avg_hz.pack()

        # Интерактивный холст
        self.test_canvas = tk.Canvas(c_test, bg="#08090f", highlightbackground="#22283a", highlightthickness=1, height=180)
        self.test_canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.test_canvas.create_text(
            220, 90,
            text="🎯 ДВИГАЙТЕ МЫШЬ ЗДЕСЬ ДЛЯ ТЕСТА ГЕРЦОВКИ",
            fill="#3e475c",
            font=("Segoe UI", 10, "bold"),
            tags="hint"
        )

        self.test_canvas.bind("<Motion>", self.on_tester_mouse_move)

        reset_test_btn = tk.Button(
            c_test, text="Сбросить показатели тестера", font=("Segoe UI", 8),
            fg="#9aa4b8", bg="#161924", activebackground="#222838", relief="flat", padx=10, pady=3, cursor="hand2",
            command=self.reset_tester
        )
        reset_test_btn.pack(anchor="e")

        # --- КАРТОЧКА 2: БАТАРЕЯ & ЗДОРОВЬЕ ---
        c_bat = tk.Frame(right_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_bat.pack(fill=tk.X, pady=(0, 10))

        tk.Label(c_bat, text="🔋 Монитор батареи и автономность", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_bat, text="Расчет примерного времени работы аккумулятора при текущем уровне заряда:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        bat_grid = tk.Frame(c_bat, bg="#0f121a")
        bat_grid.pack(fill=tk.X)

        estimates = [
            ("В режиме 1000 Гц:", "~ 50-70 часов игры"),
            ("В режиме 2000 Гц:", "~ 28-35 часов игры"),
            ("В режиме 4000 Гц:", "~ 16-20 часов игры"),
            ("В режиме 8000 Гц:", "~ 8-10 часов игры")
        ]
        for mode_title, est_val in estimates:
            row = tk.Frame(bat_grid, bg="#0f121a")
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=mode_title, font=("Segoe UI", 8, "bold"), fg="#788298", bg="#0f121a", width=18, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=est_val, font=("Segoe UI", 8), fg="#00f09a", bg="#0f121a").pack(side=tk.LEFT)

        # --- КАРТОЧКА 3: GAME OPTIMIZER & УВЕДОМЛЕНИЯ ---
        c_opt = tk.Frame(right_col, bg="#0f121a", padx=16, pady=14, highlightbackground="#1a202e", highlightthickness=1)
        c_opt.pack(fill=tk.BOTH, expand=True)

        tk.Label(c_opt, text="Оптимизация производительности в играх", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#0f121a").pack(anchor="w")
        tk.Label(c_opt, text="Исключает любые задержки ввода во время игровых сессий:", font=("Segoe UI", 8), fg="#6d768a", bg="#0f121a").pack(anchor="w", pady=(1, 8))

        self.pause_game_var = tk.BooleanVar(value=self.cfg.get("pause_in_game", True))
        tk.Checkbutton(
            c_opt,
            text="Отключать опрос в играх (0% задержек и нагрузки, авто-опрос при Alt-Tab)",
            variable=self.pause_game_var,
            font=("Segoe UI", 9), fg="#d8dde8", bg="#0f121a", selectcolor="#07080c",
            activebackground="#0f121a", activeforeground="#00f09a", highlightthickness=0, cursor="hand2",
            command=self.on_pause_game_toggled
        ).pack(anchor="w", pady=2)

        self.notif_var = tk.BooleanVar(value=self.cfg.get("notify_on_switch", True))
        tk.Checkbutton(
            c_opt,
            text="Всплывающие уведомления Windows при смене режима кнопкой",
            variable=self.notif_var,
            font=("Segoe UI", 9), fg="#d8dde8", bg="#0f121a", selectcolor="#07080c",
            activebackground="#0f121a", activeforeground="#00f09a", highlightthickness=0, cursor="hand2",
            command=self.on_notif_toggled
        ).pack(anchor="w", pady=2)

    def on_tester_mouse_move(self, event):
        now = time.perf_counter()
        if self.last_mouse_time is not None:
            dt = now - self.last_mouse_time
            if 0.00005 < dt < 0.1:
                hz = int(round(1.0 / dt))
                self.hz_history.append(hz)
                if len(self.hz_history) > 40:
                    self.hz_history.pop(0)

                self.live_hz = hz
                if hz > self.peak_hz and hz < 12000:
                    self.peak_hz = hz

                self.avg_hz = int(sum(self.hz_history) / len(self.hz_history))

                self.lbl_live_hz.config(text=f"{self.live_hz} Гц")
                self.lbl_peak_hz.config(text=f"{self.peak_hz} Гц")
                self.lbl_avg_hz.config(text=f"{self.avg_hz} Гц")

                # Анимация следа
                self.test_canvas.create_oval(
                    event.x - 3, event.y - 3, event.x + 3, event.y + 3,
                    fill="#00f09a", outline=""
                )
                if len(self.test_canvas.find_all()) > 60:
                    items = self.test_canvas.find_all()
                    if len(items) > 1:
                        self.test_canvas.delete(items[1])

        self.last_mouse_time = now

    def reset_tester(self):
        self.hz_history.clear()
        self.peak_hz = 0
        self.avg_hz = 0
        self.live_hz = 0
        self.lbl_live_hz.config(text="0 Гц")
        self.lbl_peak_hz.config(text="0 Гц")
        self.lbl_avg_hz.config(text="0 Гц")
        self.test_canvas.delete("all")
        self.test_canvas.create_text(
            220, 90,
            text="🎯 ДВИГАЙТЕ МЫШЬ ЗДЕСЬ ДЛЯ ТЕСТА ГЕРЦОВКИ",
            fill="#3e475c",
            font=("Segoe UI", 10, "bold")
        )

    def on_pause_game_toggled(self):
        v = self.pause_game_var.get()
        self.cfg["pause_in_game"] = v
        self.auto_apply("Пауза опроса в играх", lambda x: None, v)

    def on_notif_toggled(self):
        v = self.notif_var.get()
        self.cfg["notify_on_switch"] = v
        self.auto_apply("Уведомления Windows", lambda x: None, v)

    # =========================================================================
    # TAB 4: РАЗРАБОТЧИК & ДОНАТЫ (SUPPORT)
    # =========================================================================
    def render_support_tab(self):
        wrap = tk.Frame(self.container, bg="#07080c")
        wrap.pack(fill=tk.BOTH, expand=True)

        card_box = tk.Frame(wrap, bg="#0f121a", padx=24, pady=20, highlightbackground="#1e2436", highlightthickness=1)
        card_box.pack(fill=tk.X, pady=(10, 10))

        tk.Label(card_box, text="💖 Поддержка автора проекта", font=("Segoe UI", 14, "bold"), fg="#ff3b69", bg="#0f121a").pack(anchor="w")
        tk.Label(
            card_box,
            text="Если приложение LAMZU Battery Monitor помогло вам, вы можете отблагодарить автора любой суммой:",
            font=("Segoe UI", 9), fg="#8c97ad", bg="#0f121a"
        ).pack(anchor="w", pady=(4, 14))

        # Виртуальная банковская карта Obsidian Black
        card_frame = tk.Frame(card_box, bg="#11141e", padx=20, pady=16, highlightbackground="#22283a", highlightthickness=1)
        card_frame.pack(fill=tk.X, pady=(0, 14))

        card_head = tk.Frame(card_frame, bg="#11141e")
        card_head.pack(fill=tk.X)

        tk.Label(card_head, text="ЯНДЕКС БАНК (СБП)", font=("Segoe UI", 9, "bold"), fg="#00f09a", bg="#11141e").pack(side=tk.LEFT)
        tk.Label(card_head, text="● Перевод без комиссии", font=("Segoe UI", 8), fg="#636c82", bg="#11141e").pack(side=tk.RIGHT)

        card_num_lbl = tk.Label(
            card_frame,
            text=format_card_number(CARD_NUMBER),
            font=("Consolas", 18, "bold"),
            fg="#ffffff",
            bg="#11141e",
            pady=10
        )
        card_num_lbl.pack(anchor="w")

        tk.Label(card_frame, text=f"Получатель: {CARD_HOLDER}", font=("Segoe UI", 9, "bold"), fg="#8b95ac", bg="#11141e").pack(anchor="w")

        btn_row = tk.Frame(card_box, bg="#0f121a")
        btn_row.pack(fill=tk.X)

        def copy_card():
            clean = "".join(c for c in CARD_NUMBER if c.isdigit())
            self.root.clipboard_clear()
            self.root.clipboard_append(clean)
            c_btn.config(text="✔ Номер скопирован!", bg="#00c880")
            self.root.after(2500, lambda: c_btn.config(text="Скопировать номер карты", bg="#ff3366"))

        c_btn = tk.Button(
            btn_row, text="Скопировать номер карты", font=("Segoe UI", 10, "bold"),
            fg="#ffffff", bg="#ff3366", activebackground="#d62252", relief="flat", cursor="hand2", padx=16, pady=8,
            command=copy_card
        )
        c_btn.pack(side=tk.LEFT, padx=(0, 10))

        gh_btn = tk.Button(
            btn_row, text="⭐ Открыть репозиторий на GitHub", font=("Segoe UI", 10),
            fg="#b5bccf", bg="#1a1e2b", activebackground="#262d40", relief="flat", cursor="hand2", padx=16, pady=8,
            command=lambda: webbrowser.open(GITHUB_URL)
        )
        gh_btn.pack(side=tk.LEFT)

    # =========================================================================
    # FOOTER
    # =========================================================================
    def create_footer(self):
        footer = tk.Frame(self.root, bg="#07080c", padx=20, pady=8)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        left = tk.Frame(footer, bg="#07080c")
        left.pack(side=tk.LEFT)

        tk.Label(left, text="● 8K Dongle Active", font=("Segoe UI", 8, "bold"), fg="#00f09a", bg="#07080c").pack(side=tk.LEFT, padx=(0, 10))

        self.toast_lbl = tk.Label(
            left,
            text="Все изменения применяются мгновенно на лету",
            font=("Segoe UI", 9),
            fg="#4e5870",
            bg="#07080c"
        )
        self.toast_lbl.pack(side=tk.LEFT)

        close_btn = tk.Button(
            footer,
            text="Закрыть",
            font=("Segoe UI", 9, "bold"),
            fg="#08090d",
            bg="#00f09a",
            activebackground="#00c880",
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=4,
            command=self.root.destroy
        )
        close_btn.pack(side=tk.RIGHT)

def show_settings_dialog(on_change_callback: Optional[Callable[[str, Any], None]] = None):
    root = tk.Tk()
    app = LamzuControlSuiteGUI(root, on_change_callback)
    root.mainloop()

if __name__ == "__main__":
    show_settings_dialog()
