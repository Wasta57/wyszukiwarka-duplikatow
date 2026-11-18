"""Wyrażenia regularne: rozmiary plików, nazwy plików i listy rozszerzeń."""

import re

# Wzorzec 1: rozmiar, np. "10MB", "1,5 GB", "500k", "2048"
SIZE_RE = re.compile(
    r"""
    \s*
    (?P<value>\d+(?:[.,]\d+)?)   # liczba, opcjonalnie z częścią ułamkową
    \s*
    (?P<unit>[KMGT]?B?)          # jednostka (pusta = bajty)
    \s*
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Wzorzec 2: nazwa pliku = nazwa + opcjonalne rozszerzenie
FILENAME_RE = re.compile(r"(?P<name>.+?)(?:\.(?P<ext>[^./\\]+))?")

# Wzorzec 3: separatory na liście rozszerzeń
EXT_SEPARATOR_RE = re.compile(r"[,;\s]+")

UNITS: dict[str, int] = {
    "": 1, "B": 1,
    "K": 1024, "KB": 1024,
    "M": 1024**2, "MB": 1024**2,
    "G": 1024**3, "GB": 1024**3,
    "T": 1024**4, "TB": 1024**4,
}


def parse_size(text: str) -> int:
    """Zamienia zapis typu '10MB' lub '1,5 GB' na liczbę bajtów.

    Raises:
        ValueError: gdy tekst nie jest poprawnym rozmiarem.
    """
    match = SIZE_RE.fullmatch(text)
    if match is None:
        raise ValueError(f"Nieprawidłowy rozmiar: {text!r}")
    value = float(match["value"].replace(",", "."))
    return int(value * UNITS[match["unit"].upper()])


def split_filename(filename: str) -> tuple[str, str]:
    """Dzieli nazwę pliku na (nazwa, rozszerzenie małymi literami).

    Pliki ukryte (".gitignore") i bez rozszerzenia dają puste rozszerzenie.
    """
    match = FILENAME_RE.fullmatch(filename)
    if match is None:  # np. pusty napis
        raise ValueError(f"Nieprawidłowa nazwa pliku: {filename!r}")
    return match["name"], (match["ext"] or "").lower()


def parse_extensions(text: str) -> set[str]:
    """Zamienia 'jpg, .PNG;txt' na zbiór {'jpg', 'png', 'txt'}."""
    parts = EXT_SEPARATOR_RE.split(text.strip())
    return {part.lstrip(".").lower() for part in parts if part.strip(".")}