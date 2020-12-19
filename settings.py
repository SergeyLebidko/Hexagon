from math import pi, cos

# Добавлен сюда, чтобы избежать циклического импорта в других модулях
import pygame as pg

# Параметры окна
WINDOW_TITLE = 'Hexagon'
W, H = 1400, 900

# Частота ткадров
FPS = 30

# Цветовой диапазон для отрисовки фона
BACKGROUND_COLORS_RANGE = (240, 250)

# Параметры отдельных гексов
RADIUS = 45
NORMAL = RADIUS * cos(pi / 6)
HEX_MARGIN = 3

# Параметры сглаживания углов гексов
SMOOTH_FACTOR = 0.15
SMOOTH_DEPTH = 1

# Параметры игрового поля
LAYERS_COUNT = 4
EMPTY_HEXAGON_COLOR = (220, 220, 220)
MARKED_HEXAGON_COLOR = (180, 180, 180)

# Параметры смещений для корректной нумерации гексов на игровом поле
D_PARAMS = [
    {'x-axis': 1, 'y-axis': 1, 'z-axis': 0},
    {'x-axis': 1, 'y-axis': 0, 'z-axis': -1},
    {'x-axis': 0, 'y-axis': -1, 'z-axis': -1},
    {'x-axis': -1, 'y-axis': -1, 'z-axis': 0},
    {'x-axis': -1, 'y-axis': 0, 'z-axis': 1},
    {'x-axis': 0, 'y-axis': 1, 'z-axis': 1},
]

# Цвет, который будет использоваться как прозрачный при создании поверхностей
TRANSPARENT_COLOR = (0, 0, 0)

# Цвет шрифта
FONT_COLOR = (0, 191, 255)

# Цветовые пресеты для фигур
COLOR_PRESETS = [
    (255, 69, 0),
    (138, 43, 226),
    (30, 144, 255),
    (0, 139, 139),
    (139, 0, 139),
    (199, 21, 133)
]

# Исходные данные для создания фигур
FIGURES_DATA = [
    [],
    [3, 5, 3],
    [5, 3, 5],
    [3, 5, 0],
    [5, 5, 5],
    [3, 3, 3],
    [4, 4, 4],
    [4, 4, 2],
    [3, 3, 5],
    [0, 0, 4],
    [5, 5, 1],
    [1, 1, 3],
    [2, 2, 0],
    [4, 3, 2, 1],
    [5, 4, 3, 2],
    [2, 3, 4, 5],
    [1, 2, 3, 4],
    [0, 5, 4, 3],
    [3, 4, 5, 0],
    [0, 0, 2],
    [1, 1, 5],
    [4, 4, 0],
    [5, 5, 3],
    [3, 3, 1],
    [2, 2, 4]
]

# Режимы работы
GAME_MODE = 'game_mode'
FINAL_MODE = 'final_mode'

# Коэффициенты масштабирования для эффекта взятия фигуры мышкой
SCALE_FACTOR_LESS = 0.8
SCALE_FACTOR_MORE = 1 / SCALE_FACTOR_LESS
