"""
Генератор высококачественных динамических иконок для системного трея Windows.
Использует суперсемплинг 4x (256x256) и фильтр Lanczos для кристальной четкости
шрифтов и сглаженных углов на любых мониторах и разрешениях Windows.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

def _get_font(font_size: int):
    candidates = [
        r"C:\Windows\Fonts\bahnschrift.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, font_size)
            except Exception:
                pass
    return ImageFont.load_default()

def generate_battery_icon(
    percent: Optional[int],
    is_charging: bool = False,
    is_online: bool = True
) -> Image.Image:
    """
    Генерирует иконку 64x64 с процентом заряда в стильном глубоком черном дизайне.
    """
    S = 256  # 4x суперсемплинг
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if percent is None:
        # Устройство еще не ответило ни разу
        txt = "--"
        accent = (95, 105, 125, 255)         # Графитовый
        bg = (11, 13, 18, 250)
        num_color = (175, 185, 205, 240)
    else:
        val = max(1, min(100, percent))
        txt = f"{val}"

        if is_charging:
            accent = (0, 230, 255, 255)       # Неоновый кибер-голубой
            bg = (6, 17, 26, 250)             # Глубокий темный циан
            num_color = (255, 255, 255, 255)
        elif val <= 15:
            accent = (255, 52, 85, 255)       # Неоновый красный
            bg = (24, 7, 11, 250)             # Глубокий темный кармин
            num_color = (255, 255, 255, 255)
        elif val <= 30:
            accent = (255, 175, 25, 255)      # Неоновый оранжевый/золото
            bg = (24, 15, 6, 250)             # Темный янтарный
            num_color = (255, 255, 255, 255)
        else:
            accent = (0, 242, 148, 255)       # Неоновый изумрудно-зеленый
            bg = (6, 18, 12, 250)             # Глубокий обсидиановый черновато-зеленый
            num_color = (255, 255, 255, 255)

        if not is_online:
            # Мышь уснула: сохраняем точный процент, но делаем контур мягче
            accent = (70, 95, 85, 255) if val > 30 else (120, 90, 70, 255)
            bg = (10, 13, 16, 240)
            num_color = (210, 220, 230, 230)

    # 1. Мягкое внешнее неоновое свечение (Outer Glow)
    glow_col = (accent[0], accent[1], accent[2], 55)
    draw.rounded_rectangle([3, 3, S - 4, S - 4], radius=68, outline=glow_col, width=10)

    # 2. Основная глубокая черная карточка с ярким контуром
    draw.rounded_rectangle([10, 10, S - 11, S - 11], radius=60, fill=bg, outline=accent, width=15)

    # 3. Тонкий внутренний блик для эффекта премиального стекла
    inner_highlight = (255, 255, 255, 24)
    draw.rounded_rectangle([26, 26, S - 27, S - 27], radius=44, outline=inner_highlight, width=4)

    # 4. Типографика (Bahnschrift / Segoe UI Bold)
    font_size = 142 if len(txt) <= 2 else 106
    font = _get_font(font_size)

    bbox = draw.textbbox((0, 0), txt, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    tx = (S - tw) / 2 - bbox[0]
    ty = (S - th) / 2 - bbox[1] - 3

    # Если мышь заряжается, выводим стильную молнию в правом верхнем углу
    if is_charging and is_online:
        tx -= 12
        bolt = [
            (S - 66, 20),
            (S - 26, 20),
            (S - 52, 68),
            (S - 24, 68),
            (S - 74, 134),
            (S - 60, 80),
            (S - 84, 80),
        ]
        draw.polygon(bolt, fill=(0, 240, 255, 255))
        draw.line(bolt + [bolt[0]], fill=(0, 120, 200, 220), width=3)

    # Отрисовка цифр
    draw.text((tx, ty), txt, font=font, fill=num_color)

    # Высококачественное сжатие Lanczos до финального размера трея 64x64
    final_icon = img.resize((64, 64), Image.Resampling.LANCZOS)
    return final_icon
