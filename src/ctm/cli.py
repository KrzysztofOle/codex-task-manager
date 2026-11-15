"""Command-line entrypoint for CTM-01, no GUI and no scheduling."""
from __future__ import annotations

import argparse
import json
import os
import sys
import sqlite3
from pathlib import Path

from .core import CTMError, Coordinator, Store


def default_data_dir() -> Path:
    base = os.environ.get("PROGRAMDATA") if os.name == "nt" else None
    return Path(base or (Path.home() / ".local" / "share")) / "CodexTaskManager"


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(prog="ctm", description="Local read-only Codex task queue")
    cli.add_argument("--data-dir", type=Path, default=default_data_dir())
    sub = cli.add_subparsers(dest="command", required=True)
    project = sub.add_parser("register", help="Register the root of a local Git repository")
    project.add_argument("id")
    project.add_argument("root")
    task = sub.add_parser("enqueue", help="Queue a read-only task from a UTF-8 prompt file")
    task.add_argument("id")
    task.add_argument("project")
    task.add_argument("--prompt-file", required=True, type=Path)
    task.add_argument("--depends-on", action="append", default=[])
    task.add_argument("--priority", type=int, default=50)
    task.add_argument("--timeout", type=int, default=900)
    task.add_argument("--max-attempts", type=int, default=1)
    dep = sub.add_parser("depend", help="Add a dependency to a pending task")
    dep.add_argument("id")
    dep.add_argument("dependency")
    sub.add_parser("list", help="List task states (never prints prompts)")
    history = sub.add_parser("history", help="List event metadata for a task")
    history.add_argument("id")
    sub.add_parser("run-once", help="Run at most one ready task, blocking until complete")
    sub.add_parser("pause")
    sub.add_parser("resume")
    recover = sub.add_parser("recover", help="Mark orphaned running tasks as INTERRUPTED")
    recover.add_argument("--confirm-no-active-worker", action="store_true", required=True)
    retry = sub.add_parser("retry", help="Manually retry after effects have been reviewed")
    retry.add_argument("id")
    retry.add_argument("--confirm-safe", action="store_true", required=True)
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        store = Store(args.data_dir)
        if args.command == "register":
            store.register(args.id, args.root)
            result = {"registered": args.id}
        elif args.command == "enqueue":
            prompt = args.prompt_file.read_text(encoding="utf-8")
            store.enqueue(args.id, args.project, prompt, tuple(args.depends_on),
                          args.priority, args.timeout, args.max_attempts)
            result = {"queued": args.id}
        elif args.command == "depend":
            store.add_dependency(args.id, args.dependency)
            result = {"dependency_added": [args.id, args.dependency]}
        elif args.command == "list":
            result = store.list_tasks()
        elif args.command == "history":
            result = store.get_events(args.id)
        elif args.command == "run-once":
            result = Coordinator(store).run_once() or {"status": "IDLE"}
        elif args.command in ("pause", "resume"):
            store.set_paused(args.command == "pause")
            result = {"paused": args.command == "pause"}
        elif args.command == "recover":
            result = {"interrupted": store.recover()}
        elif args.command == "retry":
            store.retry(args.id)
            result = {"retry_queued": args.id}
        else:
            return 2
        print(json.dumps(result, ensure_ascii=False))
        return 1 if args.command == "run-once" and result.get("status") in ("FAILED", "BLOCKED", "REVIEW") else 0
    except (CTMError, OSError, ValueError, UnicodeError, sqlite3.Error) as exc:
        print(f"CTM error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
