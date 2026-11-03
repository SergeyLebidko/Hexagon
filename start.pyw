#!/usr/bin/env python3
"""Точка входа в игру.

Проверка зависимостей выполняется до создания окна: без неё при запуске
двойным кликом пользователь видит лишь чёрное окно, которое сразу закрывается
(сообщение об ошибке уходит в несуществующий терминал).
"""
import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def check_requirements():
    """Возвращает текст ошибки или None, если всё в порядке."""
    try:
        import pygame
    except ImportError:
        return ('Не установлен pygame-ce.\n\n'
                'Выполните в терминале:\n'
                '    pip install -r requirements.txt')

    missing = []
    if not getattr(pygame, 'IS_CE', False):
        missing.append('установлен обычный pygame (%s), а нужен pygame-ce' % pygame.version.ver)
    if not hasattr(pygame.transform, 'box_blur'):
        missing.append('не хватает pygame-ce >= 2.5 (нет transform.box_blur)')

    if missing:
        return ('Игра требует pygame-ce, а не обычный pygame.\n\n'
                'Причина: %s\n\n'
                'Исправление:\n'
                '    pip uninstall -y pygame\n'
                '    pip install -r requirements.txt' % '; '.join(missing))
    return None


def report_error(message, details=None):
    """Показывает ошибку заметным способом: диалогом и записью в файл."""
    text = message if details is None else '%s\n\n%s' % (message, details)

    log_path = os.path.join(BASE_DIR, 'error.log')
    try:
        with open(log_path, 'w', encoding='utf-8') as log:
            log.write(text)
    except OSError:
        log_path = None

    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror('Hexagon', text)
        root.destroy()
    except Exception:
        pass

    sys.stderr.write(text + '\n')
    if log_path:
        sys.stderr.write('Подробности записаны в %s\n' % log_path)


def main_entry():
    problem = check_requirements()
    if problem:
        report_error(problem)
        return 1

    try:
        from main import run
    except Exception:
        report_error('Не удалось запустить игру.', traceback.format_exc())
        return 1

    try:
        run()
    except Exception:
        report_error('Игра завершилась с ошибкой.', traceback.format_exc())
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main_entry())


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
                exit()

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
                    figure = drag_and_drop.figure
                    drop_pos = event.pos
                    if drag_and_drop.drop():
                        field.refresh_field()
                        pool.refresh_slots()

                        score_data = field.get_scored_data()
                        tab.update_score(*score_data)

                        # Эффекты: очки за фигуру и искры за удалённые линии.
                        gained = tab.target_score - tab.score
                        if gained > 0:
                            fx.popup(*drop_pos, text='+{}'.format(int(round(gained))))
                        lines = score_data[1]
                        if lines:
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


if __name__ == '__main__':
    main()
