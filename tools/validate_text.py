"""Validate a processed text file (texts/<id>.json) against texts/README.md.

Checks: verbatim match with source.input, every word token points to a form, every form to a
lemma, lemma fields per part of speech (6 tenses x 6 persons for verbs, gender/article/plural
for nouns, 4 forms for adjectives). Prints a summary; exit code 1 on any error.

Usage: python3 tools/validate_text.py texts/mate.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TENSES = ["presente", "preterito_indefinido", "preterito_imperfecto",
          "futuro", "condicional", "subjuntivo_presente"]
POS = {"v", "n", "adj", "adv", "prep", "conj", "pron", "det", "num", "interj", "other"}
WORD_RE = re.compile(r"[^\W\d_]")


def norm(text):
    """Paragraphs = non-empty lines, trailing spaces stripped."""
    return [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]


def validate(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = []
    forms, lemmas = doc.get("forms", {}), doc.get("lemmas", {})

    for key in ("id", "title", "source", "chapters", "forms", "lemmas"):
        if key not in doc:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors, {}

    # tokens
    built, n_words, used_forms = [], 0, set()
    for ch in doc["chapters"]:
        for pi, para in enumerate(ch["paragraphs"]):
            parts = []
            for tok in para:
                if isinstance(tok, str):
                    if WORD_RE.search(tok):
                        errors.append(f"{ch['id']} p{pi + 1}: letters in a non-word token {tok!r}")
                    parts.append(tok)
                elif isinstance(tok, list) and len(tok) in (2, 3):
                    n_words += 1
                    parts.append(tok[0])
                    if tok[1] is None:      # proper name / not in lexicon: plain text
                        continue
                    if tok[1] not in forms:
                        errors.append(f"{ch['id']} p{pi + 1}: {tok[0]!r} -> unknown form {tok[1]!r}")
                    used_forms.add(tok[1])
                else:
                    errors.append(f"{ch['id']} p{pi + 1}: bad token {tok!r}")
            built.append("".join(parts))

    # verbatim
    src = doc["source"].get("input")
    if not src or not (ROOT / src).exists():
        errors.append(f"source.input not found: {src}")
    else:
        expected = norm((ROOT / src).read_text(encoding="utf-8"))
        got = norm("\n".join(built))
        if expected != got:
            for i, (e, g) in enumerate(zip(expected, got)):
                if e != g:
                    j = next((k for k in range(min(len(e), len(g))) if e[k] != g[k]), min(len(e), len(g)))
                    errors.append(f"verbatim mismatch in paragraph {i + 1} at char {j}: "
                                  f"source {e[j:j + 40]!r} vs json {g[j:j + 40]!r}")
                    break
            if len(expected) != len(got):
                errors.append(f"paragraph count: source {len(expected)}, json {len(got)}")

    # phrases
    for o in (doc["chapters"][0].get("phraseOcc") or []):
        if o["ph"] not in doc.get("phrases", {}):
            errors.append(f"phrase occurrence points to unknown phrase {o['ph']}")

    # forms -> lemmas
    for fk, f in forms.items():
        if f.get("lemma") not in lemmas:
            errors.append(f"form {fk}: unknown lemma {f.get('lemma')!r}")
        if not f.get("en"):
            errors.append(f"form {fk}: empty 'en'")
    unused = set(forms) - used_forms
    if unused:
        errors.append(f"{len(unused)} forms not used by any token, e.g. {sorted(unused)[:5]}")

    # lemmas
    for lk, lm in lemmas.items():
        pos = lm.get("pos")
        if pos not in POS:
            errors.append(f"lemma {lk}: bad pos {pos!r}")
        if not lm.get("en"):
            errors.append(f"lemma {lk}: empty 'en'")
        if lm.get("lang") == "en":                  # English lemma: forms come from tools/english.py
            if pos == "v" and not all((lm.get("forms") or {}).get(k) for k in ("base", "s", "past", "pp", "ing")):
                errors.append(f"lemma {lk}: English verb needs base/s/past/pp/ing forms")
            if pos == "n" and not lm.get("plural"):
                errors.append(f"lemma {lk}: English noun needs a plural")
            continue
        if pos == "v":
            conj = lm.get("conjugation", {})
            for t in TENSES:
                if len(conj.get(t, [])) != 6 or not all(conj.get(t, [])):
                    errors.append(f"lemma {lk}: conjugation.{t} must have 6 non-empty forms")
        elif pos == "n":
            for k in ("gender", "article", "plural"):
                if not lm.get(k):
                    errors.append(f"lemma {lk}: missing {k}")
        elif pos == "adj":
            fs = lm.get("forms", {})
            for k in ("m_sg", "f_sg", "m_pl", "f_pl"):
                if not fs.get(k):
                    errors.append(f"lemma {lk}: missing forms.{k}")

    stats = {"chapters": len(doc["chapters"]), "paragraphs": len(built), "word tokens": n_words,
             "forms": len(forms), "lemmas": len(lemmas),
             "verbs": sum(1 for v in lemmas.values() if v.get("pos") == "v")}
    return errors, stats


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    errs, stats = validate(sys.argv[1])
    for k, v in stats.items():
        print(f"{k}: {v}")
    if errs:
        print(f"\nFAIL — {len(errs)} error(s):")
        for e in errs[:50]:
            print(" -", e)
        sys.exit(1)
    print("\nOK")
