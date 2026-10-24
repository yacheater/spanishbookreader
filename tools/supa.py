"""Shared helpers for talking to the Lector Supabase project with the secret key from .env.

Used by tools/publish_texts.py and tools/queue.py. Accounts are described in inputs/users.json
(gitignored — it holds emails):  {"nastya": {"email": "...", "learns": "es"}, "maria": {...}}
The folder name inputs/<user>/ is the key in that file.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def env():
    f = ROOT / ".env"
    if not f.exists():
        sys.exit("No .env in the project root — see .env.example.")
    vals = {}
    for ln in f.read_text().splitlines():
        if "=" in ln and not ln.lstrip().startswith("#"):
            k, v = ln.split("=", 1)
            vals[k.strip()] = v.split("   #")[0].strip().strip('"')
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if not vals.get(k):
            sys.exit(f".env is missing {k}")
    return vals


def call(method, path, body=None, extra=None):
    cfg = env()
    key = cfg["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, "Content-Type": "application/json", **(extra or {})}
    if not key.startswith("sb_"):          # legacy service_role JWT also goes in Authorization; sb_secret_ keys must not
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(cfg["SUPABASE_URL"].rstrip("/") + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} → {e.code}: {e.read().decode()[:300]}")


def users():
    """{name: {"email", "learns", "id" (None if the account isn't created yet)}}."""
    f = ROOT / "inputs/users.json"
    reg = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    if not reg and env().get("LECTOR_EMAIL"):
        reg = {"nastya": {"email": env()["LECTOR_EMAIL"], "learns": "es"}}
    accounts = call("GET", "/auth/v1/admin/users?per_page=1000")
    accounts = accounts.get("users", accounts) if isinstance(accounts, dict) else accounts
    by_email = {a.get("email", "").lower(): a["id"] for a in accounts}
    for name, u in reg.items():
        u["id"] = by_email.get(u["email"].lower())
    return reg


def name_of(reg, user_id):
    return next((n for n, u in reg.items() if u.get("id") == user_id), None)


q = urllib.parse.quote
