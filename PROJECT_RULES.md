# PROJECT_RULES.md — codex-task-manager

## Tożsamość i cel
- Repozytorium: `KrzysztofOle/codex-task-manager`
- Gałąź domyślna: `main`
- Cel: lokalna kolejka i harmonogram zadań Codex na Windows, z obsługą wielu repozytoriów, kryteriów sukcesu, historii i bram bezpieczeństwa.
- Własność: wyłącznie kod, konfiguracja przykładowa, testy i dokumentacja **menedżera**.
- Poza zakresem: modyfikowanie kodu KSeF, T05, AI_SOTAX, Codex Knowledge Base; produkcyjne wykonanie ich zadań bez osobnego zlecenia.

## Stan
- CTM-00: dokumentacja na `main`.
- CTM-01: lokalna odczytowa kolejka CLI/SQLite zaimplementowana na gałęzi `feature/ctm-01-local-queue`, 20/20 syntetycznych testów PASS na Linux/Python 3.13.5; Windows i realny Codex CLI **NOT RUN**. Brama CTM-01 nie jest jeszcze pełnym LIVE PASS.
- CTM-02: Windows Task Scheduler, kontrola okresowa i test blokady (plan).
- CTM-03: klient System Tray i panel NiceGUI (plan).
- CTM-04: dedykowana usługa Windows, IPC i recovery (plan).
- CTM-05: adaptery MCP i wielu wykonawców (plan).

## Środowisko i struktura docelowa
- Windows 11 Pro; Python 3.12, standardowe SQLite, PowerShell; Git oraz zainstalowany i uwierzytelniony Codex CLI.
- NiceGUI oraz System Tray dopiero CTM-03. Usługa Windows dopiero CTM-04. MCP i wykonawcy na wielu komputerach dopiero CTM-05.
- Sugerowany katalog kodu: `C:\VSCode\codex-task-manager`; katalog stanu: `%ProgramData%\CodexTaskManager\`. Oba są propozycją, nie potwierdzoną instalacją.
- Źródło prawdy dla założeń: `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`.
- Ścieżki projektów i poświadczenia nie mogą być zaszyte na stałe; instalacja działa z lokalną konfiguracją każdej stacji.

## Testowanie
- R0: sprawdzenie dokumentacji, linków i `git diff --check`.
- R1/R2: wybrane testy Python przez `python -m pytest -q --tb=short tests/test_core.py`; `ruff check` po dodaniu konfiguracji Ruff.
- R3: syntetyczne testy procesu, restartu, kolejności i SQLite; realny Codex CLI testowany oddzielnie po potwierdzeniu wersji/kontraktu.
- R4: rzeczywiste testy Windows lock, System Tray, usługi, IPC, konta usługi, harmonogramu, izolacji, ACL i sekretów.
- Nie włączaj płatnych GitHub-hosted jobów bez potrzeby. Odróżniaj offline od live i zapisuj `NOT_RUN`.

## Wymogi architektury tła

- Główny dispatcher działa docelowo jako usługa w Session 0; aplikacja tray w sesji użytkownika nie przejmuje jego zadań.
- Komunikacja tray z workerem przez lokalne, uwierzytelnione i autoryzowane IPC (do kwalifikacji Named Pipe + ACL).
- Sygnał po `enqueue` i kontrola okresowa co domyślnie 300 s; obie ścieżki używają tych samych atomowych zabezpieczeń przed dublem.
- Zamknięcie tray nie zatrzymuje usługi; pauza zatrzymuje tylko nowe dispatch.
- Wdrożenie usługi wymaga odrębnej zgody oraz testu tożsamości Codexa/Git. Wyłącz uruchamianie workera z Task Scheduler przed przejściem na usługę.
- Model usługi/tray nie jest wdrożony w CTM-01; wykonanie CLI pozostaje ręczne. Retry wyłącznie po świadomej decyzji operatora; automatyczny backoff nadal OPEN (patrz `docs/CTM01_IMPLEMENTATION.md`).

## Git — ograniczenia
- Zweryfikowany remote GitHub do pracy nad tym repozytorium: `https://github.com/KrzysztofOle/codex-task-manager.git`.
- Automatyczny push na `main`: **niedozwolony domyślnie**; bezpośredni commit dokumentacji CTM-00 jest odrębnym zleceniem właściciela.
- Dla nowych zmian: gałąź zadaniowa o jednoznacznej nazwie, np. `feature/ctm-01-queue`, potwierdzony upstream, tylko commity bieżącego zadania; publikacja zgodna z uprawnieniami i bieżącym poleceniem.
- Merge do `main`, publikacja release, force-push i usuwanie gałęzi wyłącznie po osobnej zgodzie.

## Bramki zewnętrzne
- Domyślnie żadnych zapisów poza własnym katalogiem stanu oraz izolowanym katalogiem testowym.
- Każdy zapis do zarządzanego repozytorium wymaga jawnej polityki i izolacji; środowiska produkcyjne — odrębnych zgód.
- MCP: brak lub odmowa dostępu do opcjonalnej bazy nie może blokować startu menedżera; dla zadania wymagającego MCP skutkuje `BLOCKED`.
- Interaktywne GUI: zadania `REQUIRES_INTERACTIVE_SESSION`, nie wykonuj po zablokowaniu/wylogowaniu bez potwierdzonego mechanizmu.
- Sekrety: bezpieczny magazyn systemu/istniejące logowanie aplikacji, nie w repo, YAML, logach ani SQLite w postaci jawnej.
- Backup/rollback: patrz `docs/WINDOWS_OPERATIONS.md` i `docs/SECURITY.md`.

## Dokumentacja
- Aktualizuj przy zmianie kontraktów, zachowania, ryzyka, konfiguracji, kryteriów sukcesu i kamieni milowych.
- Nie wpisuj `COMPLETE`/PASS dla funkcji nieistniejących lub nieprzetestowanych.
