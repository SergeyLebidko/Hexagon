"""Игровой цикл.

Вынесен из start.pyw, чтобы проверки окружения и показ ошибок жили в точке
входа, а игровая логика оставалась простой.
"""
from settings import pg, W, H, WINDOW_TITLE, FPS, GAME_MODE, FINAL_MODE
from theme import theme, THEMES
from config import board, load_preferences, save_preferences
from sprites import cache
from classes import (Field, Pool, DragAndDrop, Background, Tab, Renderer,
                     FxLayer, ThemeButton, SizeButton, Leaderboard)
from records import records


def init_new_game(sc):
    field = Field(sc)
    pool = Pool(sc)
    drag_and_drop = DragAndDrop(sc, pool, field)
    tab = Tab(sc)
    return field, pool, drag_and_drop, tab


def apply_saved_preferences():
    """Применяет сохранённые настройки. Битый файл просто игнорируется."""
    prefs = load_preferences()
    if not prefs:
        return

    board.set_size(prefs.get('board_size', board.size))
    saved_theme = prefs.get('theme')
    if saved_theme in THEMES:
        theme.current = THEMES[saved_theme]


def store_preferences():
    save_preferences({'board_size': board.size, 'theme': theme.name})


def run():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    apply_saved_preferences()

    background = Background(sc)
    field, pool, drag_and_drop, tab = init_new_game(sc)
    fx = FxLayer(sc)
    theme_button = ThemeButton(sc)
    size_button = SizeButton(sc)
    leaderboard = Leaderboard(sc, tab)

    def build_layers():
        """Единственное место, где собирается список слоёв.

        Раньше список задавался в двух местах, и при перезапуске игры кнопка
        темы из него терялась: нарисоваться она больше не могла, хотя клики
        по её месту продолжали работать.
        """
        return [field, pool, drag_and_drop, fx, tab, leaderboard,
                theme_button, size_button]

    # Порядок слоёв задаёт порядок наложения: поле, пул, фигура под курсором,
    # эффекты, счёт и поверх всего кнопки в углу. Таблица лучших лежит над
    # счётом, поэтому затемнение финального экрана её не скрывает.
    renderer = Renderer(sc, background, build_layers())

    def restart_game():
        """Начинает новую партию, сохраняя выбранные размер и тему.

        Результат предыдущей партии уже занесён в таблицу в момент её
        окончания, поэтому здесь достаточно привязать новую партию.
        """
        nonlocal field, pool, drag_and_drop, tab
        field, pool, drag_and_drop, tab = init_new_game(sc)
        leaderboard.attach(tab)
        renderer.layers = build_layers()
        fx.clear()
        renderer.invalidate_all()

    def switch_theme():
        """Перекрашивает всё под выбранную тему.

        Спрайты и фон кэшируются по теме, поэтому повторное переключение
        не пересчитывает картинки заново.
        """
        theme.toggle()
        background.rebuild()
        field._shadow = None
        tab._rendered = {}
        leaderboard._rendered = {}
        leaderboard.invalidate(leaderboard.bounds)
        theme_button.invalidate(theme_button.bounds)
        size_button.invalidate(size_button.bounds)
        renderer.invalidate_all()
        store_preferences()

    def switch_size(size):
        """Меняет размер поля. Смена размера требует новой партии."""
        if size == board.size:
            return
        leaderboard.submit_current()
        records.save()
        board.set_size(size)
        # Спрайты нарисованы под конкретный радиус гекса - их нужно пересобрать.
        cache.clear()
        field._shadow = None
        size_button.invalidate(size_button.bounds)
        restart_game()
        store_preferences()

    def quit_game():
        """Сохраняет таблицу рекордов и закрывает игру.

        Рекорды пишутся на диск только здесь и при смене размера: счёт
        меняется десятки раз за партию, и сохранять файл каждый раз незачем.
        Незаконченная партия тоже попадает в таблицу — она про максимум
        набранных очков, а не про число доигранных игр.
        """
        leaderboard.submit_current()
        records.save()
        pg.quit()

    mode = GAME_MODE
    while True:

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                quit_game()
                return

            # Окно могло быть перекрыто или восстановлено - перерисовываем всё.
            if event.type == pg.WINDOWEXPOSED:
                renderer.invalidate_all()

            if event.type == pg.KEYDOWN and event.key in (pg.K_t, pg.K_F1):
                switch_theme()
                continue

            # Кнопки в углу обрабатываются раньше всего остального и
            # перехватывают клик: иначе он мог бы начать перетаскивание фигуры.
            if event.type == pg.MOUSEMOTION:
                theme_button.set_hover(event.pos)
                size_button.set_hover(event.pos)

            if event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
                if theme_button.hit(event.pos):
                    switch_theme()
                    continue
                size = size_button.hit(event.pos)
                if size:
                    switch_size(size)
                    continue

            if mode == GAME_MODE:
                if event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
                    drag_and_drop.take(*event.pos)

                if event.type == pg.MOUSEMOTION:
                    drag_and_drop.drag(*event.rel)

                if event.type == pg.MOUSEBUTTONUP and event.button == pg.BUTTON_LEFT:
                    if drag_and_drop.drop():
                        field.refresh_field()
                        pool.refresh_slots()

                        score_data = field.get_scored_data()
                        tab.update_score(*score_data)

                        # Эффекты: очки за фигуру и искры за удалённые линии.
                        gained = tab.target_score - tab.score
                        if gained > 0 and hasattr(fx, 'popup'):
                            fx.popup(event.pos[0], event.pos[1], '+{}'.format(int(round(gained))))
                        if score_data[1]:
                            for hexagon in field.animation:
                                fx.burst(hexagon.x0, hexagon.y0, hexagon.color_index, count=6)

                        figures_in_pool = pool.get_current_figures_list()
                        if not field.check_figures_list(figures_in_pool):
                            tab.set_final_text()
                            # Партия закончена — фиксируем результат. Раньше
                            # этого момента записывать нельзя: счёт проходит
                            # много промежуточных значений.
                            leaderboard.submit_current()
                            records.save()
                            mode = FINAL_MODE

            elif mode == FINAL_MODE:
                # Кнопки: наведение подсвечивает, клик выполняет действие.
                if event.type == pg.MOUSEMOTION:
                    tab.set_hover(event.pos)

                if event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
                    action = tab.button_at(event.pos)
                    if action == 'new_game':
                        restart_game()
                        mode = GAME_MODE
                    elif action == 'quit':
                        quit_game()
                        return

        renderer.draw()
        clock.tick(FPS)
