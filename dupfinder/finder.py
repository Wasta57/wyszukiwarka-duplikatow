"""Wyszukiwanie duplikatów plików w trzech etapach."""

import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self, get_args

from dupfinder.decorators import measure_time, requires_root
from dupfinder.hashing import (
    PARTIAL_SIZE,
    hash_multiprocess,
    hash_sequential,
    hash_threaded,
)
from dupfinder.patterns import parse_extensions, parse_size
from dupfinder.scanner import group_by_size, scan

logger = logging.getLogger(__name__)

Mode = Literal["sequential", "threads", "processes"]


@dataclass(frozen=True)
class DuplicateGroup:
    """Grupa identycznych plików."""

    size: int
    digest: str
    paths: tuple[str, ...]

    @property
    def wasted_bytes(self) -> int:
        """Ile miejsca zajmują nadmiarowe kopie (wszystkie poza jedną)."""
        return self.size * (len(self.paths) - 1)


class DuplicateFinder:
    """Szuka duplikatów: rozmiar, potem skrót początku pliku, potem pełny skrót.

    Każdy kolejny etap dostaje tylko to, co przeszło przez poprzedni, dzięki
    czemu drogie liczenie pełnych skrótów obejmuje jak najmniej plików.

    Args:
        root: katalog do przeszukania.
        min_size: pomijaj pliki mniejsze niż tyle bajtów.
        extensions: zbiór rozszerzeń (None = wszystkie).
        mode: "sequential", "threads" lub "processes".
        workers: liczba wątków/procesów (None = wartość domyślna).
    """

    def __init__(
        self,
        root: str | Path,
        min_size: int = 1,
        extensions: set[str] | None = None,
        mode: Mode = "threads",
        workers: int | None = None,
    ) -> None:
        if mode not in get_args(Mode):
            raise ValueError(f"Nieznany tryb: {mode!r}")
        self.root = Path(root)
        self.min_size = min_size  # przechodzi przez setter
        self.extensions = extensions
        self.mode: Mode = mode
        self.workers = workers

    @property
    def min_size(self) -> int:
        """Minimalny rozmiar pliku branego pod uwagę (bajty)."""
        return self._min_size

    @min_size.setter
    def min_size(self, value: int) -> None:
        if value < 0:
            raise ValueError("min_size nie może być ujemny")
        self._min_size = value

    @classmethod
    def from_strings(
        cls,
        root: str,
        min_size: str = "1",
        extensions: str = "",
        **kwargs: object,
    ) -> Self:
        """Alternatywny konstruktor: rozmiar i rozszerzenia jako zwykły tekst.

        Przykład: DuplicateFinder.from_strings(".", min_size="10KB", extensions="jpg, png")
        """
        return cls(
            root,
            min_size=parse_size(min_size),
            extensions=parse_extensions(extensions) or None,
            **kwargs,  # type: ignore[arg-type]
        )

    @staticmethod
    def format_size(size: int) -> str:
        """Zamienia bajty na czytelny zapis, np. 1536 -> '1.5 KB'."""
        units = ("B", "KB", "MB", "GB", "TB")
        value, index = float(size), 0
        while value >= 1024 and index < len(units) - 1:
            value /= 1024
            index += 1
        return f"{int(value)} B" if index == 0 else f"{value:.1f} {units[index]}"

    @staticmethod
    def _group(
        hashes: dict[str, str], sizes: dict[str, int]
    ) -> dict[tuple[int, str], list[str]]:
        """Grupuje pliki po (rozmiar, skrót) i zostawia grupy z min. 2 plikami."""
        groups: defaultdict[tuple[int, str], list[str]] = defaultdict(list)
        for path, digest in hashes.items():
            groups[(sizes[path], digest)].append(path)
        return {key: paths for key, paths in groups.items() if len(paths) > 1}

    def _hash(self, paths: list[str], limit: int | None = None) -> dict[str, str]:
        """Wybiera sposób liczenia skrótów zgodnie z self.mode."""
        match self.mode:
            case "sequential":
                return hash_sequential(paths, limit)
            case "threads":
                return hash_threaded(paths, limit, workers=self.workers or 8)
            case _:
                return hash_multiprocess(paths, limit, workers=self.workers)

    @requires_root
    @measure_time
    def find(self) -> list[DuplicateGroup]:
        """Zwraca grupy duplikatów posortowane od największej straty miejsca."""
        # Etap 1: rozmiar
        size_groups = group_by_size(scan(self.root, self.min_size, self.extensions))
        sizes = {p: size for size, paths in size_groups.items() for p in paths}
        logger.info("Etap 1 (rozmiar): %d kandydatów", len(sizes))

        # Etap 2: skrót pierwszych PARTIAL_SIZE bajtów
        partial = self._hash(list(sizes), limit=PARTIAL_SIZE)
        stage2 = self._group(partial, sizes)
        survivors = [p for paths in stage2.values() for p in paths]
        logger.info("Etap 2 (początek pliku): %d kandydatów", len(survivors))

        # Etap 3: pełny skrót
        full = self._hash(survivors)
        stage3 = self._group(full, sizes)
        logger.info("Etap 3 (pełny skrót): %d grup duplikatów", len(stage3))

        result = [
            DuplicateGroup(size, digest, tuple(sorted(paths)))
            for (size, digest), paths in stage3.items()
        ]
        result.sort(key=lambda group: group.wasted_bytes, reverse=True)
        return result