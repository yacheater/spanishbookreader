"""English word forms for the English-through-Spanish direction (texts with "lang": "en").

forms(lemma, pos, lm) gives the forms shown on the card; analyse(surface, lemma, pos, lm) says which
form a word in the text is. Verbs: ~170 irregular verbs tabled, regular spelling rules (-s/-es/-ies,
-ed/-ied, doubling stop→stopped, dropping -e). Lemma entries may override anything: "past", "pp", "ing",
"s", "pl", "cmp", "sup", "double": true (prefer → preferred). Self-test: python3 tools/english.py
"""
VOWELS = "aeiou"

IRREGULAR = {}  # base: (past, past participle)
for line in """
arise arose arisen|awake awoke awoken|be was/were been|bear bore born|beat beat beaten|become became become
begin began begun|bend bent bent|bet bet bet|bind bound bound|bite bit bitten|bleed bled bled|blow blew blown
break broke broken|breed bred bred|bring brought brought|broadcast broadcast broadcast|build built built
burn burnt/burned burnt/burned|burst burst burst|buy bought bought|catch caught caught|choose chose chosen
cling clung clung|come came come|cost cost cost|creep crept crept|cut cut cut|deal dealt dealt|dig dug dug
do did done|draw drew drawn|dream dreamt/dreamed dreamt/dreamed|drink drank drunk|drive drove driven
eat ate eaten|fall fell fallen|feed fed fed|feel felt felt|fight fought fought|find found found|flee fled fled
fly flew flown|forbid forbade forbidden|forget forgot forgotten|forgive forgave forgiven|freeze froze frozen
get got got/gotten|give gave given|go went gone|grind ground ground|grow grew grown|hang hung hung|have had had
hear heard heard|hide hid hidden|hit hit hit|hold held held|hurt hurt hurt|keep kept kept|kneel knelt knelt
know knew known|lay laid laid|lead led led|lean leant/leaned leant/leaned|leap leapt/leaped leapt/leaped
learn learnt/learned learnt/learned|leave left left|lend lent lent|let let let|lie lay lain|light lit lit
lose lost lost|make made made|mean meant meant|meet met met|mistake mistook mistaken|overcome overcame overcome
pay paid paid|prove proved proven/proved|put put put|quit quit quit|read read read|ride rode ridden|ring rang rung
rise rose risen|run ran run|say said said|see saw seen|seek sought sought|sell sold sold|send sent sent
set set set|sew sewed sewn|shake shook shaken|shine shone shone|shoot shot shot|show showed shown|shrink shrank shrunk
shut shut shut|sing sang sung|sink sank sunk|sit sat sat|sleep slept slept|slide slid slid|smell smelt/smelled smelt/smelled
speak spoke spoken|speed sped sped|spell spelt/spelled spelt/spelled|spend spent spent|spill spilt/spilled spilt/spilled
spin spun spun|spit spat spat|split split split|spoil spoilt/spoiled spoilt/spoiled|spread spread spread
spring sprang sprung|stand stood stood|steal stole stolen|stick stuck stuck|sting stung stung|stink stank stunk
strike struck struck|strive strove striven|swear swore sworn|sweep swept swept|swim swam swum|swing swung swung
take took taken|teach taught taught|tear tore torn|tell told told|think thought thought|throw threw thrown
understand understood understood|undertake undertook undertaken|upset upset upset|wake woke woken|wear wore worn
weave wove woven|weep wept wept|win won won|wind wound wound|withdraw withdrew withdrawn|write wrote written
forecast forecast forecast|overtake overtook overtaken|rebuild rebuilt rebuilt|redo redid redone|rethink rethought rethought
""".replace("\n", "|").split("|"):
    if line.strip():
        b, p, pp = line.split()
        IRREGULAR[b] = (p, pp)

IRR_PLURAL = {"man": "men", "woman": "women", "child": "children", "person": "people", "foot": "feet",
              "tooth": "teeth", "mouse": "mice", "goose": "geese", "ox": "oxen", "life": "lives", "knife": "knives",
              "wife": "wives", "leaf": "leaves", "half": "halves", "wolf": "wolves", "shelf": "shelves",
              "thief": "thieves", "loaf": "loaves", "self": "selves", "calf": "calves", "potato": "potatoes",
              "tomato": "tomatoes", "hero": "heroes", "echo": "echoes", "crisis": "crises", "analysis": "analyses",
              "phenomenon": "phenomena", "criterion": "criteria", "sheep": "sheep", "fish": "fish",
              "deer": "deer", "series": "series", "species": "species", "news": "news"}
IRR_CMP = {"good": ("better", "best"), "well": ("better", "best"), "bad": ("worse", "worst"),
           "far": ("further", "furthest"), "little": ("less", "least"), "many": ("more", "most"),
           "much": ("more", "most"), "old": ("older", "oldest")}


def _cvc(w):
    """Ends consonant-vowel-consonant (not w/x/y) in a one-syllable word → double the last letter."""
    return (len(w) >= 3 and w[-1] not in VOWELS + "wxy" and w[-2] in VOWELS and w[-3] not in VOWELS
            and sum(ch in VOWELS for ch in w) == 1)


def _suffix(w, suf, lm=None):
    """Add -ed / -ing / -er / -est with English spelling rules."""
    double = (lm or {}).get("double") or _cvc(w)
    if suf == "ing":
        if w.endswith("ie"):
            return w[:-2] + "ying"
        if w.endswith("e") and not w.endswith(("ee", "ye", "oe")) and w != "be":
            return w[:-1] + "ing"
        return w + w[-1] + "ing" if double else w + "ing"
    if w.endswith("e"):
        return w + suf[1:]                                   # liked, nicer, nicest
    if w.endswith("y") and w[-2] not in VOWELS:
        return w[:-1] + "i" + suf                            # studied, happier
    return w + w[-1] + suf if double else w + suf           # stopped, bigger


def _s(w):
    if w.endswith(("s", "x", "z", "ch", "sh", "o")) and w not in ("piano", "photo", "radio", "video", "zoo"):
        return w + "es"
    if w.endswith("y") and w[-2] not in VOWELS:
        return w[:-1] + "ies"
    return w + "s"


def forms(lemma, pos, lm=None):
    lm = lm or {}
    w = lemma.lower()
    if pos == "v":
        if " " in w:                                        # phrasal lemma typed as one entry: inflect the verb
            head, rest = w.split(" ", 1)
            f = forms(head, "v", lm)
            return {k: (v + " " + rest) for k, v in f.items()}
        if w == "be":
            return {"base": "be", "s": "is", "past": "was/were", "pp": "been", "ing": "being"}
        if w == "have":
            return {"base": "have", "s": "has", "past": "had", "pp": "had", "ing": "having"}
        p, pp = IRREGULAR.get(w, (None, None))
        reg = _suffix(w, "ed", lm)
        return {"base": w, "s": lm.get("s", "does" if w == "do" else "goes" if w == "go" else _s(w)),
                "past": lm.get("past", p or reg), "pp": lm.get("pp", pp or reg), "ing": lm.get("ing", _suffix(w, "ing", lm))}
    if pos == "n":
        return {"sg": w, "pl": lm.get("pl", IRR_PLURAL.get(w, _s(w) if not w.endswith("o") or w in IRR_PLURAL else w + "s"))}
    if pos == "adj" or pos == "adv":
        if w in IRR_CMP:
            c, s = IRR_CMP[w]
        elif "cmp" in lm:
            c, s = lm["cmp"], lm.get("sup")
        else:
            syll = sum(1 for i, ch in enumerate(w) if ch in VOWELS + "y" and (i == 0 or w[i - 1] not in VOWELS + "y"))
            if w.endswith("e") and syll > 1:
                syll -= 1
            if pos == "adj" and (syll == 1 or (syll == 2 and w.endswith("y"))):
                c, s = _suffix(w, "er", lm), _suffix(w, "est", lm)
            else:
                c, s = "more " + w, "most " + w
        return {"base": w, "cmp": c, "sup": s}
    return {}


LABEL = {"s": "present simple · he/she/it", "past": "past simple", "pp": "past participle", "ing": "-ing form",
         "pl": "plural", "cmp": "comparative", "sup": "superlative"}


def analyse(surface, lemma, pos, lm=None):
    """Which form of the lemma the word is; '' for the base form; None if it is not a form of it."""
    s = surface.lower()
    f = forms(lemma, pos, lm)
    if not f:
        return "" if s == lemma.lower() else None
    if s == lemma.lower():
        return "base form" if pos == "v" else ""
    hits = []
    for k, v in f.items():
        if k in LABEL and s in str(v).split("/"):
            hits.append(LABEL[k])
    if pos == "v" and lemma == "be":
        hits = {"am": ["present · I"], "are": ["present · you/we/they"], "is": ["present · he/she/it"],
                "was": ["past · I/he/she/it"], "were": ["past · you/we/they"]}.get(s, hits)
    if "past simple" in hits and "past participle" in hits:
        hits = ["past simple / past participle"]
    return " / ".join(hits) if hits else None


if __name__ == "__main__":
    checks = {
        ("go", "v"): {"base": "go", "s": "goes", "past": "went", "pp": "gone", "ing": "going"},
        ("stop", "v"): {"base": "stop", "s": "stops", "past": "stopped", "pp": "stopped", "ing": "stopping"},
        ("study", "v"): {"base": "study", "s": "studies", "past": "studied", "pp": "studied", "ing": "studying"},
        ("make", "v"): {"base": "make", "s": "makes", "past": "made", "pp": "made", "ing": "making"},
        ("lie", "v"): {"base": "lie", "s": "lies", "past": "lay", "pp": "lain", "ing": "lying"},
        ("watch", "v"): {"base": "watch", "s": "watches", "past": "watched", "pp": "watched", "ing": "watching"},
        ("play", "v"): {"base": "play", "s": "plays", "past": "played", "pp": "played", "ing": "playing"},
        ("put off", "v"): {"base": "put off", "s": "puts off", "past": "put off", "pp": "put off", "ing": "putting off"},
        ("child", "n"): {"sg": "child", "pl": "children"},
        ("box", "n"): {"sg": "box", "pl": "boxes"},
        ("city", "n"): {"sg": "city", "pl": "cities"},
        ("day", "n"): {"sg": "day", "pl": "days"},
        ("big", "adj"): {"base": "big", "cmp": "bigger", "sup": "biggest"},
        ("happy", "adj"): {"base": "happy", "cmp": "happier", "sup": "happiest"},
        ("nice", "adj"): {"base": "nice", "cmp": "nicer", "sup": "nicest"},
        ("important", "adj"): {"base": "important", "cmp": "more important", "sup": "most important"},
        ("good", "adj"): {"base": "good", "cmp": "better", "sup": "best"},
    }
    bad = 0
    for (w, p), exp in checks.items():
        got = forms(w, p)
        if got != exp:
            bad += 1
            print(f"FAIL {w}: {got}")
    for s, w, p, exp in [("went", "go", "v", "past simple"), ("gone", "go", "v", "past participle"),
                         ("stopped", "stop", "v", "past simple / past participle"), ("goes", "go", "v", "present simple · he/she/it"),
                         ("children", "child", "n", "plural"), ("better", "good", "adj", "comparative"),
                         ("were", "be", "v", "past · you/we/they"), ("making", "make", "v", "-ing form")]:
        if analyse(s, w, p) != exp:
            bad += 1
            print(f"FAIL analyse {s}: {analyse(s, w, p)}")
    print("OK" if not bad else f"{bad} failures", f"({len(checks) + 8} checks)")
