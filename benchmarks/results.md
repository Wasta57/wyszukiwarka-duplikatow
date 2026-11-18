## Wyniki benchmarku GIL

- Python: 3.15.2
- Rdzenie CPU: 8, liczba wątków/procesów: 8
- GIL: włączony

### I/O-bound: 8 x sleep(0.5 s)

| Wariant | Czas [s] | Przyspieszenie |
|---|---|---|
| sekwencyjnie | 4.00 | 1.00x |
| wątki | 0.50 | 7.98x |
| procesy | 0.83 | 4.84x |

### CPU-bound: 8 x pętla 3 000 000

| Wariant | Czas [s] | Przyspieszenie |
|---|---|---|
| sekwencyjnie | 1.95 | 1.00x |
| wątki | 1.90 | 1.03x |
| procesy | 0.71 | 2.76x |

### SHA-256: 8 plików po 32 MB

| Wariant | Czas [s] | Przyspieszenie |
|---|---|---|
| sekwencyjnie | 0.20 | 1.00x |
| wątki | 0.07 | 2.80x |
| procesy | 0.33 | 0.62x |
