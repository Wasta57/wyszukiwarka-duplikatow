# Wyszukiwarka duplikatów plików

Projekt zaliczeniowy z przedmiotu *Zaawansowane techniki programowania w języku Python*.
Autor: Marceli Rogowski

## Opis

Program rekurencyjnie przeszukuje katalog i znajduje pliki o identycznej zawartości.
Żeby nie liczyć drogich skrótów dla każdego pliku, działa w trzech etapach, a każdy
kolejny dostaje tylko kandydatów, którzy przeszli poprzedni:

1. grupowanie po **rozmiarze** (plik o unikalnym rozmiarze nie ma duplikatu),
2. skrót SHA-256 z **pierwszych 4 KB** pliku (tani filtr wstępny),
3. **pełny** skrót SHA-256.

Skróty można liczyć sekwencyjnie, na wątkach lub na procesach (opcja `--mode`).

## Wymagania i uruchomienie

- Python 3.12 lub nowszy (kod używa składni generyków z PEP 695, np. `def retry[**P, R]`),
- kod główny nie wymaga bibliotek zewnętrznych.
- do testów: `pytest` (`pip install -r requirements.txt`); sam program nie wymaga bibliotek zewnętrznych.
```
Repozytorium: https://github.com/Wasta57/wyszukiwarka-dupikatow
cd wyszukiwarka-duplikatow
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Przykłady (z aktywnym środowiskiem):

```
python main.py C:\Users\mrogo\Pictures
python main.py C:\Users\mrogo\Pictures --min-size 10KB --ext "jpg, png" --mode processes -v
python main.py -h
python -m benchmarks.gil_benchmark
```

Opcje: `--min-size` (np. `10KB`, `1,5MB`), `--ext` (lista rozszerzeń), `--mode`
(`sequential`, `threads`, `processes`), `--workers`, `-v` / `-vv` (poziom logowania).

## Struktura projektu

```
main.py                  # CLI (argparse) i konfiguracja logging
dupfinder/
    decorators.py        # dekoratory funkcji i metod
    patterns.py          # wyrażenia regularne
    scanner.py           # potok generatorów (skanowanie katalogów)
    reader.py            # własny iterator ChunkReader
    hashing.py           # skróty SHA-256: sekwencyjnie, wątki, procesy
    finder.py            # klasa DuplicateFinder (trzy etapy)
benchmarks/
    gil_benchmark.py     # pomiar wpływu GIL
    results.md           # wyniki ostatniego pomiaru
```

## Mapowanie zagadnień na kod

| Zagadnienie | Gdzie w kodzie |
|---|---|
| Dekoratory funkcji | `dupfinder/decorators.py` → `measure_time`, `log_call`, `retry(attempts, delay, exceptions)` (z parametrami, wszystkie z `functools.wraps`); użyte w `hashing.py` (`hash_file`, `hash_sequential`, `hash_threaded`, `hash_multiprocess`) |
| Dekorator metody korzystający z `self` | `dupfinder/decorators.py` → `requires_root`, użyty w `finder.py` → `DuplicateFinder.find` |
| `@property` z setterem | `finder.py` → `DuplicateFinder.min_size` |
| `@classmethod` | `finder.py` → `DuplicateFinder.from_strings` (alternatywny konstruktor) |
| `@staticmethod` | `finder.py` → `DuplicateFinder.format_size`, `DuplicateFinder._group` |
| Iterator | `dupfinder/reader.py` → klasa `ChunkReader` (`__iter__`, `__next__`) |
| Generator (`yield`, `yield from`) | `dupfinder/scanner.py` → `walk_directory` (rekurencja przez `yield from`), `with_size`, `filter_by_extension` |
| Wyrażenie generujące | `scanner.py` → `filter_by_size`; `hashing.py` → `hash_sequential` |
| Potok generatorów | `scanner.py` → `scan()` składa `walk_directory` → `with_size` → filtry |
| Wyrażenia regularne (grupy nazwane) | `dupfinder/patterns.py` → `SIZE_RE` (`value`, `unit`), `FILENAME_RE` (`name`, `ext`), `EXT_SEPARATOR_RE` |
| Wątki + synchronizacja | `hashing.py` → `hash_threaded` (`ThreadPoolExecutor`), `ProgressCounter` (`Lock`) |
| Procesy | `hashing.py` → `hash_multiprocess` (`ProcessPoolExecutor`) |
| Pomiar GIL | `benchmarks/gil_benchmark.py` |

## Wyniki pomiarów wydajności

Środowisko: CPython 3.15.2, GIL włączony, 8 rdzeni CPU, 8 wątków/procesów, Windows
(procesy startują metodą `spawn`). Każdy wynik to najlepszy z 3 pomiarów.

**I/O-bound: 8 × `sleep(0.5 s)`**

| Wariant | Czas [s] | Przyspieszenie |
|---|---|---|
| sekwencyjnie | 4,00 | 1,00x |
| wątki | 0,50 | 7,98x |
| procesy | 0,83 | 4,84x |

**CPU-bound: 8 × pętla 3 000 000 (czysty Python)**

| Wariant | Czas [s] | Przyspieszenie |
|---|---|---|
| sekwencyjnie | 1,95 | 1,00x |
| wątki | 1,90 | 1,03x |
| procesy | 0,71 | 2,76x |

**SHA-256: 8 plików po 32 MB**

| Wariant | Czas [s] | Przyspieszenie |
|---|---|---|
| sekwencyjnie | 0,20 | 1,00x |
| wątki | 0,07 | 2,80x |
| procesy | 0,33 | 0,62x |

## Testy

```
python -m pip install -r requirements.txt
python -m pytest -v
```

Zestaw zawiera 96 testów jednostkowych (`pytest`) obejmujących dekoratory, wyrażenia regularne,
iterator, generatory, skróty (wszystkie trzy tryby), klasę `DuplicateFinder` i interfejs
wiersza poleceń.

### Wnioski dotyczące GIL

Pomiary wykonano w CPythonie 3.15.2 z włączonym GIL na maszynie z 8 rdzeniami.
W zadaniu I/O-bound wątki dały przyspieszenie 7,98x, ponieważ `time.sleep` zwalnia GIL,
a procesy były wolniejsze (4,84x) przez koszt uruchomienia ośmiu interpreterów.
W zadaniu CPU-bound w czystym Pythonie wątki nie przyspieszyły obliczeń (1,03x), bo w danej
chwili kod bajtowy wykonuje tylko jeden wątek, natomiast procesy, mające osobne interpretery
i osobne GIL-e, osiągnęły 2,76x. Przyspieszenie procesów jest mniejsze niż liczba rdzeni,
ponieważ zadania są krótkie (ok. 0,25 s), więc narzut startu procesów (metoda `spawn`
w Windows) jest porównywalny z czasem obliczeń. Przy liczeniu SHA-256 wątki dały 2,80x, bo
`hashlib` zwalnia GIL podczas przetwarzania dużych bloków, a procesy były wolniejsze od wersji
sekwencyjnej (0,62x), ponieważ koszt ich startu przewyższył ok. 0,2 s pracy. Dlatego domyślnym
trybem programu są wątki, a procesy opłacają się dopiero przy dłuższych zadaniach CPU-bound
w czystym Pythonie. Pomiar ma ograniczenia: pliki testowe były świeżo zapisane i leżały
w pamięci podręcznej systemu, a część czasów jest krótka, więc wyniki mogą się wahać między
uruchomieniami.

## Napotkane problemy

- **Za stara wersja Pythona.** W systemie był Python 3.8, a projekt wymaga 3.12+. Zainstalowałem
  nowszy i utworzyłem środowisko wirtualne `.venv`.
- **Git niewidoczny w terminalu po instalacji.** Terminal VS Code nie widział nowego programu,
  dopóki nie zamknąłem całkowicie VS Code (odświeża zmienną PATH).
- **Blokada skryptów w PowerShellu.** Aktywacja środowiska (`Activate.ps1`) wymagała jednorazowego
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Zmiana nazwy folderu projektu.** Środowisko `.venv` zapisuje bezwzględne ścieżki, więc po
  zmianie nazwy folderu musiałem utworzyć je od nowa.
- **Funkcje przesyłane do procesów.** `ProcessPoolExecutor` przesyła funkcje przez `pickle`, który nie
  obsługuje funkcji zagnieżdżonych, dlatego `safe_hash` jest zdefiniowana na poziomie modułu.
- **Metoda `spawn` w Windows.** Procesy potomne importują moduł główny od nowa, więc `main.py`
  i benchmark mają zabezpieczenie `if __name__ == "__main__":`.
- **Procesy wolniejsze przy krótkich zadaniach.** Początkowo zaskoczyło mnie, że `ProcessPoolExecutor`
  jest wolniejszy od sekwencyjnego liczenia skrótów małych plików. Wyjaśnił to benchmark: koszt
  startu procesów przewyższa zysk, gdy zadania trwają ułamki sekundy.
- **Uruchamianie z przycisku ▶ w VS Code.** Uruchomienie przez debugger zawiesiło się, dlatego
  skrypty uruchamiam z terminala poleceniem `python`.