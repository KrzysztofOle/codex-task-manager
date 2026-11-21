# Audyt gałęzi — 2026-11-21

Porównanie zdalnych gałęzi do `main` (przed commitem raportu). Stan `main` pozostaje **DESIGN / DOCUMENTATION ONLY**; nie traktować kodu z gałęzi pobocznej jako wdrożonego.

| Gałąź | Ostatni commit (UTC) | Ahead / behind | Zawartość techniczna | Rekomendacja |
|---|---|---:|---|---|
| `feature/ctm-01-local-queue` | 2026-11-15 | 6 / 0 | Implementacja `src/ctm/cli.py`, `src/ctm/core.py` oraz `__main__.py`, pakiet w `pyproject.toml`, testy `tests/test_core.py`, opis CTM-01 i aktualizacje architektury. Unikalny kod nie jest na `main`. | **[DO PRZEGLĄDU]** — zweryfikować izolację repozytoriów, trwałość kolejki, testy awarii/restartu i bramki R3/R4; dopiero potem integrować na `main` |

Do czasu kwalifikacji nie zmieniać README na `main` w sposób sugerujący zaimplementowane uruchamianie zadań. Nie uruchamiano Codex CLI ani zadań autonomicznych; nie wykonano merge.
