"""
Модуль настроек приложения LAMZU Battery Monitor & Control Center.
"""

import os
import json
import sys

# Неизменяемые реквизиты автора проекта (не могут быть изменены пользователем)
CARD_NUMBER = "2204 3110 1790 0938"
CARD_HOLDER = "Яндекс Банк (СБП)"
GITHUB_URL = "https://github.com/nikchudinovich-del/lamzu-battery-monitor"

DEFAULT_CONFIG = {
    # Этап 1: Киберспортивный режим + 2000 Гц
    "stage1_rate": 2000,
    "stage1_mode": "high_speed",

    # Этап 2: 20K FPS + 4000 Гц
    "stage2_rate": 4000,
    "stage2_mode": "20k",

    # Этап 3 (Выключение): Обычный режим + 1000 Гц
    "stage0_rate": 1000,
    "stage0_mode": "normal",

    # Настройки сенсора и производительности:
    "current_dpi": 800,
    "mouse_lod": 1.0,          # Высота отрыва (0.7 мм, 1.0 мм, 2.0 мм)
    "mouse_sleep_time": 60,    # Время до сна (сек): 10, 30, 60 (1 мин), 300 (5 мин), 600 (10 мин), 1800 (30 мин)
    "led_color": [0, 240, 154], # RGB цвет светодиода

    # Расширенные настройки из оригинального ПО:
    "debounce_time": 0,        # Debounce Time в мс (0, 1, 2, 4, 8, 12, 16, 20)
    "motion_sync": True,       # Motion Sync (аппаратная синхронизация пакетов)
    "ripple_control": False,   # Сглаживание микро-джиттера на высоких DPI
    "angle_snap": False,       # Доводка прямых линий
    "angle_tune": 0,           # Доворот угла сенсора (-30° до +30°)
    "xy_split": False,         # Раздельная настройка X и Y DPI
    "profile_id": 0,           # Номер профиля (0 = Profile 1 .. 3 = Profile 4)
    "stage_count": 5,          # Количество этапов DPI (от 1 до 5)
    "active_dpi_stage": 2,     # Активный этап DPI (0-4)
    "dpi_stages": [
        {"x": 800, "y": 800, "color": [255, 51, 102]},
        {"x": 1200, "y": 1200, "color": [0, 240, 154]},
        {"x": 1600, "y": 1600, "color": [0, 180, 255]},
        {"x": 2400, "y": 2400, "color": [168, 85, 247]},
        {"x": 3200, "y": 3200, "color": [255, 184, 46]}
    ],
    "macros": {},

    # Оптимизация производительности:
    "poll_interval": 30,       # 30 секунд интервал обновления
    "pause_in_game": True,     # Отключение опроса во время игры (0% нагрузки и задержек)

    "auto_sync_button": True,
    "notify_on_switch": True,

    # Реквизиты автора:
    "card_number": CARD_NUMBER,
    "card_holder": CARD_HOLDER,
    "github_url": GITHUB_URL,
}

def get_config_path() -> str:
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "config.json")

def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    p = get_config_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception:
            pass
    # Гарантируем неизменность авторских реквизитов
    cfg["card_number"] = CARD_NUMBER
    cfg["card_holder"] = CARD_HOLDER
    cfg["github_url"] = GITHUB_URL
    return cfg

def save_config(cfg: dict) -> bool:
    # Гарантируем неизменность авторских реквизитов при сохранении
    cfg["card_number"] = CARD_NUMBER
    cfg["card_holder"] = CARD_HOLDER
    cfg["github_url"] = GITHUB_URL
    p = get_config_path()
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
