import random
from copy import deepcopy
from math import pi, sin, cos
from settings import pg, W, H, LAYERS_COUNT, NORMAL, D_PARAMS, EMPTY_HEXAGON_COLOR, FIGURES_DATA, COLOR_PRESETS, \
    TRANSPARENT_COLOR, BACKGROUND_COLORS_RANGE, FONT_COLOR, MARKED_HEXAGON_COLOR
from utils import create_hexagon_coords, normalize_value, get_distance


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
    FAST_SCALE_SPEED = 0.2
    NORMAL_SCALE_SPEED = 0.1

    def __init__(self, x0, y0, ):
        self.x0, self.y0 = x0, y0
        self.current_scale = 1
        self.coords = create_hexagon_coords(x0, y0, self.current_scale)
        self.process_list = []

    def draw(self, surface):
        color = getattr(self, 'color')
        self._execute_process_list()
        pg.draw.polygon(surface, color, self.coords)
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

    def scale(self, next_scale):
        self.current_scale = next_scale
        self.coords = create_hexagon_coords(self.x0, self.y0, next_scale)

    def start_scale_process(self, target_scale, step_scale):
        def process():
            if self.current_scale < target_scale:
                self.current_scale = min(target_scale, self.current_scale + step_scale)
                self.coords = create_hexagon_coords(self.x0, self.y0, self.current_scale)
            elif self.current_scale > target_scale:
                self.current_scale = max(target_scale, self.current_scale - step_scale)
                self.coords = create_hexagon_coords(self.x0, self.y0, self.current_scale)
            return self.current_scale == target_scale

        self.process_list.append(process)

    def has_process(self):
        return len(self.process_list) != 0

    def _get_border_color(self):
        color = getattr(self, 'color')
        return max(10, color[0] - 50), max(10, color[1] - 50), max(10, color[2] - 50)

    def _execute_process_list(self):
        if not self.process_list:
            return
        next_process_list = []
        for process in self.process_list:
            end_flag = process()
            if not end_flag:
                next_process_list.append(process)
        self.process_list = next_process_list


class FieldHexagon(Hexagon):

    def __init__(self, x0, y0, x_axis, y_axis, z_axis):
        Hexagon.__init__(self, x0, y0)
        self.x_axis, self.y_axis, self.z_axis = x_axis, y_axis, z_axis
        self.content = False
        self.color = EMPTY_HEXAGON_COLOR


class FigureHexagon(Hexagon):
    STEP_MOTION = 100

    def __init__(self, x0, y0):
        Hexagon.__init__(self, x0, y0)
        self.target_x0, self.target_y0 = self.x0, self.y0

    def offset(self, delta_x, delta_y):
        self.x0, self.y0 = self.x0 + delta_x, self.y0 + delta_y
        self.coords = create_hexagon_coords(self.x0, self.y0, self.current_scale)

    def start_offset_process(self, dx, dy):
        target_x, target_y = self.x0 + dx, self.y0 + dy

        def process():
            current_distance = get_distance(self.x0, self.y0, target_x, target_y)
            delta_x = self.STEP_MOTION * ((target_x - self.x0) / current_distance)
            delta_y = self.STEP_MOTION * ((target_y - self.y0) / current_distance)
            next_x0, next_y0 = self.x0 + delta_x, self.y0 + delta_y
            next_distance = get_distance(next_x0, next_y0, target_x, target_y)
            if next_distance < current_distance:
                self.offset(delta_x, delta_y)
            else:
                self.x0, self.y0 = target_x, target_y
                self.coords = create_hexagon_coords(self.x0, self.y0, self.current_scale)
            return (self.x0, self.y0) == (target_x, target_y)

        self.process_list.append(process)


class Figure:

    def __init__(self, hexagon_list, data_for_create):
        self._color = None
        self.hexagon_list = hexagon_list
        self.data_for_create = data_for_create
        self.width = self.max_x - self.min_x
        self.height = self.max_y - self.min_y

    @property
    def min_x(self):
        return min(x for hexagon in self.hexagon_list for x, _ in hexagon.coords)

    @property
    def max_x(self):
        return max(x for hexagon in self.hexagon_list for x, _ in hexagon.coords)

    @property
    def min_y(self):
        return min(y for hexagon in self.hexagon_list for _, y in hexagon.coords)

    @property
    def max_y(self):
        return max(y for hexagon in self.hexagon_list for _, y in hexagon.coords)

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        for hexagon in self.hexagon_list:
            hexagon.color = color

    def collide(self, x, y):
        return any(hexagon.collide(x, y) for hexagon in self.hexagon_list)

    def draw(self, surface):
        for hexagon in self.hexagon_list:
            hexagon.draw(surface)

    def offset(self, delta_x, delta_y):
        for hexagon in self.hexagon_list:
            hexagon.offset(delta_x, delta_y)

    def scale(self, factor):
        for hexagon in self.hexagon_list:
            hexagon.scale(factor)

    def start_scale_process(self, target_scale, step_scale):
        for hexagon in self.hexagon_list:
            hexagon.start_scale_process(target_scale, step_scale)

    def start_offset_process(self, dx, dy):
        for hexagon in self.hexagon_list:
            hexagon.start_offset_process(dx, dy)

    def has_process(self):
        return any(hexagon.has_process() for hexagon in self.hexagon_list)

    def __len__(self):
        return len(self.hexagon_list)


class Pool:
    BORDER = 10

    def __init__(self, sc):
        self.sc = sc
        self.figures_pool = []

        # Генерируем все виды фигур
        for figure_data in FIGURES_DATA:
            hexagon_list = []
            x0 = y0 = 0
            last_hexagon = FigureHexagon(x0, y0)
            hexagon_list.append(last_hexagon)

            for direction in figure_data:
                alpha = pi / 3 + direction * (pi / 3)
                last_hexagon = FigureHexagon(
                    last_hexagon.x0 + 2 * NORMAL * cos(alpha),
                    last_hexagon.y0 - 2 * NORMAL * sin(alpha)
                )
                hexagon_list.append(last_hexagon)

            figure = Figure(hexagon_list, figure_data)
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

        # Заполняем слоты
        self.refresh_slots()

    def refresh_slots(self):
        """Метод проверяет слоты и если находит пустой - добавляет в него фигуру из списка заранее созданных"""
        for slot in self.slots:
            if slot['figure']:
                continue
            figure = deepcopy(random.choice(self.figures_pool))
            figure.color = random.choice(COLOR_PRESETS)
            anchor_x, anchor_y = self._get_slot_anchor_point(slot, figure)
            figure.offset(anchor_x - figure.min_x, anchor_y - figure.min_y)
            slot['figure'] = figure
            self.update_flag = True

            # Добавляем анимацию появления
            figure.scale(0.1)
            figure.start_scale_process(1, Hexagon.FAST_SCALE_SPEED)

    def draw(self):
        if self.update_flag:
            self.surface.fill(TRANSPARENT_COLOR)

            for slot in self.slots:
                figure = slot['figure']
                if not figure:
                    continue
                figure.draw(self.surface)

            self.update_flag = any(slot['figure'].has_process() for slot in self.slots if slot['figure'])

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
            slot['figure'] = figure

            # Добавляем анимацию перемещения фигуры в слот
            anchor_x, anchor_y = self._get_slot_anchor_point(slot, figure)
            figure.start_offset_process(anchor_x - figure.min_x, anchor_y - figure.min_y)
            self.update_flag = True

    def get_current_figures_list(self):
        return [slot['figure'] for slot in self.slots if slot['figure']]

    def _get_slot_anchor_point(self, slot, figure):
        return slot['x'] + self.slot_width / 2 - figure.width / 2, slot['y'] + self.slot_height / 2 - figure.height / 2


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

        # Количество добавленных на предыдущем ходу гексов и количество удаленных на предыдущем ходу линий
        self.last_hexagon_add_count = 0
        self.last_line_remove_count = 0

        # Данные для воспроизведения анимации
        self.animation = []

    def draw(self):
        if self.update_flag:
            self.surface.fill(TRANSPARENT_COLOR)
            for hexagon in self.hexagon_list:
                hexagon.draw(self.surface)

            # Если нужно - отрисовываем кадр анимации
            self.update_flag = any(hexagon.has_process() for hexagon in self.animation)
            if self.update_flag:
                for hexagon in self.animation:
                    hexagon.draw(self.surface)

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
        self.animation = deepcopy(list_for_clear)
        for hexagon in self.animation:
            hexagon.start_scale_process(0.1, Hexagon.NORMAL_SCALE_SPEED)

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
            self.figure.scale(0.8)
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
            self.figure.scale(1)
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
        self.target_score = 0
        self.msg_template = '{SCORE}'
        self.update_flag = True

    def update_score(self, hexagon_count, line_count):
        self.target_score = self.score + hexagon_count + ((10 + 10 * line_count) / 2) * line_count
        self.update_flag = True

    def set_final_text(self):
        self.msg_template = 'Game Over. Your score: {SCORE}. Press any key to new game...'
        self.update_flag = True

    def draw(self):
        if self.update_flag:
            if self.score < self.target_score:
                self.score += 1
            self.surface = self.font.render(self.msg_template.format(SCORE=self.score), True, FONT_COLOR)
            self.update_flag = (self.score < self.target_score)

        surface_rect = self.surface.get_rect()
        x, y = W // 2 - surface_rect.width // 2, self.BORDER
        self.sc.blit(self.surface, (x, y))
