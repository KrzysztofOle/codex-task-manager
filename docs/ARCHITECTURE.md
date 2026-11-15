# Architektura Codex Task Manager

**Status:** plan, CTM-00; żaden z opisywanych modułów nie został uruchomiony.

## Model odpowiedzialności

### Docelowo: dwa oddzielne procesy (CTM-04)

```text
Sesja użytkownika (po logowaniu)              Usługa Windows (Session 0)
  System Tray + NiceGUI ─── lokalne IPC ──> Dispatcher / policy / leases
    status, menu, pause  <── events/status ─ SQLite + audit + Codex CLI
```

Usługa Windows odpowiada za dispatch, trwałość, wykonanie i walidację. Tray to klient UI — **nie** wykonuje prac, nie przechowuje sekretów workera i nie edytuje SQLite. Interfejs może być zamknięty bez zatrzymywania wykonania.

### Etapy migracji

- **CTM-01:** lokalny worker CLI uruchamiany ręcznie.
- **CTM-02:** Windows Task Scheduler wznawia `run-once`, zachowując mutex i lease.
- **CTM-03:** osobny proces System Tray + NiceGUI i lokalny kanał sterowania.
- **CTM-04:** usługa Windows przejmuje dispatch; stary Scheduler-worker wyłączony.
- **CTM-05:** MCP i worker-y na wielu hostach.

## Komponenty CTM-01
1. **Configuration loader:** wersjonowany schemat reguł; lokalny rejestr repo; walidacja realpath i dozwolonych katalogów.
2. **SQLite store:** tabele `projects`, `tasks`, `dependencies`, `attempts`, `events`, `leases`; migracje jawne i odwracalne z backupem.
3. **Dispatcher:** tylko zadania bez nierozwiązanych zależności; priorytet i deterministyczne sortowanie, limit równoległości.
4. **Lease manager:** atomowy claim z transakcją, timestamp i identity właściciela; wygasły lease nie daje automatycznej zgody na uruchomienie nieidempotentnego zadania.
5. **Executor:** bez `shell=True`; jawny `cwd` oraz `argv`, maksymalny czas, zakończenie drzewa procesów, ograniczenie logów i kontrola exit code.
6. **Verifier:** predefiniowane bezpieczne testy/warunki, artefakty i status; modelowy komunikat nie jest dowodem.
7. **Recovery:** uzgadnia PID/heartbeat, status repo i wykonane skutki uboczne; niepewne zadanie otrzymuje `INTERRUPTED` lub `REVIEW`.

## Kontrakt zadania (propozycja, nie format wdrożony)

```yaml
id: CTM-EXAMPLE-001
project_id: sample_repository
kind: analysis
priority: 50
depends_on: []
prompt_file: tasks/CTM-EXAMPLE-001.md
sandbox: read-only
requires_interactive_session: false
timeout_seconds: 900
max_attempts: 1
retry_policy: manual_on_uncertain_effect
required_capabilities: [git, codex_cli]
verification:
  type: command_allowlisted
  command_id: verify_example_artifact
```

To przykład formatu do ustalenia w CTM-01, nie gotowy plik konfiguracyjny. `prompt_file` należy rozwiązać w dozwolonej przestrzeni konfiguracji, a `verification.command_id` musi wskazywać wcześniej zdefiniowaną, zaufaną komendę — **nie dowolny tekst z modelu**.

## Przejścia i niezawodność
- `PENDING`: czeka na zależności; `READY`: kwalifikuje się do claim; `RUNNING`: proces wystartował; `VERIFYING`: zakończył się, wymagane dowody.
- `PASS`: testy i bramy PASS; `FAILED`: potwierdzona porażka; `PARTIAL`: część wykonana; `BLOCKED`: brak warunku/capability; `REVIEW`: potrzebna decyzja; `CANCELLED`: jawne anulowanie; `INTERRUPTED`: utracono jednoznaczny wynik.
- Każde przejście zapisuje `attempt_id`, czas, źródło decyzji i ślady dowodowe; nigdy nie opieraj kolejnych zadań na samym tekstowym podsumowaniu LLM.
- Nie da się zagwarantować uniwersalnego **exactly-once** dla obcych procesów i zewnętrznych efektów; zapewnić atomowy claim, idempotency keys tam, gdzie to możliwe, oraz `REVIEW` dla niepewnego skutku.
- Po powrocie z uśpienia/wylogowania nie przechodzić automatycznie od RUNNING do PASS; wykonać recovery.

## Izolacja
- Przed każdą próbą sprawdź kanoniczną ścieżkę repozytorium i jego tożsamość Git; odrzuć zmienioną/missing ścieżkę.
- P0: 1 worker, tylko zadania odczytowe i syntetyczne fixtures; opcja zwiększenia limitów dopiero po testach współbieżności.
- Dla późniejszych zadań zapisujących preferuj oddzielny Git worktree i jeden writer na repo. Weryfikuj czystość/worktree oraz nie nadpisuj zmian innych procesów.
- MCP opcjonalny: jego brak nie blokuje startu, tylko konkretne wymagające go zadanie.
- Dla wielu komputerów (CTM-05) potrzebne podpisane capability/identity workerów, transport, kolejki leasingowe, a nie bezpośredni dostęp wielu hostów do jednego SQLite przez udział sieciowy.

## Proponowany układ kodu
```text
src/ctm/{config,store,queue,worker,verifier,recovery}.py
tests/{unit,integration,fixtures}/
docs/
examples/           # wyłącznie niesekretne przykłady
```

Nie twórz tych katalogów przed CTM-01 tylko dla pozoru gotowej implementacji.

## Hybrydowe budzenie kolejki

1. `enqueue` najpierw zapisuje zadanie transakcyjnie w SQLite, a następnie wysyła sygnał do workera.
2. Dispatcher natychmiast sprawdza `READY`, zależności i polityki oraz wykonuje atomowy claim.
3. Niezależnie odbywa się kontrola okresowa co domyślnie **300 sekund**; zadania planowane mają osobne terminy.
4. Zdarzeniowy i okresowy dispatch korzystają z tego samego lease; po uśpieniu/restartcie wykonywane jest reconciliation.
5. `pause` wstrzymuje **nowe** zadania. `cancel` jest odrębnym, kontrolowanym poleceniem.

### IPC i separacja procesów

Preferowany kandydat: **Windows Named Pipe** z ograniczonym DACL i kontrolą tożsamości, do potwierdzenia w CTM-03; alternatywnie uwierzytelniony endpoint loopback z ochroną CSRF. Usługa działa w Session 0 i nie może sterować GUI w sesji użytkownika. Brak tray nie jest awarią usługi. Konto usługi musi posiadać własny, prawidłowo zakwalifikowany dostęp do Codex CLI i Git; nie kopiować tokenów z profilu użytkownika.

## Znane zależności i zagrożenia
Autoryzacja Codex CLI w sesji nieinteraktywnej, dostęp do mapowanych dysków, retry przy niepewnym zapisie, kontrola budżetu/tokenów, różnice sandbox Windows i interaktywne aplikacje wymagają osobnych testów. Szczegóły: [Security](SECURITY.md) i [Windows Operations](WINDOWS_OPERATIONS.md).
