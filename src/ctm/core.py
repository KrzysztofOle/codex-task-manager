"""SQLite-backed, read-only Codex CLI queue. No scheduler/service/GUI in CTM-01."""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
SCHEMA_VERSION = 1
MAX_PROMPT = 16_384
MAX_LOG_BYTES = 1_048_576


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CTMError(Exception):
    """Invalid operation or preflight failure, never silently ignored."""


def git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], check=True, text=True,
            encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=15, shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CTMError(f"Git preflight failed: {' '.join(args)}") from exc
    return result.stdout.strip()


def repo_info(path: str | Path) -> tuple[str, str]:
    raw = Path(path).expanduser()
    if not raw.is_absolute():
        raise CTMError("Repository path must be absolute")
    try:
        root = raw.resolve(strict=True)
    except OSError as exc:
        raise CTMError("Repository path does not exist") from exc
    if not root.is_dir() or not root.is_absolute():
        raise CTMError("Repository must be an absolute existing directory")
    top = Path(git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if os.path.normcase(str(top)) != os.path.normcase(str(root)):
        raise CTMError("Path must point to the Git repository root")
    try:
        remote = git(root, "remote", "get-url", "origin")
    except CTMError:
        remote = ""
    return str(root), remote


def fingerprint(root: str) -> tuple[str, str]:
    path = Path(root)
    try:
        head = git(path, "rev-parse", "HEAD")
    except CTMError:
        head = "UNBORN"
    # Include untracked files: read-only execution must not create files in repo.
    status = git(path, "status", "--porcelain=v1", "--untracked-files=all")
    return head, status


def secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)


def event(db: sqlite3.Connection, task: str | None, kind: str, detail: str = "") -> None:
    db.execute("INSERT INTO events(task_id,kind,detail,created_at) VALUES(?,?,?,?)",
               (task, kind, detail[:500], utcnow()))


@dataclass(frozen=True)
class Execution:
    code: int
    timed_out: bool
    pid: int | None


class Executor(Protocol):
    def run(self, root: str, prompt: str, timeout: int, out: Path, err: Path) -> Execution: ...


class CodexExecutor:
    """Executes codex with explicit arguments and stdin, never via a shell."""

    def __init__(self, executable: str = "codex") -> None:
        self.executable = executable

    def run(self, root: str, prompt: str, timeout: int, out: Path, err: Path) -> Execution:
        binary = shutil.which(self.executable)
        if not binary:
            raise CTMError("Codex executable not available in this account's PATH")
        args = [binary, "exec", "-C", root, "--sandbox", "read-only", "--json", "-"]
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        with out.open("wb") as stdout, err.open("wb") as stderr:
            process = subprocess.Popen(
                args, cwd=root, stdin=subprocess.PIPE, stdout=stdout,
                stderr=stderr, shell=False, creationflags=creationflags,
                start_new_session=(os.name != "nt"),
            )
            try:
                process.communicate(prompt.encode("utf-8"), timeout=timeout)
                return Execution(process.returncode, False, process.pid)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=10, check=False)
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.kill() if process.poll() is None else None
                process.communicate()
                return Execution(-1, True, process.pid)


def valid_completion(path: Path) -> bool:
    """Check Codex JSONL process completion, not the model's claim of success."""
    if not path.exists() or path.stat().st_size > MAX_LOG_BYTES:
        return False
    completed, failed = False, False
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    completed |= obj.get("type") == "turn.completed"
                    failed |= obj.get("type") == "turn.failed"
    except OSError:
        return False
    return completed and not failed


def trim_log(path: Path) -> None:
    if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
        with path.open("rb+") as stream:
            stream.truncate(MAX_LOG_BYTES)


class Store:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir).expanduser().resolve()
        secure_dir(self.data_dir)
        self.log_dir = self.data_dir / "logs"
        secure_dir(self.log_dir)
        self.db_path = self.data_dir / "tasks.db"
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS projects(
                    id TEXT PRIMARY KEY, root TEXT NOT NULL UNIQUE,
                    origin TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks(
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    prompt TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 50,
                    status TEXT NOT NULL DEFAULT 'PENDING', reason TEXT NOT NULL DEFAULT '',
                    timeout_sec INTEGER NOT NULL, max_attempts INTEGER NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS dependencies(
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    dependency_id TEXT NOT NULL REFERENCES tasks(id),
                    PRIMARY KEY(task_id, dependency_id), CHECK(task_id <> dependency_id));
                CREATE TABLE IF NOT EXISTS attempts(
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                    status TEXT NOT NULL, started_at TEXT NOT NULL,
                    finished_at TEXT, pid INTEGER, exit_code INTEGER,
                    log_stdout TEXT, log_stderr TEXT, note TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT,
                    kind TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT OR IGNORE INTO settings(key,value) VALUES('paused','0');
            """)
            row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row and int(row[0]) != SCHEMA_VERSION:
                raise CTMError("Unknown schema version; backup and migrate explicitly")
            db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version',?)",
                       (str(SCHEMA_VERSION),))
        if os.name != "nt":
            self.db_path.chmod(0o600)

    def connection(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def register(self, name: str, path: str | Path) -> None:
        self._id(name)
        root, origin = repo_info(path)
        with self.connection() as db:
            db.execute("INSERT INTO projects VALUES(?,?,?,?)", (name, root, origin, utcnow()))
            event(db, None, "PROJECT_REGISTERED", name)

    @staticmethod
    def _id(value: str) -> None:
        if not IDENTIFIER.fullmatch(value):
            raise CTMError("Invalid identifier (ASCII letters, digits, _, ., -; max 80 chars)")

    def enqueue(self, task_id: str, project: str, prompt: str,
                dependencies: tuple[str, ...] = (), priority: int = 50,
                timeout: int = 900, max_attempts: int = 1) -> None:
        self._id(task_id)
        if not prompt.strip() or len(prompt) > MAX_PROMPT:
            raise CTMError("Prompt must contain 1..16384 characters")
        if not 1 <= timeout <= 7200 or not 1 <= max_attempts <= 3:
            raise CTMError("Invalid timeout (1..7200) or max_attempts (1..3)")
        if not -1000 <= priority <= 1000:
            raise CTMError("Priority must be -1000..1000")
        if task_id in dependencies:
            raise CTMError("Self dependency")
        for dep in dependencies:
            self._id(dep)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if not db.execute("SELECT 1 FROM projects WHERE id=?", (project,)).fetchone():
                    raise CTMError("Unknown project")
                for dep in dependencies:
                    if not db.execute("SELECT 1 FROM tasks WHERE id=?", (dep,)).fetchone():
                        raise CTMError("Missing dependency: " + dep)
                db.execute("""INSERT INTO tasks(id,project_id,prompt,priority,timeout_sec,
                              max_attempts,created_at) VALUES(?,?,?,?,?,?,?)""",
                           (task_id, project, prompt, priority, timeout, max_attempts, utcnow()))
                db.executemany("INSERT INTO dependencies VALUES(?,?)",
                               [(task_id, dep) for dep in set(dependencies)])
                event(db, task_id, "ENQUEUED", "dependencies=" + str(len(set(dependencies))))
                db.commit()
            except Exception:
                db.rollback()
                raise

    def add_dependency(self, task_id: str, dependency_id: str) -> None:
        self._id(task_id)
        self._id(dependency_id)
        if task_id == dependency_id:
            raise CTMError("Self dependency")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                for task in (task_id, dependency_id):
                    row = db.execute("SELECT status FROM tasks WHERE id=?", (task,)).fetchone()
                    if not row or row["status"] not in ("PENDING", "BLOCKED"):
                        raise CTMError("Dependencies can change only on pending/blocked tasks")
                # Walk dependency_id's ancestors. A path to task_id would create a cycle.
                ancestor = db.execute("""WITH RECURSIVE ancestors(id) AS (
                    SELECT ? UNION SELECT d.dependency_id FROM dependencies d
                    JOIN ancestors a ON d.task_id=a.id)
                    SELECT 1 FROM ancestors WHERE id=? LIMIT 1""",
                    (dependency_id, task_id)).fetchone()
                if ancestor:
                    raise CTMError("Cycle in dependencies")
                db.execute("INSERT INTO dependencies VALUES(?,?)", (task_id, dependency_id))
                event(db, task_id, "DEPENDENCY_ADDED", dependency_id)
                db.commit()
            except Exception:
                db.rollback()
                raise

    def list_tasks(self) -> list[dict]:
        with self.connection() as db:
            return [dict(row) for row in db.execute("""SELECT id,project_id,priority,status,reason,
                attempts,max_attempts,created_at FROM tasks ORDER BY priority DESC,created_at,id""")]

    def get_events(self, task_id: str) -> list[dict]:
        with self.connection() as db:
            return [dict(row) for row in db.execute("""SELECT kind,detail,created_at
                FROM events WHERE task_id=? ORDER BY id""", (task_id,))]

    def set_paused(self, pause: bool) -> None:
        with self.connection() as db:
            db.execute("UPDATE settings SET value=? WHERE key='paused'", ("1" if pause else "0",))
            event(db, None, "PAUSED" if pause else "RESUMED")

    def claim(self) -> tuple[dict, str] | None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0] == "1":
                    db.commit()
                    return None
                # P0 deliberately enforces one global worker, including other processes.
                if db.execute("SELECT 1 FROM tasks WHERE status IN ('RUNNING','VERIFYING') LIMIT 1").fetchone():
                    db.commit()
                    return None
                blocked = db.execute("""SELECT DISTINCT t.id FROM tasks t
                    JOIN dependencies d ON d.task_id=t.id JOIN tasks parent ON parent.id=d.dependency_id
                    WHERE t.status='PENDING' AND parent.status IN
                      ('FAILED','BLOCKED','REVIEW','CANCELLED','INTERRUPTED')""").fetchall()
                for row in blocked:
                    db.execute("UPDATE tasks SET status='BLOCKED',reason='dependency not PASS' WHERE id=?",
                               (row["id"],))
                    event(db, row["id"], "BLOCKED", "dependency not PASS")
                row = db.execute("""SELECT t.*,p.root,p.origin FROM tasks t
                  JOIN projects p ON p.id=t.project_id
                  WHERE t.status='PENDING' AND NOT EXISTS (
                    SELECT 1 FROM dependencies d JOIN tasks dep ON dep.id=d.dependency_id
                    WHERE d.task_id=t.id AND dep.status<>'PASS')
                  ORDER BY t.priority DESC,t.created_at ASC,t.id ASC LIMIT 1""").fetchone()
                if not row:
                    db.commit()
                    return None
                task = dict(row)
                attempt_id = uuid.uuid4().hex
                db.execute("UPDATE tasks SET status='READY' WHERE id=?", (task["id"],))
                event(db, task["id"], "READY")
                db.execute("UPDATE tasks SET status='RUNNING',attempts=attempts+1 WHERE id=?",
                           (task["id"],))
                db.execute("INSERT INTO attempts(id,task_id,status,started_at) VALUES(?,?,?,?)",
                           (attempt_id, task["id"], "RUNNING", utcnow()))
                event(db, task["id"], "RUNNING", attempt_id)
                db.commit()
                return task, attempt_id
            except Exception:
                db.rollback()
                raise

    def finish(self, task: str, attempt: str, status: str, note: str,
               result: Execution | None = None, out: Path | None = None,
               err: Path | None = None) -> None:
        if status not in ("PASS", "FAILED", "BLOCKED", "REVIEW"):
            raise CTMError("Invalid result status")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT status FROM tasks WHERE id=?", (task,)).fetchone()
                if not row or row[0] not in ("RUNNING", "VERIFYING"):
                    raise CTMError("Task not running")
                db.execute("UPDATE tasks SET status='VERIFYING' WHERE id=?", (task,))
                event(db, task, "VERIFYING")
                db.execute("UPDATE tasks SET status=?,reason=? WHERE id=?",
                           (status, note[:300], task))
                db.execute("""UPDATE attempts SET status=?,finished_at=?,exit_code=?,pid=?,
                    log_stdout=?,log_stderr=?,note=? WHERE id=? AND task_id=?""",
                    (status, utcnow(), result.code if result else None,
                     result.pid if result else None,
                     str(out) if out else None, str(err) if err else None,
                     note[:300], attempt, task))
                event(db, task, status, note[:300])
                db.commit()
            except Exception:
                db.rollback()
                raise

    def recover(self) -> int:
        """Manual, operator-only recovery. Caller MUST ensure old worker has exited."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT id FROM tasks WHERE status IN ('RUNNING','VERIFYING')").fetchall()
            for row in rows:
                db.execute("UPDATE tasks SET status='INTERRUPTED',reason='manual recovery: outcome unknown' WHERE id=?", (row[0],))
                db.execute("""UPDATE attempts SET status='INTERRUPTED',finished_at=?,
                    note='manual recovery: outcome unknown' WHERE task_id=? AND status='RUNNING'""",
                    (utcnow(), row[0]))
                event(db, row[0], "INTERRUPTED", "operator recovery; no auto retry")
            db.commit()
            return len(rows)

    def retry(self, task_id: str) -> None:
        """Manual retry; only after operator verifies that effects are safe."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status,attempts,max_attempts FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row or row["status"] not in ("FAILED", "BLOCKED", "REVIEW", "INTERRUPTED"):
                db.rollback()
                raise CTMError("Task cannot be retried")
            if row["attempts"] >= row["max_attempts"]:
                db.rollback()
                raise CTMError("Maximum attempts exhausted")
            db.execute("UPDATE tasks SET status='PENDING',reason='' WHERE id=?", (task_id,))
            event(db, task_id, "RETRY_REQUESTED", "operator verified; no automatic retry")
            db.commit()


class Coordinator:
    def __init__(self, store: Store, executor: Executor | None = None) -> None:
        self.store = store
        self.executor = executor or CodexExecutor()

    def run_once(self) -> dict | None:
        claimed = self.store.claim()
        if claimed is None:
            return None
        task, attempt = claimed
        out = self.store.log_dir / f"{attempt}.jsonl"
        err = self.store.log_dir / f"{attempt}.stderr.log"
        result = None
        status, reason = "REVIEW", "execution outcome uncertain"
        try:
            registered, origin = repo_info(task["root"])
            if registered != task["root"] or origin != task["origin"]:
                raise CTMError("Repository path or origin changed since registration")
            before = fingerprint(task["root"])
            result = self.executor.run(task["root"], task["prompt"], task["timeout_sec"], out, err)
            after = fingerprint(task["root"])
            if before != after:
                status, reason = "REVIEW", "Git HEAD/status changed during read-only execution"
            elif result.timed_out:
                status, reason = "FAILED", "Codex process timed out; manual review before retry"
            elif result.code != 0:
                status, reason = "FAILED", "Codex process failed (nonzero exit code)"
            elif not valid_completion(out):
                status, reason = "FAILED", "Missing Codex JSONL turn.completed event"
            else:
                status, reason = "PASS", "CLI completion verified; Git fingerprint unchanged (semantic quality not assessed)"
        except CTMError as exc:
            status, reason = "BLOCKED", str(exc)
        except (OSError, subprocess.SubprocessError) as exc:
            status, reason = "REVIEW", "Executor/IO error: " + type(exc).__name__
        finally:
            trim_log(out)
            trim_log(err)
            self.store.finish(task["id"], attempt, status, reason, result, out, err)
        return {"id": task["id"], "status": status, "reason": reason}
