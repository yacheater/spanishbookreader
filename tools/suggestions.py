"""The "Suggest a text" queue: texts friends (or you) sent from the app's Texts page.

  python3 tools/suggestions.py list                 — open suggestions (new / processing) with who sent them
  python3 tools/suggestions.py take <n> <text_id>   — write inputs/<user>/<text_id>.txt + .meta.json, mark processing
  python3 tools/suggestions.py done <n> <text_id>   — mark done (the sender sees "Ready" in the app)
  python3 tools/suggestions.py reject <n> "reason"  — mark rejected with a short reason shown to the sender

After `take`: build, annotate, `publish_texts.py <text_id>`, then `done`. If the suggestion has only a link,
`take` writes an empty .txt — fill it from the page (verbatim) before building. Song lyrics are never
processed (copyright) — reject with an offer of a study text about the song instead.
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supa import ROOT, call, users, name_of, q  # noqa: E402

now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()  # noqa: E731


def get(n):
    rows = call("GET", f"/rest/v1/submissions?id=eq.{int(n)}&select=*")
    if not rows:
        sys.exit(f"no suggestion #{n}")
    return rows[0]


def update(n, fields):
    call("PATCH", f"/rest/v1/submissions?id=eq.{int(n)}", fields, {"Prefer": "return=minimal"})


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    reg = users()
    if cmd == "list":
        rows = call("GET", "/rest/v1/submissions?status=in.(new,processing)&select=*&order=created_at")
        if not rows:
            print("queue is empty")
        for r in rows:
            who = name_of(reg, r["user_id"]) or "unknown account (add to inputs/users.json)"
            print(f"#{r['id']} [{r['status']}] {who}: {r['title'] or '(no title)'}"
                  f"{' · ' + r['source_url'] if r['source_url'] else ''} · {len(r['body'])} chars"
                  f"{' · note: ' + r['note'] if r['note'] else ''}")
    elif cmd == "take":
        n, tid = sys.argv[2], sys.argv[3]
        if not re.fullmatch(r"[a-z0-9_]+", tid):
            sys.exit("text_id: lowercase letters, digits, _ only")
        r = get(n)
        who = name_of(reg, r["user_id"])
        if not who:
            sys.exit("sender is not in inputs/users.json")
        folder = ROOT / f"inputs/{who}"
        folder.mkdir(parents=True, exist_ok=True)
        body = "\n".join(ln.strip() for ln in r["body"].replace("\r\n", "\n").split("\n") if ln.strip())
        (folder / f"{tid}.txt").write_text(body + ("\n" if body else ""), encoding="utf-8")
        meta = {"id": tid, "title": r["title"] or tid, "submission": r["id"],
                "source": {"kind": "url" if r["source_url"] else "txt", "ref": r["source_url"],
                           "retrieved": now()[:10], "edited": "Suggested in the app; text as pasted."}}
        (folder / f"{tid}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        update(n, {"status": "processing", "text_id": tid})
        print(f"#{n} → inputs/{who}/{tid}.txt ({len(body)} chars{'; EMPTY — fill it from the link' if not body else ''})")
    elif cmd == "done":
        n, tid = sys.argv[2], sys.argv[3]
        update(n, {"status": "done", "text_id": tid, "processed_at": now(), "reply": "Ready — open it in Texts."})
        print(f"#{n} done")
    elif cmd == "reject":
        n, reason = sys.argv[2], " ".join(sys.argv[3:])
        update(n, {"status": "rejected", "processed_at": now(), "reply": reason})
        print(f"#{n} rejected")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
