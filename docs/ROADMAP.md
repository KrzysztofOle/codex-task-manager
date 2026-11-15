# Plan realizacji CTM-00 — CTM-04

**Nie oznaczać etapów jako PASS bez potwierdzonych dowodów.** Harmonogram i daty wykonania nie są zobowiązaniem.

| Etap | Cel | Wynik | Brama |
| --- | --- | --- | --- |
| **CTM-00** | Dokumentacja, decyzje i zasady | README, AGENTS, PROJECT_RULES, docs/ | R0: spójność i linki, zapis w Git |
| **CTM-01** | Lokalna kolejka MVP | SQLite, CLI, kolejność A->B, retries, walidacja, recovery, syntetyczne testy | P0 end-to-end PASS, brak duplikacji po awarii, brak zapisu bez zgody |
| **CTM-02** | Harmonogram i odporność Windows | Windows Task Scheduler, pominięte uruchomienia, startup i restart, CTM-LOCK-01 | Test Windows odblokowany / Win+L / restart / brak logowania; potwierdzona polityka zasilania |
| **CTM-03** | Panel NiceGUI | Kolejka, filtry, logi, zatwierdzenia, kontrola dostępu | Brak bypass polityki API, testy UI, kontrola sesji |
| **CTM-04** | Adaptery i wiele hostów | MCP, możliwości workerów, kwalifikacja WINTEST/T05, bezpieczna orkiestracja | Test izolacji, tożsamości, rozłączeń i niedostępnych MCP |

## CTM-01 — zadania do wykonania
1. Potwierdź wersję i sposób odnajdywania Codex CLI oraz ograniczenia sandbox na konkretnym Windows.
2. Dodaj podstawową strukturę pakietu Python i migrację SQLite.
3. Zaimplementuj model zadań, walidację konfiguracji, zależności DAG i statusy.
4. Zaimplementuj scheduler lokalnej kolejki (bez zegara Windows), atomowe claim i audyt.
5. Uruchamiaj `codex exec` przez kontrolowany subprocess z timeoutem i logami.
6. Dodaj niezależny walidator i rozróżnienie `PASS`/`PARTIAL`/`FAILED`/`BLOCKED`.
7. Dodaj recovery po utracie procesu i testy syntetyczne.
8. Wykonaj zatwierdzony test integracyjny CLI **read-only**, oddzielny od testów offline.

## CTM-02 — wymogi uruchamiania
- Tryb co kilka minut i start po uruchomieniu komputera, bez równoległych instancji kontrolera.
- Windows lock nie jest Windows sleep; tylko test CLI `Win+L` potwierdzi działanie w docelowej konfiguracji.
- Tryb `Run whether user is logged on or not` wymaga oddzielnej próby uwierzytelnienia Codex i Git oraz sprawdzenia ścieżek i ACL.
- Przy niedostępnym środowisku nie obejść blokady GUI: zadanie oznacz jako `BLOCKED`.

## CTM-03 — wymogi interfejsu
- Sterowanie przez ten sam API/warstwę domenową co CLI.
- Wyświetlanie przyczyn statusu i dowodów weryfikacyjnych, nie tylko etykiety PASS.
- Oddzielne zatwierdzanie zadań o zwiększonych uprawnieniach.
- Domyślnie wyłącznie localhost, brak publikacji panelu w Internecie.

## CTM-04 — przyszłość
- Zewnętrzna wiedza MCP z listą dozwolonych narzędzi i kontrolą zakresu.
- Workery na różnych komputerach (np. oddzielny WINTEST, TIA i deweloperski), z jawnymi capabilities.
- Zadania interaktywne Windows (Optima/TIA) nadal wymagają ręcznie zatwierdzonego środowiska sesji; nie maskować tego automatycznym unlockiem.

## Definicja gotowości do następnego etapu
Zapisz: wynik, Git SHA, wykonane testy, logi/artefakty (bez sekretów), wersje narzędzi, `NOT_RUN`, znane ryzyka i rollback. Przy `PARTIAL` kontynuuj niezależne, bezpieczne części; nie awansuj zakresu, którego brama nie przeszła.
