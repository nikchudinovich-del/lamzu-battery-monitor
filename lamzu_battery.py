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
            _cached_control_path = None
            return None
        try:
            h.open_path(new_path)
            h.set_nonblocking(True)
            path = new_path
        except Exception:
            _cached_control_path = None
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
            _cached_control_path = None
            return None
        try:
            h.open_path(new_path)
            h.set_nonblocking(True)
            device_path = new_path
        except Exception:
            _cached_control_path = None
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
    """Устанавливает активный DPI мыши (симметрично и одинаково для осей X и Y)."""
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
        # Гарантируем отключение раздельного DPI по осям X и Y (100% симметричное движение)
        cmd_xy = bytearray(65)
        cmd_xy[3] = 2; cmd_xy[4] = 2; cmd_xy[5] = 1; cmd_xy[6] = 13; cmd_xy[7] = 1; cmd_xy[8] = 0
        h.send_feature_report(cmd_xy)
        time.sleep(0.015)

        # Считываем текущие этапы DPI
        q_dpi = bytearray(65)
        q_dpi[3] = 2; q_dpi[4] = 10; q_dpi[5] = 1; q_dpi[6] = 129; q_dpi[7] = 1; q_dpi[8] = 6
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

        if not dpis or len(dpis) < 5:
            dpis = [800, 1200, 1600, 2400, 3200]

        target_stage_1based = 1
        if dpi in dpis:
            target_stage_1based = dpis.index(dpi) + 1
        else:
            dpis[0] = dpi
            target_stage_1based = 1

        # Формируем буфер: X и Y строго равны!
        buf = bytearray()
        for d in dpis:
            buf.extend([(d >> 8) & 0xff, d & 0xff, (d >> 8) & 0xff, d & 0xff])

        cmd = bytearray(65)
        cmd[3] = 2; cmd[4] = 26; cmd[5] = 1; cmd[6] = 1; cmd[7] = 1; cmd[8] = len(dpis)
        cmd[9:9+len(buf)] = buf
        h.send_feature_report(cmd)
        time.sleep(0.02)

        # Активируем выбранный этап (1-based: 1..len(dpis))
        cmd_act = bytearray(65)
        cmd_act[3] = 2; cmd_act[4] = 2; cmd_act[5] = 1; cmd_act[6] = 2; cmd_act[7] = 1; cmd_act[8] = target_stage_1based
        h.send_feature_report(cmd_act)
        time.sleep(0.02)

        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

def get_mouse_led_color(path: Optional[bytes] = None) -> Optional[Tuple[int, int, int]]:
    """Возвращает текущий RGB цвет активного светодиода мыши."""
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
        # 1. Получаем активный этап (0..4)
        q_act = bytearray(65); q_act[3]=2; q_act[4]=2; q_act[5]=1; q_act[6]=130; q_act[7]=1
        h.send_feature_report(q_act)
        time.sleep(0.02)
        act = 0
        for _ in range(15):
            r = h.get_feature_report(0, 65)
            if r and len(r) > 8 and r[1] == 0xa1 and r[6] == 130:
                act = r[8]
                break
            time.sleep(0.015)

        # 2. Получаем цвета этапов
        q_col = bytearray(65); q_col[3]=2; q_col[4]=19; q_col[5]=2; q_col[6]=129; q_col[7]=1
        h.send_feature_report(q_col)
        time.sleep(0.02)
        for _ in range(25):
            r = h.get_feature_report(0, 65)
            if r and len(r) > 22 and r[1] == 0xa1 and r[6] == 129:
                idx = 8 + (act % 5) * 3
                return (r[idx], r[idx+1], r[idx+2])
            time.sleep(0.015)
    except Exception:
        pass
    finally:
        try:
            h.close()
        except Exception:
            pass
    return None

def set_mouse_led_color(r: int, g: int, b: int, path: Optional[bytes] = None) -> bool:
    """Устанавливает цвет светодиода мыши (RGB 0-255)."""
    p = path or get_control_device_path()
    if not p:
        return False

    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))

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
            p = new_p
        except Exception:
            return False

    try:
        # Включаем индикатор
        for prof in (1, 0):
            cmd_ind = bytearray(65)
            cmd_ind[3] = 2; cmd_ind[4] = 2; cmd_ind[5] = 2; cmd_ind[6] = 4; cmd_ind[7] = prof; cmd_ind[8] = 1
            h.send_feature_report(cmd_ind)
            time.sleep(0.015)

        # Задаем выбранный цвет для всех этапов, чтобы мышь всегда светила этим цветом
        colors = [r, g, b] * 5
        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3] = 2; cmd[4] = 19; cmd[5] = 2; cmd[6] = 1; cmd[7] = prof
            cmd[8:8+len(colors)] = bytearray(colors)
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


def get_mouse_debounce(path: Optional[bytes] = None) -> Optional[int]:
    """Возвращает текущий Debounce Time в мс (0..20)."""
    p = path or get_control_device_path()
    if not p: return None
    r = send_aurora_cmd(p, 0, 136, 1, 0)
    if r and len(r) > 8 and r[6] == 136:
        return r[8]
    return None

def set_mouse_debounce(ms: int, path: Optional[bytes] = None) -> bool:
    """Устанавливает Debounce Time в мс (0..20)."""
    p = path or get_control_device_path()
    if not p: return False
    ms = max(0, min(20, int(ms)))
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p: return False
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
        except Exception:
            return False
    try:
        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3]=2; cmd[4]=2; cmd[5]=0; cmd[6]=8; cmd[7]=prof; cmd[8]=ms
            h.send_feature_report(cmd)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try: h.close()
        except Exception: pass

def get_mouse_motion_sync(path: Optional[bytes] = None) -> Optional[bool]:
    """Возвращает статус Motion Sync (True/False)."""
    p = path or get_control_device_path()
    if not p: return None
    r = send_aurora_cmd(p, 1, 137, 1, 0)
    if r and len(r) > 8 and r[6] == 137:
        return (r[8] == 1)
    return None

def set_mouse_motion_sync(enabled: bool, path: Optional[bytes] = None) -> bool:
    """Включает или выключает Motion Sync."""
    p = path or get_control_device_path()
    if not p: return False
    val = 1 if enabled else 0
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p: return False
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
        except Exception:
            return False
    try:
        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=9; cmd[7]=prof; cmd[8]=val
            h.send_feature_report(cmd)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try: h.close()
        except Exception: pass

def get_mouse_ripple_control(path: Optional[bytes] = None) -> Optional[bool]:
    """Возвращает статус Ripple Control."""
    p = path or get_control_device_path()
    if not p: return None
    r = send_aurora_cmd(p, 1, 138, 1, 0)
    if r and len(r) > 8 and r[6] == 138:
        return (r[8] == 1)
    return None

def set_mouse_ripple_control(enabled: bool, path: Optional[bytes] = None) -> bool:
    """Включает или выключает Ripple Control."""
    p = path or get_control_device_path()
    if not p: return False
    val = 1 if enabled else 0
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p: return False
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
        except Exception:
            return False
    try:
        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=10; cmd[7]=prof; cmd[8]=val
            h.send_feature_report(cmd)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try: h.close()
        except Exception: pass

def get_mouse_angle_snap(path: Optional[bytes] = None) -> Optional[bool]:
    """Возвращает статус Angle Snap."""
    p = path or get_control_device_path()
    if not p: return None
    r = send_aurora_cmd(p, 1, 132, 1, 0)
    if r and len(r) > 8 and r[6] == 132:
        return (r[8] == 1)
    return None

def set_mouse_angle_snap(enabled: bool, path: Optional[bytes] = None) -> bool:
    """Включает или выключает Angle Snap."""
    p = path or get_control_device_path()
    if not p: return False
    val = 1 if enabled else 0
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p: return False
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
        except Exception:
            return False
    try:
        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=4; cmd[7]=prof; cmd[8]=val
            h.send_feature_report(cmd)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try: h.close()
        except Exception: pass

def get_mouse_angle_tune(path: Optional[bytes] = None) -> Optional[int]:
    """Возвращает угол доворота сенсора (-30..+30 градусов)."""
    p = path or get_control_device_path()
    if not p: return None
    r = send_aurora_cmd(p, 1, 148, 1, 0)
    if r and len(r) > 8 and r[6] == 148:
        val = r[8]
        if val > 128:
            return val - 256
        return val
    return None

def set_mouse_angle_tune(angle: int, path: Optional[bytes] = None) -> bool:
    """Устанавливает угол доворота сенсора (-30..+30 градусов)."""
    p = path or get_control_device_path()
    if not p: return False
    angle = max(-30, min(30, int(angle)))
    b_val = (angle + 256) % 256
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p: return False
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
        except Exception:
            return False
    try:
        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=20; cmd[7]=prof; cmd[8]=b_val
            h.send_feature_report(cmd)
            time.sleep(0.015)
        return True
    except Exception:
        return False
    finally:
        try: h.close()
        except Exception: pass

def get_mouse_dpi_detailed(path: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
    """Считывает подробную информацию по всем этапам DPI, активному этапу, цветам и X/Y split."""
    p = path or get_control_device_path()
    if not p: return None
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        return None
    try:
        # 1. getActiveDPI
        cmd_act = bytearray(65); cmd_act[3]=2; cmd_act[4]=2; cmd_act[5]=1; cmd_act[6]=130; cmd_act[7]=1
        h.send_feature_report(cmd_act)
        time.sleep(0.02)
        active_idx = 0
        for _ in range(15):
            r = h.get_feature_report(0, 65)
            if r and len(r) > 8 and r[6] == 130:
                raw_act = r[8]
                # Аппаратный индекс этапа 1-based (1..cnt), приводим к 0-based для GUI
                active_idx = max(0, raw_act - 1) if raw_act >= 1 else 0
                break
            time.sleep(0.01)

        # 2. getDPIXYOnOff
        cmd_xy = bytearray(65); cmd_xy[3]=2; cmd_xy[4]=2; cmd_xy[5]=1; cmd_xy[6]=141; cmd_xy[7]=1
        h.send_feature_report(cmd_xy)
        time.sleep(0.02)
        xy_split = False
        for _ in range(15):
            r = h.get_feature_report(0, 65)
            if r and len(r) > 8 and r[6] == 141:
                xy_split = (r[8] == 1)
                break
            time.sleep(0.01)

        # 3. getDPIStageInfo
        cmd_st = bytearray(65); cmd_st[3]=2; cmd_st[4]=10; cmd_st[5]=1; cmd_st[6]=129; cmd_st[7]=1; cmd_st[8]=6
        h.send_feature_report(cmd_st)
        time.sleep(0.02)
        stages = []
        for _ in range(25):
            r = h.get_feature_report(0, 65)
            if r and len(r) > 8 and r[6] == 129 and r[5] == 1:
                cnt = r[8]
                for i in range(cnt):
                    x = (r[9 + i*4] << 8) | r[10 + i*4]
                    y = (r[11 + i*4] << 8) | r[12 + i*4]
                    stages.append({"x": x, "y": y})
                break
            time.sleep(0.01)

        # 4. getDPIStageColors
        cmd_col = bytearray(65); cmd_col[3]=2; cmd_col[4]=19; cmd_col[5]=2; cmd_col[6]=129; cmd_col[7]=1
        h.send_feature_report(cmd_col)
        time.sleep(0.02)
        colors = []
        for _ in range(25):
            r = h.get_feature_report(0, 65)
            if r and len(r) > 22 and r[6] == 129 and r[5] == 2:
                for i in range(len(stages) or 5):
                    idx = 8 + i*3
                    colors.append([r[idx], r[idx+1], r[idx+2]])
                break
            time.sleep(0.01)

        for i, s in enumerate(stages):
            s["color"] = colors[i] if i < len(colors) else [0, 240, 154]

        return {
            "active_index": active_idx,
            "xy_split": xy_split,
            "stages": stages,
            "count": len(stages)
        }
    except Exception:
        return None
    finally:
        try: h.close()
        except Exception: pass

def set_mouse_full_dpi(stages: list, active_idx: int, xy_split: bool = False, path: Optional[bytes] = None) -> bool:
    """Записывает полную конфигурацию этапов DPI, активный этап, цвета и режим X/Y Split."""
    p = path or get_control_device_path()
    if not p or not stages: return False
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p: return False
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
            p = new_p
        except Exception:
            return False
    try:
        # 1. XY Split on/off (строго Profile 1)
        split_val = 1 if xy_split else 0
        cmd_xy = bytearray(65)
        cmd_xy[3]=2; cmd_xy[4]=2; cmd_xy[5]=1; cmd_xy[6]=13; cmd_xy[7]=1; cmd_xy[8]=split_val
        h.send_feature_report(cmd_xy)
        time.sleep(0.015)

        # 2. Stage values buffer
        buf = bytearray()
        colors_flat = []
        for s in stages:
            x = max(50, min(30000, int(s.get("x", 800))))
            y = max(50, min(30000, int(s.get("y", x)))) if xy_split else x
            buf.extend([(x >> 8) & 0xff, x & 0xff, (y >> 8) & 0xff, y & 0xff])
            c = s.get("color", [0, 240, 154])
            colors_flat.extend([int(c[0]), int(c[1]), int(c[2])])

        # 3. Write stages (длина пакета 26 по спецификации Nordic)
        cmd = bytearray(65)
        cmd[3]=2; cmd[4]=26; cmd[5]=1; cmd[6]=1; cmd[7]=1; cmd[8]=len(stages)
        cmd[9:9+len(buf)] = buf
        h.send_feature_report(cmd)
        time.sleep(0.02)

        # 4. Activate chosen stage (1-based: 1..len(stages))
        target_stage = max(1, min(len(stages), int(active_idx) + 1))
        cmd_act = bytearray(65)
        cmd_act[3]=2; cmd_act[4]=2; cmd_act[5]=1; cmd_act[6]=2; cmd_act[7]=1; cmd_act[8]=target_stage
        h.send_feature_report(cmd_act)
        time.sleep(0.02)

        # 5. Write stage colors if provided
        if colors_flat:
            while len(colors_flat) < 15:
                colors_flat.extend([0, 240, 154])
            cmd_c = bytearray(65)
            cmd_c[3]=2; cmd_c[4]=19; cmd_c[5]=2; cmd_c[6]=1; cmd_c[7]=1
            cmd_c[8:8+15] = bytearray(colors_flat[:15])
            h.send_feature_report(cmd_c)
            time.sleep(0.015)

        return True
    except Exception:
        return False
    finally:
        try: h.close()
        except Exception: pass

def factory_reset_mouse(path: Optional[bytes] = None) -> bool:
    """Выполняет полный аппаратный сброс мыши LAMZU до заводских настроек и восстанавливает безопасные параметры."""
    p = path or get_control_device_path()
    if not p: return False
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        return False
    try:
        def send(cmd):
            h.send_feature_report(cmd)
            time.sleep(0.02)

        # 1. defaultDevice
        cmd_def = bytearray(65)
        cmd_def[3] = 2; cmd_def[4] = 2; cmd_def[5] = 0; cmd_def[6] = 0; cmd_def[7] = 192; cmd_def[8] = 1
        send(cmd_def)

        # 2. resetProfile for 0 and 1
        for prof in (0, 1):
            cmd_rp = bytearray(65)
            cmd_rp[3] = 2; cmd_rp[4] = 1; cmd_rp[5] = 0; cmd_rp[6] = 13; cmd_rp[7] = prof
            send(cmd_rp)

        time.sleep(0.08)

        # 3. Восстановление гарантированно рабочих параметров:
        # LOD = 1.0 mm (code 1)
        for prof in (1, 0):
            cmd = bytearray(65); cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=8; cmd[7]=prof; cmd[8]=1
            send(cmd)

        # Debounce = 4 ms
        for prof in (1, 0):
            cmd = bytearray(65); cmd[3]=2; cmd[4]=2; cmd[5]=0; cmd[6]=8; cmd[7]=prof; cmd[8]=4
            send(cmd)

        # Sleep Time = 60 s
        for prof in (1, 0):
            cmd = bytearray(65); cmd[3]=2; cmd[4]=3; cmd[5]=0; cmd[6]=7; cmd[7]=prof; cmd[8]=0; cmd[9]=60
            send(cmd)

        # Polling Rate = 1000 Hz
        for prof in (1, 0):
            cmd = bytearray(65); cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=0; cmd[7]=prof; cmd[8]=1
            send(cmd)

        # Отключение Split XY, Angle Tune, Ripple, Snap
        for prof in (1, 0):
            cmd = bytearray(65); cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=13; cmd[7]=prof; cmd[8]=0
            send(cmd)
            cmd = bytearray(65); cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=20; cmd[7]=prof; cmd[8]=0
            send(cmd)
            cmd = bytearray(65); cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=10; cmd[7]=prof; cmd[8]=0
            send(cmd)
            cmd = bytearray(65); cmd[3]=2; cmd[4]=2; cmd[5]=1; cmd[6]=4; cmd[7]=prof; cmd[8]=0
            send(cmd)

        # Стандартные этапы DPI: [800, 1200, 1600, 2400, 3200]
        dpis = [800, 1200, 1600, 2400, 3200]
        buf = bytearray()
        for d in dpis:
            buf.extend([(d >> 8) & 0xff, d & 0xff, (d >> 8) & 0xff, d & 0xff])

        for prof in (1, 0):
            cmd = bytearray(65)
            cmd[3] = 2; cmd[4] = 2 + len(buf); cmd[5] = 1; cmd[6] = 1; cmd[7] = prof; cmd[8] = len(dpis)
            cmd[9:9+len(buf)] = buf
            send(cmd)

        # Активация 800 DPI (Stage 1 = 1)
        for prof in (1, 0):
            cmd = bytearray(65); cmd[3] = 2; cmd[4] = 2; cmd[5] = 1; cmd[6] = 2; cmd[7] = prof; cmd[8] = 1
            send(cmd)

        # Восстановление нижней кнопки в Competition Mode
        for prof in (1, 0):
            cmd = bytearray(65); cmd[3] = 2; cmd[4] = 6; cmd[5] = 3; cmd[6] = 0; cmd[7] = prof; cmd[8] = 20; cmd[10] = 20; cmd[11] = 1; cmd[12] = 0
            send(cmd)

        return True
    except Exception:
        return False
    finally:
        try: h.close()
        except Exception: pass


BOTTOM_BUTTON_MODES = {
    "competition": {"func": 20, "data": 0, "name": "Competition Mode (По умолчанию)"},
    "dpi_loop": {"func": 7, "data": 6, "name": "DPI Loop (Цикл DPI)"},
    "polling_rate": {"func": 13, "data": 3, "name": "PollingRate (Частота опроса)"},
    "lod": {"func": 14, "data": 3, "name": "LOD (Высота отрыва)"},
}

FUNC_TO_BOTTOM_MODE = {
    20: "competition",
    7: "dpi_loop",
    13: "polling_rate",
    14: "lod",
}

def get_mouse_bottom_button(path: Optional[bytes] = None) -> Optional[str]:
    """Возвращает текущую функцию нижней физической кнопки мыши ('competition', 'dpi_loop', 'polling_rate', 'lod')."""
    p = path or get_control_device_path()
    if not p:
        return None
    h = hid.device()
    try:
        h.open_path(p)
        h.set_nonblocking(True)
    except Exception:
        new_p = get_control_device_path(force_refresh=True)
        if not new_p:
            return None
        try:
            h.open_path(new_p)
            h.set_nonblocking(True)
            p = new_p
        except Exception:
            return None

    try:
        q = bytearray(65)
        q[0] = 0x00
        q[3] = 0x02
        q[4] = 0x05
        q[5] = 0x03  # Category 3: Button
        q[6] = 128   # Opcode 128: GetButton
        q[7] = 1     # Profile 1
        q[8] = 20    # Button 20 (DPILoopUp / Bottom Button)
        h.send_feature_report(q)
        time.sleep(0.02)
        for _ in range(20):
            r = h.get_feature_report(0, 65)
            if r and len(r) > 10 and r[1] == 0xa1 and r[5] == 3 and r[6] == 128 and r[8] == 20:
                func = r[10]
                return FUNC_TO_BOTTOM_MODE.get(func, "competition")
            time.sleep(0.01)
    except Exception:
        pass
    finally:
        try:
            h.close()
        except Exception:
            pass
    return None

def set_mouse_bottom_button(mode_key: str, path: Optional[bytes] = None) -> bool:
    """Устанавливает функцию нижней физической кнопки мыши."""
    info = BOTTOM_BUTTON_MODES.get(mode_key)
    if not info:
        return False
    func = info["func"]
    data0 = info["data"]

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
        for prof in (1, 0):
            q = bytearray(65)
            q[0] = 0x00
            q[3] = 0x02
            q[4] = 0x06  # length 5 + 1
            q[5] = 0x03  # Category 3: Button
            q[6] = 0x00  # Opcode 0: SetButton
            q[7] = prof
            q[8] = 20    # Button 20
            q[9] = 0
            q[10] = func
            q[11] = 1    # len 1
            q[12] = data0
            h.send_feature_report(q)
            time.sleep(0.02)
        return True
    except Exception:
        return False
    finally:
        try:
            h.close()
        except Exception:
            pass

