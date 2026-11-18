"""Własny iterator czytający plik binarny blokami."""

from pathlib import Path
from typing import BinaryIO, Self


class ChunkReader:
    """Iterator zwracający kolejne bloki bajtów z pliku.

    Plik jest otwierany leniwie (przy pierwszym next()) i zamykany
    automatycznie po wyczerpaniu iteracji lub przy błędzie odczytu.
    Obiekt jest jednorazowy: po wyczerpaniu nie da się go "przewinąć".

    Args:
        path: ścieżka do pliku.
        chunk_size: rozmiar jednego bloku w bajtach (> 0).
        limit: maksymalna łączna liczba bajtów do odczytania
            (None = cały plik).

    Raises:
        ValueError: gdy chunk_size <= 0 lub limit < 0.
    """

    def __init__(
        self, path: str | Path, chunk_size: int = 64 * 1024, limit: int | None = None
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size musi być > 0")
        if limit is not None and limit < 0:
            raise ValueError("limit nie może być ujemny")
        self.path = Path(path)
        self.chunk_size = chunk_size
        self._remaining = limit
        self._file: BinaryIO | None = None
        self._finished = False

    def __iter__(self) -> Self:
        return self  # iterator zwraca samego siebie

    def __next__(self) -> bytes:
        if self._finished:
            raise StopIteration
        try:
            if self._file is None:
                self._file = open(self.path, "rb")
            size = self.chunk_size
            if self._remaining is not None:
                size = min(size, self._remaining)
            chunk = self._file.read(size) if size > 0 else b""
        except OSError:
            self.close()
            raise
        if not chunk:
            self.close()
            raise StopIteration  # sygnał końca iteracji
        if self._remaining is not None:
            self._remaining -= len(chunk)
        return chunk

    def close(self) -> None:
        """Zamyka plik i kończy iterację."""
        self._finished = True
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()