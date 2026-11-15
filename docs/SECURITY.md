# Model bezpieczeństwa CTM

**Status:** polityka projektowa; mechanizmy egzekwowania będą implementowane i testowane od CTM-01.

## Granice zaufania
- **Operator** zatwierdza cel i politykę zadania; kontroler jest źródłem prawdy dla uprawnień.
- **Prompt, kod repozytorium, odpowiedź modelu, MCP i logi** są danymi niezaufanymi; nie mogą edytować własnych bram ani rozszerzać uprawnień zadania.
- **Worker Codex CLI** działa z prawami dedykowanej tożsamości systemowej. Nie dawaj mu więcej uprawnień, niż wymagane.
- **Dane SQLite** i pliki audytu to dane integralnościowe; procesy użytkownika nie powinny móc ich dowolnie nadpisywać.
- **Publiczne repozytorium GitHub** nie jest magazynem stanu, poświadczeń ani rzeczywistych logów sesji.

## Domyślna polityka
| Obszar | Wartość początkowa |
| --- | --- |
| Sandbox Codex | `read-only` |
| Przyznanie zapisu | Wyłącznie jawna polityka per zadanie, po kwalifikacji |
| Liczba workerów P0 | 1 |
| Dopuszczone katalogi | Zarejestrowane, kanonicznie zweryfikowane `repo_root` |
| Auto merge / force push | Zabronione |
| Produkcyjne SQL, KSeF, Optima, TIA, PLC/HMI | Zabronione bez osobnej autoryzacji |
| Brak obowiązkowego MCP | `BLOCKED` dla danego zadania, nie awaria menedżera |
| Zmiana polityki z promptu | Zabroniona |
| GUI na zablokowanej/wylogowanej sesji | Nie wykonuj automatycznie |

## Dostęp i sekrety
- Używaj dedykowanego konta z minimalnymi uprawnieniami; nie uruchamiaj usługi jako LocalSystem bez uzasadnienia.
- Uwierzytelnienie Codexa/Git i MCP sprawdź w tożsamości, w której *naprawdę* wystartuje zadanie; logowanie użytkownika interaktywnego nie gwarantuje dostępu konta usługi.
- Nie kopiuj tokenów, profili `.codex`, cookies, prywatnych kluczy i credential store do katalogu repo ani do konfiguracji zadania.
- Chroń `%ProgramData%\CodexTaskManager` odpowiednimi NTFS ACL; publiczne lub wspólne zapisy/odczyty niedozwolone.
- Logi mogą zawierać kod, ścieżki, fragmenty dokumentów i dane wrażliwe; wymagają redakcji, ograniczenia rozmiaru, retencji i kontroli dostępu.
- Nie korzystaj z widocznej w promptach wartości tokenów przy budowie audytu. Jeśli konieczne, zapisuj tylko referencje do zabezpieczonych sekretów.

## Egzekucja i bramy
1. **Preflight:** allowlista projektu, tożsamość `repo_root`, uprawnienia, rodzaj sesji, wymagane capabilities, poprawność promptu i kontraktu CLI.
2. **Execution:** argumenty jako lista, nie powłoka; sandbox, timeout, zapis zminimalizowanych metadanych; brak samozwiększania uprawnień.
3. **Validation:** zaufane polecenia lokalne (allowlista), testy i dowody; wynik modelu ma charakter pomocniczy.
4. **Review:** jeżeli rzeczywisty efekt uboczny jest niepewny, oznacz zadanie `REVIEW` lub `INTERRUPTED`. Nie uruchamiaj go ponownie przez samo wygaśnięcie lease.
5. **Audit:** kto i kiedy zatwierdził zwiększone uprawnienia, jakie sprawdzenia wykonano, SHA projektu przed i po oraz odwołania do artefaktów.

## Wyjątki
- Wyjątki muszą mieć ograniczenie: zadanie, repozytorium, czas, zakres działań i sposób weryfikacji.
- Nie stosuj ogólnych wyjątków „pełny dostęp do wszystkiego”.
- Zgoda na commit/push w repozytorium menedżera **nie** upoważnia do zmian w repozytoriach zarządzanych.
- Zgoda na implementację projektu **nie** obejmuje instalacji usług Windows, zmiany konfiguracji zabezpieczeń czy uruchomienia produkcyjnych testów.

## Testy bezpieczeństwa do wdrożenia
- Prompt injection w treści zadania i pliku repo próbuje wyłączyć blokady -> odmowa.
- Nieautoryzowana ścieżka / symlink / junction -> odmowa poza allowlistą.
- Nieistniejący repo lub zmieniony Git remote -> `BLOCKED`.
- Niedozwolone write, merge, SQL DML i GUI w trybie headless -> odmowa.
- Niepowodzenie redakcji sekretu nie powoduje jego publikacji.
- Restart po częściowo wykonanej operacji zapisującej -> `REVIEW`, nie auto-retry.
- Dwa niezależne workerzy -> brak równoległego write do jednego repo.
- Brak MCP wymaganej tylko dla części zadań -> pozostałe dalej działają.

## Backup / rollback
Przed migracją SQLite: wykonaj spójny backup (SQLite backup API), waliduj schemat i zaplanuj rollback. Przy odtwarzaniu nie wznowić automatycznie osieroconych zadań ze skutkiem zewnętrznym. Kluczy uwierzytelnienia nie obejmuj eksportem wprost. Operacje produkcyjne nie są objęte zwykłym rollbackiem menedżera.
