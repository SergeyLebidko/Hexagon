"""Кэш готовых спрайтов.

Каждый гекс рисуется один раз в отдельную поверхность (мягкая тень, градиент,
внутренняя светлая кромка, сглаженный контур) и дальше только блитится.
Отрисовка блитом дешевле, чем polygon + линии, поэтому визуальные эффекты
не только не замедляют кадр, но и ускоряют его.
"""
import pygame as pg
from math import cos, pi, sin, sqrt
from pygame import gfxdraw

from settings import (BORDER_WIDTH, HEX_MARGIN, VOLUME_DARK,
                      VOLUME_LIGHT, BEVEL_WIDTH, BEVEL_STRENGTH)
from config import board, volume
from utils import hexagon_points

# Направление на источник света для фаски. Свет падает сверху-слева, как и
# тень под гексами, поэтому объём и тень не спорят друг с другом.
LIGHT_X, LIGHT_Y = -0.42, -0.91


def shade(color, factor):
    """Осветляет (factor > 1) или затемняет (factor < 1) цвет."""
    return tuple(max(0, min(255, int(channel * factor))) for channel in color[:3])


def _hex_points(cx, cy, scale=1.0):
    """Контур гекса. Геометрия общая с логикой столкновений (utils)."""
    return hexagon_points(cx, cy, scale)


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


def _mask(size, cx, cy, scale=1.0):
    """Маска по контуру гекса: ею обрезаются эффекты объёма."""
    mask = pg.Surface((size, size), pg.SRCALPHA)
    gfxdraw.filled_polygon(mask, _int_points(cx, cy, scale), (255, 255, 255, 255))
    return mask


def _corner_points(cx, cy, scale=1.0):
    """Контур без скруглений: грани фаски должны сходиться в настоящих углах."""
    radius = (board.radius - HEX_MARGIN) * scale
    points = []
    alpha = pi / 6
    for _ in range(6):
        points.append((cx + radius * cos(alpha), cy - radius * sin(alpha)))
        alpha += pi / 3
    return points


def _add_dome(layer, cx, cy, scale, fill, dark, light):
    """Радиальный градиент: светлое пятно смещено к верхнему левому углу.

    Линейный градиент красит все гексы одинаково, поэтому они выглядят
    плоскими плитками. Купол даёт центру объём: блик сверху-слева, тень
    по краям.

    Градиент считается в маленькой текстуре и растягивается: рисовать
    десятки кругов в полном размере спрайта заметно дороже, а на глаз
    разницы нет.
    """
    size = layer.get_size()[0]
    small = 64
    gradient = pg.Surface((small, small), pg.SRCALPHA)
    origin_x, origin_y = int(small * 0.38), int(small * 0.30)
    max_radius = int(small * 0.95)
    for radius in range(max_radius, 0, -1):
        ratio = radius / max_radius
        color = shade(fill, dark + (light - dark) * (1 - ratio))
        pg.draw.circle(gradient, (*color, 255), (origin_x, origin_y), radius)

    texture = pg.transform.smoothscale(gradient, (size, size))
    texture.blit(_mask(size, cx, cy, scale), (0, 0), special_flags=pg.BLEND_RGBA_MIN)
    layer.blit(texture, (0, 0))


def _add_bevel(layer, cx, cy, scale, fill, width, strength):
    """Фаска по рёбрам: грани к свету светлее, от света темнее.

    Кольцо между контуром и сжатой копией делится на шесть трапеций по
    числу рёбер; яркость каждой считается по её нормали. Так у гекса
    появляются настоящие грани, а не только градиент.
    """
    size = layer.get_size()[0]
    radius = (board.radius - HEX_MARGIN) * scale
    if radius <= width:
        return

    factor = 1.0 - width / radius
    outer = _corner_points(cx, cy, scale)
    inner = [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in outer]

    ring = pg.Surface((size, size), pg.SRCALPHA)
    for index in range(6):
        following = (index + 1) % 6
        # Нормаль ребра — от центра к его середине.
        normal_x = (outer[index][0] + outer[following][0]) / 2 - cx
        normal_y = (outer[index][1] + outer[following][1]) / 2 - cy
        length = sqrt(normal_x * normal_x + normal_y * normal_y) or 1
        dot = (normal_x / length) * LIGHT_X + (normal_y / length) * LIGHT_Y
        color = shade(fill, 1.0 + strength * dot)
        quad = [outer[index], outer[following], inner[following], inner[index]]
        points = [(int(round(x)), int(round(y))) for x, y in quad]
        gfxdraw.filled_polygon(ring, points, (*color, 255))
        gfxdraw.aapolygon(ring, points, (*color, 255))

    ring.blit(_mask(size, cx, cy, scale), (0, 0), special_flags=pg.BLEND_RGBA_MIN)
    layer.blit(ring, (0, 0))


def _stroke(surface, points, color, width, cx, cy, scale=1.0):
    """Обводка контура заданной толщины, растущая внутрь.

    gfxdraw.aapolygon рисует линию толщиной в один пиксель, а несколько
    сдвинутых копий дают рваный край. Поэтому граница строится как разница
    между внешним контуром и уменьшенной копией: получается ровное кольцо,
    которое не выходит за силуэт гекса.
    """
    if width <= 1:
        gfxdraw.aapolygon(surface, points, color)
        return

    outer = [(int(x), int(y)) for x, y in points]

    # Во сколько раз уменьшить контур, чтобы отступить на width пикселей.
    base_radius = (board.radius - 1) * scale
    if base_radius <= 0:
        gfxdraw.aapolygon(surface, outer, color)
        return
    factor = max(0.0, 1.0 - width / base_radius)

    ring = pg.Surface(surface.get_size(), pg.SRCALPHA)
    gfxdraw.filled_polygon(ring, outer, color)
    if factor > 0:
        inner = [(int(cx + (x - cx) * factor), int(cy + (y - cy) * factor)) for x, y in points]
        gfxdraw.filled_polygon(ring, inner, (0, 0, 0, 0))
    surface.blit(ring, (0, 0))


def make_hex_sprite(fill, border, scale=1.0, pad=26, shadow_alpha=0, glow=None,
                    inner_light=True, blur=7, border_width=1, volume=False):
    """Собирает гекс как спрайт.

    pad — запас вокруг гекса под тень и свечение;
    shadow_alpha — сила мягкой тени (0 отключает её);
    glow — цвет внешнего свечения (используется для подсветки ячейки);
    border_width — толщина обводки в пикселях;
    volume — добавить объём (купол и фаску). Включается только у цветных
    гексов: на пустых ячейках он превращал бы поле в стёганое одеяло.
    """
    size = int(2 * (board.radius * scale + pad))
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

    if volume:
        # Купол заменяет линейный градиент: два градиента друг на друге
        # дали бы грязный цвет.
        _add_dome(layer, cx, cy, scale, fill, VOLUME_DARK, VOLUME_LIGHT)
        _add_bevel(layer, cx, cy, scale, fill,
                   BEVEL_WIDTH * scale, BEVEL_STRENGTH)
    else:
        layer.blit(_gradient_body(size, fill, scale), (0, 0))

    _stroke(layer, points, (*border, 255), max(1, int(round(border_width * scale))),
            cx, cy, scale)
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
        """Состояние гекса.

        'empty'  — свободная ячейка поля;
        'marked' — ячейка под перетаскиваемой фигурой;
        'placed' — ячейка поля с поставленным гексом;
        'figure' — гекс внутри фигуры (в пуле и под курсором).
        """
        quantized = self.quantize(scale)
        colored = state in ('figure', 'placed')
        key = (theme.name, volume.name, state, color_index if colored else None, quantized)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        if state == 'placed':
            # Ячейка поля: обводка нейтральная, того же цвета, что у пустых
            # ячеек. Она не зависит от заливки, поэтому одинаково выглядит на
            # всех девяти цветах и явно меняется вместе с темой. Считать её
            # от заливки нельзя: палитры тем равнояркие, и контур получался
            # почти одного цвета в обеих темах. Тени нет — иначе она ложится
            # на соседние гексы.
            fill = theme.palette_color(color_index)
            border = theme['empty_border']
            shadow_alpha = 0
        elif state == 'figure':
            fill = theme.palette_color(color_index)
            # У фигур обводка совпадает с заливкой: тёмный контур «нарезал»
            # фигуру на отдельные гексы. Цвет обводки оставлен, чтобы край
            # оставался ровным и сглаженным, а не размывался градиентом.
            border = fill
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
            border_width=BORDER_WIDTH,
            # Объём получают только цветные гексы: 'placed' и 'figure'.
            volume=volume.enabled and state in ('placed', 'figure'),
        )
        self._cache[key] = sprite
        return sprite


cache = SpriteCache()
