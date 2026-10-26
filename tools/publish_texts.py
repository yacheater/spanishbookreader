"""Upload built texts (texts/<id>.json) to the private Supabase `texts` table.

Owner = the account whose folder the input lives in (inputs/<user>/<id>.txt → inputs/users.json).
Sharing: "share": ["maria"] in inputs/<user>/<id>.meta.json adds those accounts as readers.
Texts are never published with the site. Needs .env (see .env.example) and accounts that exist
(the person must have signed up in the app once).

Usage: python3 tools/publish_texts.py mate [bby_wow …]   (these texts)
       python3 tools/publish_texts.py --all                (every built text — would bring back texts deleted in the app)
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from supa import ROOT, call, users  # noqa: E402


def main():
    reg = users()
    if not sys.argv[1:]:
        sys.exit(__doc__)
    ids = [p.stem for p in sorted((ROOT / "texts").glob("*.json"))] if sys.argv[1:] == ["--all"] else sys.argv[1:]
    for tid in ids:
        d = json.loads((ROOT / f"texts/{tid}.json").read_text(encoding="utf-8"))
        if "chapters" not in d:
            continue
        src = Path(d["source"]["input"])
        owner_name = src.parts[1] if len(src.parts) == 3 else next(iter(reg))
        meta = json.loads((ROOT / src).with_suffix(".meta.json").read_text(encoding="utf-8"))
        owner = reg.get(owner_name, {}).get("id")
        if not owner:
            print(f"skip {tid}: account '{owner_name}' not found — add it to inputs/users.json and let them sign up first")
            continue
        readers, missing = [], []
        for n in meta.get("share", []):
            (readers if reg.get(n, {}).get("id") else missing).append(reg.get(n, {}).get("id") or n)
        words = sum(1 for c in d["chapters"] for p in c["paragraphs"] for t in p if isinstance(t, list))
        from build_text import phrase_index
        info = {"source": d["source"].get("ref", ""), "words": words, "lang": d.get("lang", "es"),
                "glosses": d.get("glosses", []), "license": d.get("license", ""),
                "phrases": phrase_index(d),
                "chapters": [{"id": c["id"], "title": c["title"]} for c in d["chapters"]]}
        row = {"id": tid, "owner": owner, "title": d["title"], "meta": info, "data": d,
               "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if readers:                       # the column exists only after supabase/migrations/002
            row["readers"] = readers
        if meta.get("public"):            # open shelf — column from supabase/migrations/004
            row["public"] = True
        call("POST", "/rest/v1/texts?on_conflict=id", [row],
             {"Prefer": "resolution=merge-duplicates,return=minimal"})
        shared = f", shared with {len(readers)}" if readers else ""
        print(f"uploaded {tid} → {owner_name}{shared}: {d['title']} ({words} words)"
              + (f"  [not shared yet, no account: {', '.join(missing)}]" if missing else ""))


if __name__ == "__main__":
    main()
