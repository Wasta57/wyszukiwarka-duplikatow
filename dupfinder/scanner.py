"""Skanowanie katalogów jako potok generatorów."""

import logging
import os
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from dupfinder.patterns import split_filename

logger = logging.getLogger(__name__)

FileInfo = tuple[str, int]  # (ścieżka, rozmiar w bajtach)


def walk_directory(root: str | Path) -> Iterator[os.DirEntry[str]]:
    """Rekurencyjnie zwraca wszystkie zwykłe pliki z katalogu.

    Katalogi, do których nie ma dostępu, są pomijane (z ostrzeżeniem w logu).
    Dowiązania symboliczne nie są śledzone, co chroni przed pętlami.
    """
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        yield from walk_directory(entry.path)  # delegacja do podkatalogu
                    elif entry.is_file(follow_symlinks=False):
                        yield entry
                except OSError as err:
                    logger.warning("Pomijam %s: %s", entry.path, err)
    except OSError as err:
        logger.warning("Pomijam katalog %s: %s", root, err)


def with_size(entries: Iterable[os.DirEntry[str]]) -> Iterator[FileInfo]:
    """Zamienia wpisy katalogu na pary (ścieżka, rozmiar)."""
    for entry in entries:
        try:
            yield entry.path, entry.stat(follow_symlinks=False).st_size
        except OSError as err:
            logger.warning("Nie można odczytać rozmiaru %s: %s", entry.path, err)


def filter_by_size(files: Iterable[FileInfo], min_size: int = 1) -> Iterator[FileInfo]:
    """Odrzuca pliki mniejsze niż min_size (domyślnie pomija puste pliki)."""
    return ((path, size) for path, size in files if size >= min_size)  # wyrażenie generujące


def filter_by_extension(
    files: Iterable[FileInfo], extensions: set[str]
) -> Iterator[FileInfo]:
    """Przepuszcza tylko pliki o podanych rozszerzeniach (małymi literami, bez kropki)."""
    for path, size in files:
        _, ext = split_filename(os.path.basename(path))
        if ext in extensions:
            yield path, size


def scan(
    root: str | Path,
    min_size: int = 1,
    extensions: set[str] | None = None,
) -> Iterator[FileInfo]:
    """Składa cały potok: katalog -> pliki -> rozmiary -> filtry."""
    files = with_size(walk_directory(root))
    files = filter_by_size(files, min_size)
    if extensions:
        files = filter_by_extension(files, extensions)
    return files


def group_by_size(files: Iterable[FileInfo]) -> dict[int, list[str]]:
    """Grupuje pliki po rozmiarze i zostawia tylko grupy z co najmniej 2 plikami.

    Plik o unikalnym rozmiarze nie może mieć duplikatu, więc nie ma sensu liczyć dla niego skrótu.
    """
    groups: defaultdict[int, list[str]] = defaultdict(list)
    for path, size in files:
        groups[size].append(path)
    return {size: paths for size, paths in groups.items() if len(paths) > 1}