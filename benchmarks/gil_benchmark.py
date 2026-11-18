"""Benchmark GIL: porównanie wariantów sekwencyjnego, wątków i procesów.

Uruchomienie (z głównego folderu projektu):
    python -m benchmarks.gil_benchmark
"""

import argparse
import os
import sys
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from dupfinder.hashing import hash_multiprocess, hash_sequential, hash_threaded

Results = dict[str, float]

RESULTS_FILE = Path(__file__).with_name("results.md")


def cpu_task(n: int) -> int:
    """Czysto pythonowe obliczenia: pętla trzyma GIL przez cały czas."""
    total = 0
    for i in range(n):
        total += i * i
    return total


def io_task(seconds: float) -> float:
    """Symulacja oczekiwania na sieć lub dysk: sleep zwalnia GIL."""
    time.sleep(seconds)
    return seconds


def best_of(repeats: int, action: Callable[[], object]) -> float:
    """Zwraca najkrótszy z kilku pomiarów czasu (w sekundach)."""
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        action()
        times.append(time.perf_counter() - start)
    return min(times)


def run_pool(
    executor_cls: type[ThreadPoolExecutor] | type[ProcessPoolExecutor],
    workers: int,
    func: Callable[[Any], Any],
    args: list[Any],
) -> list[Any]:
    """Wykonuje func dla każdego argumentu w puli wątków lub procesów."""
    with executor_cls(max_workers=workers) as pool:
        return list(pool.map(func, args))


def compare(
    func: Callable[[Any], Any], args: list[Any], workers: int, repeats: int
) -> Results:
    """Mierzy ten sam zestaw zadań trzema sposobami."""
    return {
        "sekwencyjnie": best_of(repeats, lambda: [func(a) for a in args]),
        "wątki": best_of(
            repeats, lambda: run_pool(ThreadPoolExecutor, workers, func, args)
        ),
        "procesy": best_of(
            repeats, lambda: run_pool(ProcessPoolExecutor, workers, func, args)
        ),
    }


def compare_hashing(paths: list[str], workers: int, repeats: int) -> Results:
    """Mierzy liczenie skrótów SHA-256 funkcjami z dupfinder.hashing."""
    return {
        "sekwencyjnie": best_of(repeats, lambda: hash_sequential(paths)),
        "wątki": best_of(repeats, lambda: hash_threaded(paths, workers=workers)),
        "procesy": best_of(repeats, lambda: hash_multiprocess(paths, workers=workers)),
    }


def create_files(directory: Path, count: int, size_mb: int) -> list[str]:
    """Tworzy `count` plików testowych po `size_mb` MB losowych danych."""
    block = os.urandom(1024 * 1024)
    paths = []
    for i in range(count):
        path = directory / f"plik{i}.bin"
        with open(path, "wb") as file:
            for _ in range(size_mb):
                file.write(block)
        paths.append(str(path))
    return paths


def format_table(title: str, results: Results) -> str:
    """Formatuje wyniki jako tabelę Markdown (gotową do wklejenia w README)."""
    baseline = results["sekwencyjnie"]
    lines = [
        f"### {title}",
        "",
        "| Wariant | Czas [s] | Przyspieszenie |",
        "|---|---|---|",
    ]
    for name, seconds in results.items():
        lines.append(f"| {name} | {seconds:.2f} | {baseline / seconds:.2f}x |")
    return "\n".join(lines)


def describe_environment(workers: int) -> str:
    """Opisuje środowisko pomiaru (potrzebne do interpretacji wyników)."""
    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    return (
        f"- Python: {sys.version.split()[0]}\n"
        f"- Rdzenie CPU: {os.cpu_count()}, liczba wątków/procesów: {workers}\n"
        f"- GIL: {'włączony' if gil_enabled else 'wyłączony (free-threading)'}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark GIL")
    parser.add_argument("--repeats", type=int, default=3, help="liczba powtórzeń (best of)")
    parser.add_argument("--tasks", type=int, default=None, help="liczba zadań (domyślnie = liczba rdzeni)")
    parser.add_argument("--cpu-n", type=int, default=3_000_000, help="rozmiar zadania CPU")
    parser.add_argument("--files", type=int, default=8, help="liczba plików do hashowania")
    parser.add_argument("--size-mb", type=int, default=32, help="rozmiar pliku w MB")
    args = parser.parse_args()

    workers = os.cpu_count() or 1
    tasks = args.tasks or workers

    sections = ["## Wyniki benchmarku GIL", "", describe_environment(workers), ""]

    print("1/3 I/O-bound (time.sleep)...")
    io = compare(io_task, [0.5] * tasks, workers, args.repeats)
    sections += [format_table(f"I/O-bound: {tasks} x sleep(0.5 s)", io), ""]

    print("2/3 CPU-bound (czysty Python)...")
    cpu = compare(cpu_task, [args.cpu_n] * tasks, workers, args.repeats)
    sections += [format_table(f"CPU-bound: {tasks} x pętla {args.cpu_n:,}".replace(",", " "), cpu), ""]

    print("3/3 Skróty SHA-256 plików (tworzę pliki testowe)...")
    with tempfile.TemporaryDirectory() as tmp:
        paths = create_files(Path(tmp), args.files, args.size_mb)
        hashing = compare_hashing(paths, workers, args.repeats)
    sections += [format_table(f"SHA-256: {args.files} plików po {args.size_mb} MB", hashing), ""]

    report = "\n".join(sections)
    print()
    print(report)
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print(f"Zapisano wyniki do {RESULTS_FILE}")


if __name__ == "__main__":  # obowiązkowe na Windows (procesy startują metodą spawn)
    main()