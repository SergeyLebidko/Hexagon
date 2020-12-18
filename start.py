from settings import pg, W, H, WINDOW_TITLE, FPS
from classes import Field, Pool, DragAndDrop, Background


def main():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    background = Background(sc)
    field = Field(sc)
    pool = Pool(sc)
    drag_and_drop = DragAndDrop(sc, pool)

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
                drag_and_drop.drop(*event.pos)

        background.draw()
        field.draw()
        pool.draw()
        drag_and_drop.draw()

        pg.display.update()
        clock.tick(FPS)


if __name__ == '__main__':
    main()
