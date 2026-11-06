"""Темы оформления.

Все цвета интерфейса собраны здесь, чтобы переключение темы не требовало
перекрашивать объекты игры: фигура хранит не RGB, а индекс цвета в палитре,
и конкретный оттенок берётся из активной темы в момент отрисовки.
"""

LIGHT = {
    'name': 'light',

    # Фон окна
    'background_top': (246, 246, 250),
    'background_bottom': (236, 238, 246),
    'background_noise': (244, 250),
    'background_noise_mode': 'min',
    'vignette': (16, 16, 20),

    # Игровое поле
    'board_shadow': (30, 40, 70, 26),
    'empty_fill': (226, 231, 241),
    'empty_border': (196, 203, 217),
    'marked_fill': (150, 205, 255),
    'marked_border': (72, 150, 226),
    'marked_glow': (110, 180, 255),

    # Фигуры: 9 равноярких оттенков
    'palette': [
        (255, 99, 99),
        (255, 159, 67),
        (240, 196, 66),
        (72, 199, 116),
        (54, 190, 178),
        (74, 158, 255),
        (124, 131, 253),
        (166, 122, 250),
        (240, 110, 170),
    ],

    # Текст
    'text_primary': (44, 54, 82),
    'text_secondary': (130, 142, 168),
    'text_shadow': (150, 170, 210),
    'text_final': (200, 60, 70),

    # Тень гекса
    'sprite_shadow': 70,

    # Финальный экран
    'overlay': (28, 34, 52, 90),
    'card_fill': (252, 253, 255, 252),
    'card_border': (214, 220, 234, 255),
    'card_shadow': (24, 32, 56, 80),

    # Кнопки
    'button_primary': (74, 158, 255),
    'button_primary_hover': (52, 138, 240),
    'button_primary_text': (255, 255, 255),
    'button_secondary': (236, 239, 247),
    'button_secondary_hover': (224, 229, 240),
    'button_secondary_text': (74, 86, 116),
    'button_border': (205, 212, 228),

    # Кнопка переключения темы
    'theme_button_fill': (255, 255, 255, 190),
    'theme_button_hover': (226, 236, 252, 250),
    'theme_button_border': (208, 215, 230),
    'theme_button_border_hover': (150, 186, 240),
    'theme_button_icon': (96, 108, 138),
    'theme_button_icon_hover': (52, 104, 190),
}

DARK = {
    'name': 'dark',

    'background_top': (34, 38, 50),
    'background_bottom': (24, 27, 37),
    'background_noise': (28, 38),
    'background_noise_mode': 'add',
    'vignette': (10, 10, 14),

    'board_shadow': (0, 0, 0, 90),
    'empty_fill': (62, 69, 89),
    'empty_border': (96, 106, 132),
    'marked_fill': (58, 120, 190),
    'marked_border': (130, 195, 255),
    'marked_glow': (90, 170, 255),

    'palette': [
        (255, 122, 122),
        (255, 176, 92),
        (250, 208, 96),
        (98, 214, 136),
        (72, 205, 194),
        (96, 174, 255),
        (146, 152, 255),
        (186, 146, 255),
        (250, 132, 186),
    ],

    'text_primary': (232, 238, 250),
    'text_secondary': (126, 140, 170),
    'text_shadow': (70, 90, 130),
    'text_final': (255, 130, 140),

    'sprite_shadow': 110,

    # Финальный экран
    'overlay': (0, 0, 0, 120),
    'card_fill': (44, 50, 68, 252),
    'card_border': (78, 88, 112, 255),
    'card_shadow': (0, 0, 0, 130),

    # Кнопки
    'button_primary': (96, 174, 255),
    'button_primary_hover': (122, 190, 255),
    'button_primary_text': (18, 24, 38),
    'button_secondary': (62, 70, 92),
    'button_secondary_hover': (78, 88, 114),
    'button_secondary_text': (226, 233, 246),
    'button_border': (88, 98, 124),

    'theme_button_fill': (54, 61, 80, 190),
    'theme_button_hover': (78, 88, 116, 250),
    'theme_button_border': (86, 96, 122),
    'theme_button_border_hover': (126, 158, 210),
    'theme_button_icon': (214, 223, 240),
    'theme_button_icon_hover': (255, 255, 255),
}

THEMES = {'light': LIGHT, 'dark': DARK}


class ThemeManager:
    """Хранит активную тему и уведомляет об её смене."""

    def __init__(self, name='light'):
        self.current = THEMES[name]

    @property
    def name(self):
        return self.current['name']

    def toggle(self):
        self.current = DARK if self.current is LIGHT else LIGHT
        return self.current

    def __getitem__(self, key):
        return self.current[key]

    def palette_color(self, index):
        """Цвет фигуры по индексу. Индекс хранится в самой фигуре."""
        palette = self.current['palette']
        return palette[index % len(palette)]


theme = ThemeManager()
