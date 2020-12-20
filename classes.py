import random
from copy import deepcopy
from math import pi, sin, cos
from settings import pg, W, H, LAYERS_COUNT, NORMAL, D_PARAMS, EMPTY_HEXAGON_COLOR, FIGURES_DATA, COLOR_PRESETS, \
    TRANSPARENT_COLOR, BACKGROUND_COLORS_RANGE, FONT_COLOR, MARKED_HEXAGON_COLOR
from utils import create_hexagon_coords, normalize_value


class Background:
    STEP = 5

    def __init__(self, sc):
        self.sc = sc
        self.surface = pg.Surface((W, H))
        for y in range(0, H, self.STEP):
            for x in range(0, W, self.STEP):
                color_component = random.randint(*BACKGROUND_COLORS_RANGE)
                color = (color_component,) * 3
                pg.draw.rect(self.surface, color, (x, y, self.STEP, self.STEP))

    def draw(self):
        self.sc.blit(self.surface, (0, 0))


class Hexagon:

    def __init__(self, x0, y0, color=None):
        self.color = color
        self.x0, self.y0 = x0, y0
        self.coords = create_hexagon_coords(x0, y0)
        self._vectors = [(x - x0, y - y0) for x, y in self.coords]

    def draw(self, surface):
        if not self.color:
            raise Exception('Not color for hexagon!')
        pg.draw.polygon(surface, self.color, self.coords)
        pg.draw.lines(surface, self._get_border_color(), True, self.coords)

    def collide(self, x, y):
        tmp_coords = self.coords + [self.coords[0]]
        for (x1, y1), (x2, y2) in ((tmp_coords[index], tmp_coords[index + 1]) for index in range(len(tmp_coords) - 1)):
            a, b, c = y2 - y1, x1 - x2, y1 * (x2 - x1) - x1 * (y2 - y1)
            dot_val = normalize_value(a * x + b * y + c)
            if dot_val == 0:
                return True

            center_val = normalize_value(a * self.x0 + b * self.y0 + c)
            if dot_val != center_val:
                return False

        return True

    def scale(self, factor):
        self.coords = [(self.x0 + factor * dx, self.y0 + factor * dy) for dx, dy in self._vectors]

    def _get_border_color(self):
        return max(10, self.color[0] - 50), max(10, self.color[1] - 50), max(10, self.color[2] - 50)


class FieldHexagon(Hexagon):

    def __init__(self, x0, y0, x_axis, y_axis, z_axis):
        Hexagon.__init__(self, x0, y0, EMPTY_HEXAGON_COLOR)
        self.x_axis, self.y_axis, self.z_axis = x_axis, y_axis, z_axis
        self.content = False


class FigureHexagon(Hexagon):

    def __init__(self, x0, y0):
        Hexagon.__init__(self, x0, y0)

    def offset(self, delta_x, delta_y):
        self.x0, self.y0 = self.x0 + delta_x, self.y0 + delta_y
        self.coords = [(coord[0] + delta_x, coord[1] + delta_y) for coord in self.coords]


class Figure:

    def __init__(self):
        self.hexagon_list = []
        self.color = None
        self.data_for_create = None

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

    def offset(self, delta_x, delta_y):
        for hexagon in self.hexagon_list:
            hexagon.offset(delta_x, delta_y)

    def set_color(self, color):
        self.color = color
        for hexagon in self.hexagon_list:
            hexagon.color = color

    def draw(self, surface):
        for hexagon in self.hexagon_list:
            hexagon.draw(surface)

    def scale_hexagons(self, factor):
        for hexagon in self.hexagon_list:
            hexagon.scale(factor)

    def __len__(self):
        return len(self.hexagon_list)


class Pool:
    BORDER = 10
    ANIMATION_STEP = 0.2

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

            figure.data_for_create = figure_data
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

        # Данные для воспроизведения анимации появления фигуры
        self.animation = {'tape': False}

        # Заполняем слоты
        self.refresh_slots()

    def _add_figure_to_slot(self, figure, slot):
        x_anchor = slot['x'] + self.slot_width // 2 - figure.width // 2
        y_anchor = slot['y'] + self.slot_height // 2 - figure.height // 2
        delta_x, delta_y = x_anchor - figure.min_x, y_anchor - figure.min_y
        for hexagon in figure.hexagon_list:
            hexagon.offset(delta_x, delta_y)

        slot['figure'] = figure
        self.update_flag = True

    def refresh_slots(self):
        """Метод проверяет слоты и если находит пустой - добавляет в него фигуру из списка заранее созданных"""
        empty_slots = [slot for slot in self.slots if not slot['figure']]

        if empty_slots:
            self.animation = {
                'tape': True,
                'scale': 0.1,
                'figures': []
            }

        for slot in empty_slots:
            if slot['figure']:
                continue

            figure = deepcopy(random.choice(self.figures_pool))
            figure.set_color(random.choice(COLOR_PRESETS))
            self._add_figure_to_slot(figure, slot)

            # Добавляем анимацию появления
            figure.scale_hexagons(0.1)
            self.animation['figures'].append(figure)

    def draw(self):
        if self.update_flag:
            self.surface.fill(TRANSPARENT_COLOR)

            for slot in self.slots:
                figure = slot['figure']
                if not figure:
                    continue
                figure.draw(self.surface)

            # Если нужно - обрабатываем анимацию
            if self.animation['tape']:
                if self.animation['scale'] == 1:
                    self.animation['tape'] = False
                else:
                    self.animation['scale'] = min(1, self.animation['scale'] + self.ANIMATION_STEP)
                    for figure in self.animation['figures']:
                        figure.scale_hexagons(self.animation['scale'])

            self.update_flag = self.animation['tape']

        self.sc.blit(self.surface, (0, 0))

    def take_from_pool(self, x, y):
        """Метод отдает фигуру, если переданная точка попадает в один из её гексов"""
        for slot in self.slots:
            figure = slot['figure']
            if not figure:
                continue
            if figure.collide(x, y):
                slot['figure'] = None
                self.update_flag = True
                return figure

        return None

    def put_to_pool(self, figure):
        """Метод принимает фигуру и размещает ее в первом свободном слоте"""
        for slot in self.slots:
            if slot['figure']:
                continue
            self._add_figure_to_slot(figure, slot)

    def get_current_figures_list(self):
        return [slot['figure'] for slot in self.slots if slot['figure']]


class Field:
    ANIMATION_STEP = 0.1

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

        # Количество добавленных на предыдущем ходу гексов и количество удаленных на предыдущем ходу линий
        self.last_hexagon_add_count = 0
        self.last_line_remove_count = 0

        # Данные для воспроизведения анимации исчезновения гексов
        self.animation = {'tape': False}

    def draw(self):
        if self.update_flag:
            self.surface.fill(TRANSPARENT_COLOR)
            for hexagon in self.hexagon_list:
                hexagon.draw(self.surface)

            # Если нужно - отрисовываем кадр анимации
            if self.animation['tape']:
                self.animation['scale'] = max(0, self.animation['scale'] - self.ANIMATION_STEP)
                if self.animation['scale'] == 0:
                    self.animation['tape'] = False
                else:
                    for hexagon in self.animation['hexagon_list']:
                        hexagon.scale(self.animation['scale'])
                        hexagon.draw(self.surface)

            self.update_flag = self.animation['tape']

        self.sc.blit(self.surface, (0, 0))

    def mark_hexagons_under_figure(self, figure):
        """Метод перебирает гексы и помечает все свободные, расположенные под переданной фигурой"""
        free_hexagons_under_figure = self._get_free_hexagons_under_figure(figure)
        for hexagon in self.hexagon_list:
            if not hexagon.content:
                color_before = hexagon.color
                if hexagon in free_hexagons_under_figure:
                    hexagon.color = MARKED_HEXAGON_COLOR
                else:
                    hexagon.color = EMPTY_HEXAGON_COLOR
                if hexagon.color != color_before:
                    self.update_flag = True

    def put_figure(self, figure):
        """Метод принимает фигуру, пытается разместить её на игровом поле и возвращет True, если это удалось"""
        free_hexagons_under_figure = self._get_free_hexagons_under_figure(figure)

        if len(free_hexagons_under_figure) < len(figure):
            if free_hexagons_under_figure:
                for hexagon in free_hexagons_under_figure:
                    hexagon.color = EMPTY_HEXAGON_COLOR
                self.update_flag = True
            return False

        self.last_hexagon_add_count = len(free_hexagons_under_figure)
        for field_hexagon in free_hexagons_under_figure:
            field_hexagon.content = True
            field_hexagon.color = figure.color
        self.update_flag = True
        return True

    def refresh_field(self):
        """Метод ищет заполненные строки и удаляет их, если находит"""
        self.last_line_remove_count = 0
        list_for_clear = []
        for axis in ['x_axis', 'y_axis', 'z_axis']:
            for val in range(-LAYERS_COUNT, LAYERS_COUNT + 1):
                tmp_hexagon_list = [hexagon for hexagon in self.hexagon_list if getattr(hexagon, axis) == val]
                if all(hexagon.content for hexagon in tmp_hexagon_list):
                    self.last_line_remove_count += 1
                    list_for_clear.extend(tmp_hexagon_list)

        if not list_for_clear:
            return
        self.update_flag = True

        # Создаем данные для анимации
        self.animation = {
            'tape': True,
            'scale': 1,
            'hexagon_list': deepcopy(list_for_clear)

        }
        for hexagon in list_for_clear:
            hexagon.content = False
            hexagon.color = EMPTY_HEXAGON_COLOR

    def check_figures_list(self, figures_list):
        """Метод проверяет список фигур и возвращает True, если хотя бы одну из них можно разместить на гровом поле"""
        for figure in figures_list:
            for hexagon in self.hexagon_list:
                if hexagon.content:
                    continue

                x_axis, y_axis, z_axis = hexagon.x_axis, hexagon.y_axis, hexagon.z_axis
                for direction in figure.data_for_create:
                    x_axis += D_PARAMS[direction]['x-axis']
                    y_axis += D_PARAMS[direction]['y-axis']
                    z_axis += D_PARAMS[direction]['z-axis']
                    next_hexagon = self._get_hexagons_for_axises(x_axis, y_axis, z_axis)
                    if not next_hexagon or next_hexagon.content:
                        break
                else:
                    return True
        return False

    def get_scored_data(self):
        """
        Метод возвращает количество гексов в последней размещенной на поле фигуре и
        количество удаленных при последней проверке линий
        """
        return self.last_hexagon_add_count, self.last_line_remove_count

    def _get_hexagons_for_axises(self, x_axis, y_axis, z_axis):
        for hexagon in self.hexagon_list:
            if hexagon.x_axis == x_axis and hexagon.y_axis == y_axis and hexagon.z_axis == z_axis:
                return hexagon
        return None

    def _get_free_hexagons_under_figure(self, figure):
        result = []
        for field_hexagon in self.hexagon_list:
            if field_hexagon.content:
                continue
            for figure_hexagon in figure.hexagon_list:
                if field_hexagon.collide(figure_hexagon.x0, figure_hexagon.y0):
                    result.append(field_hexagon)

        return result


class DragAndDrop:

    def __init__(self, sc, pool, field):
        self.sc = sc
        self.pool = pool
        self.field = field
        self.figure = None
        self.surface = pg.Surface((W, H))
        self.surface.set_colorkey(TRANSPARENT_COLOR)
        self.update_flag = True

    def take(self, x, y):
        self.figure = self.pool.take_from_pool(x, y)
        if self.figure:
            self.figure.scale_hexagons(0.8)
            self.update_flag = True

    def drag(self, delta_x, delta_y):
        if not self.figure:
            return
        self.field.mark_hexagons_under_figure(self.figure)
        self.figure.offset(delta_x, delta_y)
        self.update_flag = True

    def drop(self):
        if not self.figure:
            return

        put_result = self.field.put_figure(self.figure)
        if not put_result:
            self.figure.scale_hexagons(1)
            self.pool.put_to_pool(self.figure)

        self.figure = None
        self.update_flag = True
        return put_result

    def draw(self):
        if self.update_flag:
            self.surface.fill(TRANSPARENT_COLOR)
            if self.figure:
                self.figure.draw(self.surface)
            self.update_flag = False

        self.sc.blit(self.surface, (0, 0))


class Tab:
    BORDER = 10

    def __init__(self, sc):
        self.sc = sc
        self.font = pg.font.Font(None, 48)
        self.surface = pg.Surface((W, H))
        self.surface.set_colorkey(TRANSPARENT_COLOR)
        self.score = 0
        self.text = '0'
        self.update_flag = True

    def update_score(self, hexagon_count, line_count):
        self.score += hexagon_count
        self.score += ((10 + 10 * line_count) / 2) * line_count
        self.text = str(int(self.score))
        self.update_flag = True

    def set_final_text(self):
        self.text = f'Game Over. Your score: {int(self.score)}. Press any key to new game...'
        self.update_flag = True

    def draw(self):
        if self.update_flag:
            self.surface = self.font.render(self.text, True, FONT_COLOR)
            self.update_flag = False

        surface_rect = self.surface.get_rect()
        x, y = W // 2 - surface_rect.width // 2, self.BORDER
        self.sc.blit(self.surface, (x, y))
