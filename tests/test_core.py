from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ctm.core import CTMError, Coordinator, Execution, Store, CodexExecutor, fingerprint
from ctm.cli import main


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "README.txt").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Tester", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
    return repo


class FakeRunner:
    def __init__(self, code=0, completion=True, mutate=False, timeout=False):
        self.code = code
        self.completion = completion
        self.mutate = mutate
        self.timeout = timeout
        self.calls = []

    def run(self, root, prompt, timeout, out, err):
        self.calls.append(prompt)
        records = [{"type": "item.completed", "item": {"text": "PASS"}}]
        if self.completion:
            records.append({"type": "turn.completed", "usage": {"input_tokens": 1}})
        out.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        err.write_text("", encoding="utf-8")
        if self.mutate:
            (Path(root) / "injected.txt").write_text("unexpected\n")
        return Execution(self.code, self.timeout, 99999)


@pytest.fixture
def env(tmp_path):
    repo = make_repo(tmp_path)
    store = Store(tmp_path / "private")
    store.register("sample", repo)
    return store, repo


def get_state(store, task_id):
    return {r["id"]: r["status"] for r in store.list_tasks()}[task_id]


def test_order_and_pass(env):
    store, _ = env
    store.enqueue("A", "sample", "read status")
    store.enqueue("B", "sample", "read status", ("A",))
    runner = FakeRunner()
    worker = Coordinator(store, runner)
    assert worker.run_once()["id"] == "A"
    assert get_state(store, "B") == "PENDING"
    assert worker.run_once()["id"] == "B"
    assert worker.run_once() is None
    assert runner.calls == ["read status", "read status"]
    assert get_state(store, "A") == "PASS"
    assert get_state(store, "B") == "PASS"
    assert {e["kind"] for e in store.get_events("A")} >= {"READY", "RUNNING", "VERIFYING", "PASS"}


def test_failure_blocks_only_dependency(env):
    store, _ = env
    store.enqueue("A", "sample", "A", priority=100)
    store.enqueue("B", "sample", "B", ("A",), priority=50)
    store.enqueue("C", "sample", "C", priority=1)
    assert Coordinator(store, FakeRunner(code=1)).run_once()["status"] == "FAILED"
    assert Coordinator(store, FakeRunner()).run_once()["id"] == "C"
    assert get_state(store, "B") == "BLOCKED"


def test_model_claim_cannot_bypass_verifier(env):
    store, _ = env
    store.enqueue("A", "sample", "analyse")
    result = Coordinator(store, FakeRunner(completion=False)).run_once()
    assert result["status"] == "FAILED"
    assert "turn.completed" in result["reason"]


def test_git_fingerprint_modified_is_review(env):
    store, repo = env
    store.enqueue("A", "sample", "analyse")
    assert Coordinator(store, FakeRunner(mutate=True)).run_once()["status"] == "REVIEW"
    assert (repo / "injected.txt").exists()


def test_wrong_repo_and_unregistered(env, tmp_path):
    store, repo = env
    other = make_repo(tmp_path / "second")
    with pytest.raises(CTMError):
        store.register("bad", other / ".git")
    with pytest.raises(CTMError):
        store.enqueue("X", "missing", "prompt")
    with pytest.raises(CTMError):
        store.enqueue("A", "sample", "prompt", ("unknown",))


def test_cycle_and_self_dependency(env):
    store, _ = env
    store.enqueue("A", "sample", "A")
    store.enqueue("B", "sample", "B", ("A",))
    with pytest.raises(CTMError, match="Cycle"):
        store.add_dependency("A", "B")
    with pytest.raises(CTMError, match="Self"):
        store.add_dependency("A", "A")


def test_atomic_claim_between_connections(env):
    store, _ = env
    store.enqueue("A", "sample", "A")
    store.enqueue("B", "sample", "B")
    a = store.claim()
    assert a is not None and a[0]["id"] == "A"
    assert Store(store.data_dir).claim() is None
    store.finish("A", a[1], "PASS", "synthetic verified")
    b = Store(store.data_dir).claim()
    assert b is not None and b[0]["id"] == "B"
    store.finish("B", b[1], "PASS", "synthetic verified")


def test_recovery_manual_no_auto_retry(env):
    store, _ = env
    store.enqueue("A", "sample", "A", max_attempts=2)
    assert store.claim()
    assert Store(store.data_dir).claim() is None
    assert store.recover() == 1
    assert get_state(store, "A") == "INTERRUPTED"
    assert store.recover() == 0
    assert store.claim() is None
    assert store.get_events("A")[-1]["kind"] == "INTERRUPTED"
    store.retry("A")
    assert Coordinator(store, FakeRunner()).run_once()["status"] == "PASS"


def test_retry_limited_and_manual(env):
    store, _ = env
    store.enqueue("A", "sample", "A", max_attempts=1)
    assert Coordinator(store, FakeRunner(code=2)).run_once()["status"] == "FAILED"
    with pytest.raises(CTMError, match="Maximum"):
        store.retry("A")
    store.enqueue("B", "sample", "B", max_attempts=2)
    assert Coordinator(store, FakeRunner(code=2)).run_once()["status"] == "FAILED"
    store.retry("B")
    assert Coordinator(store, FakeRunner()).run_once()["status"] == "PASS"


def test_pause_resume(env):
    store, _ = env
    store.enqueue("A", "sample", "A")
    store.set_paused(True)
    assert Coordinator(store, FakeRunner()).run_once() is None
    store.set_paused(False)
    assert Coordinator(store, FakeRunner()).run_once()["status"] == "PASS"


def test_timeout_and_empty_jsonl(env):
    store, _ = env
    store.enqueue("A", "sample", "A")
    assert Coordinator(store, FakeRunner(timeout=True)).run_once()["status"] == "FAILED"


def test_persistence_no_prompt_in_list(env):
    store, _ = env
    store.enqueue("A", "sample", "SENSITIVE_PROMPT")
    result = Store(store.data_dir).list_tasks()
    assert result[0]["status"] == "PENDING"
    assert "SENSITIVE_PROMPT" not in str(result)


def test_invalid_prompts_and_ids(env):
    store, _ = env
    with pytest.raises(CTMError):
        store.enqueue("invalid id", "sample", "x")
    with pytest.raises(CTMError):
        store.enqueue("X", "sample", "")
    with pytest.raises(CTMError):
        store.enqueue("X", "sample", "x", timeout=0)


def test_codex_missing_is_blocked(env):
    store, _ = env
    store.enqueue("A", "sample", "hello")
    result = Coordinator(store, CodexExecutor("codex-absent-test-12345678")).run_once()
    assert result["status"] == "BLOCKED"
    assert "PATH" in result["reason"]


def test_cli_integration_without_live_codex(env, tmp_path, capsys):
    store, repo = env
    file = tmp_path / "prompt.txt"
    file.write_text("test", encoding="utf-8")
    assert main(["--data-dir", str(store.data_dir), "enqueue", "A", "sample", "--prompt-file", str(file)]) == 0
    assert main(["--data-dir", str(store.data_dir), "list"]) == 0
    assert "test" not in capsys.readouterr().out
    assert main(["--data-dir", str(store.data_dir), "pause"]) == 0
    assert main(["--data-dir", str(store.data_dir), "run-once"]) == 0
    assert get_state(store, "A") == "PENDING"


def test_changed_origin_blocks(env):
    store, repo = env
    store.enqueue("A", "sample", "read")
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", "https://example.invalid/other.git"], check=True)
    result = Coordinator(store, FakeRunner()).run_once()
    assert result["status"] == "BLOCKED"


def test_process_runner_fake_executable(env, tmp_path):
    if os.name == "nt":
        pytest.skip("Shell-free fake executable uses POSIX shebang; real Windows CLI NOT_RUN")
    store, repo = env
    fake = tmp_path / "fake_codex"
    fake.write_text(f"#!{sys.executable}\n"
                    "import sys,json\n"
                    "assert sys.argv[1:4] == ['exec','-C',sys.argv[3]]\n"
                    "assert '--sandbox' in sys.argv and 'read-only' in sys.argv\n"
                    "assert '--json' in sys.argv and sys.argv[-1] == '-'\n"
                    "assert sys.stdin.read() == 'read-only'\n"
                    "print(json.dumps({'type':'turn.completed'}))\n")
    fake.chmod(0o700)
    store.enqueue("A", "sample", "read-only")
    result = Coordinator(store, CodexExecutor(str(fake))).run_once()
    assert result["status"] == "PASS"


def test_preflight_block_does_not_spend_attempt(env):
    store, _ = env
    store.enqueue("A", "sample", "read")
    assert Coordinator(store, CodexExecutor("codex-not-installed-91237")).run_once()["status"] == "BLOCKED"
    assert next(t for t in store.list_tasks() if t["id"] == "A")["attempts"] == 0
    store.retry("A")
    assert Coordinator(store, FakeRunner()).run_once()["status"] == "PASS"


def test_stale_finish_rejected_after_manual_recovery(env):
    store, _ = env
    store.enqueue("A", "sample", "read", max_attempts=2)
    _, attempt = store.claim()
    assert store.recover() == 1
    store.retry("A")
    _, current = store.claim()
    with pytest.raises(CTMError, match="stale"):
        store.finish("A", attempt, "PASS", "obsolete result")
    assert get_state(store, "A") == "RUNNING"
    store.finish("A", current, "PASS", "synthetic verified")
    assert get_state(store, "A") == "PASS"


def test_embedded_credentials_in_git_remote_rejected(tmp_path):
    repo = make_repo(tmp_path)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin",
                    "https://user:secret@example.invalid/private.git"], check=True)
    store = Store(tmp_path / "private")
    with pytest.raises(CTMError, match="credentials"):
        store.register("unsafe", repo)
