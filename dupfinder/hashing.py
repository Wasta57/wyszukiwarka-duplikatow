"""Liczenie skrótów SHA-256: sekwencyjnie, na wątkach i na procesach."""

import hashlib
import itertools
import logging
import os
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from dupfinder.decorators import measure_time, retry
from dupfinder.reader import ChunkReader

logger = logging.getLogger(__name__)

PARTIAL_SIZE = 4096  # tyle bajtów z początku pliku wystarcza do taniego wstępnego filtra

ProgressCallback = Callable[[int, int], None]  # (ukończone, wszystkie)


class ProgressCounter:
    """Bezpieczny wątkowo licznik postępu.

    Operacja `+=` nie jest atomowa (odczyt, dodanie, zapis), więc bez blokady
    wątki gubiłyby aktualizacje, nawet mimo GIL.
    """

    def __init__(self, total: int) -> None:
        self.total = total
        self._done = 0
        self._lock = threading.Lock()

    def increment(self) -> int:
        """Zwiększa licznik o 1 i zwraca nową wartość."""
        with self._lock:
            self._done += 1
            return self._done

    @property
    def done(self) -> int:
        """Liczba ukończonych zadań."""
        with self._lock:
            return self._done


@retry(attempts=3, delay=0.05, exceptions=(PermissionError,))
def hash_file(path: str, limit: int | None = None) -> str:
    """Zwraca SHA-256 pliku (lub tylko jego pierwszych `limit` bajtów).

    Ponawia próbę przy PermissionError, bo na Windows plik bywa chwilowo
    zablokowany przez inny program (np. antywirus).
    """
    digest = hashlib.sha256()
    with ChunkReader(path, limit=limit) as reader:
        for chunk in reader:
            digest.update(chunk)
    return digest.hexdigest()


def safe_hash(path: str, limit: int | None = None) -> tuple[str, str | None]:
    """Jak hash_file, ale błąd odczytu daje (path, None) zamiast wyjątku.

    Musi być funkcją najwyższego poziomu, bo ProcessPoolExecutor przesyła
    ją do procesów potomnych przez pickle.
    """
    try:
        return path, hash_file(path, limit)
    except (OSError, RuntimeError) as err:
        logger.warning("Pomijam %s: %s", path, err)
        return path, None


def _collect(results: Iterable[tuple[str, str | None]]) -> dict[str, str]:
    """Składa wyniki w słownik {ścieżka: skrót}, pomijając pliki z błędem."""
    return {path: digest for path, digest in results if digest is not None}


@measure_time
def hash_sequential(paths: Iterable[str], limit: int | None = None) -> dict[str, str]:
    """Wersja bazowa: jeden wątek, jeden proces."""
    return _collect(safe_hash(path, limit) for path in paths)


@measure_time
def hash_threaded(
    paths: Iterable[str],
    limit: int | None = None,
    workers: int = 8,
    on_progress: ProgressCallback | None = None,
) -> dict[str, str]:
    """Pula wątków. Opłaca się, bo hashlib i operacje dyskowe zwalniają GIL.

    `on_progress` jest wywoływane z wątków roboczych, więc musi być bezpieczne wątkowo.
    """
    path_list = list(paths)
    counter = ProgressCounter(len(path_list))

    def task(path: str) -> tuple[str, str | None]:
        result = safe_hash(path, limit)
        done = counter.increment()
        if on_progress is not None:
            on_progress(done, counter.total)
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return _collect(pool.map(task, path_list))


@measure_time
def hash_multiprocess(
    paths: Iterable[str], limit: int | None = None, workers: int | None = None
) -> dict[str, str]:
    """Pula procesów: każdy proces ma własny interpreter, a więc własny GIL.

    Na Windows (metoda startu `spawn`) wywołanie musi pochodzić z kodu
    chronionego przez `if __name__ == "__main__":`.
    """
    path_list = list(paths)
    if not path_list:
        return {}
    workers = workers or os.cpu_count() or 1
    chunksize = max(1, len(path_list) // (workers * 4))  # mniej komunikacji między procesami
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = pool.map(
            safe_hash, path_list, itertools.repeat(limit), chunksize=chunksize
        )
        return _collect(results)