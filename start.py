import random
from math import pi, sin, cos
import pygame as pg

WINDOW_TITLE = 'Hexagon'
W, H = 1400, 900
RADIUS = 50
NORMAL = RADIUS * cos(pi / 6)
HEX_MARGIN = 3
FPS = 30

LAYERS_COUNT = 4
BACKGROUND_COLORS_RANGE = (240, 250)
EMPTY_HEXAGON_COLOR = (220, 220, 220)
D_PARAMS = [
    {'x-axis': 1, 'y-axis': 1, 'z-axis': 0},
    {'x-axis': 1, 'y-axis': 0, 'z-axis': -1},
    {'x-axis': 0, 'y-axis': -1, 'z-axis': -1},
    {'x-axis': -1, 'y-axis': -1, 'z-axis': 0},
    {'x-axis': -1, 'y-axis': 0, 'z-axis': 1},
    {'x-axis': 0, 'y-axis': 1, 'z-axis': 1},
]

# В дальнейшем удалить
CENTER_HEX_COLOR = (100, 100, 255)
ANCHOR_HEX_COLOR = (100, 255, 100)
OTHER_HEX_COLOR = (255, 100, 100)


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


def create_hexagon_list():
    result = []

    # Создаем центральный гекс
    x0, y0 = W // 2, H // 2
    coords = create_hexagon_coords(x0, y0)
    center_hexagon = {
        'center': (x0, y0),
        'coords': coords,
        'x-axis': 0,
        'y-axis': 0,
        'z-axis': 0,
        'color': CENTER_HEX_COLOR
    }
    result.append(center_hexagon)

    # Последовательно создаем слои гексов вокруг центрального
    delta_alpha = pi / 3
    for layer in range(LAYERS_COUNT):
        anchor_hexagons = []
        alpha = 2 * pi / 6

        # Генерируем список опорных гексов
        for direction in range(6):
            x0, y0 = center_hexagon['center']
            x0, y0 = x0 + (2 * NORMAL * (layer + 1)) * cos(alpha), y0 - (2 * NORMAL * (layer + 1)) * sin(alpha)
            anchor_hexagons.append({
                'center': (x0, y0),
                'coords': create_hexagon_coords(x0, y0),
                'x-axis': D_PARAMS[direction]['x-axis'] * (layer + 1),
                'y-axis': D_PARAMS[direction]['y-axis'] * (layer + 1),
                'z-axis': D_PARAMS[direction]['z-axis'] * (layer + 1),
                'color': ANCHOR_HEX_COLOR
            })
            alpha += delta_alpha

        result.extend(anchor_hexagons)
        if layer == 0:
            continue

        # Создаем гексы между опорными
        anchor_hexagons.append(anchor_hexagons[0])
        for anchor_index in range(6):
            direction = anchor_index + 2
            if direction > 5:
                direction -= 6
            hexagon1 = anchor_hexagons[anchor_index]
            hexagon2 = anchor_hexagons[anchor_index + 1]
            x_axis_0, y_axis_0, z_axis_0 = hexagon1['x-axis'], hexagon1['y-axis'], hexagon1['z-axis']
            delta_x = (hexagon2['center'][0] - hexagon1['center'][0]) / (layer + 1)
            delta_y = (hexagon2['center'][1] - hexagon1['center'][1]) / (layer + 1)
            for index in range(layer):
                x0, y0 = hexagon1['center'][0] + delta_x * (index + 1), hexagon1['center'][1] + delta_y * (index + 1)
                result.append({
                    'center': (x0, y0),
                    'coords': create_hexagon_coords(x0, y0),
                    'x-axis': x_axis_0 + D_PARAMS[direction]['x-axis'] * (index + 1),
                    'y-axis': y_axis_0 + D_PARAMS[direction]['y-axis'] * (index + 1),
                    'z-axis': z_axis_0 + D_PARAMS[direction]['z-axis'] * (index + 1),
                    'color': OTHER_HEX_COLOR
                })

    return result


def draw_hexagon_list(sc, hexagon_list, font):
    for hexagon in hexagon_list:
        text = font.render(f'{hexagon["x-axis"]} | {hexagon["y-axis"]} | {hexagon["z-axis"]}', True, (0, 0, 0))
        pg.draw.polygon(sc, hexagon['color'], hexagon['coords'])
        text_rect = text.get_rect()
        text_rect_width, text_rect_height = text_rect.width, text_rect.height
        sc.blit(text, (hexagon['center'][0] - text_rect_width // 2, hexagon['center'][1] - text_rect_height // 2))


def main():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    background_surface = create_background_surface()

    hexagon_list = create_hexagon_list()
    font = pg.font.Font(None, 24)

    while True:

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

        sc.blit(background_surface, (0, 0))
        draw_hexagon_list(sc, hexagon_list, font)
        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
