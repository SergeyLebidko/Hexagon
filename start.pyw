#!/usr/bin/env python3
from settings import pg, W, H, WINDOW_TITLE, FPS, GAME_MODE, FINAL_MODE
from classes import Field, Pool, DragAndDrop, Background, Tab, Renderer


def init_new_game(sc):
    field = Field(sc)
    pool = Pool(sc)
    drag_and_drop = DragAndDrop(sc, pool, field)
    tab = Tab(sc)
    return field, pool, drag_and_drop, tab


def main():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    background = Background(sc)
    field, pool, drag_and_drop, tab = init_new_game(sc)
    # Порядок слоёв задаёт порядок наложения: фон, поле, пул, фигура под курсором, счёт.
    renderer = Renderer(sc, background, [field, pool, drag_and_drop, tab])

    mode = GAME_MODE
    while True:

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

            # Окно могло быть перекрыто или восстановлено - перерисовываем всё.
            if event.type == pg.WINDOWEXPOSED:
                renderer.invalidate_all()

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

                        figures_in_pool = pool.get_current_figures_list()
                        if not field.check_figures_list(figures_in_pool):
                            tab.set_final_text()
                            mode = FINAL_MODE

            elif mode == FINAL_MODE:
                if event.type == pg.KEYDOWN:
                    field, pool, drag_and_drop, tab = init_new_game(sc)
                    renderer.layers = [field, pool, drag_and_drop, tab]
                    renderer.invalidate_all()
                    mode = GAME_MODE

        renderer.draw()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
