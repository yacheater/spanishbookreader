"""Upload built texts (texts/<id>.json) to Supabase so the app on the phone / GitHub Pages can read them.

Texts go into the private `texts` table (see supabase/schema.sql) owned by your account — they are
never published with the site. Needs a `.env` file in the project root (gitignored):
    SUPABASE_URL=https://xxxx.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=...      (Settings → API Keys: a secret key "sb_secret_…" or the legacy
                                        service_role key; keep it secret, never commit)
    LECTOR_EMAIL=you@example.com       (the email you sign in to the app with; sign in once first)

Usage: python3 tools/publish_texts.py            (all texts)
       python3 tools/publish_texts.py mate        (one text)
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def env():
    f = ROOT / ".env"
    if not f.exists():
        sys.exit("No .env in the project root — see the docstring of this script.")
    vals = dict(ln.split("=", 1) for ln in f.read_text().splitlines() if "=" in ln and not ln.startswith("#"))
    vals = {k.strip(): v.strip().strip('"') for k, v in vals.items()}
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "LECTOR_EMAIL"):
        if not vals.get(k):
            sys.exit(f".env is missing {k}")
    return vals


def call(cfg, method, path, body=None, extra=None):
    key = cfg["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, "Content-Type": "application/json", **(extra or {})}
    if not key.startswith("sb_"):          # legacy service_role JWT also goes in Authorization; new sb_secret_ keys must not
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(cfg["SUPABASE_URL"].rstrip("/") + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} → {e.code}: {e.read().decode()[:300]}")


def main():
    cfg = env()
    users = call(cfg, "GET", "/auth/v1/admin/users?per_page=1000")
    users = users.get("users", users) if isinstance(users, dict) else users
    me = next((u for u in users if u.get("email", "").lower() == cfg["LECTOR_EMAIL"].lower()), None)
    if not me:
        sys.exit(f"No Supabase user {cfg['LECTOR_EMAIL']} yet — open the app and sign in once, then rerun.")
    ids = sys.argv[1:] or [p.stem for p in sorted((ROOT / "texts").glob("*.json"))]
    for tid in ids:
        d = json.loads((ROOT / f"texts/{tid}.json").read_text(encoding="utf-8"))
        if "chapters" not in d:
            continue
        words = sum(1 for c in d["chapters"] for p in c["paragraphs"] for t in p if isinstance(t, list))
        meta = {"source": d["source"].get("ref", ""), "words": words,
                "chapters": [{"id": c["id"], "title": c["title"]} for c in d["chapters"]]}
        call(cfg, "POST", "/rest/v1/texts?on_conflict=id",
             [{"id": tid, "owner": me["id"], "title": d["title"], "meta": meta, "data": d,
               "updated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z"}],
             {"Prefer": "resolution=merge-duplicates,return=minimal"})
        print(f"uploaded {tid}: {d['title']} ({words} words)")


if __name__ == "__main__":
    main()
