# Wymagania i kryteria akceptacji

**Status:** specyfikacja projektowa, nie potwierdzona funkcjonalność. Data bazowa: 2026-11-15.

## Problem i użytkownik
Operator kilku repozytoriów Windows potrzebuje jednej, trwałej kolejki prac Codexa, która uruchamia zadania w zależności od wyników poprzedników, bez każdorazowej interwencji człowieka. Zadania zwykle dotyczą analizy, implementacji, testów, dokumentacji i raportów, ale nie mogą same uzyskiwać zgody na działania produkcyjne.

## Priorytety

- **P0 / CTM-01:** kolejka SQLite, zależności, Codex CLI, walidacja, audyt i recovery.
- **P1 / CTM-02:** harmonogram Windows, test `Win+L`, cykliczny fallback 300 s.
- **P2 / CTM-03:** System Tray i panel NiceGUI, lokalny kanał sterowania, powiadomienia.
- **P3 / CTM-04:** dedykowana usługa Windows i niezależność od zalogowania użytkownika.
- **P4 / CTM-05:** MCP i wykonawcy na wielu komputerach.

## Wymagania funkcjonalne (P0)
| ID | Wymaganie | Akceptacja |
| --- | --- | --- |
| F-01 | Rejestr projektów z lokalnymi ścieżkami | Odrzucenie nieistniejącego/nieautoryzowanego katalogu, brak przypadkowego użycia innego repo |
| F-02 | Dodawanie zadań z ID, promptem, projektem, sandbox, timeoutem, polityką i walidatorem | Dane przeżywają restart, wartości podlegają walidacji |
| F-03 | Zależności bez cykli, FIFO w obrębie priorytetu | Wykryty cykl jest odrzucony; zależny task nie startuje przed PASS |
| F-04 | Stabilna atomowa rezerwacja zadania | Dwaj workerzy nie przejmują jednego zadania |
| F-05 | Uruchomienie `codex exec` bez shella z jawnych argumentów | Przechwycony PID, exit code, stdout/stderr, znaczniki czasu |
| F-06 | Niezależne sprawdzenie wyniku | Exit code/model PASS nie zastępuje walidacji |
| F-07 | Retry z backoff i limitem prób | Bez automatycznej powtórki zadania z nieznanym skutkiem ubocznym |
| F-08 | Awaria/restart | Osierocone RUNNING wymagają uzgodnienia; nie ma automatycznego podwójnego wykonania |
| F-09 | Blokada zapisów i wstrzymanie kolejki | Domyślny tryb read-only; jeden writer na repo |
| F-10 | Historia audytowa | Zapis prób, błędów, walidacji i decyzji bez sekretów |

## Wymagania niefunkcjonalne
- Windows 11, Python 3.12, SQLite, lokalny Codex CLI; ścieżki konfiguracji zależne od stacji.
- Domyślnie jeden worker. Izolacja katalogu roboczego, projektu oraz konfiguracji MCP; brak automatycznej eskalacji uprawnień.
- Service i tray działają w oddzielnych sesjach Windows; sterowanie wymaga lokalnego autoryzowanego IPC.
- Po enqueue następuje wybudzenie dyspozytora i rezerwowy rescan co domyślnie 300 s.
- Bezpieczne zamykanie subprocess, brak powielania procesów, limit rozmiaru i retencji logów, czytelne zdarzenia.
- Preferować własną kolejkę SQLite przed bezpośrednim sprzężeniem z automatyzacjami aplikacji desktopowej.
- Dla GUI nie zakładać działania przy zablokowanym Windows.
- Dane klientów/sekrety nie mogą trafiać do publicznego GitHub ani do debug logów.

## Model stanów (projekt)
`PENDING` -> `READY` -> `RUNNING` -> `VERIFYING` -> `PASS` lub `FAILED` / `PARTIAL` / `REVIEW` / `BLOCKED`. Ponadto `CANCELLED` oraz `INTERRUPTED` po utracie procesu; stany wymagające działania operatora nie są sukcesem. Transakcje i zdarzenia audytowe muszą uzgadniać przejścia.

**Definicja ukończenia zależności:** wyłącznie `PASS` potwierdzony walidatorem; wyjątek możliwy tylko przy jawnej polityce obsługi wyniku alternatywnego.

## Testy akceptacyjne
1. Dwa odczytowe zadania A -> B: B startuje wyłącznie po zweryfikowanym PASS A.
2. A zwraca `FAILED`: B pozostaje nieuruchomione, a niezależne C może wykonać się.
3. Cykl A -> B -> A jest odrzucony; błędna ścieżka repo nie powoduje zapisu.
4. Restart kontrolera, zabicie workera, timeout i utrata wyniku: brak automatycznego ponowienia niepewnego zapisu; pełny audit trail.
5. Dwa równoczesne procesy nie przejmują tego samego zadania; blokada zapisu na repo jest respektowana.
6. Zadanie z `PASS` zapisanym wyłącznie w tekście modelu, ale błędnym kodem/walidatorem nie otrzymuje PASS.
7. Sekrety nie są utrwalane w historii i logach; podstawowy test redakcji.
8. Test odczytowy `CTM-LOCK-01`: przy `Win+L` CLI i następne zadanie działają, jeśli komputer nie śpi (weryfikacja live na docelowej stacji, **NOT_RUN**).
9. Test interaktywny GUI w zablokowanej sesji nie jest wykonywany automatycznie.

## Wymagania dla usługi i System Tray (CTM-02 → CTM-04)

| ID | Wymaganie | Akceptacja |
| --- | --- | --- |
| BG-01 | Kontynuacja CLI przy `Win+L` | Test CTM-LOCK-01 na realnym Windows, bez uśpienia |
| BG-02 | Tray i worker jako odrębne procesy | Zamknięcie tray/NiceGUI nie przerywa kolejki |
| BG-03 | Natychmiastowy dispatch | Sygnał po enqueue sprawdza gotowość bez czekania 5 minut |
| BG-04 | Periodic fallback | Rescan co domyślnie 300 s; sygnał i poll nie duplikują zadań |
| BG-05 | Autonomiczna usługa | Praca po wylogowaniu i starcie bez sesji, pod właściwym kontem Windows |
| BG-06 | Autoryzowane IPC | Nieuprawniony użytkownik nie może enqueue/pause/cancel/zmienić polityki |
| BG-07 | Semantyka pauzy | Pause zatrzymuje nowe dispatch; cancel jest osobną operacją |
| BG-08 | Odporność | Recovery po restarcie/uśpieniu, bez powtórki niepewnego zapisu |
| BG-09 | Prywatność powiadomień | Ikona i toast bez poufnych danych lub promptów |
| BG-10 | Migracja Scheduler → Service | Nigdy dwa niezależne dispatchery na tej samej bazie |

Bramy: `CTM-LOCK-01` (CTM-02), `CTM-TRAY-01` (CTM-03), `CTM-SERVICE-01` (CTM-04). Wszystkie testy realnego Windows: **NOT_RUN** do wykonania.

## Poza MVP
Kalendarz GUI, webowy panel użytkowników, rozproszony scheduler, autonomiczny merge do main, samodzielne działania na produkcji, samonaprawiające się pętle agentów, auto-escalation, obowiązkowa chmura.

## Kryterium raportu
Rozdzielać **synthetic/offline**, **CLI integration**, **Windows locked-session**, **production/live** i **NOT_RUN**; sukces częściowy nigdy nie implikuje kwalifikacji produkcyjnej.
