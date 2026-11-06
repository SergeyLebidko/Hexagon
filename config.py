"""Размеры игрового поля и сохранение выбранных настроек.

Радиус гекса и число слоёв поля раньше были константами, которые копировались
при импорте в разные модули. Из-за этого их нельзя было менять на лету:
`settings.RADIUS = 30` не влиял на `classes.RADIUS`. Теперь значения живут
в объекте `board`, и модули читают их в момент вызова.
"""
import json
import os
from math import cos, pi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREFS_PATH = os.path.join(BASE_DIR, 'preferences.json')

# Три варианта поля. Радиус подобран так, чтобы поле помещалось в окно и
# не заезжало под фигуры пула.
BOARD_SIZES = {
    'S': {'layers': 4, 'radius': 45},
    'M': {'layers': 5, 'radius': 38},
    'L': {'layers': 6, 'radius': 33},
}

DEFAULT_SIZE = 'S'


class BoardConfig:
    """Текущий размер поля: радиус гекса и число слоёв."""

    def __init__(self, size=DEFAULT_SIZE):
        self._size = size if size in BOARD_SIZES else DEFAULT_SIZE

    @property
    def size(self):
        return self._size

    def set_size(self, size):
        if size in BOARD_SIZES:
            self._size = size
            return True
        return False

    @property
    def radius(self):
        return BOARD_SIZES[self._size]['radius']

    @property
    def normal(self):
        """Расстояние между центрами соседних гексов."""
        return self.radius * cos(pi / 6)

    @property
    def layers(self):
        return BOARD_SIZES[self._size]['layers']

    @property
    def hexagon_count(self):
        return 1 + 3 * self.layers * (self.layers + 1)


board = BoardConfig()


def load_preferences():
    """Читает сохранённые настройки. Битый файл не должен ронять игру."""
    try:
        with open(PREFS_PATH, encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None

    if not isinstance(data, dict):
        return None
    return data


def save_preferences(data):
    """Сохраняет настройки. Ошибка записи не критична для игры."""
    try:
        with open(PREFS_PATH, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False
