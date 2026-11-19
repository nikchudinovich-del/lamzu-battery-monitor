"""
Приложение системного трея для мыши LAMZU.
- Отображает реальный заряд батареи (без бага с 0% при уходе в сон).
- 3-этапное переключение кнопкой под мышкой:
    1-е нажатие: Киберспортивный режим + 2000 Гц
    2-е нажатие: Режим 20K FPS + 4000 Гц
    3-е нажатие: Выключение обоих режимов + 1000 Гц
- Удобное меню и графическое окно настроек.
"""

import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

import time
import winreg
import ctypes
import threading
from datetime import datetime
from typing import Optional

import pystray
from pystray import MenuItem as item

from lamzu_battery import (
    get_lamzu_status,
    get_mouse_polling_rate,
    set_mouse_polling_rate,
    get_mouse_hyper_mode,
    set_mouse_hyper_mode,
    get_mouse_tracking_mode,
    set_mouse_tracking_mode,
    get_mouse_lod,
    set_mouse_lod,
    get_mouse_sleep_time,
    set_mouse_sleep_time,
    get_mouse_dpi,
    set_mouse_dpi,
    get_notification_device_path
)
from icon_generator import generate_battery_icon
from config import load_config, save_config

APP_NAME = "LamzuBatteryTray"
DEFAULT_POLL_INTERVAL = 30
RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
MUTEX_NAME = "Local\\LamzuBatteryTray_SingleInstance_Mutex_v4"

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_ulong),
                ('rcMonitor', RECT),
                ('rcWork', RECT),
                ('dwFlags', ctypes.c_ulong)]

def is_fullscreen_game_active() -> bool:
    """
    Определяет, запущена ли полноэкранная игра или 3D-приложение.
    Использует Windows API SHQueryUserNotificationState и геометрическую проверку активного окна.
    """
    try:
        # 1. Проверка через SHQueryUserNotificationState
        # QUNS_RUNNING_D3D_FULL_SCREEN = 3 (DirectX / Vulkan полноэкранные игры)
        state = ctypes.c_int()
        ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
        if state.value == 3:
            return True

        # 2. Проверка активного окна на переднем плане (для игр в режиме Borderless Fullscreen)
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd or user32.IsIconic(hwnd):
            return False

        # Игнорируем рабочий стол, проводник и панель задач
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        cls = buf.value
        if cls in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd',
                   'Windows.UI.Core.CoreWindow', 'CabinetWClass', 'ExploreWClass'):
            return False

        # Проверяем, покрывает ли окно весь монитор
        wrect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(wrect)):
            return False

        hmon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        if not hmon:
            return False

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return False

        m = mi.rcMonitor
        # Если окно полностью перекрывает границы монитора
        if (wrect.left <= m.left and wrect.top <= m.top and
            wrect.right >= m.right and wrect.bottom >= m.bottom):
            return True

    except Exception:
        pass

    return False

def ensure_single_instance():
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        sys.exit(0)
    return mutex

class LamzuTrayApp:
    def __init__(self):
        self.icon: Optional[pystray.Icon] = None
        self.running = True
        self.last_battery: Optional[int] = None
        self.last_state: int = 0
        self.is_online = False
        self.product_name = "LAMZU Maya X"
        self.last_update_str = "Ожидание..."
        self.low_battery_warned = False
        self.lock = threading.Lock()

        # Настройки 3-х этапов
        self.cfg = load_config()

        # Текущий этап: 0 (Обычный), 1 (Киберспорт 2000), 2 (20K FPS 4000)
        self.current_stage: int = 0
        self.last_hardware_state: Optional[tuple] = None
        self.last_switch_time: float = 0.0
        self.mode_str = f"Обычный ({self.cfg.get('stage0_rate', 1000)} Гц)"
        self.in_game = False

    def get_run_command(self) -> str:
        if getattr(sys, 'frozen', False):
            return f'"{sys.executable}"'
        else:
            pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw_path):
                pythonw_path = sys.executable
            main_path = os.path.abspath(__file__)
            return f'"{pythonw_path}" "{main_path}"'

    def is_autostart_enabled(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(val)
        except OSError:
            return False

    def toggle_autostart(self, icon, item):
        enabled = self.is_autostart_enabled()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_WRITE) as key:
                if enabled:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except OSError:
                        pass
                else:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, self.get_run_command())
        except Exception as e:
            self.notify(f"Ошибка настройки автозагрузки: {e}", "LAMZU Battery")

    def notify(self, message: str, title: str = "LAMZU Maya X"):
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass

    def on_hardware_mode_changed(self, high_speed: bool, tracking: bool):
        """
        Вызывается мгновенно при нажатии физической кнопки под мышкой:
          1) high_speed=True,  tracking=False -> Киберспортивный режим + 2000 Гц
          2) high_speed=True,  tracking=True  -> Экстремальный режим (20K FPS) + 4000 Гц
          3) high_speed=False, tracking=False -> Обычный режим + 1000 Гц
        """
        now = time.time()
        if now - self.last_switch_time < 0.25:
            return
        self.last_switch_time = now

        show_notif = self.cfg.get("notify_on_switch", True)

        if high_speed and not tracking:
            self.current_stage = 1
            target_rate = self.cfg.get("stage1_rate", 2000)
            set_mouse_polling_rate(target_rate)
            self.mode_str = f"Киберспорт ({target_rate} Гц)"
            if show_notif:
                self.notify(f"⚡ [1/3] Киберспортивный режим: {target_rate} Гц", "LAMZU Maya X")

        elif high_speed and tracking:
            self.current_stage = 2
            target_rate = self.cfg.get("stage2_rate", 4000)
            set_mouse_polling_rate(target_rate)
            self.mode_str = f"20K FPS Экстрим ({target_rate} Гц)"
            if show_notif:
                self.notify(f"🔥 [2/3] Экстремальный режим: {target_rate} Гц (20K FPS)", "LAMZU Maya X")

        else:
            self.current_stage = 0
            target_rate = self.cfg.get("stage0_rate", 1000)
            set_mouse_polling_rate(target_rate)
            self.mode_str = f"Обычный ({target_rate} Гц)"
            if show_notif:
                self.notify(f"⚪ [3/3] Обычный режим: {target_rate} Гц", "LAMZU Maya X")

        with self.lock:
            now_str = datetime.now().strftime("%H:%M:%S")
            bat_val = self.last_battery if self.last_battery is not None else "--"
            st_str = "Заряжается" if self.last_state == 1 else "Разряжается"
            self.last_update_str = f"{self.product_name}: {bat_val}% ({st_str})\nРежим: {self.mode_str}\nОбновлено: {now_str}"

        self.last_hardware_state = (1 if high_speed else 0, 1 if tracking else 0)
        self.update_tray_icon()

    def apply_stage(self, stage: int, show_notification: bool = True):
        """Ручное применение одного из 3-х этапов из меню или настроек."""
        self.current_stage = stage

        if stage == 1:
            target_rate = self.cfg.get("stage1_rate", 2000)
            set_mouse_hyper_mode(True)
            set_mouse_tracking_mode(False)
            set_mouse_polling_rate(target_rate)
            self.mode_str = f"Киберспорт ({target_rate} Гц)"
            if show_notification and self.cfg.get("notify_on_switch", True):
                self.notify(f"⚡ [1/3] Киберспортивный режим: {target_rate} Гц", "LAMZU Maya X")

        elif stage == 2:
            target_rate = self.cfg.get("stage2_rate", 4000)
            set_mouse_hyper_mode(True)
            set_mouse_tracking_mode(True)
            set_mouse_polling_rate(target_rate)
            self.mode_str = f"20K FPS Экстрим ({target_rate} Гц)"
            if show_notification and self.cfg.get("notify_on_switch", True):
                self.notify(f"🔥 [2/3] Экстремальный режим: {target_rate} Гц (20K FPS)", "LAMZU Maya X")

        else:
            self.current_stage = 0
            target_rate = self.cfg.get("stage0_rate", 1000)
            set_mouse_tracking_mode(False)
            set_mouse_hyper_mode(False)
            set_mouse_polling_rate(target_rate)
            self.mode_str = f"Обычный ({target_rate} Гц)"
            if show_notification and self.cfg.get("notify_on_switch", True):
                self.notify(f"⚪ [3/3] Обычный режим: {target_rate} Гц", "LAMZU Maya X")

        with self.lock:
            now_str = datetime.now().strftime("%H:%M:%S")
            bat_val = self.last_battery if self.last_battery is not None else "--"
            st_str = "Заряжается" if self.last_state == 1 else "Разряжается"
            self.last_update_str = f"{self.product_name}: {bat_val}% ({st_str})\nРежим: {self.mode_str}\nОбновлено: {now_str}"

        self.last_hardware_state = (1 if stage in (1, 2) else 0, 1 if stage == 2 else 0)
        self.update_tray_icon()

    def notification_listener_worker(self):
        """
        Фоновый слушатель аппаратных событий мыши (HID Report ID 4 на Col04).
        Реагирует мгновенно (0 мс задержки, 0% CPU, 0 USB-запросов) на нажатие кнопки под мышкой!
        """
        import hid
        notif_path = get_notification_device_path()

        while self.running:
            if not notif_path:
                notif_path = get_notification_device_path(force_refresh=True)
                if not notif_path:
                    time.sleep(1)
                    continue

            h = hid.device()
            try:
                h.open_path(notif_path)
            except Exception:
                time.sleep(1)
                notif_path = None
                continue

            try:
                while self.running:
                    # Блокирующее чтение до 500 мс — 0% CPU!
                    data = h.read(64, timeout_ms=500)
                    if not data:
                        continue

                    # Проверяем отчеты от мыши (Report ID 4)
                    if len(data) >= 4 and data[0] == 4:
                        report_type = data[1]

                        # 1. Нажатие физической кнопки под мышкой (смена режимов)
                        if report_type == 13:
                            hs = (data[2] == 1)
                            tr = (data[3] == 1)
                            self.on_hardware_mode_changed(hs, tr)

                        # 2. Асинхронное обновление заряда батареи
                        elif report_type == 3:
                            bat = data[2]
                            charging = (data[3] == 1)
                            if 1 <= bat <= 100:
                                with self.lock:
                                    self.is_online = True
                                    self.last_battery = bat
                                    self.last_state = 1 if charging else 0
                                    state_str = "Заряжается" if charging else "Разряжается"
                                    now_str = datetime.now().strftime("%H:%M:%S")
                                    self.last_update_str = f"{self.product_name}: {bat}% ({state_str})\nРежим: {self.mode_str}\nОбновлено: {now_str}"
                                self.update_tray_icon()

            except Exception:
                pass
            finally:
                try:
                    h.close()
                except Exception:
                    pass
            time.sleep(0.5)

    def button_sync_worker(self):
        """
        Дополнительный синхронизатор аппаратного состояния мыши.
        Проверяет статус при запуске и в случае отсутствия прерываний.
        """
        while self.running:
            try:
                sleep_sec = 1.0 if self.in_game else 0.5
                time.sleep(sleep_sec)

                if not self.cfg.get("auto_sync_button", True):
                    continue

                curr_hyper = get_mouse_hyper_mode()
                if curr_hyper is None:
                    continue

                curr_track = get_mouse_tracking_mode() or 0
                curr_state = (curr_hyper, curr_track)

                if self.last_hardware_state is None:
                    self.last_hardware_state = curr_state
                    if curr_hyper == 1 and curr_track == 1:
                        self.current_stage = 2
                        r = self.cfg.get("stage2_rate", 4000)
                        self.mode_str = f"20K FPS Экстрим ({r} Гц)"
                    elif curr_hyper == 1:
                        self.current_stage = 1
                        r = self.cfg.get("stage1_rate", 2000)
                        self.mode_str = f"Киберспорт ({r} Гц)"
                    else:
                        self.current_stage = 0
                        r = self.cfg.get("stage0_rate", 1000)
                        self.mode_str = f"Обычный ({r} Гц)"
                    self.update_tray_icon()
                    continue

                if curr_state != self.last_hardware_state:
                    self.on_hardware_mode_changed(curr_hyper == 1, curr_track == 1)

            except Exception:
                pass

    def poll_battery(self):
        """Опрос батареи с защитой от сброса в 0% при сне."""
        status = get_lamzu_status()
        now_str = datetime.now().strftime("%H:%M:%S")

        with self.lock:
            if status.get("online") and status.get("battery", 0) > 0:
                self.is_online = True
                self.last_battery = status["battery"]
                self.last_state = status["state"]
                self.product_name = status.get("product", "LAMZU Maya X")
                state_str = status.get("state_str", "")
                self.last_update_str = f"{self.product_name}: {self.last_battery}% ({state_str})\nРежим: {self.mode_str}\nОбновлено: {now_str}"

                # Предупреждение о низком заряде
                if self.last_battery <= 15 and self.last_state != 1:
                    if not self.low_battery_warned:
                        self.low_battery_warned = True
                        self.notify(
                            f"Заряд мыши опустился до {self.last_battery}%! Пожалуйста, подключите кабель.",
                            "Низкий заряд мыши LAMZU"
                        )
                else:
                    self.low_battery_warned = False

            else:
                self.is_online = False
                # ВАЖНО: При сне last_battery сохраняет реальное значение (например 83%) и НЕ сбрасывается в 0!
                if self.last_battery is not None:
                    self.last_update_str = f"{self.product_name}: {self.last_battery}% (Режим ожидания / сон)\nРежим: {self.mode_str}\nОбновлено: {now_str}"
                else:
                    self.last_update_str = f"{self.product_name}: Поиск мыши...\nОбновлено: {now_str}"

        self.update_tray_icon()

    def update_tray_icon(self):
        if not self.icon:
            return

        with self.lock:
            percent = self.last_battery
            is_charging = (self.last_state == 1)
            is_online = self.is_online
            tooltip = self.last_update_str
            if self.in_game:
                tooltip += "\n[В игре: опрос батареи на паузе]"

        new_image = generate_battery_icon(
            percent=percent,
            is_charging=is_charging,
            is_online=is_online
        )

        self.icon.icon = new_image
        self.icon.title = tooltip[:128]
        try:
            self.icon.menu = self.create_menu()
        except Exception:
            pass

    def battery_worker(self):
        self.poll_battery()
        was_in_game = False
        elapsed = 0

        while self.running:
            time.sleep(1)

            pause_in_game = self.cfg.get("pause_in_game", True)
            poll_interval = self.cfg.get("poll_interval", 30)

            in_game = is_fullscreen_game_active() if pause_in_game else False

            # Переход: пользователь вышел из игры или свернул её (Alt+Tab на рабочий стол)
            if was_in_game and not in_game:
                was_in_game = False
                self.in_game = False
                elapsed = 0
                # Мгновенно опрашиваем заряд при выходе / Alt-Tab!
                self.poll_battery()
                continue

            was_in_game = in_game
            self.in_game = in_game

            if in_game:
                # В игре: опрос батареи полностью остановлен (0% нагрузки, 0 радиопомех)
                elapsed = 0
                continue

            elapsed += 1
            if elapsed >= poll_interval:
                elapsed = 0
                self.poll_battery()

    def format_sleep(self, sec: int) -> str:
        if sec < 60:
            return f"{sec} сек"
        return f"{sec // 60} мин"

    def apply_hardware_settings(self):
        """Применяет сохраненные настройки сенсора (DPI, LOD, время сна) к мыши."""
        def worker():
            try:
                dpi = self.cfg.get("current_dpi", 800)
                lod = self.cfg.get("mouse_lod", 1.0)
                sleep_sec = self.cfg.get("mouse_sleep_time", 60)
                set_mouse_dpi(dpi)
                set_mouse_lod(lod)
                set_mouse_sleep_time(sleep_sec)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def cycle_mode_manual(self, icon, item):
        """Ручное переключение этапа по кругу из меню трея."""
        def worker():
            next_stage = (self.current_stage + 1) % 3
            self.apply_stage(next_stage, show_notification=True)
            time.sleep(0.08)
            self.last_hardware_hyper = get_mouse_hyper_mode() or self.last_hardware_hyper
        threading.Thread(target=worker, daemon=True).start()

    def set_quick_dpi(self, dpi_val: int):
        """Быстрое переключение DPI из контекстного меню трея."""
        def worker():
            self.cfg["current_dpi"] = dpi_val
            save_config(self.cfg)
            set_mouse_dpi(dpi_val)
            if self.cfg.get("notify_on_switch", True):
                self.notify(f"🎯 DPI переключен: {dpi_val}", "LAMZU Maya X")
            self.update_tray_icon()
        threading.Thread(target=worker, daemon=True).start()

    def open_settings(self, icon, item):
        def on_saved(new_cfg):
            self.cfg = new_cfg
            self.apply_stage(self.current_stage, show_notification=False)
            self.apply_hardware_settings()
            self.update_tray_icon()

        from settings_gui import show_settings_dialog
        threading.Thread(target=lambda: show_settings_dialog(on_saved, self.apply_stage), daemon=True).start()

    def on_refresh_click(self, icon, item):
        threading.Thread(target=self.poll_battery, daemon=True).start()

    def on_exit_click(self, icon, item):
        self.running = False
        icon.stop()

    def open_donation(self, icon, item):
        from settings_gui import show_donation_dialog
        threading.Thread(target=lambda: show_donation_dialog(parent=None, cfg=self.cfg), daemon=True).start()

    def open_github(self, icon, item):
        import webbrowser
        webbrowser.open(self.cfg.get("github_url", "https://github.com/nikchudinovich-del"))

    def create_menu(self):
        def next_stage_text():
            nxt = (self.current_stage + 1) % 3
            if nxt == 1:
                return f"▶ Включить: Киберспорт ({self.cfg.get('stage1_rate', 2000)} Гц)"
            elif nxt == 2:
                return f"▶ Включить: 20K FPS ({self.cfg.get('stage2_rate', 4000)} Гц)"
            else:
                return f"▶ Включить: Обычный ({self.cfg.get('stage0_rate', 1000)} Гц)"

        def make_dpi_menu():
            dpi_list = [400, 800, 1200, 1600, 2400, 3200]
            items = []
            for d in dpi_list:
                def make_handler(val):
                    return lambda icon, it: self.set_quick_dpi(val)
                def make_checker(val):
                    return lambda it: self.cfg.get("current_dpi", 800) == val
                items.append(
                    item(
                        f"{d} DPI",
                        make_handler(d),
                        checked=make_checker(d)
                    )
                )
            return pystray.Menu(*items)

        current_dpi = self.cfg.get("current_dpi", 800)
        current_lod = self.cfg.get("mouse_lod", 1.0)
        current_sleep = self.format_sleep(self.cfg.get("mouse_sleep_time", 60))

        return pystray.Menu(
            item(
                lambda text: self.last_update_str.split("\n")[0] if self.last_update_str else "LAMZU Maya X",
                lambda icon, item: None,
                enabled=False
            ),
            item(
                lambda text: f"Режим: {self.mode_str}",
                lambda icon, item: None,
                enabled=False
            ),
            item(
                lambda text: f"DPI: {self.cfg.get('current_dpi', 800)}  |  LOD: {self.cfg.get('mouse_lod', 1.0)} мм  |  Сон: {self.format_sleep(self.cfg.get('mouse_sleep_time', 60))}",
                lambda icon, item: None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            item(lambda text: next_stage_text(), self.cycle_mode_manual),
            item("🎯 Быстрый выбор DPI", make_dpi_menu()),
            item("⚙ Настройки мыши (DPI, LOD, Сон)...", self.open_settings),
            pystray.Menu.SEPARATOR,
            item("🔄 Обновить сейчас", self.on_refresh_click),
            item(
                "✔ Автозагрузка с Windows",
                self.toggle_autostart,
                checked=lambda item: self.is_autostart_enabled()
            ),
            pystray.Menu.SEPARATOR,
            item("💖 Поддержать автора...", self.open_donation),
            item("⭐ GitHub проекта", self.open_github),
            pystray.Menu.SEPARATOR,
            item("❌ Выход", self.on_exit_click)
        )

    def run(self):
        initial_img = generate_battery_icon(None, is_charging=False, is_online=False)
        self.icon = pystray.Icon(
            name=APP_NAME,
            icon=initial_img,
            title="LAMZU Battery Monitor: Запуск...",
            menu=self.create_menu()
        )

        # Применяем сохраненные настройки сенсора (DPI, LOD, Сон) при запуске
        self.apply_hardware_settings()

        threading.Thread(target=self.battery_worker, daemon=True).start()
        threading.Thread(target=self.notification_listener_worker, daemon=True).start()
        threading.Thread(target=self.button_sync_worker, daemon=True).start()

        self.icon.run()

if __name__ == "__main__":
    _instance_mutex = ensure_single_instance()
    app = LamzuTrayApp()
    app.run()
