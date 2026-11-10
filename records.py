"""Лучшие результаты по каждому размеру поля.

Таблица хранится отдельно от настроек: настройки — это выбор игрока, а
рекорды — накопленные данные, которые нельзя терять при сбросе предпочтений.
Файл лежит рядом с preferences.json и так же не попадает в репозиторий.

У каждого размера поля (S, M, L) своя тройка: поле на 61 гекс и на 127
гексов дают несопоставимые счёта, поэтому общая таблица была бы бессмысленной.
"""
import json
import os

from config import BASE_DIR

RECORDS_PATH = os.path.join(BASE_DIR, 'records.json')

# Сколько мест показываем и храним.
TOP_COUNT = 3


class Records:
    """Тройка лучших результатов на каждый размер поля."""

    def __init__(self, path=RECORDS_PATH):
        self.path = path
        self._data = {}
        self._dirty = False
        self.load()

    def load(self):
        """Читает файл. Битый или чужой файл просто игнорируется.

        Проверяем типы: если в файле окажется строка вместо списка чисел,
        таблица не должна ронять игру при первом же обращении.
        """
        self._data = {}
        self._dirty = False
        try:
            with open(self.path, encoding='utf-8') as handle:
                raw = json.load(handle)
        except (OSError, ValueError):
            return

        if not isinstance(raw, dict):
            return

        for size, values in raw.items():
            if not isinstance(values, list):
                continue
            clean = []
            for value in values:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                clean.append(int(value))
            if clean:
                clean.sort(reverse=True)
                self._data[size] = clean[:TOP_COUNT]

    def save(self):
        """Пишет таблицу на диск. Ошибка записи не критична для игры."""
        if not self._dirty:
            return True
        try:
            with open(self.path, 'w', encoding='utf-8') as handle:
                json.dump(self._data, handle, indent=2, ensure_ascii=False)
        except OSError:
            return False
        self._dirty = False
        return True

    def entries(self, size, current=None):
        """Строки таблицы для показа.

        Возвращает пару (значения, подсветка): values — ровно TOP_COUNT
        элементов, где None означает пустое место; highlight — индекс строки
        с текущим счётом или None, если текущего счёта в тройке нет.

        Текущий счёт добавляется к сохранённым ещё до окончания партии, чтобы
        рекорд было видно сразу, как только он его обогнал. Если такой счёт
        уже был сохранён раньше, дубликат не создаётся — подсвечивается
        существующая строка.
        """
        saved = [int(value) for value in self._data.get(size, [])]
        values = list(saved)
        highlight = None

        if current is not None:
            current = int(current)
            if current in values:
                highlight = values.index(current)
            elif current > 0:
                values.append(current)
                values.sort(reverse=True)
                values = values[:TOP_COUNT]
                if current in values:
                    highlight = values.index(current)

        values = values[:TOP_COUNT]
        while len(values) < TOP_COUNT:
            values.append(None)
        return values, highlight

    def submit(self, size, score):
        """Добавляет результат в таблицу. Возвращает True, если она изменилась.

        Результат попадает в память сразу, а на диск уходит отдельным вызовом
        save(): счёт меняется много раз за партию, и писать файл каждый раз
        было бы расточительно.
        """
        score = int(score)
        if score <= 0:
            return False

        values = [int(value) for value in self._data.get(size, [])]
        if score in values:
            return False

        values.append(score)
        values.sort(reverse=True)
        values = values[:TOP_COUNT]
        if values == self._data.get(size):
            return False

        self._data[size] = values
        self._dirty = True
        return True

    def best(self, size):
        """Лучший результат для размера или 0, если партий ещё не было."""
        values = self._data.get(size) or []
        return int(values[0]) if values else 0


records = Records()
