# Rejestr decyzji architektonicznych (ADR)

**Data:** 2026-11-15. **Status:** proponowane i przyjęte do dokumentacji projektu; mogą wymagać korekty po pomiarach CTM-01. Nie oznaczają wdrożenia.

## ADR-001 — oddzielne repozytorium
**Decyzja:** `KrzysztofOle/codex-task-manager`, niezależne od `ai-project-templates`, KSeF, T05 i AI_SOTAX.

**Dlaczego:** osobny cykl życia, uprawnienia, integracje i wersjonowanie. Wzorce `ai-project-templates` służą jako punkt odniesienia, nie zależność runtime.

## ADR-002 — lokalny kontroler i trwała kolejka
**Decyzja:** Python 3.12 + SQLite z atomowym claim, historią i recovery; Codex CLI jako wykonawca.

**Dlaczego:** możliwość pracy bez GitHub Actions, inspekcja procesu i trwała kolejka mimo zablokowania sesji. Bezpośrednie automatyzacje Codex App nie stanowią jedynego źródła stanu zależności projektu.

## ADR-003 — Windows Task Scheduler jako etap przejściowy
**Decyzja:** w CTM-02 harmonogram krótkich przebiegów (domyślnie co 5 minut); w CTM-04 zastępuje go usługa Windows.

**Dlaczego:** prostsze MVP i obowiązkowy test `Win+L`; podczas migracji stary Scheduler-worker musi zostać wyłączony.

## ADR-004 — lokalnie jeden worker i domyślny odczyt
**Decyzja:** CTM-01 jeden worker, zadania odczytowe; zapisy do kodu i współbieżność dopiero po wyraźnym dopuszczeniu i izolacji.

**Dlaczego:** niższe ryzyko konfliktów, niepewnego retry i nieautoryzowanych operacji.

## ADR-005 — niezależna weryfikacja
**Decyzja:** `PASS` oznacza spełnienie kryteriów poza tekstem odpowiedzi LLM; niepewny skutek po awarii oznacza `REVIEW` lub `INTERRUPTED`.

**Dlaczego:** deklaracja agenta i exit code to niewystarczający dowód stanu repo/środowiska.

## ADR-006 — panel i MCP dopiero po MVP
**Decyzja:** NiceGUI i System Tray (CTM-03), usługa Windows (CTM-04), MCP i wielu hostów (CTM-05).

**Dlaczego:** UI i dodatkowe integracje nie mogą opóźniać podstawowego przepływu. Brak opcjonalnego MCP nie może blokować menedżera.

## ADR-007 — zaakceptowana architektura usługa + tray
**Decyzja:** niezależna usługa Windows w Session 0 realizuje dispatch i Codex CLI; osobny klient System Tray w sesji użytkownika pokazuje status, menu, powiadomienia i otwiera NiceGUI.

**Dlaczego:** zamknięcie panelu ani zablokowanie sesji nie powinno przerywać prac CLI. Usługa nie steruje GUI.

## ADR-008 — event + rescan co 5 minut
**Decyzja:** sygnał po `enqueue` powoduje bezzwłoczne sprawdzenie kolejki; rescan co domyślnie 300 s jest odpornym fallbackiem. Lease SQLite zapewnia brak duplikacji.

## ADR-009 — autoryzowane lokalne IPC
**Decyzja:** System Tray nie zapisuje SQLite i nie ma uprawnień workera. Preferowany kandydat IPC: Named Pipe z ACL i kontrolą tożsamości (do zakwalifikowania w CTM-03).

## ADR-010 — etapowanie bez blokowania MVP
**Decyzja:** CTM-01 CLI → CTM-02 Scheduler → CTM-03 Tray/NiceGUI → CTM-04 Service → CTM-05 MCP i wiele komputerów. Instalacja usługi wymaga odrębnej zgody i testu konta Codexa/Git.

## Otwarte decyzje
- Schemat plików konfiguracyjnych, wersjonowanie migracji SQLite, format dowodów walidacji.
- Czy i kiedy wprowadzić worktree, ograniczenia zasobów i wymogi budżetowe per projekt.
- Docelowe konto Windows i sposób autoryzacji Codex CLI bez interaktywnej sesji.
- Strategia dystrybucji/instalatora oraz szyfrowania/retencji lokalnego audytu.

Każdą zmianę decyzji dokumentować ze skutkami dla bezpieczeństwa, testów i kompatybilności.
