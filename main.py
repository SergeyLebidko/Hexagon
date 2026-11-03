"""Игровой цикл.

Вынесен из start.pyw, чтобы проверки окружения и показ ошибок жили в точке
входа, а игровая логика оставалась простой.
"""
from settings import pg, W, H, WINDOW_TITLE, FPS, GAME_MODE, FINAL_MODE
from theme import theme
from classes import Field, Pool, DragAndDrop, Background, Tab, Renderer, FxLayer


def init_new_game(sc):
    field = Field(sc)
    pool = Pool(sc)
    drag_and_drop = DragAndDrop(sc, pool, field)
    tab = Tab(sc)
    return field, pool, drag_and_drop, tab


def run():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    background = Background(sc)
    field, pool, drag_and_drop, tab = init_new_game(sc)
    fx = FxLayer(sc)
    # Порядок слоёв задаёт порядок наложения: поле, пул, фигура под курсором,
    # эффекты и счёт.
    renderer = Renderer(sc, background, [field, pool, drag_and_drop, fx, tab])

    def switch_theme():
        """Перекрашивает всё под выбранную тему.

        Спрайты и фон кэшируются по теме, поэтому повторное переключение
        не пересчитывает картинки заново.
        """
        theme.toggle()
        background.rebuild()
        pool._panel = None
        field._shadow = None
        tab._rendered = {}
        renderer.invalidate_all()

    mode = GAME_MODE
    while True:

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                return

            # Окно могло быть перекрыто или восстановлено - перерисовываем всё.
            if event.type == pg.WINDOWEXPOSED:
                renderer.invalidate_all()

            if event.type == pg.KEYDOWN and event.key in (pg.K_t, pg.K_F1):
                switch_theme()
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
                            mode = FINAL_MODE

            elif mode == FINAL_MODE:
                if event.type == pg.KEYDOWN:
                    field, pool, drag_and_drop, tab = init_new_game(sc)
                    renderer.layers = [field, pool, drag_and_drop, fx, tab]
                    fx.clear()
                    renderer.invalidate_all()
                    mode = GAME_MODE

        renderer.draw()
        clock.tick(FPS)
