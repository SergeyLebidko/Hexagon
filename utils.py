from math import pi, cos, sin
from settings import RADIUS, HEX_MARGIN, SMOOTH_FACTOR, SMOOTH_DEPTH


def create_hexagon_coords(x0, y0, scale):
    alpha = pi / 6
    delta_alpha = pi / 3
    coords = []
    for _ in range(6):
        coords.append(
            (
                x0 + scale * (RADIUS - HEX_MARGIN) * cos(alpha),
                y0 - scale * (RADIUS - HEX_MARGIN) * sin(alpha)
            )
        )
        alpha += delta_alpha
    return smooth(coords, SMOOTH_DEPTH)


def smooth(coords, depth):
    """Функция сглаживает края гекса"""
    if depth == 0:
        return coords

    smooth_coords = []
    for index in range(len(coords)):
        x0, y0 = coords[index]
        try:
            x1, y1 = coords[index - 1]
        except IndexError:
            x1, y1 = coords[-1]
        try:
            x2, y2 = coords[index + 1]
        except IndexError:
            x2, y2 = coords[0]

        vector1 = SMOOTH_FACTOR * (x1 - x0), SMOOTH_FACTOR * (y1 - y0)
        vector2 = SMOOTH_FACTOR * (x2 - x0), SMOOTH_FACTOR * (y2 - y0)

        xa, ya = x0 + vector1[0], y0 + vector1[1]
        xb, yb = x0 + vector2[0], y0 + vector2[1]

        xc, yc = (xa + xb) / 2, (ya + yb) / 2
        xd, yd = (x0 + xc) / 2, (y0 + yc) / 2

        smooth_coords.extend([(xa, ya), (xd, yd), (xb, yb)])

    return smooth(smooth_coords, depth - 1)


def normalize_value(value):
    if value < 0:
        return -1
    elif value > 0:
        return 1
    return value
