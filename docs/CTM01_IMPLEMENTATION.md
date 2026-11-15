# CTM-01 — Local read-only queue: implementation and verification

**State:** implementation committed to `feature/ctm-01-local-queue`; synthetic/offline verification available. **Windows 11/Codex CLI live: NOT RUN** in the model's container. Do not describe this as a qualified Windows installation.

## Implemented

- Python 3.12+ CLI package (`ctm`), standard-library SQLite database, local Git project registry, persistent tasks and dependency graph.
- Atomic `BEGIN IMMEDIATE` claim, globally one active task in P0; priorities, deterministic ordering, dependency gate (`PASS` only), pause/resume, audit events.
- `codex exec -C <repo> --sandbox read-only --json -` launched without shell; prompt passed on stdin, explicit timeout, captured stdout JSONL and stderr logs, bounded retained log files.
- Objective **process-level** verification: zero exit code, presence of `turn.completed` JSONL event and no `turn.failed` event, unchanged Git HEAD and porcelain status. A model's statement of “PASS” is not accepted.
- Repository root/origin validation, refusal of embedded credentials in Git origin, input limits, refusal of self/cyclic dependencies.
- Manual retry with explicit safety gate, `max_attempts` budget, manual recovery to `INTERRUPTED` with no automatic retry, stale attempt rejection.
- SQLite data and logs outside the repository; Python CLI never prints prompt bodies when listing tasks.

## Not implemented / limits

- **No scheduler, service, System Tray, NiceGUI, MCP, multiple-host workers, automated code changes or merge** (these belong to CTM-02–05).
- No automatic retry/backoff is enabled in CTM-01. All retries are manual after verifying effects; this is a deliberate fail-closed restriction while external MCP side-effects cannot be excluded. Requirement F-07 automatic backoff remains OPEN.
- A read-only Codex sandbox protects repository writes according to Codex runtime, **but does not by itself prove third-party MCP tools cannot write**. Before any live execution, review your connected tools and run only tasks with permitted external capabilities. Do not execute prompts containing secrets or client data.
- `PASS` verifies *CLI execution and unchanged Git*, **not the factual or semantic correctness of an AI-produced analysis**. An additional trusted domain-specific validator is needed before using a result as evidence for another production-relevant action.
- A real Windows CLI test, Windows logon/credential handling, NTFS ACL qualification, `Win+L`, restart, service and scheduler behavior remain **NOT RUN**.
- SQLite is initialized with schema version 1. Later schema upgrades require a versioned migration and a tested backup/rollback; no silent migrations.

## Windows developer quick start (manual, no admin service)

Run on a dedicated Windows development machine in PowerShell, with Python 3.12 and Git installed:

```powershell
cd C:\VSCode\codex-task-manager
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$ctm = ".\.venv\Scripts\ctm.exe"
$data = Join-Path $env:LOCALAPPDATA "CodexTaskManager"
& $ctm --data-dir $data register sample "C:\VSCode\ai-project-templates"
```

Replace `sample` path with an **existing, confirmed Git repo root** (not a parent workspace). The command above is only an example and does not run an agent. Use a fresh sandbox/test repo first; production-relevant projects require project-specific approval.

Create a **safe read-only task prompt** in a file outside the managed repo (example: `$env:TEMP\ctm-read-only.txt`), then:

```powershell
& $ctm --data-dir $data enqueue READ-01 sample --prompt-file "$env:TEMP\ctm-read-only.txt"
& $ctm --data-dir $data list
& $ctm --data-dir $data run-once
& $ctm --data-dir $data history READ-01
```

For a dependent task create another prompt and queue it with `--depends-on READ-01`. Run `run-once` a second time after the first task is verified `PASS`.

Additional commands:

```powershell
& $ctm --data-dir $data pause
& $ctm --data-dir $data resume
# ONLY after ensuring no previous CTM worker is running:
& $ctm --data-dir $data recover --confirm-no-active-worker
# ONLY after reviewing results and confirming retry is safe:
& $ctm --data-dir $data retry READ-01 --confirm-safe
```

Use `--max-attempts 2` at enqueue time if a manual retry may be needed; default is **1**. A preflight `BLOCKED` with no executed process does not consume an attempt. Existing tasks with exhausted attempts cannot be retried without a new task ID.

**Security:** CTM-01 defaults to `%LOCALAPPDATA%\CodexTaskManager`, not a shared folder. Check that logs and SQLite are protected by NTFS ACLs for your account; do not upload the database/logs to public GitHub. A future Windows service will use its own qualified data directory and identity.

## Offline checks

Run on a machine with Python 3.12+ and pytest:

```powershell
py -3.12 -m pip install -e . pytest
py -3.12 -m pytest -q --tb=short tests\test_core.py
```

Synthetic fixture uses real temporary Git repositories and an injected fake Codex executor. A POSIX-only additional test launches an executable shim and verifies argument passing/JSONL; it is skipped on Windows. The tests do **not** authenticate to OpenAI, spend GitHub Actions minutes or exercise Windows API.

**Observed offline result (model's Linux environment, Python 3.13.5, pytest 9.0.2): 20/20 PASS.** Live Windows/Codex status: **NOT RUN**. This is an implementation checkpoint, not complete CTM-01 qualification.

## Exit criteria before starting CTM-02

1. Install on Windows 11 and confirm CLI version / read-only sandbox behavior on a disposable Git repo.
2. Verify authenticated Codex CLI can execute safe prompts; records and logs in the correct local profile.
3. Qualify NTFS ACLs; check that no writable MCP tools are reachable by the test agent.
4. Rerun tests on Python 3.12 / Windows, record actual results and log metadata outside public Git.
5. Decide whether explicit read-only retry/backoff can be safely implemented without external effects; otherwise keep manual-only policy and document F-07 as OPEN.
