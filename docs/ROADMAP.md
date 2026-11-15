# Plan realizacji CTM-00 — CTM-05

**Decyzja projektowa (2026-11-15):** docelowo usługa Windows (worker/dispatcher w tle) i osobny klient System Tray obok zegara, z powiadamianiem po enqueue i rezerwową kontrolą kolejki co 300 s (konfigurowalną). Wszystkie funkcje są na razie planowane; obowiązuje **MVP-first**.

| Etap | Zakres | Brama odbiorowa |
| --- | --- | --- |
| **CTM-00** | Specyfikacja, zasady i dokumentacja | R0: spójność i commit |
| **CTM-01** | SQLite, zależności, Codex CLI, walidator, audit, retry/recovery; **CLI-only** | A→B end-to-end PASS, awaria bez powielania |
| **CTM-02** | Przejściowy Windows Task Scheduler, kontrola co 5 minut, test `Win+L` | CTM-LOCK-01: CLI przy blokadzie i poprawne recovery |
| **CTM-03** | Osobna aplikacja System Tray, menu/powiadomienia, panel NiceGUI, lokalne IPC | CTM-TRAY-01: status, pause, autoryzacja, GUI można zamknąć |
| **CTM-04** | Usługa Windows, automatyczny start, poprawne konto Codex/Git, recovery, migracja z Scheduler | CTM-SERVICE-01: praca po wylogowaniu i starcie bez GUI; nie ma dwóch dispatcherów |
| **CTM-05** | Projektowe MCP, wielu workerów/komputerów i kwalifikowane środowiska GUI | Bramy izolacji, transportu, tożsamości, utraty połączenia |

## CTM-01 — najmniejszy działający przepływ
1. Sprawdzić realną wersję Codex CLI i lokalne uwierzytelnienie.
2. Wdrożyć pakiet Python 3.12, SQLite, transakcyjne claim, statusy i zależności DAG.
3. Uruchamiać `codex exec` w trybie `read-only`, bez niebezpiecznego shell expansion.
4. Zapisywać log, exit code, czas i niezależną weryfikację — modelowy PASS to nie dowód.
5. Przetestować restart, timeout, zły projekt, brak MCP i podwójne wywołanie dispatchera.
6. Odróżnić testy syntetyczne od rzeczywistej kwalifikacji CLI. Bez wdrażania tray/usługi.

## CTM-02 — scheduler przejściowy
- Uruchomienie `run-once` po starcie / co 5 minut, bez równoległych instancji.
- Test zablokowania `Win+L`, odczytu logów i sekwencji A→B; komputer nie może być uśpiony.
- Brak logowania Codex w sesji nieinteraktywnej: `BLOCKED`, nie kopiować sekretów.
- Zabezpieczenie mutex/lease pozostaje również przy uruchamianiu z harmonogramu.

## CTM-03 — tray i panel
- Ikona przy zegarze uruchamiana dopiero po zalogowaniu. Menu: kolejka, status, raporty, harmonogram, pauza/wznowienie, ustawienia.
- NiceGUI uruchamiane na żądanie, domyślnie localhost. Tray nie zapisuje SQLite.
- Sygnał po nowym zadaniu i lokalne IPC (preferencja Named Pipe z ACL), test autoryzacji.
- Zamknięcie tray i panelu nie zmienia stanu kolejki. Powiadomienia nie mogą wyświetlać danych poufnych.

## CTM-04 — usługa Windows
- Oddzielny proces Windows Service działający w Session 0; automatyczny start, restart po awarii, niezależny od tray i zalogowania.
- Dispatcher reaguje na enqueue i fallback rescan co 300 s; ten sam atomowy mechanizm lease.
- Weryfikacja tożsamości konta, Codex login, dostępu do repozytoriów i Git, ACL plików SQLite/logów oraz IPC.
- Przed przełączeniem należy **wyłączyć Scheduler-worker**, sprawdzić brak dubli i mieć procedurę rollback do CTM-02.
- Instalacja/aktualizacja usługi i zmiany uprawnień Windows tylko po osobnej zgodzie.

## CTM-05 — dalsze integracje
- MCP per projekt, lista dozwolonych narzędzi; brak opcjonalnego MCP nie blokuje uruchomienia menedżera.
- Zdalne stacje wymagają własnej tożsamości i kontraktu capabilities, nie współdzielonej bazy SQLite na udziale sieciowym.
- Optima/TIA/WinCC GUI tylko w odpowiednio kwalifikowanej sesji interaktywnej, nigdy automatycznie przez usługę Session 0.

## Warunki raportowania
Każdy etap: wynik, testy `PASS/FAIL/NOT_RUN`, SHA, ślady dowodowe, ryzyka i rollback. Nie deklarować LIVE VERIFIED na podstawie testów syntetycznych. Nie zużywać GitHub Actions, jeśli lokalne testy wystarczają.
