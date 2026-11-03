"""Шрифты интерфейса.

Inter лежит в assets/fonts под SIL Open Font License 1.1. Если файлы
недоступны, используется системный шрифт, чтобы игра не падала.
"""
import os

import pygame as pg

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'fonts')

_FILES = {
    'regular': 'Inter-Regular.ttf',
    'medium': 'Inter-Medium.ttf',
    'semibold': 'Inter-SemiBold.ttf',
    'bold': 'Inter-Bold.ttf',
}

# Запасные системные шрифты: используется первый найденный.
_FALLBACKS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
]


class FontBook:
    """Кэш шрифтов по (начертание, размер)."""

    def __init__(self):
        self._cache = {}
        self._paths = {}

    def _path(self, weight):
        if weight in self._paths:
            return self._paths[weight]

        candidate = os.path.join(FONT_DIR, _FILES.get(weight, _FILES['regular']))
        path = None
        if os.path.exists(candidate):
            path = candidate
        else:
            for fallback in _FALLBACKS:
                if os.path.exists(fallback):
                    path = fallback
                    break

        self._paths[weight] = path
        return path

    def get(self, weight, size):
        key = (weight, size)
        font = self._cache.get(key)
        if font is None:
            font = pg.font.Font(self._path(weight), size)
            self._cache[key] = font
        return font

    def regular(self, size):
        return self.get('regular', size)

    def medium(self, size):
        return self.get('medium', size)

    def semibold(self, size):
        return self.get('semibold', size)

    def bold(self, size):
        return self.get('bold', size)

    def clear(self):
        self._cache = {}
        self._paths = {}


fonts = FontBook()
