"""Кэш готовых спрайтов.

Каждый гекс рисуется один раз в отдельную поверхность (мягкая тень, градиент,
внутренняя светлая кромка, сглаженный контур) и дальше только блитится.
Отрисовка блитом дешевле, чем polygon + линии, поэтому визуальные эффекты
не только не замедляют кадр, но и ускоряют его.
"""
from math import pi, cos, sin

import pygame as pg
from pygame import gfxdraw

from settings import RADIUS, HEX_MARGIN


def shade(color, factor):
    """Осветляет (factor > 1) или затемняет (factor < 1) цвет."""
    return tuple(max(0, min(255, int(channel * factor))) for channel in color[:3])


def _hex_points(cx, cy, scale=1.0):
    points = []
    alpha = pi / 6
    radius = (RADIUS - HEX_MARGIN) * scale
    for _ in range(6):
        points.append((cx + radius * cos(alpha), cy - radius * sin(alpha)))
        alpha += pi / 3
    return points


def _int_points(cx, cy, scale=1.0):
    return [(int(x), int(y)) for x, y in _hex_points(cx, cy, scale)]


def _gradient_body(size, fill, scale=1.0):
    """Вертикальный градиент, обрезанный по форме гекса."""
    body = pg.Surface((size, size), pg.SRCALPHA)
    top, bottom = shade(fill, 1.16), shade(fill, 0.84)
    for y in range(size):
        t = y / max(1, size - 1)
        color = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
        pg.draw.line(body, color, (0, y), (size, y))

    mask = pg.Surface((size, size), pg.SRCALPHA)
    gfxdraw.filled_polygon(mask, _int_points(size / 2, size / 2, scale), (255, 255, 255, 255))
    body.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
    return body


def make_hex_sprite(fill, border, scale=1.0, pad=26, shadow_alpha=0, glow=None,
                    inner_light=True, blur=7):
    """Собирает гекс как спрайт.

    pad — запас вокруг гекса под тень и свечение;
    shadow_alpha — сила мягкой тени (0 отключает её);
    glow — цвет внешнего свечения (используется для подсветки ячейки).
    """
    size = int(2 * (RADIUS * scale + pad))
    cx = cy = size / 2
    layer = pg.Surface((size, size), pg.SRCALPHA)
    points = _int_points(cx, cy, scale)

    if shadow_alpha:
        shadow = pg.Surface((size, size), pg.SRCALPHA)
        gfxdraw.filled_polygon(shadow, points, (0, 0, 0, 255))
        shadow = pg.transform.box_blur(shadow, blur)
        shadow.set_alpha(shadow_alpha)
        # Тень чуть ниже: свет падает сверху.
        layer.blit(shadow, (0, max(2, int(4 * scale))))

    if glow:
        halo = pg.Surface((size, size), pg.SRCALPHA)
        gfxdraw.filled_polygon(halo, _int_points(cx, cy, scale * 0.96), (*glow, 255))
        halo = pg.transform.box_blur(halo, max(4, int(12 * scale)))
        halo.set_alpha(150)
        layer.blit(halo, (0, 0))

    layer.blit(_gradient_body(size, fill, scale), (0, 0))

    # Раньше здесь рисовалась светлая кромка по внутреннему контуру, но при
    # уменьшении масштаба (взятие фигуры) она превращалась в заметную линию
    # внутри гекса. Объём создаёт сам градиент, поэтому кромка убрана.
    gfxdraw.aapolygon(layer, points, (*border, 210))
    return _trim(layer)


def _trim(surface):
    """Приводит спрайт к фиксированному размеру с центром гекса в центре картинки.

    Обрезка «по содержимому» здесь не годится: у цветных гексов есть тень, у
    пустых её нет, поэтому итоговые размеры отличались, а вместе с ними —
    и округление при позиционировании. Из-за этого одинаковые по геометрии
    ячейки выглядели по-разному удалёнными друг от друга. Поэтому картинка
    всегда одного размера, а лишние прозрачные поля остаются по краям.
    """
    return surface.convert_alpha()


class SpriteCache:
    """Кэширует спрайты по (состояние, индекс цвета, шаг масштаба).

    Масштаб квантуется: анимация появления и взятия фигуры проходит шагами,
    поэтому полный набор картинок невелик и считается один раз.
    """

    SCALE_STEPS = 20
    # Общий запас вокруг гекса. Он одинаков для всех состояний: если у цветных
    # и пустых спрайтов он разный, размеры картинок отличаются на нечётное
    # число пикселей, и при центрировании гексы смещаются друг относительно
    # друга на 1 px — зазоры между ними выглядят неравномерными.
    PADDING = 26

    def __init__(self):
        self._cache = {}
        self.clear()

    def clear(self):
        self._cache = {}

    @staticmethod
    def quantize(scale):
        step = max(1, min(SpriteCache.SCALE_STEPS, round(scale * SpriteCache.SCALE_STEPS)))
        return step / SpriteCache.SCALE_STEPS

    def hex_sprite(self, state, color_index, scale, theme, fill=None, border=None, glow=None):
        """state: 'empty' | 'marked' | 'figure'; color_index — только для figure."""
        quantized = self.quantize(scale)
        key = (theme.name, state, color_index if state == 'figure' else None, quantized)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if state == 'figure':
            fill = theme.palette_color(color_index)
            border = shade(fill, 0.62)
            shadow_alpha = theme['sprite_shadow']
        elif state == 'marked':
            fill = theme['marked_fill']
            border = theme['marked_border']
            glow = theme['marked_glow']
            shadow_alpha = theme['sprite_shadow']
        else:
            fill = theme['empty_fill']
            border = theme['empty_border']
            shadow_alpha = 0

        sprite = make_hex_sprite(
            fill, border, scale=quantized,
            pad=self.PADDING,
            shadow_alpha=shadow_alpha,
            glow=glow,
        )
        self._cache[key] = sprite
        return sprite


cache = SpriteCache()
