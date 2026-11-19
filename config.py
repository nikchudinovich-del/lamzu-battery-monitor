"""
Модуль настроек приложения LAMZU Battery Monitor.
"""

import os
import json
import sys

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

    # Оптимизация производительности:
    "poll_interval": 30,       # 30 секунд интервал обновления
    "pause_in_game": True,     # Отключение опроса во время игры (0% нагрузки и задержек)

    "auto_sync_button": True,
    "notify_on_switch": True,
    "card_number": "2204 3110 1790 0938",  # Номер карты для донатов
    "card_holder": "Яндекс Банк (СБП)",     # Банк / Получатель (СБП)
    "github_url": "https://github.com/nikchudinovich-del",
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
    return cfg

def save_config(cfg: dict) -> bool:
    p = get_config_path()
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
