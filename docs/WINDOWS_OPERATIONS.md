# Windows 11 — harmonogram, blokada sesji, awarie

**Stan:** plan procedury na CTM-02–CTM-04. Docelowo usługa Windows + System Tray, nie działająca jeszcze instalacja. Instrukcje są kryteriami konfiguracji, nie dowodem działającej instalacji.

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

1. **CTM-01:** ręczne `run-once` z syntetycznymi i odczytowymi zadaniami.
2. **CTM-02:** przejściowy Harmonogram Windows uruchamiający `run-once` co 5 minut i po starcie, bez drugiej instancji; test `Win+L`.
3. **CTM-03:** odrębna aplikacja System Tray startuje po zalogowaniu i pokazuje status oraz panel NiceGUI; jest klientem IPC, nie workerem.
4. **CTM-04:** usługa Windows w Session 0 przejmuje dispatch, autostart i recovery; harmonogram nie może już uruchamiać drugiego workera.
5. **CTM-05:** MCP i wielu wykonawców; aplikacje interaktywne w osobnych sesjach i po osobnej zgodzie.

**Mechanizm:** nowy task → sygnał do dyspozytora → natychmiastowa kwalifikacja READY. Rezerwowo co **300 s** (zmienialne ustawienie) kontroler skanuje bazę; osobno uwzględnia termin kolejnego zadania planowanego. Event i polling chroni jeden atomowy lease.

**Znaczenie menu:** zamknięcie tray nie zatrzymuje kolejki; `pause` blokuje nowe dispatch, `cancel` jest osobną, autoryzowaną operacją.

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

## Komponent System Tray (CTM-03)

Lekka ikona przy zegarze działa wyłącznie w zalogowanej sesji użytkownika. Menu obejmuje: otwórz kolejkę, status, raporty, harmonogram, wstrzymaj/wznów, ustawienia. Kolory sygnalizują gotowość, pracę, wymaganą decyzję i błąd, ale konieczny jest również opis tekstowy. Brak tray po wylogowaniu to prawidłowy stan. Kanał IPC musi weryfikować tożsamość i prawa; tray nie zapisuje SQLite.

## Kwalifikacja CTM-TRAY-01 i CTM-SERVICE-01

**CTM-TRAY-01:** sygnał nowego zadania powoduje reakcję workera; status jest odzwierciedlony w tray; zamknięcie i ponowne uruchomienie tray nie zatrzymuje wykonania; nieautoryzowana komenda IPC jest odrzucona; pauza zatrzymuje tylko nowe zadania.

**CTM-SERVICE-01:** na aktywnym komputerze usługa pracuje przy `Win+L`, po wylogowaniu i po restarcie bez zalogowanego użytkownika; poprawna tożsamość i logowanie Codex/Git, ACL lokalnych danych i IPC, brak dubli z Task Scheduler, skuteczne recovery. Po zalogowaniu tray odczytuje aktualny stan. Instalację usługi wykonuje się tylko po osobnej zgodzie.

Oba testy rzeczywistego Windows: **NOT_RUN**, dopóki nie zostaną wykonane. GUI Optima/TIA nie jest obsługiwane automatycznie przez usługę.

## Restart, awaria i recovery
- Kontroler powinien po restarcie odczytać ostatni stan, lease i identyfikatory prób, sprawdzić pozostawione procesy oraz dane zadania.
- Nie uruchamiać ponownie zapisu o nieznanym wyniku. Eskalować do `REVIEW`, przeprowadzić weryfikację efektów i dopiero decydować o dalszych działaniach.
- Dla zadania odczytowego po bezpiecznym przerwaniu można użyć ograniczonego retry z backoff.
- Retencja logów i backup SQLite bez commitowania do Git. Recovery po awarii dysku wymaga sprawdzenia integralności bazy i kopii.

## Kryterium przejścia CTM-02
Zadania wykonywane według harmonogramu po zablokowaniu ekranu i po restarcie, brak duplikacji, udokumentowany test nieinteraktywny na rzeczywistym sprzęcie oraz brak prób nieautoryzowanej automatyzacji GUI. Jeśli któregoś nie sprawdzono, status odpowiedniego testu `NOT_RUN`.

## Brama CTM-04

Usługa kwalifikuje się do zastąpienia harmonogramu dopiero po CTM-SERVICE-01 PASS, z dowodami na brak duplikacji, działanie po wylogowaniu, obsługę auth i praw oraz plan rollback. Blokada ekranu nie wymaga wyłączenia ochrony Windows; uśpienie nadal wstrzymuje proces.
