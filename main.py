"""Wyszukiwarka duplikatów plików: interfejs wiersza poleceń."""

import argparse
import logging
import sys
from collections.abc import Sequence

from dupfinder.finder import DuplicateFinder, DuplicateGroup


def build_parser() -> argparse.ArgumentParser:
    """Buduje parser argumentów wiersza poleceń."""
    parser = argparse.ArgumentParser(
        description="Wyszukuje zduplikowane pliki (rozmiar, początek pliku, pełny SHA-256)."
    )
    parser.add_argument("root", help="katalog do przeszukania")
    parser.add_argument(
        "--min-size", default="1", help="minimalny rozmiar pliku, np. 10KB, 1,5MB (domyślnie 1 B)"
    )
    parser.add_argument(
        "--ext", default="", help="tylko te rozszerzenia, np. 'jpg, png' (domyślnie wszystkie)"
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "threads", "processes"],
        default="threads",
        help="sposób liczenia skrótów (domyślnie threads)",
    )
    parser.add_argument("--workers", type=int, default=None, help="liczba wątków/procesów")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="-v: informacje, -vv: szczegóły debugowania"
    )
    return parser


def print_report(groups: list[DuplicateGroup]) -> None:
    """Wypisuje raport o znalezionych duplikatach."""
    if not groups:
        print("Nie znaleziono duplikatów.")
        return
    for number, group in enumerate(groups, start=1):
        size = DuplicateFinder.format_size(group.size)
        wasted = DuplicateFinder.format_size(group.wasted_bytes)
        print(f"Grupa {number}: {size} x {len(group.paths)} plików (do odzyskania: {wasted})")
        for path in group.paths:
            print(f"  {path}")
    total = DuplicateFinder.format_size(sum(g.wasted_bytes for g in groups))
    print(f"Znaleziono {len(groups)} grup duplikatów, do odzyskania łącznie: {total}")


def main(argv: Sequence[str] | None = None) -> int:
    """Punkt wejścia programu. Zwraca kod wyjścia (0 = sukces)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    level = {0: logging.WARNING, 1: logging.INFO}.get(args.verbose, logging.DEBUG)
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")

    try:
        finder = DuplicateFinder.from_strings(
            args.root,
            min_size=args.min_size,
            extensions=args.ext,
            mode=args.mode,
            workers=args.workers,
        )
    except ValueError as err:
        parser.error(str(err))  # wypisuje komunikat i kończy program z kodem 2

    try:
        groups = finder.find()
    except NotADirectoryError as err:
        print(f"Błąd: {err}", file=sys.stderr)
        return 1

    print_report(groups)
    return 0


if __name__ == "__main__":  # obowiązkowe na Windows (procesy startują metodą spawn)
    sys.exit(main())