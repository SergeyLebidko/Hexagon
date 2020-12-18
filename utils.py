from math import pi, cos, sin
from settings import RADIUS, HEX_MARGIN


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
