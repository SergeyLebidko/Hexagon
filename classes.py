import random
from copy import deepcopy
from math import pi, sin, cos

from settings import pg, W, H, HEX_MARGIN, D_PARAMS, FIGURES_DATA, BACKGROUND_STEP
from config import board
from records import records
from theme import theme
from fonts import fonts
from sprites import cache, shade
from utils import create_hexagon_coords, normalize_value, get_distance

# Визуальные эффекты берут случайность из отдельного генератора, чтобы шум фона
# и искры не сдвигали игровую последовательность фигур.
visual_random = random.Random()


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


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


class Layer:
    """Базовый слой отрисовки.

    Каждый слой держит собственную полноэкранную поверхность с настоящим
    альфа-каналом (он нужен для мягких теней и свечения) и помнит только ту
    область, которая изменилась с прошлого кадра. Благодаря этому статичный
    кадр не стоит вообще ничего, а во время анимации перерисовывается лишь
    небольшая часть экрана.
    """

    def __init__(self, sc):
        self.sc = sc
        self.surface = pg.Surface((W, H), pg.SRCALPHA).convert_alpha()
        self.surface.fill((0, 0, 0, 0))
        self.dirty_rect = None
        self.update_flag = True

    @property
    def bounds(self):
        """Область, которую слой может занимать."""
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
        # Обрезка критична: полупрозрачные элементы (тени, свечение) при
        # повторной отрисовке вне области накапливали бы альфу.
        self.surface.set_clip(rect)
        try:
            self.redraw(rect)
        finally:
            self.surface.set_clip(None)
        return rect

    def invalidate_all(self):
        self.invalidate(self.bounds)


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
        """Полная перерисовка: нужна при смене темы и выходе окна из-под другого."""
        self.full_redraw_pending = True
        self.background.invalidate()
        for layer in self.layers:
            layer.invalidate_all()


class Background(Layer):
    """Статичный фон: градиент, виньетка и мелкий шум."""

    STEP = BACKGROUND_STEP

    def __init__(self, sc):
        Layer.__init__(self, sc)
        self.surface = pg.Surface((W, H)).convert()
        # Фон строится долго, поэтому готовые варианты держим по темам.
        self._cache = {}
        self.rebuild()
        self.update_flag = False

    def rebuild(self):
        """Переключает фон на активную тему, собирая её при первом обращении."""
        name = theme.name
        base = self._cache.get(name)
        if base is None:
            base = self._build_theme()
            self._cache[name] = base
        self.surface = base

    def _build_theme(self):
        top = theme['background_top']
        bottom = theme['background_bottom']

        # Градиент считается на маленькой картинке и растягивается.
        sw, sh = 64, 64
        small = pg.Surface((sw, sh)).convert()
        for y in range(sh):
            for x in range(sw):
                t = (x * 0.6 + y) / (sw * 0.6 + sh)
                small.set_at((x, y), (
                    int(top[0] + (bottom[0] - top[0]) * t),
                    int(top[1] + (bottom[1] - top[1]) * t),
                    int(top[2] + (bottom[2] - top[2]) * t),
                ))
        base = pg.transform.smoothscale(small, (W, H)).convert()

        # Виньетка: края чуть темнее центра.
        vw, vh = 90, 60
        vig = pg.Surface((vw, vh)).convert()
        vig_color = theme['vignette']
        for y in range(vh):
            for x in range(vw):
                dx = (x - vw / 2) / (vw / 2)
                dy = (y - vh / 2) / (vh / 2)
                d = min(1.0, (dx * dx + dy * dy) ** 0.5)
                amount = int(vig_color[0] * (d ** 2.4))
                vig.set_at((x, y), (amount, amount, amount))
        base.blit(pg.transform.smoothscale(vig, (W, H)), (0, 0), special_flags=pg.BLEND_RGB_SUB)

        # Шум: убирает полосы и придаёт поверхности зернистость.
        low, high = theme['background_noise']
        columns = (W + self.STEP - 1) // self.STEP
        rows = (H + self.STEP - 1) // self.STEP
        span = high - low + 1
        raw = visual_random.randbytes(columns * rows)
        # Один байт на ячейку вместо трёх: шум серый, каналы совпадают.
        # Значения сразу индексируют палитру, поэтому заводим ровно span цветов.
        data = bytes(byte % span for byte in raw)
        grey = pg.image.frombuffer(data, (columns, rows), 'P')
        grey.set_palette([(low + i, low + i, low + i) for i in range(span)] +
                         [(0, 0, 0)] * (256 - span))
        noise = pg.transform.scale(grey.convert(), (W, H))
        flag = pg.BLEND_RGBA_MIN if theme['background_noise_mode'] == 'min' else pg.BLEND_RGBA_ADD
        base.blit(noise, (0, 0), special_flags=flag)

        return base

    def redraw(self, rect):
        # Фон неизменен: перерисовывать нечего.
        pass


class Hexagon:
    FAST_SCALE_SPEED = 0.2
    NORMAL_SCALE_SPEED = 0.1

    def __init__(self, x0, y0, ):
        self.x0, self.y0 = x0, y0
        self.current_scale = 1
        self.color_index = 0
        self.coords = create_hexagon_coords(x0, y0, self.current_scale)
        self.process_list = []

    @property
    def bbox(self):
        """Габариты гекса с запасом под тень и толщину обводки."""
        xs = [x for x, _ in self.coords]
        ys = [y for _, y in self.coords]
        return pg.Rect(
            int(min(xs)), int(min(ys)),
            int(max(xs)) - int(min(xs)) + 1,
            int(max(ys)) - int(min(ys)) + 1
        ).inflate(28, 28)

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

    def sprite(self):
        raise NotImplementedError

    def draw(self, surface, rect=None):
        sprite = self.sprite()
        offset_x = int(self.x0 - sprite.get_width() / 2)
        offset_y = int(self.y0 - sprite.get_height() / 2)
        if rect is not None:
            area = pg.Rect(offset_x, offset_y, *sprite.get_size())
            if not rect.colliderect(area):
                return
        surface.blit(sprite, (offset_x, offset_y))

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
            elif self.current_scale > target_scale:
                self.current_scale = max(target_scale, self.current_scale - step_scale)
            self.coords = create_hexagon_coords(self.x0, self.y0, self.current_scale)
            return self.current_scale == target_scale

        self.process_list.append(process)

    def has_process(self):
        return len(self.process_list) != 0


class FieldHexagon(Hexagon):

    def __init__(self, x0, y0, x_axis, y_axis, z_axis):
        Hexagon.__init__(self, x0, y0)
        self.x_axis, self.y_axis, self.z_axis = x_axis, y_axis, z_axis
        self.content = False
        self.state = 'empty'

    def sprite(self):
        return cache.hex_sprite(self.state, self.color_index, self.current_scale, theme)


class FigureHexagon(Hexagon):
    STEP_MOTION = 100

    def __init__(self, x0, y0):
        Hexagon.__init__(self, x0, y0)
        self.target_x0, self.target_y0 = self.x0, self.y0

    def sprite(self):
        return cache.hex_sprite('figure', self.color_index, self.current_scale, theme)

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
        self.hexagon_list = hexagon_list
        self.data_for_create = data_for_create
        self.color_index = 0
        self.render_scale = 1.0
        self.process_list = []

    @property
    def width(self):
        return self.max_x - self.min_x

    @property
    def height(self):
        return self.max_y - self.min_y

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
        """Габариты фигуры с учётом визуального масштаба."""
        if self.render_scale == 1.0:
            rect = self.hexagon_list[0].bbox
            for hexagon in self.hexagon_list[1:]:
                rect = rect.union(hexagon.bbox)
            return rect

        radius = int((board.radius + 18) * self.render_scale) + 4
        rect = None
        for hexagon in self.hexagon_list:
            hx, hy = self._scaled_center(hexagon)
            item = pg.Rect(int(hx) - radius, int(hy) - radius, radius * 2, radius * 2)
            rect = item if rect is None else rect.union(item)
        return rect

    @property
    def color_index(self):
        return self._color_index

    @color_index.setter
    def color_index(self, index):
        self._color_index = index
        for hexagon in self.hexagon_list:
            hexagon.color_index = index

    def collide(self, x, y):
        if self.render_scale == 1.0:
            return any(hexagon.collide(x, y) for hexagon in self.hexagon_list)
        # При уменьшенной фигуре попадание считается по экранным позициям.
        cx, cy = self.center
        for hexagon in self.hexagon_list:
            hx, hy = self._scaled_center(hexagon)
            radius = (board.radius - HEX_MARGIN) * self.render_scale
            if (x - hx) ** 2 + (y - hy) ** 2 <= radius * radius:
                return True
        return False

    def draw(self, surface, rect=None):
        for hexagon in self.hexagon_list:
            if self.render_scale == 1.0:
                hexagon.draw(surface, rect)
                continue
            hx, hy = self._scaled_center(hexagon)
            sprite = cache.hex_sprite('figure', self.color_index, self.render_scale, theme)
            offset = (int(hx - sprite.get_width() / 2), int(hy - sprite.get_height() / 2))
            area = pg.Rect(offset, sprite.get_size())
            if rect is not None and not rect.colliderect(area):
                continue
            surface.blit(sprite, offset)

    def update(self):
        changed = None
        for process in list(self.process_list):
            rect = self.bbox
            if process():
                self.process_list.remove(process)
            changed = rect.union(self.bbox) if changed is None else changed.union(rect).union(self.bbox)

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

    @property
    def center(self):
        """Геометрический центр фигуры."""
        return ((self.min_x + self.max_x) / 2, (self.min_y + self.max_y) / 2)

    def _scaled_center(self, hexagon):
        """Центр гекса в экранных координатах с учётом визуального масштаба.

        Логические координаты гексов не меняются: они должны оставаться на
        сетке, иначе фигура перестанет совпадать с ячейками поля. Поэтому
        при уменьшении фигуры её гексы стягиваются к центру только на экране.
        """
        cx, cy = self.center
        s = self.render_scale
        return cx + (hexagon.x0 - cx) * s, cy + (hexagon.y0 - cy) * s

    def scale(self, factor):
        """Задаёт визуальный масштаб всей фигуры."""
        changed = self.bbox
        self.render_scale = factor
        return changed.union(self.bbox)

    def start_scale_process(self, target_scale, step_scale):
        """Плавно меняет визуальный масштаб всей фигуры."""

        def process():
            current = self.render_scale
            if current < target_scale:
                next_scale = min(target_scale, current + step_scale)
            elif current > target_scale:
                next_scale = max(target_scale, current - step_scale)
            else:
                return True
            self.scale(next_scale)
            return next_scale == target_scale

        self.process_list.append(process)

    def start_offset_process(self, dx, dy):
        for hexagon in self.hexagon_list:
            hexagon.start_offset_process(dx, dy)

    def has_process(self):
        return bool(self.process_list) or any(hexagon.has_process() for hexagon in self.hexagon_list)

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
                    last_hexagon.x0 + 2 * board.normal * cos(alpha),
                    last_hexagon.y0 - 2 * board.normal * sin(alpha)
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
                'x': W - self.BORDER - self.slot_width - 14,
                'y': (H - self.slot_height * 3 - self.BORDER * 2) // 2
                     + index * (self.slot_height + self.BORDER),
                'figure': None
            })

        self.refresh_slots()
        self.invalidate(self.bounds)

    @property
    def bounds(self):
        rect = pg.Rect(int(self.slots[0]['x']), int(self.slots[0]['y']),
                       int(self.slot_width), int(self.slot_height))
        for slot in self.slots[1:]:
            rect = rect.union(pg.Rect(int(slot['x']), int(slot['y']),
                                      int(self.slot_width), int(self.slot_height)))
        return rect.inflate(40, 40)

    def refresh_slots(self):
        """Метод проверяет слоты и если находит пустой - добавляет в него фигуру из списка заранее созданных"""
        for slot in self.slots:
            if slot['figure']:
                continue
            figure = deepcopy(random.choice(self.figures_pool))
            # Цвет — только оформление, поэтому он не должен расходовать игровой random.
            figure.color_index = visual_random.randrange(9)
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
        self.surface.fill((0, 0, 0, 0), rect)

        for slot in self.slots:
            figure = slot['figure']
            if not figure:
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
        for layer in range(board.layers):
            anchor_hexagons = []
            alpha = 2 * pi / 6

            # Генерируем список опорных гексов
            for direction in range(6):
                anchor_hexagons.append(FieldHexagon(
                    center_hexagon.x0 + (2 * board.normal * (layer + 1)) * cos(alpha),
                    center_hexagon.y0 - (2 * board.normal * (layer + 1)) * sin(alpha),
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
        self._shadow = None

        self.invalidate(self.bounds)

    SHADOW_MARGIN = 54

    @property
    def bounds(self):
        """Границы слоя с запасом под мягкую тень доски.

        Без этого запаса клип слоя срезал бы тень по ровной линии у нижнего
        края — именно так она и выглядела обрезанной.
        """
        rect = self.hexagon_list[0].bbox
        for hexagon in self.hexagon_list[1:]:
            rect = rect.union(hexagon.bbox)
        return rect.inflate(self.SHADOW_MARGIN * 2, self.SHADOW_MARGIN * 2)

    def _get_shadow(self):
        """Мягкая тень под всей доской, чтобы поле «парило» над фоном.

        Поверхность тени совпадает с bounds слоя: иначе клип срезал бы её.
        """
        key = (len(self.hexagon_list), theme.name)
        if self._shadow is not None and self._shadow[0] == key:
            return self._shadow[1], self._shadow[2]

        rect = self.bounds
        shadow = pg.Surface(rect.size, pg.SRCALPHA)
        color = theme['board_shadow']
        for hexagon in self.hexagon_list:
            pg.draw.circle(
                shadow, color,
                (int(hexagon.x0 - rect.x), int(hexagon.y0 - rect.y + 10)),
                int(board.radius * 1.02))
        shadow = pg.transform.box_blur(shadow, 14)
        self._shadow = (key, shadow, rect)
        return shadow, rect

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
        self.surface.fill((0, 0, 0, 0), rect)

        shadow, shadow_rect = self._get_shadow()
        if rect.colliderect(shadow_rect):
            self.surface.blit(shadow, shadow_rect.topleft)

        for hexagon in self.hexagon_list:
            hexagon.draw(self.surface, rect)

        # Если нужно - отрисовываем кадр анимации
        for hexagon in self.animation:
            hexagon.draw(self.surface, rect)

    def mark_hexagons_under_figure(self, figure):
        """Метод перебирает гексы и помечает все свободные, расположенные под переданной фигурой"""
        free_hexagons_under_figure = self._get_free_hexagons_under_figure(figure)
        changed = None
        for hexagon in self.hexagon_list:
            if hexagon.content:
                continue
            state = 'marked' if hexagon in free_hexagons_under_figure else 'empty'
            if hexagon.state != state:
                hexagon.state = state
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
                    hexagon.state = 'empty'
                    changed = hexagon.bbox if changed is None else changed.union(hexagon.bbox)
                self.invalidate(changed)
            return False

        self.last_hexagon_add_count = len(free_hexagons_under_figure)
        changed = None
        for field_hexagon in free_hexagons_under_figure:
            field_hexagon.content = True
            field_hexagon.state = 'placed'
            field_hexagon.color_index = figure.color_index
            changed = field_hexagon.bbox if changed is None else changed.union(field_hexagon.bbox)
        self.invalidate(changed)
        return True

    def refresh_field(self):
        """Метод ищет заполненные строки и удаляет их, если находит"""
        self.last_line_remove_count = 0
        list_for_clear = []
        for axis in ['x_axis', 'y_axis', 'z_axis']:
            for val in range(-board.layers, board.layers + 1):
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
            hexagon.state = 'empty'
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
        reach = board.radius * board.radius
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
            return False

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
        self.surface.fill((0, 0, 0, 0), rect)
        if self.figure:
            self.figure.draw(self.surface, rect)


class FxLayer(Layer):
    """Слой эффектов: частицы и всплывающие очки."""

    def __init__(self, sc):
        Layer.__init__(self, sc)
        self.particles = []
        self.labels = []

    def burst(self, x, y, color_index, count=24):
        for _ in range(count):
            self.particles.append(Particle(x, y, color_index))

    def popup(self, x, y, text):
        self.labels.append(FloatingLabel(x, y, text))

    def clear(self):
        self.particles = []
        self.labels = []

    def update(self):
        if not self.particles and not self.labels:
            return

        changed = None
        survivors = []
        for particle in self.particles:
            old = particle.bbox
            if particle.step():
                survivors.append(particle)
                changed = old.union(particle.bbox) if changed is None else changed.union(old.union(particle.bbox))
            else:
                changed = old if changed is None else changed.union(old)
        self.particles = survivors

        survivors = []
        for label in self.labels:
            old = label.bbox
            if label.step():
                survivors.append(label)
                changed = old.union(label.bbox) if changed is None else changed.union(old.union(label.bbox))
            else:
                changed = old if changed is None else changed.union(old)
        self.labels = survivors

        if changed is not None:
            self.invalidate(changed)

    def redraw(self, rect):
        self.surface.fill((0, 0, 0, 0), rect)
        for particle in self.particles:
            particle.draw(self.surface, rect)
        for label in self.labels:
            label.draw(self.surface, rect)


class Particle:
    LIFETIME = 45

    def __init__(self, x, y, color_index):
        self.x, self.y = x, y
        angle = visual_random.uniform(0, 2 * pi)
        speed = visual_random.uniform(1.2, 4.2)
        self.vx = speed * cos(angle)
        self.vy = speed * sin(angle) - 1.0
        self.life = self.LIFETIME
        self.size = visual_random.randint(2, 4)
        self.color_index = color_index

    @property
    def bbox(self):
        pad = self.size + 2
        return pg.Rect(int(self.x - pad), int(self.y - pad), pad * 2, pad * 2)

    def step(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.16
        self.vx *= 0.99
        self.life -= 1
        return self.life > 0

    def draw(self, surface, rect):
        if not rect.colliderect(self.bbox):
            return
        ratio = self.life / self.LIFETIME
        base = theme.palette_color(self.color_index)
        color = shade(base, 0.45 + 0.55 * ratio)
        pg.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)


class FloatingLabel:
    LIFETIME = 50

    def __init__(self, x, y, text):
        self.x, self.y = x, y
        self.text = text
        self.life = self.LIFETIME

    @property
    def bbox(self):
        return pg.Rect(int(self.x - 60), int(self.y - 34), 120, 68)

    def step(self):
        self.y -= 0.9
        self.life -= 1
        return self.life > 0

    def draw(self, surface, rect):
        if not rect.colliderect(self.bbox):
            return
        ratio = max(0.0, self.life / self.LIFETIME)
        font = fonts.medium(30)
        color = shade(theme['text_primary'], 0.55 + 0.45 * ratio)
        text = font.render(self.text, True, color)
        text.set_alpha(int(255 * min(1.0, ratio * 1.6)))
        surface.blit(text, text.get_rect(center=(int(self.x), int(self.y))))


class Tab(Layer):
    BORDER = 10

    def __init__(self, sc):
        Layer.__init__(self, sc)
        self.score = 0
        self.target_score = 0
        self.final = False
        self.hovered = None
        self._rendered = {}

        self.label = fonts.regular(19)
        self.big = fonts.bold(64)
        self.info = fonts.medium(22)
        self.hint = fonts.regular(20)
        self.button_font = fonts.semibold(21)

        self.invalidate(self.bounds)

    def update_score(self, hexagon_count, line_count):
        self.target_score = self.score + hexagon_count + ((10 + 10 * line_count) / 2) * line_count

    def set_final_text(self):
        self.final = True
        self.invalidate_all()

    def update(self):
        if self.score < self.target_score:
            self.score += 1
            self.invalidate(self.bounds)

    @property
    def card_rect(self):
        """Карточка финального экрана. Она лежит по центру, поэтому текст
        не может оказаться поверх гексов игрового поля."""
        width, height = 560, 380
        return pg.Rect((W - width) // 2, (H - height) // 2, width, height)

    @property
    def button_rects(self):
        """Кнопки финального экрана: (действие, прямоугольник)."""
        card = self.card_rect
        width, height, gap = 200, 52, 24
        left = card.centerx - width - gap // 2
        top = card.bottom - height - 58
        return [
            ('new_game', pg.Rect(left, top, width, height)),
            ('quit', pg.Rect(left + width + gap, top, width, height)),
        ]

    def button_at(self, pos):
        """Возвращает действие кнопки под курсором или None."""
        if not self.final:
            return None
        for action, rect in self.button_rects:
            if rect.collidepoint(pos):
                return action
        return None

    def set_hover(self, pos):
        """Подсвечивает кнопку под курсором."""
        hovered = self.button_at(pos)
        if hovered != self.hovered:
            self.hovered = hovered
            self.invalidate(self.card_rect.inflate(60, 60))

    @property
    def bounds(self):
        if self.final:
            # Затемнение накрывает всё окно: под ним видно поле.
            return self.surface.get_rect()
        return pg.Rect(W // 2 - 200, 10, 400, 110)

    def _text(self, text, font, color):
        """Рендер с кэшем: шрифт перерисовывается только при смене значений."""
        key = (text, id(font), color)
        cached = self._rendered.get(key)
        if cached is None:
            cached = font.render(text, True, color)
            self._rendered[key] = cached
        return cached

    def _card_surface(self):
        """Карточка со скруглением и мягкой тенью, собирается один раз."""
        key = ('card', theme.name)
        cached = self._rendered.get(key)
        if cached is not None:
            return cached

        rect = self.card_rect
        margin = 28
        surface = pg.Surface((rect.width + margin * 2, rect.height + margin * 2), pg.SRCALPHA)

        shadow = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
        pg.draw.rect(shadow, theme['card_shadow'], shadow.get_rect(), border_radius=22)
        shadow = pg.transform.box_blur(shadow, 14)
        surface.blit(shadow, (margin, margin + 6))

        card = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
        pg.draw.rect(card, theme['card_fill'], card.get_rect(), border_radius=22)
        pg.draw.rect(card, theme['card_border'], card.get_rect(), width=1, border_radius=22)
        surface.blit(card, (margin, margin))

        result = (surface, margin)
        self._rendered[key] = result
        return result

    def redraw(self, rect):
        self.surface.fill((0, 0, 0, 0), rect)
        bounds = self.bounds
        if not rect.colliderect(bounds):
            return

        if self.final:
            self._redraw_final(rect)
            return

        center_x = bounds.centerx
        label = self._text('С Ч Ё Т', self.label, theme['text_secondary'])
        self.surface.blit(label, label.get_rect(center=(center_x, 30)))

        text = '{:,}'.format(self.score).replace(',', ' ')
        score = self._text(text, self.big, theme['text_primary'])
        shadow = self._text(text, self.big, theme['text_shadow'])
        rect_score = score.get_rect(center=(center_x, 74))
        self.surface.blit(shadow, rect_score.move(0, 3))
        self.surface.blit(score, rect_score)

    def _redraw_final(self, rect):
        # Затемняем поле: текст должен читаться, а не спорить с гексами.
        self.surface.fill(theme['overlay'], rect)

        card = self.card_rect
        surface, margin = self._card_surface()
        origin = (card.x - margin, card.y - margin)
        self.surface.blit(surface, origin)

        center_x = card.centerx
        title = self._text('ИГРА ОКОНЧЕНА', self.info, theme['text_final'])
        self.surface.blit(title, title.get_rect(center=(center_x, card.y + 54)))

        label = self._text('С Ч Ё Т', self.label, theme['text_secondary'])
        self.surface.blit(label, label.get_rect(center=(center_x, card.y + 92)))

        text = '{:,}'.format(self.score).replace(',', ' ')
        score = self._text(text, self.big, theme['text_primary'])
        shadow = self._text(text, self.big, theme['text_shadow'])
        rect_score = score.get_rect(center=(center_x, card.y + 152))
        self.surface.blit(shadow, rect_score.move(0, 3))
        self.surface.blit(score, rect_score)

        for action, button in self.button_rects:
            self._draw_button(action, button)

    def _draw_button(self, action, rect):
        if action == 'new_game':
            fill = theme['button_primary_hover'] if self.hovered == action else theme['button_primary']
            text_color = theme['button_primary_text']
            border = None
        else:
            fill = theme['button_secondary_hover'] if self.hovered == action else theme['button_secondary']
            text_color = theme['button_secondary_text']
            border = theme['button_border']

        pg.draw.rect(self.surface, fill, rect, border_radius=14)
        if border:
            pg.draw.rect(self.surface, border, rect, width=1, border_radius=14)

        caption = 'Новая игра' if action == 'new_game' else 'Выход'
        text = self._text(caption, self.button_font, text_color)
        self.surface.blit(text, text.get_rect(center=rect.center))


class Leaderboard(Layer):
    """Таблица лучших результатов в левом нижнем углу.

    Показывает тройку лучших для текущего размера поля: у каждого размера
    она своя. Текущий счёт подмешивается к сохранённым сразу, поэтому рекорд
    виден в момент, когда он обогнал третье место, а не только в конце партии.

    Панель стоит в углу, который остаётся свободным из-за ромбовидной формы
    поля: проверено попиксельно на всех трёх размерах.
    """

    WIDTH = 196
    HEIGHT = 132
    MARGIN = 24
    TITLE_TOP = 18
    ROW_TOP = 47
    ROW_STEP = 29
    TITLE = 'Л У Ч Ш И Е'
    PLACES = ('medal_gold', 'medal_silver', 'medal_bronze')

    def __init__(self, sc, tab):
        Layer.__init__(self, sc)
        self.tab = tab
        self.current = 0
        self._rendered = {}

        self.title_font = fonts.regular(12)
        self.score_font = fonts.semibold(17)
        self.digit_font = fonts.bold(10)

        self.invalidate(self.bounds)

    @property
    def rect(self):
        return pg.Rect(self.MARGIN, H - self.MARGIN - self.HEIGHT,
                       self.WIDTH, self.HEIGHT)

    @property
    def bounds(self):
        # Запас под мягкую тень карточки.
        return self.rect.inflate(48, 48)

    def attach(self, tab):
        """Привязывает новую партию: счёт живёт в объекте Tab."""
        self.tab = tab
        self.current = 0
        self.invalidate(self.bounds)

    def update(self):
        """Следит за счётом: таблица должна показывать его без задержки.

        Записывать результат здесь нельзя. За партию счёт проходит много
        значений — он прибавляется за каждую поставленную фигуру и за каждую
        удалённую линию, — и таблица заполнилась бы промежуточными числами
        одной и той же игры. Результат заносит main.py в конце партии,
        при выходе и при смене размера.

        Показываем при этом уже заработанное значение: tab.score догоняет
        tab.target_score по единице за кадр, но игроку важно видеть свой
        результат сразу, а не середину анимации.
        """
        score = max(int(self.tab.score), int(self.tab.target_score))
        if score == self.current:
            return
        self.current = score
        self.invalidate(self.bounds)

    def submit_current(self):
        """Заносит текущий результат в таблицу. Вызывается по итогам партии."""
        self.current = max(int(self.tab.score), int(self.tab.target_score))
        if self.current > 0:
            records.submit(board.size, self.current)
            self.invalidate(self.bounds)

    def redraw(self, rect):
        self.surface.fill((0, 0, 0, 0), rect)
        if not rect.colliderect(self.bounds):
            return

        card = self.rect
        surface, margin = self._card_surface()
        self.surface.blit(surface, (card.x - margin, card.y - margin))

        title = self._text(self.TITLE, self.title_font, theme['text_secondary'])
        self.surface.blit(title, title.get_rect(center=(card.centerx, card.y + self.TITLE_TOP)))

        values, highlight = records.entries(board.size, self.current)
        for index, value in enumerate(values):
            center_y = card.y + self.ROW_TOP + index * self.ROW_STEP

            if index == highlight:
                pill = pg.Rect(card.x + 8, center_y - 13, card.width - 16, 26)
                fill = pg.Surface(pill.size, pg.SRCALPHA)
                pg.draw.rect(fill, (*theme['button_primary'], 30), fill.get_rect(), border_radius=9)
                self.surface.blit(fill, pill.topleft)

            self._draw_cup(card.x + 30, center_y, self.PLACES[index], index + 1)

            color = theme['button_primary'] if index == highlight else theme['text_primary']
            text = '—' if value is None else '{:,}'.format(value).replace(',', ' ')
            score = self._text(text, self.score_font, color)
            self.surface.blit(score, score.get_rect(midright=(card.right - 14, center_y)))

    def _card_surface(self):
        """Карточка со скруглением и мягкой тенью, собирается один раз."""
        key = ('card', theme.name)
        cached = self._rendered.get(key)
        if cached is not None:
            return cached

        rect = self.rect
        margin = 18
        surface = pg.Surface((rect.width + margin * 2, rect.height + margin * 2), pg.SRCALPHA)

        shadow = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
        pg.draw.rect(shadow, theme['card_shadow'], shadow.get_rect(), border_radius=18)
        shadow = pg.transform.box_blur(shadow, 10)
        surface.blit(shadow, (margin, margin + 4))

        card = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
        pg.draw.rect(card, theme['card_fill'], card.get_rect(), border_radius=18)
        pg.draw.rect(card, theme['card_border'], card.get_rect(), width=1, border_radius=18)
        surface.blit(card, (margin, margin))

        result = (surface, margin)
        self._rendered[key] = result
        return result

    def _draw_cup(self, cx, cy, palette_key, number):
        """Кубок: чаша с градиентом, ручки, ножка и основание.

        На 20 px медаль с лентой превращается в грязное пятно, а кубок
        остаётся узнаваемым. Цифра места лежит прямо на чаше.
        """
        top, base, dark, ink = theme[palette_key]
        width, height = 24, 15
        origin_x, origin_y = cx - width // 2, cy - 12

        # Ручки рисуем первыми: чаша закроет их внутреннюю часть.
        for side in (-1, 1):
            pg.draw.circle(self.surface, dark, (cx + side * 12, cy - 8), 4, 2)

        bowl = pg.Surface((width, height), pg.SRCALPHA)
        for y in range(height):
            ratio = y / max(1, height - 1)
            color = tuple(int(a + (b - a) * ratio) for a, b in zip(top, base))
            pg.draw.line(bowl, color, (0, y), (width, y))

        mask = pg.Surface((width, height), pg.SRCALPHA)
        shape = [(2, 0), (width - 3, 0), (width - 8, height - 3), (7, height - 3)]
        pg.draw.polygon(mask, (255, 255, 255, 255), shape)
        bowl.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        self.surface.blit(bowl, (origin_x, origin_y))

        pg.draw.polygon(self.surface, dark, [(x + origin_x, y + origin_y) for x, y in shape], 1)
        pg.draw.polygon(self.surface, dark,
                        [(cx - 1, cy + 1), (cx + 2, cy + 1), (cx + 2, cy + 5), (cx - 1, cy + 5)])
        pg.draw.rect(self.surface, dark, pg.Rect(cx - 6, cy + 5, 12, 3), border_radius=1)

        digit = self._text(str(number), self.digit_font, ink)
        self.surface.blit(digit, digit.get_rect(center=(cx, cy - 5)))

    def _text(self, text, font, color):
        """Рендер с кэшем: шрифт перерисовывается только при смене значений."""
        key = (text, id(font), color)
        cached = self._rendered.get(key)
        if cached is None:
            cached = font.render(text, True, color)
            self._rendered[key] = cached
        return cached


class ThemeButton(Layer):
    """Кнопка переключения светлой и тёмной темы в левом верхнем углу.

    Раньше тему можно было сменить только клавишами T и F1, и в интерфейсе
    об этом ничего не говорило. Кнопка делает возможность видимой.
    """

    SIZE = 44
    MARGIN = 24

    def __init__(self, sc):
        Layer.__init__(self, sc)
        self.rect = pg.Rect(self.MARGIN, self.MARGIN, self.SIZE, self.SIZE)
        self.hovered = False
        self.invalidate(self.bounds)

    @property
    def bounds(self):
        # Запас под тень и подсветку, чтобы они не обрезались клипом слоя.
        return self.rect.inflate(24, 24)

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def set_hover(self, pos):
        hovered = self.hit(pos)
        if hovered != self.hovered:
            self.hovered = hovered
            self.invalidate(self.bounds)

    def redraw(self, rect):
        self.surface.fill((0, 0, 0, 0), rect)
        if not rect.colliderect(self.bounds):
            return

        body = self.rect
        fill = theme['theme_button_hover'] if self.hovered else theme['theme_button_fill']
        border = theme['theme_button_border_hover'] if self.hovered else theme['theme_button_border']
        color = theme['theme_button_icon_hover'] if self.hovered else theme['theme_button_icon']

        pg.draw.rect(self.surface, fill, body, border_radius=12)
        pg.draw.rect(self.surface, border, body, width=1, border_radius=12)

        cx, cy = body.center

        if theme.name == 'light':
            # Солнце: круг и восемь лучей.
            pg.draw.circle(self.surface, color, (cx, cy), 7)
            for index in range(8):
                angle = pi / 4 * index
                inner = 11
                outer = 15
                pg.draw.line(
                    self.surface, color,
                    (cx + inner * cos(angle), cy - inner * sin(angle)),
                    (cx + outer * cos(angle), cy - outer * sin(angle)),
                    2)
        else:
            # Луна: круг, из которого вырезан смещённый круг.
            radius = 9
            mask = pg.Surface((radius * 2 + 2, radius * 2 + 2), pg.SRCALPHA)
            pg.draw.circle(mask, (*color, 255), (radius + 1, radius + 1), radius)
            pg.draw.circle(mask, (0, 0, 0, 0), (radius + 6, radius - 2), radius)
            self.surface.blit(mask, (cx - radius - 1, cy - radius - 1))


class SizeButton(Layer):
    """Три кнопки выбора размера поля: S, M, L.

    Стоит под кнопкой темы. При переключении игра начинается заново — размер
    поля задаёт радиус гексов и их число, пересобрать партию на ходу нельзя.
    """

    SIZE = 44
    GAP = 8
    MARGIN = 24
    TOP = 80
    LABELS = ('S', 'M', 'L')

    def __init__(self, sc):
        Layer.__init__(self, sc)
        self.hovered = None
        self.font = fonts.semibold(20)
        self.invalidate(self.bounds)

    @property
    def rects(self):
        return [
            pg.Rect(self.MARGIN + index * (self.SIZE + self.GAP), self.TOP, self.SIZE, self.SIZE)
            for index in range(len(self.LABELS))
        ]

    @property
    def bounds(self):
        rect = self.rects[0]
        for item in self.rects[1:]:
            rect = rect.union(item)
        return rect.inflate(16, 16)

    def hit(self, pos):
        """Возвращает подпись размера под курсором или None."""
        for label, rect in zip(self.LABELS, self.rects):
            if rect.collidepoint(pos):
                return label
        return None

    def set_hover(self, pos):
        hovered = self.hit(pos)
        if hovered != self.hovered:
            self.hovered = hovered
            self.invalidate(self.bounds)

    def redraw(self, rect):
        self.surface.fill((0, 0, 0, 0), rect)
        if not rect.colliderect(self.bounds):
            return

        for label, button in zip(self.LABELS, self.rects):
            active = label == board.size
            if active:
                fill = theme['button_primary']
                border = None
                text_color = theme['button_primary_text']
            else:
                fill = theme['theme_button_hover'] if self.hovered == label else theme['theme_button_fill']
                border = theme['theme_button_border']
                text_color = theme['theme_button_icon']

            pg.draw.rect(self.surface, fill, button, border_radius=12)
            if border:
                pg.draw.rect(self.surface, border, button, width=1, border_radius=12)

            text = self.font.render(label, True, text_color)
            self.surface.blit(text, text.get_rect(center=button.center))
