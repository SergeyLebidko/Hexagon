import random
from math import pi, sin, cos
import pygame as pg

WINDOW_TITLE = 'Hexagon'
W, H = 1400, 900
RADIUS = 45
NORMAL = RADIUS * cos(pi / 6)
HEX_MARGIN = 3
FPS = 30


def create_background_surface():
    surface = pg.Surface((W, H))
    step = 5
    for y in range(0, H, step):
        for x in range(0, W, step):
            color_component = random.randint(0, 30)
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


def create_hexagon_list():
    result = []

    # Создаем центральный гекс
    layers_count = 4
    x0, y0 = W // 2, H // 2
    coords = create_hexagon_coords(x0, y0)
    center_hexagon = {
        'center': (x0, y0),
        'coords': coords
    }
    result.append(center_hexagon)

    # Последовательно создаем слои гексов вокруг центрального
    delta_alpha = pi / 3
    for layer in range(layers_count):
        anchor_hexagons = []
        alpha = 2 * pi / 6

        # Генерируем список опорных гексов
        for _ in range(6):
            x0, y0 = center_hexagon['center']
            x0, y0 = x0 + (2 * NORMAL * (layer + 1)) * cos(alpha), y0 - (2 * NORMAL * (layer + 1)) * sin(alpha)
            anchor_hexagons.append({
                'center': (x0, y0),
                'coords': create_hexagon_coords(x0, y0)
            })
            alpha += delta_alpha

        result.extend(anchor_hexagons)
        if layer == 0:
            continue

        # Создаем гексы между опорными
        anchor_hexagons.append(anchor_hexagons[0])
        for hexagon1, hexagon2 in [(anchor_hexagons[index], anchor_hexagons[index + 1]) for index in range(6)]:
            delta_x = (hexagon1['center'][0] - hexagon2['center'][0]) / (layer + 1)
            delta_y = (hexagon1['center'][1] - hexagon2['center'][1]) / (layer + 1)
            for index in range(layer):
                x0, y0 = hexagon2['center'][0] + delta_x * (index + 1), hexagon2['center'][1] + delta_y * (index + 1)
                result.append({
                    'center': (x0, y0),
                    'coords': create_hexagon_coords(x0, y0)
                })

    return result


def draw_hexagon_list(sc, hexagon_list):
    for hexagon in hexagon_list:
        pg.draw.polygon(sc, (255, 255, 255), hexagon['coords'])


def main():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    background_surface = create_background_surface()

    hexagon_list = create_hexagon_list()

    while True:

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

        sc.blit(background_surface, (0, 0))
        draw_hexagon_list(sc, hexagon_list)
        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
