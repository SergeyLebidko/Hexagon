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
RADIUS = 40
NORMAL = RADIUS * cos(pi / 6)
HEX_MARGIN = 3

# Параметры игрового поля
LAYERS_COUNT = 4
EMPTY_HEXAGON_COLOR = (220, 220, 220)

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

# Цветовые пресеты для фигур
COLOR_PRESETS = [
    (255, 0, 0),
    (5, 200, 100),
    (0, 0, 255),
    (128, 0, 255),
    (255, 0, 255),
    (255, 128, 0),
    (30, 30, 30),
    (150, 150, 150),
    (175, 62, 18),
    (0, 128, 255)
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