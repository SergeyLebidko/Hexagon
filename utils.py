import random
from math import pi, cos, sin
from settings import pg, W, H, BACKGROUND_COLORS_RANGE, RADIUS, HEX_MARGIN


def create_background_surface():
    surface = pg.Surface((W, H))
    step = 5
    for y in range(0, H, step):
        for x in range(0, W, step):
            color_component = random.randint(*BACKGROUND_COLORS_RANGE)
            color = (color_component,) * 3
            pg.draw.rect(surface, color, (x, y, step, step))
    return surface


def create_hexagon_coords(x0, y0):
    alpha = pi / 6
    delta_alpha = pi / 3
    coords = []
    for _ in range(6):
        coords.append((x0 + (RADIUS - HEX_MARGIN) * cos(alpha), y0 - (RADIUS - HEX_MARGIN) * sin(alpha)))
        alpha += delta_alpha
    return coords


def normalize_value(value):
    if value < 0:
        return -1
    elif value > 0:
        return 1
    return value
