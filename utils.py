from math import pi, cos, sin, sqrt, hypot
from settings import HEX_MARGIN, CORNER_ROUNDING
from config import board

# Сколько отрезков используется для каждого скруглённого угла.
# Четыре дают достаточную гладкость при 3 px и не раздувают контур.
_ROUNDING_SEGMENTS = 4


def hexagon_points(x0, y0, scale=1.0):
    """Контур гекса со скруглёнными углами.

    Каждый угол заменяется квадратичной кривой Безье: она срезает остриё,
    оставляя края прямыми. Радиус скругления масштабируется вместе с гексом,
    поэтому при уменьшении фигуры форма не «плывёт».
    """
    radius = (board.radius - HEX_MARGIN) * scale
    corners = []
    alpha = pi / 6
    for _ in range(6):
        corners.append((x0 + radius * cos(alpha), y0 - radius * sin(alpha)))
        alpha += pi / 3

    rounding = CORNER_ROUNDING * scale
    if rounding <= 0:
        return corners

    points = []
    for index in range(6):
        previous = corners[index - 1]
        current = corners[index]
        following = corners[(index + 1) % 6]

        to_previous = (previous[0] - current[0], previous[1] - current[1])
        to_following = (following[0] - current[0], following[1] - current[1])
        length_previous = hypot(*to_previous)
        length_following = hypot(*to_following)

        # Скругление не должно занимать больше половины ребра, иначе соседние
        # углы начнут наезжать друг на друга.
        limit = min(length_previous, length_following) / 2 * 0.9
        radius_here = min(rounding, limit)

        start = (current[0] + to_previous[0] / length_previous * radius_here,
                 current[1] + to_previous[1] / length_previous * radius_here)
        end = (current[0] + to_following[0] / length_following * radius_here,
               current[1] + to_following[1] / length_following * radius_here)

        for step in range(_ROUNDING_SEGMENTS + 1):
            t = step / _ROUNDING_SEGMENTS
            inverse = 1 - t
            points.append((
                inverse ** 2 * start[0] + 2 * inverse * t * current[0] + t ** 2 * end[0],
                inverse ** 2 * start[1] + 2 * inverse * t * current[1] + t ** 2 * end[1],
            ))
    return points


def create_hexagon_coords(x0, y0, scale):
    return hexagon_points(x0, y0, scale)


def normalize_value(value):
    if value < 0:
        return -1
    elif value > 0:
        return 1
    return value


def get_distance(x1, y1, x2, y2):
    return sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
