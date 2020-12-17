import random
from copy import deepcopy
from math import pi, sin, cos
from settings import pg, W, H, LAYERS_COUNT, NORMAL, D_PARAMS, EMPTY_HEXAGON_COLOR, FIGURES_DATA, COLOR_PRESETS, \
    TRANSPARENT_COLOR
from utils import create_hexagon_coords, normalize_value


class Hexagon:

    def __init__(self, x0, y0):
        self.x0, self.y0 = x0, y0
        self.coords = create_hexagon_coords(x0, y0)

    def draw(self, surface, color):
        pg.draw.polygon(surface, color, self.coords)

    def offset(self, delta_x, delta_y):
        self.x0, self.y0 = self.x0 + delta_x, self.y0 + delta_y
        self.coords = [(coord[0] + delta_x, coord[1] + delta_y) for coord in self.coords]

    def collide(self, x, y):
        tmp_coords = self.coords + [self.coords[0]]
        for (x1, y1), (x2, y2) in ((tmp_coords[index], tmp_coords[index + 1]) for index in range(6)):
            a = y2 - y1
            b = x1 - x2
            c = y1 * (x2 - x1) - x1 * (y2 - y1)
            dot_val = normalize_value(a * x + b * y + c)
            if dot_val == 0:
                return True

            center_val = normalize_value(a * self.x0 + b * self.y0 + c)
            if dot_val != center_val:
                return False

        return True


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
        self.color = None

    @property
    def min_x(self):
        return min(coord[0] for hexagon in self.hexagon_list for coord in hexagon.coords)

    @property
    def max_x(self):
        return max(coord[0] for hexagon in self.hexagon_list for coord in hexagon.coords)

    @property
    def min_y(self):
        return min(coord[1] for hexagon in self.hexagon_list for coord in hexagon.coords)

    @property
    def max_y(self):
        return max(coord[1] for hexagon in self.hexagon_list for coord in hexagon.coords)

    @property
    def width(self):
        return self.max_x - self.min_x

    @property
    def height(self):
        return self.max_y - self.min_y

    def collide(self, x, y):
        return any(hexagon.collide(x, y) for hexagon in self.hexagon_list)

    def draw(self, surface):
        if not self.color:
            raise Exception('Figure without color!')
        for hexagon in self.hexagon_list:
            hexagon.draw(surface, self.color)


class Pool:
    BORDER = 10

    def __init__(self, sc):
        self.sc = sc
        self.figures_pool = []

        # Генерируем все виды фигур
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

        # Определяем максимальные габариты фигур
        self.slot_width = max(figure.width for figure in self.figures_pool)
        self.slot_height = max(figure.height for figure in self.figures_pool)

        self.slots = []
        for index in range(3):
            self.slots.append({
                'x': W - self.BORDER - self.slot_width,
                'y': (H - self.slot_height * 3 - self.BORDER * 2) // 2 + index * (self.slot_height + self.BORDER),
                'figure': None
            })

        # Создаем поверхность для отрисовки
        self.surface = pg.Surface((W, H))
        self.surface.set_colorkey(TRANSPARENT_COLOR)
        self.update_flag = True

    def refresh_slots(self):
        for slot in self.slots:
            if slot['figure']:
                continue

            figure = deepcopy(random.choice(self.figures_pool))
            figure.color = random.choice(COLOR_PRESETS)
            x_anchor = slot['x'] + self.slot_width // 2 - figure.width // 2
            y_anchor = slot['y'] + self.slot_height // 2 - figure.height // 2
            delta_x, delta_y = x_anchor - figure.min_x, y_anchor - figure.min_y
            for hexagon in figure.hexagon_list:
                hexagon.offset(delta_x, delta_y)

            slot['figure'] = figure
            self.update_flag = True

    def draw_slots(self):
        if self.update_flag:
            self.surface.fill(TRANSPARENT_COLOR)
            for slot in self.slots:
                figure = slot['figure']
                if figure:
                    figure.draw(self.surface)

            self.update_flag = False

        self.sc.blit(self.surface, (0, 0))

    def collide(self, x, y):
        for slot in self.slots:
            figure = slot['figure']
            if not figure:
                continue
            if figure.collide(x, y):
                return True

        return False


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
        self.surface.set_colorkey(TRANSPARENT_COLOR)
        self.update_flag = True

    def draw_field(self):
        if self.update_flag:
            self.surface.fill(TRANSPARENT_COLOR)
            for hexagon in self.hexagon_list:
                color = (255, 0, 0) if hexagon.content else EMPTY_HEXAGON_COLOR
                hexagon.draw(self.surface, color)
            self.update_flag = False
        self.sc.blit(self.surface, (0, 0))
