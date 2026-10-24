"""Build texts/<id>.json + app/data/<id>.js from inputs/<id>.txt and the shared lexicon in lex/.

Every word is looked up in lex/forms.json (+ lex/parts/*.forms.json): surface -> [lemma key, English,
optional manual analysis]. Grammar (verb tense/person, noun number, adjective gender) is derived
automatically: verbs through tools/conjugate.py, nouns/adjectives from lex/lemmas.json.
Proper names come from lex/names.json + lex/parts/*.names.json. Unknown words (incl. capitalised ones
not listed as names) are written to lex/missing_<id>.tsv (surface, count, context) — the build still
runs, missing words are shown as plain text. Ends by running tools/validate_text.py.

Usage: python3 tools/build_text.py mate [tu_usted …]      (no args = every inputs/*.txt)
"""
import glob
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from conjugate import conjugate, analyse, TENSES, strip_acc  # noqa: E402
import validate_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORD = re.compile(r"[^\W\d_]+")
PRON_VARIANT = {"la", "las", "lo", "los", "le", "les"}
POS_LABEL = {"v": "verbo", "n": "sustantivo", "adj": "adjetivo", "adv": "adverbio", "prep": "preposición",
             "conj": "conjunción", "pron": "pronombre", "det": "determinante", "num": "numeral",
             "interj": "interjección", "other": ""}


def load_names():
    names = set()
    for f in [ROOT / "lex/names.json"] + sorted(Path(p) for p in glob.glob(str(ROOT / "lex/parts/*.names.json"))):
        if f.exists():
            names.update(n.lower() for n in json.loads(f.read_text(encoding="utf-8")))
    return names


def load_lex():
    lemmas, forms, conflicts = {}, {}, []
    for kind, store in (("lemmas", lemmas), ("forms", forms)):
        files = [ROOT / f"lex/{kind}.json"] + sorted(Path(p) for p in glob.glob(str(ROOT / f"lex/parts/*.{kind}.json")))
        for f in files:
            if not f.exists():
                continue
            for k, v in json.loads(f.read_text(encoding="utf-8")).items():
                if k in store and store[k] != v:
                    conflicts.append(f"{kind} {k}: kept {store[k]} ({f.name} has {v})")
                    continue
                store[k] = v
    return lemmas, forms, conflicts


def split_key(key):
    lemma, _, pos = key.rpartition(".")
    return lemma, pos


def noun_plural(w):
    last = w[-1]
    if last in "aeiouáéó":
        return w + "s"
    if last in "íú":
        return w + "es"
    if last == "z":
        return w[:-1] + "ces"
    if w.endswith("s") and strip_acc(w[-2:-1]) in "aeiou" and not w[-2:-1] in "áéíóú":
        return w                                   # crisis, análisis
    unacc = w[:-2] + strip_acc(w[-2]) + w[-1] if len(w) > 2 and w[-2] in "áéíóú" else w
    return unacc + "es"


def adj_forms(lemma, lm):
    if lemma.endswith("o"):
        d = {"m_sg": lemma, "f_sg": lemma[:-1] + "a", "m_pl": lemma + "s", "f_pl": lemma[:-1] + "as"}
    elif lemma.endswith(("or", "ón", "án", "ín")) and not lemma.endswith(("ior", "mejor", "peor", "mayor", "menor")):
        f = strip_acc(lemma) + "a" if lemma[-2] in "óáí" else lemma + "a"
        d = {"m_sg": lemma, "f_sg": f, "m_pl": noun_plural(lemma), "f_pl": f + "s"}
    else:
        pl = noun_plural(lemma)
        d = {"m_sg": lemma, "f_sg": lemma, "m_pl": pl, "f_pl": pl}
    if "f" in lm:
        d["f_sg"] = lm["f"]
        d["f_pl"] = lm.get("fpl", lm["f"] + "s")
    if "pl" in lm:
        d["m_pl"] = lm["pl"]
        if "f" not in lm:
            d["f_pl"] = lm["pl"]
    return d


def lemma_entry(key, lm):
    lemma, pos = split_key(key)
    e = {"lemma": lemma, "pos": pos, "posLabel": POS_LABEL.get(pos, ""), "en": lm["en"]}
    if pos == "n":
        g = lm.get("g", "m")
        e["gender"] = g
        e["article"] = lm.get("art") or {"m": "el", "f": "la"}.get(g, "el/la")
        e["plural"] = lm.get("pl") or noun_plural(lemma)
    elif pos == "adj":
        e["forms"] = adj_forms(lemma, lm)
    elif pos == "v":
        c = conjugate(lemma, lm.get("m"))
        e["conjugation"] = {t: c[t] for t in TENSES}
        e["gerundio"], e["participio"] = c["gerundio"], c["participio"]
        if "m" in lm:
            e["model"] = lm["m"]
    if lm.get("note"):
        e["note"] = lm["note"]
    return e


def auto_analysis(surface, key, lemmas):
    lemma, pos = split_key(key)
    s = surface.lower()
    lm = lemmas.get(key, {})
    if pos == "v":
        return analyse(s, lemma, lm.get("m"))
    if pos == "n":
        e = lemma_entry(key, lm)
        if s == lemma:
            return "sg."
        if s == e["plural"]:
            return "pl."
        return None
    if pos == "adj":
        fs = adj_forms(lemma, lm)
        hits = [k for k, v in fs.items() if v == s]
        lab = {"m_sg": "m. sg.", "f_sg": "f. sg.", "m_pl": "m. pl.", "f_pl": "f. pl."}
        return " / ".join(lab[h] for h in hits) if hits else None
    return ""


PHRASE_TYPES = {"idiom": "expression", "collocation": "collocation", "grammar": "grammar"}
MAX_GAP = 5          # words allowed between two parts of a discontinuous phrase (tomaron … decisión)


def locate_phrases(tid, paragraphs, line_to_par, problems):
    """Read lex/phrases/<id>.json and find every occurrence in the tokenised paragraphs.

    File: [{"key", "type": idiom|collocation|grammar, "en", "explain"?, "occ": [{"p": line_no, "words": [...]}]}]
    `p` is the line number in inputs/<id>.txt (as `grep -n` prints it).
    Words of an occurrence are matched in order (case-insensitive), gaps of up to MAX_GAP words allowed.
    """
    f = ROOT / f"lex/phrases/{tid}.json"
    if not f.exists():
        return {}, []
    phrases, occs, taken = {}, [], set()
    for i, ph in enumerate(json.loads(f.read_text(encoding="utf-8")), start=1):
        if ph.get("type") not in PHRASE_TYPES or not ph.get("en") or not ph.get("key"):
            problems.append(f"phrase {ph.get('key')!r}: needs key, en and type idiom|collocation|grammar")
            continue
        pid = f"ph{i}"
        phrases[pid] = {"key": ph["key"], "type": ph["type"], "typeLabel": PHRASE_TYPES[ph["type"]],
                        "en": ph["en"], "explain": ph.get("explain", "")}
        for o in ph.get("occ", []):
            pi = line_to_par.get(o["p"])
            if pi is None:
                problems.append(f"phrase {ph['key']!r}: line {o['p']} is empty or out of range")
                continue
            words = [(ti, t[0].lower()) for ti, t in enumerate(paragraphs[pi]) if isinstance(t, list)]
            want = [w.lower() for w in o["words"]]
            found, best = None, None          # tightest match wins ("chorro de agua fría. De este modo" → the 2nd "de")
            for start in range(len(words)):
                if words[start][1] != want[0] or (pi, words[start][0]) in taken:
                    continue
                idx, k, last = [words[start][0]], 1, start
                for j in range(start + 1, min(len(words), start + 1 + len(want) * (MAX_GAP + 1))):
                    if k < len(want) and words[j][1] == want[k] and j - last <= MAX_GAP + 1:
                        idx.append(words[j][0]); k += 1; last = j
                if k == len(want) and (best is None or last - start < best):
                    found, best = idx, last - start
            if not found:
                problems.append(f"phrase {ph['key']!r}: {o['words']} not found in line {o['p']}")
                continue
            taken.update((pi, t) for t in found)
            occs.append({"ph": pid, "p": pi, "t": found})
    return phrases, occs


def build(tid):
    lemmas, forms_lex, conflicts = load_lex()
    known_names = load_names()
    meta = json.loads((ROOT / f"inputs/{tid}.meta.json").read_text(encoding="utf-8"))
    src_rel = f"inputs/{tid}.txt"
    lines = [ln.rstrip() for ln in (ROOT / src_rel).read_text(encoding="utf-8").split("\n")]
    paras_txt = [ln for ln in lines if ln.strip()]
    line_no = [i + 1 for i, ln in enumerate(lines) if ln.strip()]     # paragraph index -> line in inputs/<id>.txt
    ovr = {}
    ov_file = ROOT / f"lex/overrides/{tid}.json"
    if ov_file.exists():
        for o in json.loads(ov_file.read_text(encoding="utf-8")):
            ovr[(o["p"], o["w"].lower(), o.get("n", 1))] = o["form"]

    form_ids, forms_out, used_lemmas = OrderedDict(), {}, set()
    missing, names, problems = Counter(), Counter(), []
    context = {}

    def form_id(surface, entry):
        key = entry[0]
        if key not in lemmas:
            problems.append(f"{surface!r}: lemma {key} not in lemmas")
            return None
        analysis = entry[2] if len(entry) > 2 else auto_analysis(surface, key, lemmas)
        if analysis is None:
            problems.append(f"{surface!r} is not a known form of {key} — add a manual analysis")
            analysis = ""
        sig = (surface.lower(), key, entry[1], analysis)
        if sig not in form_ids:
            fid = f"f{len(form_ids) + 1}"
            form_ids[sig] = fid
            forms_out[fid] = {"lemma": key, "analysis": analysis, "en": entry[1]}
        used_lemmas.add(key)
        return form_ids[sig]

    paragraphs, headings = [], []
    for pi, text in zip(line_no, paras_txt):           # pi = line number (overrides use it)
        pieces, pos = [], 0
        for m in WORD.finditer(text):
            if m.start() > pos:
                pieces.append(text[pos:m.start()])
            pieces.append([m.group()])
            pos = m.end()
        if pos < len(text):
            pieces.append(text[pos:])
        words = [p for p in pieces if isinstance(p, list)]
        seen = Counter()
        for wi, w in enumerate(words):
            surface = w[0]
            low = surface.lower()
            seen[low] += 1
            entry = ovr.get((pi, low, seen[low])) or forms_lex.get(low) or forms_lex.get(surface)
            if low in PRON_VARIANT and f"{low}#pron" in forms_lex and wi + 1 < len(words):
                nxt = forms_lex.get(words[wi + 1][0].lower())
                if nxt and split_key(nxt[0])[1] == "v" and not ovr.get((pi, low, seen[low])):
                    entry = forms_lex[f"{low}#pron"]
            if entry:
                w.append(form_id(surface, entry))
            elif low in known_names:
                names[surface] += 1
                w.append(None)
            else:
                missing[low] += 1
                context.setdefault(low, text[max(0, text.lower().find(low) - 50):text.lower().find(low) + 50])
                w.append(None)
        paragraphs.append(pieces)
        bare = text.strip().strip("“”\"'‘’ ")
        if len(text) < 120 and not re.search(r"[.:;!?]$", bare):
            headings.append(len(paragraphs) - 1)

    phrases, occurrences = locate_phrases(tid, paragraphs, {ln: i for i, ln in enumerate(line_no)}, problems)
    doc = {
        "id": tid, "title": meta["title"],
        "source": dict(meta["source"], input=src_rel),
        "chapters": [{"id": "c1", "title": meta["title"], "paragraphs": paragraphs, "headings": headings,
                      "phraseOcc": occurrences}],
        "forms": forms_out,
        "lemmas": {k: lemma_entry(k, lemmas[k]) for k in sorted(used_lemmas)},
        "phrases": phrases,
    }
    (ROOT / "texts").mkdir(exist_ok=True)
    (ROOT / f"texts/{tid}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "app/data").mkdir(parents=True, exist_ok=True)
    (ROOT / f"app/data/{tid}.js").write_text(
        "window.LECTOR_TEXTS=window.LECTOR_TEXTS||{};window.LECTOR_TEXTS[" + json.dumps(tid) + "]="
        + json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")

    miss_file = ROOT / f"lex/missing_{tid}.tsv"
    if missing:
        miss_file.write_text("".join(f"{w}\t{n}\t{context[w]}\n" for w, n in missing.most_common()), encoding="utf-8")
    elif miss_file.exists():
        miss_file.unlink()
    n_words = sum(1 for p in paragraphs for t in p if isinstance(t, list))
    print(f"[{tid}] paragraphs {len(paragraphs)}, headings {len(headings)}, words {n_words}, "
          f"forms {len(forms_out)}, lemmas {len(used_lemmas)}, "
          f"missing {sum(missing.values())} ({len(missing)} unique), names {len(names)}, "
          f"phrases {len(phrases)} ({len(occurrences)} occurrences)")
    if names:
        print("  treated as names:", ", ".join(sorted(names)))
    for p in problems[:40]:
        print("  !", p)
    if len(problems) > 40:
        print(f"  … {len(problems) - 40} more problems")
    for c in conflicts[:10]:
        print("  conflict:", c)
    return not missing and not problems


def write_index():
    items = []
    for f in sorted((ROOT / "texts").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if "chapters" not in d:
            continue
        items.append({"id": d["id"], "title": d["title"], "source": d["source"].get("ref", ""),
                      "chapters": [{"id": c["id"], "title": c["title"]} for c in d["chapters"]],
                      "words": sum(1 for c in d["chapters"] for p in c["paragraphs"] for t in p if isinstance(t, list))})
    (ROOT / "app/data/index.js").write_text(
        "window.LECTOR_INDEX=" + json.dumps(items, ensure_ascii=False) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    ids = sys.argv[1:] or [Path(p).stem for p in sorted(glob.glob(str(ROOT / "inputs/*.txt")))]
    ok = True
    for tid in ids:
        ok = build(tid) and ok
        errs, stats = validate_text.validate(ROOT / f"texts/{tid}.json")
        print(f"  validate: {'OK' if not errs else f'{len(errs)} error(s)'}")
        for e in errs[:15]:
            print("   -", e)
        ok = ok and not errs
    write_index()
    sys.exit(0 if ok else 1)
