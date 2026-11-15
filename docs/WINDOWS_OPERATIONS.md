# Windows 11 — harmonogram, blokada sesji, awarie

**Stan:** plan procedury na CTM-02. Instrukcje są kryteriami konfiguracji, nie dowodem działającej instalacji.

## Co działa przy blokadzie?
| Stan Windows | Zadanie Codex CLI bez GUI | GUI (TIA/Optima/WinCC) |
| --- | --- | --- |
| Wyłączony monitor | Zwykle tak | Zależne od interfejsu |
| `Win+L` (sesja zablokowana, komputer aktywny) | Powinno działać; **wymagany test live** | Nie zakładać działania |
| Wylogowanie / brak zalogowanego użytkownika | Tylko uruchomienie w odpowiednim kontekście nieinteraktywnym, po teście credentials/ACL | Nie |
| Uśpienie / hibernacja | Nie pracuje w czasie uśpienia; potrzebne recovery | Nie |
| Restart | Zadanie przerwane; po starcie kontrolera potrzebne uzgodnienie stanu | Nie |

**Uwaga:** blokada ekranu nie jest uśpieniem i nie wymaga wyłączania ochrony sesji. Nie należy wyłączać automatycznej blokady dla potrzeb CTM.

## Zalecany sposób uruchamiania
1. **CTM-01:** ręczny `worker run-once` na syntetycznych zadaniach i read-only Codex CLI.
2. **CTM-02:** rejestracja w Windows Task Scheduler z unikalną nazwą `CodexTaskManager`, bez zależności od otwartego okna aplikacji. Harmonogram może uruchamiać krótki `run-once` co np. 5 minut, ale kontroler musi sam zapewniać mutex/lease.
3. Dopiero po zakwalifikowaniu nieinteraktywnego uruchomienia można rozważyć uruchamianie bez zalogowanego użytkownika (`Run whether user is logged on or not`). Zbadać uprawnienia konta i sposób przechowania poświadczeń.
4. Usługa Windows to **opcjonalny dalszy wariant**, nie wymóg CTM-01/CTM-02.

## Checklista konfiguracji docelowej
- Tożsamość konta uruchamiającego zadanie i dostęp do Codexa, Git, Python, SQLite, repozytoriów i logów.
- Sprawdzić `where.exe codex` i konkretną wersję CLI w kontekście planowanego konta.
- Ścieżki preferować lokalne absolutne, np. `C:\VSCode\...`. Nie zakładać mapowania `X:`, `M:` w sesji bez logowania; jeżeli konieczny udział sieciowy, sprawdzić UNC i uprawnienia.
- W Scheduler: brak uzależnienia od `Idle`; `Run task as soon as possible after a scheduled start is missed`; ignoruj nową instancję, jeśli poprzednia jeszcze działa. Dodatkowo kontroler musi mieć własny mechanizm anty-duplikacji.
- Zasilanie: ograniczenie uśpienia tylko na **dedykowanej stacji**, po zgodzie operatora i sprawdzeniu polityk bezpieczeństwa/energii. Wyłączenie monitora jest dopuszczalne bez wyłączania blokady.
- Użytkownik z reguły nie potrzebuje praw administratora do samych analiz read-only; instalację zadania/usługi i zmiany polityk osobno autoryzować.
- Nie zapisuj hasła do konta w argumentach skryptu czy repozytorium.
- Nie zakładać, że cmdlet Task Scheduler, flagi logon type lub profile użytkownika zachowują się identycznie na każdej stacji: test rzeczywistego środowiska jest obowiązkowy.

## Protokół CTM-LOCK-01 (do wykonania na Windows)
1. Zapisz identyfikator komputera, wersję Windows/CLI/Python, konto oraz ustawienia zasilania (bez sekretów).
2. Dodaj dwa zależne zadania **read-only**, każde z własnym weryfikowalnym artefaktem/zdarzeniem.
3. Uruchom pierwsze, zablokuj ekran `Win+L` przed jego zakończeniem.
4. Po powrocie sprawdź: zakończenie próby, WAL/SQLite, timestamps, logi i start drugiego zadania.
5. Powtórz test po wylogowaniu, **tylko** jeśli zostało skonfigurowane odrębne konto i bezpieczny logon type.
6. Negatywny test: uśpienie i przywrócenie; osierocone zadanie ma przejść przez recovery, a nie automatyczny PASS.
7. Zapisz `PASS/FAIL/PARTIAL/NOT_RUN` z dowodami. Osobno kwalifikuj zadania wymagające GUI — wynik CLI nie jest dowodem GUI.

## Restart, awaria i recovery
- Kontroler powinien po restarcie odczytać ostatni stan, lease i identyfikatory prób, sprawdzić pozostawione procesy oraz dane zadania.
- Nie uruchamiać ponownie zapisu o nieznanym wyniku. Eskalować do `REVIEW`, przeprowadzić weryfikację efektów i dopiero decydować o dalszych działaniach.
- Dla zadania odczytowego po bezpiecznym przerwaniu można użyć ograniczonego retry z backoff.
- Retencja logów i backup SQLite bez commitowania do Git. Recovery po awarii dysku wymaga sprawdzenia integralności bazy i kopii.

## Kryterium przejścia CTM-02
Zadania wykonywane według harmonogramu po zablokowaniu ekranu i po restarcie, brak duplikacji, udokumentowany test nieinteraktywny na rzeczywistym sprzęcie oraz brak prób nieautoryzowanej automatyzacji GUI. Jeśli któregoś nie sprawdzono, status odpowiedniego testu `NOT_RUN`.
