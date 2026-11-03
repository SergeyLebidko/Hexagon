import random
from copy import deepcopy
from math import pi, sin, cos
from settings import pg, W, H, LAYERS_COUNT, NORMAL, RADIUS, D_PARAMS, EMPTY_HEXAGON_COLOR, FIGURES_DATA, \
    COLOR_PRESETS, TRANSPARENT_COLOR, BACKGROUND_COLORS_RANGE, BACKGROUND_STEP, FONT_COLOR, MARKED_HEXAGON_COLOR
from utils import create_hexagon_coords, normalize_value, get_distance


def merge_rects(rects):
    """Объединяет пересекающиеся прямоугольники, чтобы не перерисовывать одну
    и ту же область дважды. Список прямоугольников обычно очень короткий
    (их не больше, чем слоёв), поэтому квадратичная сложность не важна."""
    merged = []
    for rect in rects:
        rect = pg.Rect(rect)
        index = 0
        while index < len(merged):
            if merged[index].colliderect(rect):
                rect = merged.pop(index).union(rect)
                index = 0
            else:
                index += 1
        merged.append(rect)
    return merged


class Layer:
    """Базовый слой отрисовки.

    Каждый слой держит собственную полноэкранную поверхность с прозрачным
    цветом-ключом. Поверхность перерисовывается и блитится не целиком, а
    только внутри области, которая изменилась с прошлого кадра. Благодаря
    этому статичный кадр не стоит вообще ничего, а во время анимации
    перерисовывается лишь небольшая часть экрана.
    """

    def __init__(self, sc):
        self.sc = sc
        self.surface = pg.Surface((W, H)).convert()
        self.surface.set_colorkey(TRANSPARENT_COLOR)
        self.surface.fill(TRANSPARENT_COLOR)
        self.dirty_rect = None
        self.update_flag = True

    @property
    def bounds(self):
        """Область, которую слой может занимать. Используется при первичной
        отрисовке, чтобы не перерисовывать весь экран без необходимости."""
        return self.surface.get_rect()

    def invalidate(self, rect=None):
        """Помечает область как требующую перерисовки."""
        if rect is None:
            rect = self.bounds
        rect = pg.Rect(rect)
        # Пустой прямоугольник объединять нельзя: он тянет результат к (0, 0).
        if rect.width <= 0 or rect.height <= 0:
            return
        self.dirty_rect = rect if self.dirty_rect is None else self.dirty_rect.union(rect)
        self.update_flag = True

    def update(self):
        """Продвигает анимации слоя. Вызывается каждый кадр."""
        return None

    def redraw(self, rect):
        """Перерисовывает содержимое слоя внутри указанной области."""
        raise NotImplementedError

    def render(self):
        """Перерисовывает изменившуюся область и возвращает её или None."""
        if self.dirty_rect is None:
            self.update_flag = False
            return None

        rect = self.dirty_rect
        self.dirty_rect = None
        self.update_flag = False
        self.redraw(rect)
        return rect


class Renderer:
    """Собирает кадр из слоёв, перерисовывая только изменившиеся области."""

    def __init__(self, sc, background, layers):
        self.sc = sc
        self.background = background
        self.layers = layers
        self.full_redraw_pending = True

    def draw(self):
        for layer in self.layers:
            layer.update()

        rects = [rect for rect in (layer.render() for layer in self.layers) if rect is not None]
        if not rects and not self.full_redraw_pending:
            return

        if self.full_redraw_pending:
            # Первый кадр и выход окна из-под другого окна: собираем всё заново.
            self.full_redraw_pending = False
            self.sc.blit(self.background.surface, (0, 0))
            for layer in self.layers:
                self.sc.blit(layer.surface, (0, 0))
            pg.display.update()
            return

        for rect in merge_rects(rects):
            self.sc.blit(self.background.surface, rect.topleft, rect)
            for layer in self.layers:
                self.sc.blit(layer.surface, rect.topleft, rect)

        pg.display.update(rects)

    def invalidate_all(self):
        """Полная перерисовка: нужна, когда окно показалось из-под другого окна."""
        self.full_redraw_pending = True
        self.background.invalidate()
        for layer in self.layers:
            layer.invalidate()


class Background(Layer):
    """Статичный фон. Генерируется один раз и дальше только блитится."""

    STEP = BACKGROUND_STEP

    def __init__(self, sc):
        Layer.__init__(self, sc)
        # Фон непрозрачный: цвет-ключ ему только мешает.
        self.surface.set_colorkey(None)
        self._generate()
        self.update_flag = False

    def _generate(self):
        """Генерирует шум по ячейкам STEPxSTEP.

        Вместо десятков тысяч отдельных draw.rect рисуется маленькая картинка
        размером с сетку ячеек, которая затем растягивается методом
        ближайшего соседа: каждый пиксель превращается в ровный квадрат.
        """
        columns = (W + self.STEP - 1) // self.STEP
        rows = (H + self.STEP - 1) // self.STEP
        low, high = BACKGROUND_COLORS_RANGE
        span = high - low + 1

        raw = random.randbytes(columns * rows * 3)
        data = bytes(low + (byte % span) for byte in raw)
        small = pg.image.frombuffer(data, (columns, rows), 'RGB')

        self.surface = pg.transform.scale(small, (W, H)).convert()

    def redraw(self, rect):
        # Фон неизменен: перерисовывать нечего.
        pass


class Hexagon:
    FAST_SCALE_SPEED = 0.2
    NORMAL_SCALE_SPEED = 0.1

    def __init__(self, x0, y0, ):
        self.x0, self.y0 = x0, y0
        self.current_scale = 1
        self.coords = create_hexagon_coords(x0, y0, self.current_scale)
        self.process_list = []

    @property
    def bbox(self):
        """Габариты гекса с запасом под толщину линии обводки."""
        xs = [x for x, _ in self.coords]
        ys = [y for _, y in self.coords]
        return pg.Rect(
            int(min(xs)), int(min(ys)),
            int(max(xs)) - int(min(xs)) + 1,
            int(max(ys)) - int(min(ys)) + 1
        ).inflate(4, 4)

    def update(self):
        """Продвигает анимации гекса. Возвращает изменившуюся область или None."""
        if not self.process_list:
            return None

        before = self.bbox
        next_process_list = []
        for process in self.process_list:
            if not process():
                next_process_list.append(process)
        self.process_list = next_process_list
        return before.union(self.bbox)

    def draw(self, surface):
        color = getattr(self, 'color')
        pg.draw.polygon(surface, color, self.coords)
        pg.draw.lines(surface, self._get_border_color(), True, self.coords)

    def collide(self, x, y):
        tmp_coords = self.coords + [self.coords[0]]
        for index in range(len(tmp_coords) - 1):
            x1, y1 = tmp_coords[index]
            x2, y2 = tmp_coords[index + 1]
            a, b, c = y2 - y1, x1 - x2, y1 * (x2 - x1) - x1 * (y2 - y1)
            dot_val = normalize_value(a * x + b * y + c)
            if dot_val == 0:
                # Точка лежит на прямой ребра. Это ещё не значит «внутри»:
                # продолжение ребра уходит далеко за пределы гекса, поэтому
                # решение отдаём остальным рёбрам.
                continue

            center_val = normalize_value(a * self.x0 + b * self.y0 + c)
            if dot_val != center_val:
                return False

        return True

    def scale(self, next_scale):
        before = self.bbox
        self.current_scale = next_scale
        self.coords = create_hexagon_coords(self.x0, self.y0, next_scale)
        return before.union(self.bbox)

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
        before = self.bbox
        self.x0, self.y0 = self.x0 + delta_x, self.y0 + delta_y
        self.coords = create_hexagon_coords(self.x0, self.y0, self.current_scale)
        return before.union(self.bbox)

    def start_offset_process(self, dx, dy):
        target_x, target_y = self.x0 + dx, self.y0 + dy

        def process():
            current_distance = get_distance(self.x0, self.y0, target_x, target_y)
            # Предотвращаем деление на ноль, если игрок возьмёт и сразу же отпустит фигурку
            if current_distance == 0:
                return True
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
    def bbox(self):
        rect = self.hexagon_list[0].bbox
        for hexagon in self.hexagon_list[1:]:
            rect = rect.union(hexagon.bbox)
        return rect

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

    def draw(self, surface, rect=None):
        """Рисует фигуру, при необходимости пропуская гексы вне rect."""
        for hexagon in self.hexagon_list:
            if rect is None or rect.colliderect(hexagon.bbox):
                hexagon.draw(surface)

    def update(self):
        """Продвигает анимации всех гексов фигуры. Возвращает изменившуюся область."""
        changed = None
        for hexagon in self.hexagon_list:
            rect = hexagon.update()
            if rect is not None:
                changed = rect if changed is None else changed.union(rect)
        return changed

    def offset(self, delta_x, delta_y):
        """Смещает фигуру. Возвращает область, которая была затронута."""
        changed = None
        for hexagon in self.hexagon_list:
            rect = hexagon.offset(delta_x, delta_y)
            changed = rect if changed is None else changed.union(rect)
        return changed

    def scale(self, factor):
        """Масштабирует фигуру. Возвращает область, которая была затронута."""
        changed = None
        for hexagon in self.hexagon_list:
            rect = hexagon.scale(factor)
            changed = rect if changed is None else changed.union(rect)
        return changed

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


class Pool(Layer):
    BORDER = 10

    def __init__(self, sc):
        Layer.__init__(self, sc)
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

        # Заполняем слоты
        self.refresh_slots()

    @property
    def bounds(self):
        rect = pg.Rect(int(self.slots[0]['x']), int(self.slots[0]['y']),
                       int(self.slot_width) + self.BORDER, int(self.slot_height) + self.BORDER)
        for slot in self.slots[1:]:
            rect = rect.union(pg.Rect(int(slot['x']), int(slot['y']),
                                      int(self.slot_width) + self.BORDER, int(self.slot_height) + self.BORDER))
        return rect

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

            # Добавляем анимацию появления
            figure.scale(0.1)
            figure.start_scale_process(1, Hexagon.FAST_SCALE_SPEED)
            self.invalidate(figure.bbox)

    def take_from_pool(self, x, y):
        """Метод отдает фигуру, если переданная точка попадает в один из её гексов"""
        for slot in self.slots:
            figure = slot['figure']
            if not figure:
                continue
            if figure.collide(x, y):
                slot['figure'] = None
                self.invalidate(figure.bbox)
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
            self.invalidate(figure.bbox)
            return

    def get_current_figures_list(self):
        return [slot['figure'] for slot in self.slots if slot['figure']]

    def update(self):
        changed = None
        for slot in self.slots:
            figure = slot['figure']
            if not figure:
                continue
            rect = figure.update()
            if rect is not None:
                changed = rect if changed is None else changed.union(rect)
        if changed is not None:
            self.invalidate(changed)

    def redraw(self, rect):
        self.surface.fill(TRANSPARENT_COLOR, rect)
        for slot in self.slots:
            figure = slot['figure']
            if not figure:
                continue
            if not rect.colliderect(figure.bbox):
                continue
            figure.draw(self.surface, rect)

    def _get_slot_anchor_point(self, slot, figure):
        return slot['x'] + self.slot_width / 2 - figure.width / 2, slot['y'] + self.slot_height / 2 - figure.height / 2


class Field(Layer):

    def __init__(self, sc):
        Layer.__init__(self, sc)
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

        # Количество добавленных на предыдущем ходу гексов и количество удаленных на предыдущем ходу линий
        self.last_hexagon_add_count = 0
        self.last_line_remove_count = 0

        # Данные для воспроизведения анимации
        self.animation = []

        self.invalidate(self.bounds)

    @property
    def bounds(self):
        rect = self.hexagon_list[0].bbox
        for hexagon in self.hexagon_list[1:]:
            rect = rect.union(hexagon.bbox)
        return rect

    def update(self):
        changed = None
        if self.animation:
            for hexagon in self.animation:
                rect = hexagon.update()
                if rect is not None:
                    changed = rect if changed is None else changed.union(rect)

            if not any(hexagon.has_process() for hexagon in self.animation):
                # Анимация закончилась - нужно стереть последний кадр.
                for hexagon in self.animation:
                    changed = hexagon.bbox if changed is None else changed.union(hexagon.bbox)
                self.animation = []

        if changed is not None:
            self.invalidate(changed)

    def redraw(self, rect):
        self.surface.fill(TRANSPARENT_COLOR, rect)
        for hexagon in self.hexagon_list:
            if rect.colliderect(hexagon.bbox):
                hexagon.draw(self.surface)

        # Если нужно - отрисовываем кадр анимации
        for hexagon in self.animation:
            if rect.colliderect(hexagon.bbox):
                hexagon.draw(self.surface)

    def mark_hexagons_under_figure(self, figure):
        """Метод перебирает гексы и помечает все свободные, расположенные под переданной фигурой"""
        free_hexagons_under_figure = self._get_free_hexagons_under_figure(figure)
        changed = None
        for hexagon in self.hexagon_list:
            if not hexagon.content:
                color_before = hexagon.color
                if hexagon in free_hexagons_under_figure:
                    hexagon.color = MARKED_HEXAGON_COLOR
                else:
                    hexagon.color = EMPTY_HEXAGON_COLOR
                if hexagon.color != color_before:
                    changed = hexagon.bbox if changed is None else changed.union(hexagon.bbox)

        if changed is not None:
            self.invalidate(changed)

    def put_figure(self, figure):
        """Метод принимает фигуру, пытается разместить её на игровом поле и возвращет True, если это удалось"""
        free_hexagons_under_figure = self._get_free_hexagons_under_figure(figure)

        # Сравниваем именно на равенство: если гекс фигуры попал сразу в две
        # ячейки (или два гекса слиплись в одной), число ячеек не совпадёт с
        # числом гексов, и такой бросок нужно отклонить.
        if len(free_hexagons_under_figure) != len(figure):
            if free_hexagons_under_figure:
                changed = None
                for hexagon in free_hexagons_under_figure:
                    hexagon.color = EMPTY_HEXAGON_COLOR
                    changed = hexagon.bbox if changed is None else changed.union(hexagon.bbox)
                self.invalidate(changed)
            return False

        self.last_hexagon_add_count = len(free_hexagons_under_figure)
        changed = None
        for field_hexagon in free_hexagons_under_figure:
            field_hexagon.content = True
            field_hexagon.color = figure.color
            changed = field_hexagon.bbox if changed is None else changed.union(field_hexagon.bbox)
        self.invalidate(changed)
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

        # Создаем данные для анимации
        self.animation = deepcopy(list_for_clear)
        for hexagon in self.animation:
            hexagon.start_scale_process(0.1, Hexagon.NORMAL_SCALE_SPEED)

        changed = None
        for hexagon in list_for_clear:
            hexagon.content = False
            hexagon.color = EMPTY_HEXAGON_COLOR
            changed = hexagon.bbox if changed is None else changed.union(hexagon.bbox)
        self.invalidate(changed)

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
        centers = [(hexagon.x0, hexagon.y0) for hexagon in figure.hexagon_list]
        # Гекс фигуры не может накрыть ячейку, центр которой дальше его радиуса,
        # поэтому такие пары отсеиваем ещё до дорогой проверки на пересечение.
        reach = RADIUS * RADIUS
        for field_hexagon in self.hexagon_list:
            if field_hexagon.content:
                continue
            for x0, y0 in centers:
                delta_x = field_hexagon.x0 - x0
                delta_y = field_hexagon.y0 - y0
                if delta_x * delta_x + delta_y * delta_y >= reach:
                    continue
                if field_hexagon.collide(x0, y0):
                    result.append(field_hexagon)
                    # Один гекс фигуры не должен добавлять одну и ту же ячейку дважды.
                    break

        return result


class DragAndDrop(Layer):

    def __init__(self, sc, pool, field):
        Layer.__init__(self, sc)
        self.pool = pool
        self.field = field
        self.figure = None

    def take(self, x, y):
        self.figure = self.pool.take_from_pool(x, y)
        if self.figure:
            self.invalidate(self.figure.scale(0.8))

    def drag(self, delta_x, delta_y):
        if not self.figure:
            return
        self.field.mark_hexagons_under_figure(self.figure)
        self.invalidate(self.figure.offset(delta_x, delta_y))

    def drop(self):
        if not self.figure:
            return

        put_result = self.field.put_figure(self.figure)
        if not put_result:
            self.invalidate(self.figure.scale(1))
            self.pool.put_to_pool(self.figure)
        else:
            self.invalidate(self.figure.bbox)

        self.figure = None
        return put_result

    def update(self):
        if self.figure:
            rect = self.figure.update()
            if rect is not None:
                self.invalidate(rect)

    def redraw(self, rect):
        self.surface.fill(TRANSPARENT_COLOR, rect)
        if self.figure:
            self.figure.draw(self.surface, rect)


class Tab(Layer):
    BORDER = 10

    def __init__(self, sc):
        Layer.__init__(self, sc)
        self.font = pg.font.Font(None, 48)
        self.score = 0
        self.target_score = 0
        self.msg_template = '{SCORE}'
        self.text_surface = None
        self.text_rect = pg.Rect(0, 0, 0, 0)
        self._render_text()

    def update_score(self, hexagon_count, line_count):
        self.target_score = self.score + hexagon_count + ((10 + 10 * line_count) / 2) * line_count

    def set_final_text(self):
        self.msg_template = 'Game Over. Your score: {SCORE}. Press any key to new game...'
        self._render_text()

    def update(self):
        if self.score < self.target_score:
            self.score += 1
            self._render_text()

    def _render_text(self):
        old_rect = self.text_rect
        self.text_surface = self.font.render(self.msg_template.format(SCORE=self.score), True, FONT_COLOR)
        self.text_rect = self.text_surface.get_rect()
        self.text_rect.centerx = W // 2
        self.text_rect.y = self.BORDER
        # Ширина строки меняется вместе со счётом, поэтому стираем и старую область.
        self.invalidate(old_rect.union(self.text_rect))

    @property
    def bounds(self):
        return self.text_rect

    def redraw(self, rect):
        self.surface.fill(TRANSPARENT_COLOR, rect)
        self.surface.blit(self.text_surface, self.text_rect)
