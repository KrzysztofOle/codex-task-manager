# PROJECT_RULES.md — codex-task-manager

## Tożsamość i cel
- Repozytorium: `KrzysztofOle/codex-task-manager`
- Gałąź domyślna: `main`
- Cel: lokalna kolejka i harmonogram zadań Codex na Windows, z obsługą wielu repozytoriów, kryteriów sukcesu, historii i bram bezpieczeństwa.
- Własność: wyłącznie kod, konfiguracja przykładowa, testy i dokumentacja **menedżera**.
- Poza zakresem: modyfikowanie kodu KSeF, T05, AI_SOTAX, Codex Knowledge Base; produkcyjne wykonanie ich zadań bez osobnego zlecenia.

## Stan
- CTM-00: dokumentacja; implementacja, testy CLI/Windows i instalacja **NOT_RUN**.
- CTM-01: lokalna odczytowa kolejka bez GUI (plan).
- CTM-02/03/04: harmonogram, GUI, adaptery i wielu wykonawców (plan).

## Środowisko i struktura docelowa
- Windows 11 Pro; Python 3.12, standardowe SQLite, PowerShell; Git oraz zainstalowany i uwierzytelniony Codex CLI.
- NiceGUI dopiero CTM-03. MCP i wykonawcy na wielu komputerach dopiero CTM-04.
- Sugerowany katalog kodu: `C:\VSCode\codex-task-manager`; katalog stanu: `%ProgramData%\CodexTaskManager\`. Oba są propozycją, nie potwierdzoną instalacją.
- Źródło prawdy dla założeń: `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`.
- Ścieżki projektów i poświadczenia nie mogą być zaszyte na stałe; instalacja działa z lokalną konfiguracją każdej stacji.

## Testowanie
- R0: sprawdzenie dokumentacji, linków i `git diff --check`.
- R1/R2: docelowo wybrane testy Python przez `python -m pytest -q --tb=short`; `ruff check` po dodaniu konfiguracji Ruff.
- R3: syntetyczne testy procesu, restartu, kolejności i SQLite; realny Codex CLI testowany oddzielnie po potwierdzeniu wersji/kontraktu.
- R4: rzeczywiste testy zablokowanej sesji Windows, harmonogramu, izolacji zapisów, ACL, sekretów i uprawnień.
- Nie włączaj płatnych GitHub-hosted jobów bez potrzeby. Odróżniaj offline od live i zapisuj `NOT_RUN`.

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
