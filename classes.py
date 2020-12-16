import random
from math import pi, sin, cos
from settings import pg, W, H, LAYERS_COUNT, NORMAL, D_PARAMS, EMPTY_HEXAGON_COLOR, FIGURES_DATA, COLOR_PRESETS
from utils import create_hexagon_coords


class Hexagon:

    def __init__(self, x0, y0):
        self.x0, self.y0 = x0, y0
        self.coords = create_hexagon_coords(x0, y0)


class FieldHexagon(Hexagon):

    def __init__(self, x0, y0, x_axis, y_axis, z_axis):
        Hexagon.__init__(self, x0, y0)
        self.x_axis, self.y_axis, self.z_axis = x_axis, y_axis, z_axis
        self.content = None


class FigureHexagon(Hexagon):

    def __init__(self, x0, y0):
        Hexagon.__init__(self, x0, y0)


class Figure:

    def __init__(self):
        self.hexagon_list = []

    @property
    def size(self):
        all_x = [coord[0] for hexagon in self.hexagon_list for coord in hexagon.coords]
        all_y = [coord[1] for hexagon in self.hexagon_list for coord in hexagon.coords]

        # Возвращаем кортеж (ширина, высота)
        return max(all_x) - min(all_x), max(all_y) - min(all_y)


class Pool:
    BORDER = 10

    def __init__(self):
        self.figures_pool = []

        # Генерируем все виды фигур
        max_w = max_h = 0
        for figure_data in FIGURES_DATA:
            x0 = y0 = 0
            figure = Figure()
            last_hexagon = FigureHexagon(x0, y0)
            figure.hexagon_list.append(last_hexagon)

            for direction in figure_data:
                alpha = pi / 3 + direction * (pi / 3)
                last_hexagon = FigureHexagon(
                    last_hexagon.x0 + 2 * NORMAL * cos(alpha),
                    last_hexagon.y0 - 2 * NORMAL * sin(alpha)
                )
                figure.hexagon_list.append(last_hexagon)

            self.figures_pool.append(figure)

            # Определяем габариты созданной фигуры и находим среди них максимальные
            max_w = max(figure.size[0], max_w)
            max_h = max(figure.size[1], max_h)

        # Находим опорные точки для слотов и отображения фигур в них
        self.slot_height = max_h
        self.slot_width = max_w
        self.slots_baseline = W - self.BORDER - max_w


class Field:

    def __init__(self, sc):
        self.sc = sc
        self.hexagon_list = []

        # Создаем центральный гекс
        x0, y0 = W // 2, H // 2
        center_hexagon = FieldHexagon(x0, y0, 0, 0, 0)
        self.hexagon_list.append(center_hexagon)

        # Последовательно создаем слои гексов вокруг центрального
        delta_alpha = pi / 3
        for layer in range(LAYERS_COUNT):
            anchor_hexagons = []
            alpha = 2 * pi / 6

            # Генерируем список опорных гексов
            for direction in range(6):
                anchor_hexagons.append(FieldHexagon(
                    center_hexagon.x0 + (2 * NORMAL * (layer + 1)) * cos(alpha),
                    center_hexagon.y0 - (2 * NORMAL * (layer + 1)) * sin(alpha),
                    D_PARAMS[direction]['x-axis'] * (layer + 1),
                    D_PARAMS[direction]['y-axis'] * (layer + 1),
                    D_PARAMS[direction]['z-axis'] * (layer + 1)
                ))
                alpha += delta_alpha

            self.hexagon_list.extend(anchor_hexagons)
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
                x_axis_0, y_axis_0, z_axis_0 = hexagon1.x_axis, hexagon1.y_axis, hexagon1.z_axis
                delta_x = (hexagon2.x0 - hexagon1.x0) / (layer + 1)
                delta_y = (hexagon2.y0 - hexagon1.y0) / (layer + 1)
                for index in range(layer):
                    self.hexagon_list.append(FieldHexagon(
                        hexagon1.x0 + delta_x * (index + 1),
                        hexagon1.y0 + delta_y * (index + 1),
                        x_axis_0 + D_PARAMS[direction]['x-axis'] * (index + 1),
                        y_axis_0 + D_PARAMS[direction]['y-axis'] * (index + 1),
                        z_axis_0 + D_PARAMS[direction]['z-axis'] * (index + 1)
                    ))

        # Создаем поверхность для отрисовки
        self.surface = pg.Surface((W, H))
        self.surface.set_colorkey((0, 0, 0))
        self.update_flag = True

    def draw_field(self):
        if self.update_flag:
            self.surface.fill((0, 0, 0))
            for hexagon in self.hexagon_list:
                color = (255, 0, 0) if hexagon.content else EMPTY_HEXAGON_COLOR
                pg.draw.polygon(self.surface, color, hexagon.coords)
            self.update_flag = False
        self.sc.blit(self.surface, (0, 0))
