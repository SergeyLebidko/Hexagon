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
