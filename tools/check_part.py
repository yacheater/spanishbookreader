"""Check one lexicon annotation part (lex/parts/partN.forms.json + partN.lemmas.json) against its chunk.

Reports: chunk words neither annotated nor listed as names, forms pointing to undefined lemmas,
missing lemma fields, and forms that the grammar engine can't recognise for their lemma
(wrong lemma, wrong verb model, or a manual analysis is needed). Prints the conjugation of
every verb with a stem-change model so it can be eyeballed.

Usage: python3 tools/check_part.py 7 [lex/missing_<id>.tsv]   (default word list: lex/parts/chunk_7.tsv)
       python3 tools/check_part.py 1 lex_en/missing_<id>.tsv --en     (English lexicon: lex_en/parts/)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_text import auto_analysis, split_key, POS_LABEL  # noqa: E402
from conjugate import conjugate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if a != "--en"]
LANG = "en" if "--en" in sys.argv else "es"
n = args[0]
P = ROOT / ("lex_en/parts" if LANG == "en" else "lex/parts")
forms = json.loads((P / f"part{n}.forms.json").read_text(encoding="utf-8"))
lemmas = json.loads((P / f"part{n}.lemmas.json").read_text(encoding="utf-8"))
names_f = P / f"part{n}.names.json"
names = set(json.loads(names_f.read_text(encoding="utf-8"))) if names_f.exists() else set()
chunk_file = Path(args[1]) if len(args) > 1 else P / f"chunk_{n}.tsv"
chunk = [ln.split("\t")[0] for ln in chunk_file.read_text(encoding="utf-8").splitlines()
         if ln and not ln.startswith("surface\t")]

problems = []
for w in chunk:
    if w not in forms and w not in names:
        problems.append(f"not annotated: {w}")
for k, lm in lemmas.items():
    lemma, pos = split_key(k)
    if pos not in POS_LABEL:
        problems.append(f"lemma {k}: unknown pos {pos!r}")
    if not lm.get("en"):
        problems.append(f"lemma {k}: no en")
    if LANG == "es" and pos == "n" and lm.get("g") not in ("m", "f", "m/f"):
        problems.append(f"lemma {k}: g must be m / f / m/f")
    if LANG == "es" and pos == "v" and lm.get("m") not in (None, "e>ie", "e>ie,i", "o>ue", "o>ue,u", "e>i", "u>ue", "í", "ú"):
        problems.append(f"lemma {k}: bad model {lm.get('m')!r}")
for surf, e in forms.items():
    if not isinstance(e, list) or len(e) not in (2, 3) or not e[1]:
        problems.append(f"form {surf}: must be [lemmaKey, en] or [lemmaKey, en, analysis]")
        continue
    if e[0] not in lemmas:
        problems.append(f"form {surf}: lemma {e[0]} not defined in part{n}.lemmas.json")
        continue
    if len(e) == 2:
        a = auto_analysis(surf.split("#")[0], e[0], lemmas, LANG)
        if a is None:
            problems.append(f"form {surf}: not recognised as a form of {e[0]} — fix lemma/model or add analysis")
for k, lm in lemmas.items():
    if LANG == "es" and k.endswith(".v") and lm.get("m"):
        c = conjugate(k[:-2], lm["m"])
        print(f"{k} [{lm['m']}]: pres {' '.join(c['presente'])} | subj {' '.join(c['subjuntivo_presente'])}")
print(f"part{n}: {len(forms)} forms, {len(lemmas)} lemmas, {len(names)} names, chunk {len(chunk)}")
print("OK" if not problems else f"{len(problems)} problem(s):")
for p in problems:
    print(" -", p)
