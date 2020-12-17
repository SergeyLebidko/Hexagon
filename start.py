from settings import pg, W, H, WINDOW_TITLE, FPS
from utils import create_background_surface
from classes import Field, Pool


def main():
    # Инициализируем окно
    pg.init()
    sc = pg.display.set_mode((W, H))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    background_surface = create_background_surface()
    field = Field(sc)
    pool = Pool(sc)
    pool.refresh_slots()

    while True:

        events = pg.event.get()
        for event in events:
            if event.type == pg.QUIT:
                pg.quit()
                exit()

            if event.type == pg.MOUSEBUTTONDOWN:
                print(pool.collide(*event.pos))

        sc.blit(background_surface, (0, 0))
        field.draw_field()
        pool.draw_slots()
        pg.display.update()

        clock.tick(FPS)


if __name__ == '__main__':
    main()
