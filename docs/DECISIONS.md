# Rejestr decyzji architektonicznych (ADR)

**Data:** 2026-11-15. **Status:** proponowane i przyjęte do dokumentacji projektu; mogą wymagać korekty po pomiarach CTM-01. Nie oznaczają wdrożenia.

## ADR-001 — oddzielne repozytorium
**Decyzja:** `KrzysztofOle/codex-task-manager`, niezależne od `ai-project-templates`, KSeF, T05 i AI_SOTAX.

**Dlaczego:** osobny cykl życia, uprawnienia, integracje i wersjonowanie. Wzorce `ai-project-templates` służą jako punkt odniesienia, nie zależność runtime.

## ADR-002 — lokalny kontroler i trwała kolejka
**Decyzja:** Python 3.12 + SQLite z atomowym claim, historią i recovery; Codex CLI jako wykonawca.

**Dlaczego:** możliwość pracy bez GitHub Actions, inspekcja procesu i trwała kolejka mimo zablokowania sesji. Bezpośrednie automatyzacje Codex App nie stanowią jedynego źródła stanu zależności projektu.

## ADR-003 — Windows Task Scheduler, nie stale otwarta aplikacja
**Decyzja:** docelowo harmonogram krótkich przebiegów kontrolera (CTM-02). Usługa Windows tylko gdy uzasadni ją kwalifikacja.

**Dlaczego:** mniej komponentów MVP, łatwiejsza diagnostyka. Blokada nie równa się uśpieniu; test `Win+L` jest obowiązkowy.

## ADR-004 — lokalnie jeden worker i domyślny odczyt
**Decyzja:** CTM-01 jeden worker, zadania odczytowe; zapisy do kodu i współbieżność dopiero po wyraźnym dopuszczeniu i izolacji.

**Dlaczego:** niższe ryzyko konfliktów, niepewnego retry i nieautoryzowanych operacji.

## ADR-005 — niezależna weryfikacja
**Decyzja:** `PASS` oznacza spełnienie kryteriów poza tekstem odpowiedzi LLM; niepewny skutek po awarii oznacza `REVIEW` lub `INTERRUPTED`.

**Dlaczego:** deklaracja agenta i exit code to niewystarczający dowód stanu repo/środowiska.

## ADR-006 — panel i MCP dopiero po MVP
**Decyzja:** NiceGUI (CTM-03), MCP i wielu hostów (CTM-04).

**Dlaczego:** UI i dodatkowe integracje nie mogą opóźniać podstawowego przepływu. Brak opcjonalnego MCP nie może blokować menedżera.

## Otwarte decyzje
- Schemat plików konfiguracyjnych, wersjonowanie migracji SQLite, format dowodów walidacji.
- Czy i kiedy wprowadzić worktree, ograniczenia zasobów i wymogi budżetowe per projekt.
- Docelowe konto Windows i sposób autoryzacji Codex CLI bez interaktywnej sesji.
- Strategia dystrybucji/instalatora oraz szyfrowania/retencji lokalnego audytu.

Każdą zmianę decyzji dokumentować ze skutkami dla bezpieczeństwa, testów i kompatybilności.
