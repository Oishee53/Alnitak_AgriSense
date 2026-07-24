"""Export / import session history and agent traces as JSON.

The SQLite database is gitignored (it is local state, and it would churn on
every commit), so it never travels with the repo. This script is the bridge:
export produces a single committable JSON file holding sessions, messages and
the full agent trace; import replays it into any machine's database.

Use it to:
  * archive a good demo run so it survives a laptop reset or a fresh clone,
  * hand a recorded conversation to a teammate,
  * keep a "golden" trace to show judges if the live demo misbehaves.

    python scripts/export_sessions.py                      # all sessions -> data/exports/
    python scripts/export_sessions.py --session <id>       # just one
    python scripts/export_sessions.py --out demo.json      # choose the file
    python scripts/export_sessions.py --import-file demo.json
    python scripts/export_sessions.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.memory.db import SessionLocal, init_db  # noqa: E402
from app.memory.models import Message, Session, TraceEntry  # noqa: E402

EXPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "exports"


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def export(session_id: str | None, out: Path) -> None:
    with SessionLocal() as db:
        q = db.query(Session)
        if session_id:
            q = q.filter(Session.id == session_id)
        sessions = q.all()
        if not sessions:
            print(f"no sessions found{f' for {session_id}' if session_id else ''}")
            return

        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "sessions": [],
        }
        total_trace = 0
        for s in sessions:
            msgs = (
                db.query(Message)
                .filter(Message.session_id == s.id)
                .order_by(Message.created_at, Message.id)
                .all()
            )
            trace = (
                db.query(TraceEntry)
                .filter(TraceEntry.session_id == s.id)
                .order_by(TraceEntry.id)
                .all()
            )
            total_trace += len(trace)
            payload["sessions"].append(
                {
                    "id": s.id,
                    "created_at": _iso(s.created_at),
                    "profile_snapshot": s.profile_snapshot,
                    "latest_plan": s.latest_plan,
                    "messages": [
                        {"role": m.role, "content": m.content, "created_at": _iso(m.created_at)}
                        for m in msgs
                    ],
                    "trace": [
                        {
                            "kind": t.kind,
                            "tool": t.tool,
                            "params": t.params,
                            "result": t.result,
                            "summary": t.summary,
                            "created_at": _iso(t.created_at),
                        }
                        for t in trace
                    ],
                }
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"exported {len(payload['sessions'])} session(s), {total_trace} trace step(s) -> {out}"
    )


def import_file(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    init_db()
    added = skipped = steps = 0
    with SessionLocal() as db:
        for s in payload.get("sessions", []):
            if db.get(Session, s["id"]) is not None:
                skipped += 1
                continue  # never clobber an existing session
            db.add(
                Session(
                    id=s["id"],
                    profile_snapshot=s.get("profile_snapshot") or {},
                    latest_plan=s.get("latest_plan") or {},
                )
            )
            for m in s.get("messages", []):
                db.add(Message(session_id=s["id"], role=m["role"], content=m["content"]))
            for t in s.get("trace", []):
                steps += 1
                db.add(
                    TraceEntry(
                        session_id=s["id"],
                        kind=t["kind"],
                        tool=t.get("tool"),
                        params=t.get("params"),
                        result=t.get("result"),
                        summary=t.get("summary"),
                    )
                )
            added += 1
        db.commit()
    print(f"imported {added} session(s), {steps} trace step(s); skipped {skipped} already present")


def list_sessions() -> None:
    with SessionLocal() as db:
        rows = db.query(Session).order_by(Session.created_at).all()
        if not rows:
            print("no sessions in the database")
            return
        print(f"{'session id':34}  {'msgs':>4}  {'trace':>5}  profile")
        for s in rows:
            m = db.query(Message).filter(Message.session_id == s.id).count()
            t = db.query(TraceEntry).filter(TraceEntry.session_id == s.id).count()
            prof = s.profile_snapshot or {}
            label = " · ".join(
                str(v) for v in [prof.get("location"), prof.get("target_season")] if v
            )
            print(f"{s.id:34}  {m:>4}  {t:>5}  {label}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", help="export only this session id")
    ap.add_argument("--out", type=Path, help="output file (default data/exports/<stamp>.json)")
    ap.add_argument("--import-file", type=Path, dest="import_path", help="import a JSON export")
    ap.add_argument("--list", action="store_true", help="list sessions with message/trace counts")
    args = ap.parse_args()

    if args.list:
        list_sessions()
    elif args.import_path:
        import_file(args.import_path)
    else:
        out = args.out or EXPORT_DIR / f"sessions-{datetime.now():%Y%m%d-%H%M%S}.json"
        export(args.session, out)


if __name__ == "__main__":
    main()
