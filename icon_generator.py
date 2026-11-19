"""
Генератор динамических иконок для системного трея Windows.
Отображает процент заряда мыши и индикатор зарядки.
"""

from PIL import Image, ImageDraw, ImageFont
from typing import Optional

def generate_battery_icon(
    percent: Optional[int],
    is_charging: bool = False,
    is_online: bool = True
) -> Image.Image:
    """
    Генерирует иконку 64x64 с процентом заряда.
    """
    size = (64, 64)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if percent is None:
        # Устройство еще не ответило ни разу
        border_color = (120, 120, 130, 200)
        bg_color = (30, 30, 35, 230)
        text_color = (160, 160, 170, 220)
        display_text = "--"
    else:
        # Отображаем реальный процент заряда (даже если мышь в режиме сна!)
        val = max(1, min(100, percent))
        display_text = f"{val}"

        if is_charging:
            border_color = (0, 190, 255, 255)      # Неоново-голубой
            bg_color = (15, 28, 45, 240)
            text_color = (255, 255, 255, 255)
        elif val <= 15:
            border_color = (245, 60, 60, 255)      # Красный
            bg_color = (45, 18, 18, 240)
            text_color = (255, 255, 255, 255)
        elif val <= 30:
            border_color = (245, 170, 40, 255)     # Оранжевый
            bg_color = (40, 30, 15, 240)
            text_color = (255, 255, 255, 255)
        else:
            border_color = (40, 210, 95, 255)      # Зеленый
            bg_color = (18, 38, 25, 240)
            text_color = (255, 255, 255, 255)

        # Если мышь уснула, слегка смягчаем фон, но процент четко виден
        if not is_online:
            bg_color = (25, 30, 35, 230)
            text_color = (220, 225, 230, 240)

    # Отрисовка скругленного фона
    draw.rounded_rectangle(
        [2, 2, 61, 61],
        radius=14,
        fill=bg_color,
        outline=border_color,
        width=3
    )

    # Подбор шрифта
    font = None
    font_candidates = ["segoeuib.ttf", "arialbd.ttf", "tahoma.ttf", "arial.ttf"]
    
    # Размер шрифта: для "100" нужен чуть меньший кегль
    target_font_size = 31 if len(display_text) <= 2 else 25
    
    for font_name in font_candidates:
        try:
            font = ImageFont.truetype(font_name, target_font_size)
            break
        except Exception:
            continue

    if font is None:
        font = ImageFont.load_default()

    # Центрирование текста
    bbox = draw.textbbox((0, 0), display_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # Смещение по вертикали с учетом индикатора зарядки
    y_offset = 0 if not is_charging else 2
    x = (64 - tw) / 2
    y = (60 - th) / 2 - 2 + y_offset

    draw.text((x, y), display_text, font=font, fill=text_color)

    # Иконка молнии при зарядке (в верхнем правом углу)
    if is_charging and is_online:
        # Молния
        bolt = [
            (46, 5),
            (56, 5),
            (49, 16),
            (57, 16),
            (41, 30),
            (44, 18),
            (37, 18)
        ]
        draw.polygon(bolt, fill=(0, 230, 255, 255))
        # Маленькая обводка молнии для контраста
        draw.line(bolt + [bolt[0]], fill=(0, 100, 180, 200), width=1)

    return img
