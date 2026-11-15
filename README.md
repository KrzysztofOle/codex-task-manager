# Codex Task Manager (CTM)

> **Status: DESIGN / DOCUMENTATION ONLY (2026-11-15).** Repozytorium definiuje projekt aplikacji. Kolejka, harmonogram, panel i usługa Windows **nie zostały jeszcze zaimplementowane ani przetestowane**.

**Codex Task Manager** to planowany, lokalny menedżer kolejki i harmonogramu zadań dla OpenAI Codex na Windows 11. Docelowo składa się z usługi Windows pracującej w tle i oddzielnego klienta System Tray przy zegarze. Ma umożliwiać uruchamianie kolejnych prac w wielu repozytoriach Git bez ręcznego wysyłania następnego polecenia, z zachowaniem zależności, priorytetów, audytu i bram bezpieczeństwa.

## Główny scenariusz MVP

1. Operator rejestruje lokalne repozytorium i dodaje dwa zależne, bezpieczne zadania odczytowe.
2. Lokalny kontroler zapisuje zadania i zależności w SQLite oraz wybiera pierwsze gotowe zadanie.
3. Wykonawca uruchamia `codex exec` w katalogu właściwego repozytorium, zapisuje logi i kod zakończenia.
4. Walidator sprawdza **obiektywne** kryteria powodzenia. Sama odpowiedź modelu „PASS” nie wystarcza.
5. Po potwierdzonym sukcesie kontroler uruchamia drugie zadanie; po błędzie blokuje tylko gałąź zależną, pozostawiając inne prace możliwe do wykonania.
6. Po przerwaniu procesu i ponownym uruchomieniu menedżera zachowana zostaje historia, a niepewne wykonania nie są bezmyślnie ponawiane.

**Mierzalne kryterium MVP:** na testowym repozytorium dwa zadania odczytowe przechodzą kolejno do zweryfikowanego `PASS`, a symulowany błąd, przerwanie procesu i restart nie powodują duplikacji ani utraty historii.

## Docelowe moduły i tryb pracy w tle

| Moduł | Przeznaczenie | Etap |
| --- | --- | --- |
| SQLite, kolejka DAG, walidator, Codex CLI | Trwały stan, zależności, wykonanie i weryfikacja | CTM-01 |
| Windows Task Scheduler | Przejściowe uruchamianie w tle | CTM-02 |
| System Tray + NiceGUI | Ikona obok zegara, menu, status, panel i zatwierdzanie | CTM-03 |
| Usługa Windows | Główny dyspozytor/worker niezależny od zalogowania i panelu | CTM-04 |
| MCP i wiele komputerów | Kontekst projektu i wykonawcy zdalni | CTM-05 |

### Przyjęta architektura docelowa

```text
System Tray (sesja użytkownika) -- autoryzowane lokalne IPC --> Windows Service (Session 0)
  status, menu, NiceGUI                                  | SQLite + dispatch
                                                        +--> Codex CLI
```

**Dwa osobne procesy:** zamknięcie ikony lub panelu **nie zatrzymuje** usługi ani bieżących prac. Po dodaniu zadania dyspozytor otrzymuje sygnał i może działać od razu; dodatkowo kontroluje kolejkę **co 5 minut** (300 sekund, konfigurowalne). Pauza blokuje uruchamianie **nowych** zadań, a anulowanie to osobne polecenie.

Usługa Windows zostanie wdrożona po kwalifikacji MVP CLI, harmonogramu i procesu tray; opisane funkcje **nie są jeszcze zaimplementowane**.

## Zasady operacyjne

- **Windows zablokowany** (`Win+L`) nie jest przeszkodą dla zadań CLI niewymagających GUI; wymaga to testu na docelowym komputerze. **Uśpienie** zatrzymuje wykonywanie; po wznowieniu trzeba uzgodnić stan zadań.
- Nie uruchamiać w sesji nieinteraktywnej działań wymagających pulpitu (np. TIA Portal, WinCC Runtime, Comarch Optima GUI). Takie zadania muszą oczekiwać na właściwą interaktywną sesję i osobną kwalifikację.
- Przestrzegać granic pomiędzy projektami, w szczególności KSeF/Optima, Siemens T05, AI_SOTAX i bazami wiedzy Codexa.
- Domyślny tryb zadania: odczyt. Uprawnienia zapisu są nadawane **per zadanie / repozytorium** i nie oznaczają zgody na produkcyjne operacje.
- Bez automatycznego merge do `main`, force-push, zmian produkcyjnego SQL, KSeF submit, zapisów PLC/HMI, deploymentu lub obchodzenia wymaganych zgód.
- Preferować lokalne testy bez GitHub Actions. Limity Actions oraz koszt wywołań Codexa to niezależne zagadnienia; kontroler musi mieć limity uruchomień i ponowień.

## Docelowe środowisko

- Windows 11 Pro, PowerShell, Python 3.12, SQLite.
- Oficjalny Codex CLI jako proces wykonawczy (`codex exec`); argumenty i format wyjścia trzeba potwierdzić testem zgodności przed użyciem.
- Kod źródłowy: sugerowany katalog `C:\VSCode\codex-task-manager`.
- Dane lokalne: sugerowany `%ProgramData%\CodexTaskManager\` (dostęp i ACL do zatwierdzenia); **nigdy** w katalogu Git.
- Konfiguracja ścieżek repozytoriów jest **lokalna dla stacji**, a nie zakodowana na stałe; nie zakłada się dostępności dysków mapowanych w zadaniach nieinteraktywnych.

## Dokumentacja

- [Wymagania i kryteria akceptacji](docs/REQUIREMENTS.md)
- [Architektura i model kolejki](docs/ARCHITECTURE.md)
- [Plan wdrożenia CTM-00 → CTM-05](docs/ROADMAP.md)
- [Model bezpieczeństwa](docs/SECURITY.md)
- [Windows: blokada sesji i harmonogram](docs/WINDOWS_OPERATIONS.md)
- [Decyzje architektoniczne](docs/DECISIONS.md)
- [Instrukcje dla Codexa](AGENTS.md) i [reguły projektu](PROJECT_RULES.md)

## Etap i dalsze kroki

- **CTM-00:** dokumentacja i decyzje.
- **CTM-01:** kolejka CLI/SQLite, bez interfejsu ani harmonogramu.
- **CTM-02:** Windows Task Scheduler i test `Win+L`.
- **CTM-03:** ikona System Tray oraz panel NiceGUI.
- **CTM-04:** niezależna usługa Windows, autostart, IPC i recovery.
- **CTM-05:** adaptery MCP i wiele komputerów.

Przed przejściem do kolejnego etapu wymagane są rzeczywiste dowody wykonania bram.

**Nie uruchamiaj poleceń z dokumentacji jako gotowego systemu.** Opisują projekt i wymagania, nie potwierdzoną instalację.
