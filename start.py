from settings import pg, W, H, WINDOW_TITLE, FPS
from classes import Field, Pool, DragAndDrop, Background


def init_new_game(sc):
    field = Field(sc)
    pool = Pool(sc)
    drag_and_drop = DragAndDrop(sc, pool, field)
    return field, pool, drag_and_drop


def main():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    background = Background(sc)
    field, pool, drag_and_drop = init_new_game(sc)

    while True:

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

            if event.type == pg.MOUSEBUTTONDOWN and event.button == pg.BUTTON_LEFT:
                drag_and_drop.take(*event.pos)

            if event.type == pg.MOUSEMOTION:
                drag_and_drop.drag(*event.rel)

            if event.type == pg.MOUSEBUTTONUP and event.button == pg.BUTTON_LEFT:
                drop_result = drag_and_drop.drop()
                if not drop_result:
                    continue

                field.refresh_field()
                pool.refresh_slots()
                figures_in_pool = pool.get_figures_list()
                if not field.check_figures_list(figures_in_pool):
                    input('Вы проиграли')
                    # field, pool, drag_and_drop = init_new_game(sc)

        background.draw()
        field.draw()
        pool.draw()
        drag_and_drop.draw()

        pg.display.update()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
