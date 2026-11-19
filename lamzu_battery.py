"""
Модуль взаимодействия с мышью LAMZU по протоколу HID.
Поддерживает чтение батареи, переключение герцовки и киберспортивных режимов.
"""

import hid
import time
from typing import Optional, Tuple, Dict, Any

LAMZU_VIDS = {0x373e, 0x3554, 0x37b0}

RATE_TO_CODE = {
    125: 0x08,
    250: 0x04,
    500: 0x02,
    1000: 0x01,
    2000: 0x20,
    4000: 0x40,
    8000: 0x80
}

CODE_TO_RATE = {
    0x01: 1000,
    0x02: 500,
    0x04: 250,
    0x08: 125,
    0x10: 2000,
    0x20: 2000,
    0x40: 4000,
    0x80: 8000
}

_cached_control_path = None
_cached_notif_path = None

def get_control_device_path(force_refresh: bool = False) -> Optional[bytes]:
    """Возвращает кэшированный путь к интерфейсу управления мыши Lamzu (Interface 2)."""
    global _cached_control_path
    if _cached_control_path and not force_refresh:
        return _cached_control_path

    try:
        devices = hid.enumerate()
    except Exception:
        return None

    candidates = []
    for d in devices:
        vid = d.get('vendor_id')
        prod = (d.get('product_string') or '').upper()
        if vid in LAMZU_VIDS or 'LAMZU' in prod:
            candidates.append(d)

    if not candidates:
        _cached_control_path = None
        return None

    def candidate_score(d):
        s = 0
        if d.get('interface_number') == 2:
            s += 100
        if d.get('usage_page', 0) >= 0xff00:
            s += 50
        return s

    candidates.sort(key=candidate_score, reverse=True)
    _cached_control_path = candidates[0]['path']
    return _cached_control_path

def get_notification_device_path(force_refresh: bool = False) -> Optional[bytes]:
    """Возвращает путь к интерфейсу уведомлений мыши Lamzu (Report ID 4 на Col04)."""
    global _cached_notif_path
    if _cached_notif_path and not force_refresh:
        return _cached_notif_path

    try:
        devices = hid.enumerate()
    except Exception:
        return None

    for d in devices:
        vid = d.get('vendor_id')
        prod = (d.get('product_string') or '').upper()
        if vid in LAMZU_VIDS or 'LAMZU' in prod:
            if d.get('usage_page') == 0xffa0 and d.get('usage') == 0x1:
                _cached_notif_path = d['path']
                return _cached_notif_path
            if b'Col04' in d.get('path', b''):
                _cached_notif_path = d['path']
                return _cached_notif_path

    _cached_notif_path = None
    return None

def send_aurora_cmd(path: bytes, category: int, opcode: int, p6: int = 1, p7: int = 0) -> Optional[bytes]:
    """Отправляет команду протокола Aurora и возвращает ответ."""
    global _cached_control_path
    h = hid.device()
    try:
        h.open_path(path)
        h.set_nonblocking(True)
    except Exception:
        # Повторная попытка с обновленным путем, если порт сменился
        new_path = get_control_device_path(force_refresh=True)
        if not new_path or new_path == path:
            return None
        try:
            h.open_path(new_path)
            h.set_nonblocking(True)
            path = new_path
        except Exception:
            return None

    try:
        q = bytearray(65)
        q[0] = 0x00
        q[3] = 0x02
        q[4] = 0x02
        q[5] = category
        q[6] = opcode
        q[7] = p6
        q[8] = p7
        h.send_feature_report(q)
        time.sleep(0.02)

        for _ in range(5):
            for _ in range(25):
                r = h.get_feature_report(0, 65)
                if r and len(r) > 1 and r[1] == 0xa1:
                    return bytes(r)
                time.sleep(0.01)
            h.send_feature_report(q)
            time.sleep(0.015)
    except Exception:
        pass
    finally:
        try:
            h.close()
        except Exception:
            pass

    return None

def query_aurora_battery(device_path: bytes) -> Optional[Tuple[int, int]]:
    """
    Запрашивает заряд батареи.
    Возвращает (battery, state) ТОЛЬКО при валидном ответе 1..100%.
    Если мышь спит (0xa0) или возвращает 0, возвращает None (не затирает заряд нулем).
    """
    global _cached_control_path
    h = hid.device()
    try:
        h.open_path(device_path)
        h.set_nonblocking(True)
    except Exception:
        new_path = get_control_device_path(force_refresh=True)
        if not new_path or new_path == device_path:
            return None
        try:
            h.open_path(new_path)
            h.set_nonblocking(True)
            device_path = new_path
        except Exception:
            return None

    try:
        q = bytearray(65)
        q[0] = 0x00
        q[3] = 0x02
        q[4] = 0x02
        q[6] = 0x83
        h.send_feature_report(q)
        time.sleep(0.03)

        for _ in range(25):
            feat = h.get_feature_report(0, 65)
            if not feat:
                time.sleep(0.02)
                continue

            marker = feat[1] if len(feat) > 1 else 0
            if marker == 0xa1 or (len(feat) > 0 and feat[0] == 0xa1):
                # Ищем опкод 0x83 в ответе
                for i in range(len(feat) - 2):
                    if feat[i] == 0x83:
                        state = feat[i + 1]
                        battery = feat[i + 2]
                        # ВАЖНО: 0% при 0xa1/0xa0 бывает при выходе из сна или неинициализированном буфере.
                        # Реальный заряд всегда строго > 0
                        if 1 <= battery <= 100:
                            return battery, state

                if len(feat) >= 9 and feat[6] == 0x83:
                    state = feat[7]
                    battery = feat[8]
                    if 1 <= battery <= 100:
                        return battery, state

            elif marker > 0xa1:
                h.send_feature_report(q)

            time.sleep(0.02)
    except Exception:
        pass
    finally:
        try:
            h.close()
        except Exception:
            pass

    return None

def get_mouse_polling_rate(path: Optional[bytes] = None) -> Optional[int]:
    """Возвращает текущую герцовку мыши (1000, 2000, 4000, 8000 и т.д.)."""
    p = path or get_control_device_path()
    if not p:
        return None
    r = send_aurora_cmd(p, 1, 128, 1, 0)
    if r and len(r) >= 9 and r[6] == 128:
        code = r[8]
        return CODE_TO_RATE.get(code, 1000)
    return None

def set_mouse_polling_rate(rate_hz: int, path: Optional[bytes] = None) -> bool:
    """Устанавливает частоту опроса мыши в Гц (1000, 2000, 4000, 8000)."""
    p = path or get_control_device_path()
    if not p:
        return False
    code = RATE_TO_CODE.get(rate_hz)
    if not code:
        return False

    h = hid.device()
    try:
        h.open_path(p)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p:
            return False
        try:
            h.open_path(new_p)
            p = new_p
        except Exception:
            return False

    try:
        # Отправляем для профиля 1 (активный) и 0
        for prof in (1, 0):
            q = bytearray(65)
            q[0] = 0x00
            q[3] = 0x02
            q[4] = 0x02
            q[5] = 0x01
            q[6] = 0x00  # opcode 0 = setPollingRate
            q[7] = prof
            q[8] = code
            h.send_feature_report(q)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

def get_mouse_hyper_mode(path: Optional[bytes] = None) -> Optional[int]:
    """Возвращает статус Competition Mode (1 = включен, 0 = выключен, None = сон)."""
    p = path or get_control_device_path()
    if not p:
        return None
    r = send_aurora_cmd(p, 1, 139, 1, 0)
    if r and len(r) >= 9 and r[6] == 139:
        return 1 if r[8] == 1 else 0
    return None

def set_mouse_hyper_mode(enabled: bool, path: Optional[bytes] = None) -> bool:
    """Включает или выключает Competition Mode (High-Speed)."""
    p = path or get_control_device_path()
    if not p:
        return False
    val = 1 if enabled else 0

    h = hid.device()
    try:
        h.open_path(p)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p:
            return False
        try:
            h.open_path(new_p)
            p = new_p
        except Exception:
            return False

    try:
        for prof in (1, 0):
            q = bytearray(65)
            q[0] = 0x00
            q[3] = 0x02
            q[4] = 0x02
            q[5] = 0x01
            q[6] = 11  # opcode 11 = setHyperMode
            q[7] = prof
            q[8] = val
            h.send_feature_report(q)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

def get_mouse_tracking_mode(path: Optional[bytes] = None) -> Optional[int]:
    """Возвращает статус 20K FPS (1 = включен, 0 = выключен, None = сон)."""
    p = path or get_control_device_path()
    if not p:
        return None
    r = send_aurora_cmd(p, 1, 147, 1, 0)
    if r and len(r) >= 9 and r[6] == 147:
        return 1 if r[8] == 1 else 0
    return None

def set_mouse_tracking_mode(enabled: bool, path: Optional[bytes] = None) -> bool:
    """Включает или выключает режим 20K FPS."""
    p = path or get_control_device_path()
    if not p:
        return False
    val = 1 if enabled else 0

    h = hid.device()
    try:
        h.open_path(p)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p:
            return False
        try:
            h.open_path(new_p)
            p = new_p
        except Exception:
            return False

    try:
        for prof in (1, 0):
            q = bytearray(65)
            q[0] = 0x00
            q[3] = 0x02
            q[4] = 0x02
            q[5] = 0x01
            q[6] = 19  # opcode 19 = setTrackingMode
            q[7] = prof
            q[8] = val
            h.send_feature_report(q)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

def get_mouse_lod(path: Optional[bytes] = None) -> Optional[float]:
    """Возвращает текущую высоту отрыва в мм (0.7, 1.0, 2.0)."""
    p = path or get_control_device_path()
    if not p:
        return None
    r = send_aurora_cmd(p, 1, 136, 1, 0)
    if r and len(r) >= 9 and r[6] == 136:
        code = r[8]
        if code == 135:
            return 0.7
        elif code in (1, 2):
            return float(code)
    return None

def set_mouse_lod(lod_mm: float, path: Optional[bytes] = None) -> bool:
    """Устанавливает высоту отрыва сенсора (0.7, 1.0, 2.0 мм)."""
    p = path or get_control_device_path()
    if not p:
        return False

    if lod_mm <= 0.8:
        code = 135  # 0x87 -> 0.7 мм
    elif lod_mm >= 1.8:
        code = 2    # 2.0 мм
    else:
        code = 1    # 1.0 мм

    h = hid.device()
    try:
        h.open_path(p)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p:
            return False
        try:
            h.open_path(new_p)
            p = new_p
        except Exception:
            return False

    try:
        for prof in (1, 0):
            q = bytearray(65)
            q[0] = 0x00
            q[3] = 0x02
            q[4] = 0x02
            q[5] = 0x01
            q[6] = 0x08  # opcode 8 = setLOD
            q[7] = prof
            q[8] = code
            h.send_feature_report(q)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

def get_mouse_sleep_time(path: Optional[bytes] = None) -> Optional[int]:
    """Возвращает время перехода мыши в спящий режим в секундах (10, 30, 60, 300...)."""
    p = path or get_control_device_path()
    if not p:
        return None

    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        return None

    try:
        q = bytearray(65)
        q[0] = 0x00
        q[3] = 0x02
        q[4] = 0x03
        q[5] = 0x00
        q[6] = 135
        q[7] = 0x01
        h.send_feature_report(q)
        time.sleep(0.02)
        for _ in range(5):
            for _ in range(25):
                r = h.get_feature_report(0, 65)
                if r and len(r) > 9 and r[1] == 0xa1 and r[6] == 135:
                    return (r[8] << 8) | r[9]
                time.sleep(0.01)
            h.send_feature_report(q)
            time.sleep(0.015)
    except Exception:
        pass
    finally:
        try:
            h.close()
        except Exception:
            pass
    return None

def set_mouse_sleep_time(seconds: int, path: Optional[bytes] = None) -> bool:
    """Устанавливает время перехода мыши в спящий режим в секундах."""
    p = path or get_control_device_path()
    if not p:
        return False

    h = hid.device()
    try:
        h.open_path(p)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p:
            return False
        try:
            h.open_path(new_p)
            p = new_p
        except Exception:
            return False

    try:
        sec_hi = (seconds >> 8) & 0xff
        sec_lo = seconds & 0xff
        for prof in (1, 0):
            q = bytearray(65)
            q[0] = 0x00
            q[3] = 0x02
            q[4] = 0x03
            q[5] = 0x00
            q[6] = 0x07  # opcode 7 = setSleepTime
            q[7] = prof
            q[8] = sec_hi
            q[9] = sec_lo
            h.send_feature_report(q)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

def get_mouse_dpi(path: Optional[bytes] = None) -> Optional[int]:
    """Возвращает текущий активный DPI мыши."""
    p = path or get_control_device_path()
    if not p:
        return None

    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        return None

    try:
        # 1. Получаем активный номер этапа DPI (0..4)
        q_act = bytearray(65)
        q_act[3] = 2; q_act[4] = 2; q_act[5] = 1; q_act[6] = 130; q_act[7] = 1
        h.send_feature_report(q_act)
        time.sleep(0.02)
        active_stage = None
        for _ in range(5):
            for _ in range(25):
                r = h.get_feature_report(0, 65)
                if r and len(r) > 8 and r[1] == 0xa1 and r[6] == 130:
                    active_stage = r[8]
                    break
                time.sleep(0.01)
            if active_stage is not None:
                break
            h.send_feature_report(q_act)
            time.sleep(0.015)

        if active_stage is None:
            active_stage = 0

        # 2. Получаем список значений этапов DPI
        q_dpi = bytearray(65)
        q_dpi[3] = 2; q_dpi[4] = 10; q_dpi[5] = 1; q_dpi[6] = 129; q_dpi[7] = 1; q_dpi[8] = 5
        h.send_feature_report(q_dpi)
        time.sleep(0.02)
        dpis = []
        for _ in range(5):
            for _ in range(25):
                r = h.get_feature_report(0, 65)
                if r and len(r) > 8 and r[1] == 0xa1 and r[6] == 129:
                    cnt = r[8]
                    for i in range(cnt):
                        val = (r[9 + i * 4] << 8) | r[10 + i * 4]
                        dpis.append(val)
                    break
                time.sleep(0.01)
            if dpis:
                break
            h.send_feature_report(q_dpi)
            time.sleep(0.015)

        if dpis and active_stage < len(dpis):
            return dpis[active_stage]
        elif dpis:
            return dpis[0]
    except Exception:
        pass
    finally:
        try:
            h.close()
        except Exception:
            pass
    return None

def set_mouse_dpi(dpi: int, path: Optional[bytes] = None) -> bool:
    """Устанавливает активный DPI мыши (400, 800, 1200, 1600, 2400, 3200 и т.д.)."""
    p = path or get_control_device_path()
    if not p or dpi <= 0:
        return False

    dpi = max(50, min(30000, dpi))

    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p:
            return False
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
            p = new_p
        except Exception:
            return False

    try:
        # Получаем текущие этапы
        q_dpi = bytearray(65)
        q_dpi[3] = 2; q_dpi[4] = 10; q_dpi[5] = 1; q_dpi[6] = 129; q_dpi[7] = 1; q_dpi[8] = 5
        h.send_feature_report(q_dpi)
        time.sleep(0.02)
        dpis = []
        for _ in range(5):
            for _ in range(25):
                r = h.get_feature_report(0, 65)
                if r and len(r) > 8 and r[1] == 0xa1 and r[6] == 129:
                    cnt = r[8]
                    for i in range(cnt):
                        val = (r[9 + i * 4] << 8) | r[10 + i * 4]
                        dpis.append(val)
                    break
                time.sleep(0.01)
            if dpis:
                break
            h.send_feature_report(q_dpi)
            time.sleep(0.015)

        if not dpis:
            dpis = [800, 1200, 1600, 2400, 3200]

        target_stage = 0
        if dpi in dpis:
            target_stage = dpis.index(dpi)
        else:
            dpis[0] = dpi
            target_stage = 0
            buf = bytearray()
            for d in dpis:
                buf.extend([(d >> 8) & 0xff, d & 0xff, (d >> 8) & 0xff, d & 0xff])
            for prof in (1, 0):
                cmd = bytearray(65)
                cmd[3] = 2; cmd[4] = 2 + len(buf); cmd[5] = 1; cmd[6] = 1; cmd[7] = prof; cmd[8] = len(dpis)
                cmd[9:9+len(buf)] = buf
                h.send_feature_report(cmd)
                time.sleep(0.015)

        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3] = 2; cmd[4] = 2; cmd[5] = 1; cmd[6] = 2; cmd[7] = prof; cmd[8] = target_stage
            h.send_feature_report(cmd)
            time.sleep(0.015)

        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

def get_lamzu_status() -> Dict[str, Any]:
    """
    Опрашивает мышь и возвращает текущий статус.
    Если мышь в режиме сна, возвращает online=False и error='sleep',
    чтобы вызывающий код сохранял последний известный заряд и не обнулял его.
    """
    path = get_control_device_path()
    if not path:
        return {"online": False, "error": "Мышь не найдена"}

    res = query_aurora_battery(path)
    if res:
        bat, state = res
        return {
            "online": True,
            "battery": bat,
            "state": state,
            "state_str": "Заряжается" if state == 1 else ("Полный заряд" if state == 2 else "Разряжается"),
            "product": "LAMZU Maya X",
        }

    return {
        "online": False,
        "product": "LAMZU Maya X",
        "error": "sleep"
    }
