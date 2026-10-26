"""Spanish verb conjugator: 6 card tenses + subjuntivo imperfecto, gerundio, participio.

Used by build_text.py to fill the conjugation table of every verb lemma and to recognise which
form a word in the text is. Regular verbs follow the rules; stem changes come from `model`
(e>ie, o>ue, e>i, u>ue, í, ú) or the built-in STEM list; ~30 irregular verbs (and their
prefixed families: mantener, componer, producir, describir, …) are tabled below.
Self-test: python3 tools/conjugate.py
"""
import unicodedata

PERSONS = ["yo", "tú", "él/ella/usted", "nosotros/as", "vosotros/as", "ellos/ellas/ustedes"]
TENSES = ["presente", "preterito_indefinido", "preterito_imperfecto",
          "futuro", "condicional", "subjuntivo_presente"]
TENSE_LABEL = {
    "presente": "presente", "preterito_indefinido": "pretérito indefinido",
    "preterito_imperfecto": "pretérito imperfecto", "futuro": "futuro",
    "condicional": "condicional", "subjuntivo_presente": "subjuntivo presente",
    "subjuntivo_imperfecto": "subjuntivo imperfecto",
    "subjuntivo_imperfecto_se": "subjuntivo imperfecto (-se)",
}

END = {
    "ar": {"pres": ["o", "as", "a", "amos", "áis", "an"],
           "pret": ["é", "aste", "ó", "amos", "asteis", "aron"],
           "imp": ["aba", "abas", "aba", "ábamos", "abais", "aban"],
           "subj": ["e", "es", "e", "emos", "éis", "en"]},
    "er": {"pres": ["o", "es", "e", "emos", "éis", "en"],
           "pret": ["í", "iste", "ió", "imos", "isteis", "ieron"],
           "imp": ["ía", "ías", "ía", "íamos", "íais", "ían"],
           "subj": ["a", "as", "a", "amos", "áis", "an"]},
    "ir": {"pres": ["o", "es", "e", "imos", "ís", "en"],
           "pret": ["í", "iste", "ió", "imos", "isteis", "ieron"],
           "imp": ["ía", "ías", "ía", "íamos", "íais", "ían"],
           "subj": ["a", "as", "a", "amos", "áis", "an"]},
}
FUT = ["é", "ás", "á", "emos", "éis", "án"]
COND = ["ía", "ías", "ía", "íamos", "íais", "ían"]
STRONG = ["e", "iste", "o", "imos", "isteis", "ieron"]

# common stem-changing verbs (a lemma's own `model` wins)
STEM = {m: "e>ie" for m in (
    "pensar empezar comenzar cerrar despertar sentar recomendar gobernar calentar negar regar "
    "fregar nevar atravesar confesar manifestar merendar tropezar querer entender perder "
    "defender encender extender tender ascender descender atender verter").split()}
STEM.update({m: "e>ie,i" for m in (
    "sentir mentir preferir sugerir convertir divertir advertir hervir herir referir "
    "requerir consentir invertir").split()})
STEM.update({m: "o>ue" for m in (
    "contar encontrar recordar costar mostrar demostrar probar comprobar aprobar sonar soñar "
    "volar acostar almorzar colgar rogar consolar acordar poder mover volver devolver "
    "envolver resolver soler doler llover morder torcer cocer").split()})
STEM.update({m: "o>ue,u" for m in "dormir morir".split()})
STEM.update({m: "e>i" for m in (
    "servir pedir repetir medir seguir conseguir perseguir vestir competir elegir corregir "
    "despedir impedir rendir gemir").split()})
STEM.update({m: "u>ue" for m in ["jugar"]})
STEM.update({m: "i>ie" for m in "adquirir inquirir".split()})
STEM.update({m: "í" for m in "enviar enfriar confiar fiar guiar variar ampliar desviar criar".split()})
STEM.update({m: "ú" for m in "continuar actuar evaluar situar graduar habituar insinuar".split()})

# fully irregular bases; prefixed verbs (mantener, componer, …) reuse them when PREFIXABLE
IRR = {
    "ser": {"presente": "soy eres es somos sois son", "preterito_imperfecto": "era eras era éramos erais eran",
            "preterito_indefinido": "fui fuiste fue fuimos fuisteis fueron",
            "subjuntivo_presente": "sea seas sea seamos seáis sean", "ger": "siendo", "part": "sido"},
    "ir": {"presente": "voy vas va vamos vais van", "preterito_imperfecto": "iba ibas iba íbamos ibais iban",
           "preterito_indefinido": "fui fuiste fue fuimos fuisteis fueron",
           "subjuntivo_presente": "vaya vayas vaya vayamos vayáis vayan", "ger": "yendo", "part": "ido"},
    "estar": {"presente": "estoy estás está estamos estáis están", "pret": "estuv",
              "subjuntivo_presente": "esté estés esté estemos estéis estén"},
    "haber": {"presente": "he has ha hemos habéis han", "pret": "hub", "fut": "habr",
              "subjuntivo_presente": "haya hayas haya hayamos hayáis hayan"},
    "dar": {"presente": "doy das da damos dais dan",
            "preterito_indefinido": "di diste dio dimos disteis dieron",
            "subjuntivo_presente": "dé des dé demos deis den"},
    "ver": {"presente": "veo ves ve vemos veis ven",
            "preterito_imperfecto": "veía veías veía veíamos veíais veían",
            "preterito_indefinido": "vi viste vio vimos visteis vieron",
            "subjuntivo_presente": "vea veas vea veamos veáis vean", "part": "visto"},
    "saber": {"yo": "sé", "pret": "sup", "fut": "sabr", "subj": "sep"},
    "caber": {"yo": "quepo", "pret": "cup", "fut": "cabr", "subj": "quep"},
    "poder": {"pret": "pud", "fut": "podr", "ger": "pudiendo"},
    "querer": {"pret": "quis", "fut": "querr"},
    "tener": {"yo": "tengo", "pret": "tuv", "fut": "tendr"},
    "venir": {"yo": "vengo", "pret": "vin", "fut": "vendr", "ger": "viniendo"},
    "poner": {"yo": "pongo", "pret": "pus", "fut": "pondr", "part": "puesto"},
    "hacer": {"yo": "hago", "pret": "hic", "pret3": "hizo", "fut": "har", "part": "hecho"},
    "decir": {"yo": "digo", "pret": "dij", "fut": "dir", "part": "dicho", "ger": "diciendo"},
    "traer": {"yo": "traigo", "pret": "traj"},
    "caer": {"yo": "caigo"},
    "oír": {"presente": "oigo oyes oye oímos oís oyen"},
    "salir": {"yo": "salgo", "fut": "saldr"},
    "valer": {"yo": "valgo", "fut": "valdr"},
    "andar": {"pret": "anduv"},
    "reír": {"presente": "río ríes ríe reímos reís ríen", "preterito_indefinido": "reí reíste rio reímos reísteis rieron",
             "subjuntivo_presente": "ría rías ría riamos riáis rían", "ger": "riendo", "part": "reído"},
    "ducir": {"pret": "duj"},          # conducir, producir, introducir, traducir, reducir …
    "volver": {"part": "vuelto"}, "solver": {"part": "suelto"}, "morir": {"part": "muerto"},
    "scribir": {"part": "scrito"}, "cubrir": {"part": "cubierto"}, "abrir": {"part": "abierto"},
    "romper": {"part": "roto"},
}
PREFIXABLE = {"tener", "venir", "poner", "hacer", "decir", "traer", "ducir", "volver", "solver", "reír",
              "scribir", "cubrir", "abrir", "caer"}
NO_ZC = {"hacer", "cocer", "mecer", "torcer", "vencer", "ejercer", "convencer"}


def strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def acc(v):
    return {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}.get(v, v)


def _base(inf):
    """Return (prefix, irregular base) or ("", None)."""
    if inf in IRR:
        return "", inf
    for b in sorted(PREFIXABLE, key=len, reverse=True):
        if inf.endswith(b) and inf != b:
            return inf[:-len(b)], b
    return "", None


def _change(stem, model, kind):
    """Apply a stem change. kind: 'strong' (ie/ue) or 'weak' (i/u)."""
    if not model:
        return stem
    if model in ("í", "ú"):
        if kind != "strong":
            return stem
        i = stem.rfind(model == "í" and "i" or "u")
        return stem[:i] + model + stem[i + 1:]
    src = model[0]
    i = stem.rfind(src)
    if i < 0:
        return stem
    if kind == "strong":
        rep = {"e>ie": "ie", "e>ie,i": "ie", "o>ue": "ue", "o>ue,u": "ue", "e>i": "i", "u>ue": "ue", "i>ie": "ie"}[model]
        if model == "o>ue" and i == 0:   # oler -> huelo
            rep = "hue"
    else:
        rep = {"e>ie,i": "i", "o>ue,u": "u", "e>i": "i"}.get(model)
        if not rep:
            return stem
    return stem[:i] + rep + stem[i + 1:]


def _ortho(inf, stem, ending):
    """Spelling changes before an ending."""
    e0 = strip_acc(ending[:1])
    if e0 == "e":
        if inf.endswith("car"):
            return stem[:-1] + "qu"
        if inf.endswith("gar"):
            return stem + "u"
        if inf.endswith("zar"):
            return stem[:-1] + "c"
        if inf.endswith("guar"):
            return stem[:-1] + "ü"
    if e0 in ("a", "o"):
        if inf.endswith(("cer", "cir")) and not inf.endswith("ducir") or inf.endswith("ducir"):
            pre = inf[-4]
            if pre in "aeiouáéíóú" and inf not in NO_ZC and not inf.endswith("hacer"):
                return stem[:-1] + "zc"
            if not inf.endswith("hacer") and not inf.endswith("decir"):
                return stem[:-1] + "z"
        if inf.endswith(("ger", "gir")):
            return stem[:-1] + "j"
        if inf.endswith("guir"):
            return stem[:-1]
    return stem


def conjugate(inf, model=None):
    """{tense: [6 forms], 'subjuntivo_imperfecto': [...], 'gerundio': str, 'participio': str}."""
    refl = inf.endswith("se") and inf[-4:-2] in ("ar", "er", "ir", "ír")
    if refl:
        t = conjugate(inf[:-2], model)
        pro = ["me", "te", "se", "nos", "os", "se"]
        for k in TENSES + ["subjuntivo_imperfecto"]:
            t[k] = [f"{p} {f}" for p, f in zip(pro, t[k])]
        t["vos"] = {"presente": "te " + t["vos"]["presente"], "imperativo": strip_acc(t["vos"]["imperativo"]) + "te"}
        return t

    prefix, base = _base(inf)
    irr = dict(IRR.get(base, {}))
    model = model or STEM.get(inf) or STEM.get(base or "")
    cls = "ir" if inf.endswith("ír") else inf[-2:]
    stem = inf[:-2]
    E = END[cls]
    uir = inf.endswith("uir") and not inf.endswith(("guir", "quir"))
    vowel_stem = strip_acc(stem[-1:]) in ("a", "e", "o") and cls != "ar"   # leer, caer, oír
    out = {}

    def table(key):
        if key in irr and isinstance(irr[key], str) and " " in irr[key]:
            return [prefix + f for f in irr[key].split()]
        return None

    # presente
    pres = table("presente")
    if not pres:
        pres = []
        for i, e in enumerate(E["pres"]):
            strong = i in (0, 1, 2, 5)
            s = _change(stem, model, "strong") if strong else stem
            if uir and strong:
                s = s + "y"
            pres.append(_ortho(inf, s, e) + e)
        if "yo" in irr:
            pres[0] = prefix + irr["yo"]
        if base == "decir":
            pres[1:3], pres[5] = [prefix + "dices", prefix + "dice"], prefix + "dicen"
        if base == "venir":
            pres[1:3], pres[5] = [prefix + "vienes", prefix + "viene"], prefix + "vienen"
        if base == "tener":
            pres[1:3], pres[5] = [prefix + "tienes", prefix + "tiene"], prefix + "tienen"
        if inf.endswith("ducir"):
            pres[0] = stem[:-1] + "zco"
    out["presente"] = pres

    # pretérito indefinido
    pret = table("preterito_indefinido")
    if not pret:
        if "pret" in irr:
            ps = prefix + irr["pret"]
            ends = list(STRONG)
            if ps.endswith("j"):
                ends[5] = "eron"
            pret = [ps + e for e in ends]
            if "pret3" in irr:
                pret[2] = prefix + irr["pret3"]
        else:
            pret = []
            for i, e in enumerate(E["pret"]):
                s = stem
                if cls == "ir" and i in (2, 5):
                    s = _change(stem, model, "weak")
                if (vowel_stem or uir) and i in (2, 5):
                    e = {"ió": "yó", "ieron": "yeron"}[e]
                elif vowel_stem and e.startswith("i"):
                    e = "í" + e[1:]
                pret.append(_ortho(inf, s, e) + e)
    out["preterito_indefinido"] = pret

    # imperfecto
    out["preterito_imperfecto"] = table("preterito_imperfecto") or [stem + e for e in E["imp"]]

    # futuro / condicional
    fs = prefix + irr["fut"] if "fut" in irr else (inf[:-2] + "ir" if inf.endswith("ír") else inf)   # oír → oiré, reír → reiré
    out["futuro"] = [fs + e for e in FUT]
    out["condicional"] = [fs + e for e in COND]

    # subjuntivo presente
    subj = table("subjuntivo_presente")
    if not subj:
        se = END[cls]["subj"]
        if "subj" in irr:
            subj = [prefix + irr["subj"] + e for e in se]
        elif "yo" in irr or inf.endswith("ducir"):
            ys = pres[0][:-1]
            subj = [ys + e for e in se]
        else:
            subj = []
            for i, e in enumerate(se):
                if i in (0, 1, 2, 5):
                    s = _change(stem, model, "strong")
                elif cls == "ir":
                    s = _change(stem, model, "weak")
                else:
                    s = stem
                if uir:
                    s += "y"
                subj.append(_ortho(inf, s, e) + e)
        if base == "oír":
            subj = [prefix + "oig" + e for e in se]
    out["subjuntivo_presente"] = subj

    # subjuntivo imperfecto: 3pl pretérito minus -ron
    st = pret[5][:-3]
    out["subjuntivo_imperfecto"] = [st + "ra", st + "ras", st + "ra",
                                    st[:-1] + acc(st[-1]) + "ramos", st + "rais", st + "ran"]
    out["subjuntivo_imperfecto_se"] = [st + "se", st + "ses", st + "se",                     # fuese, decidiese
                                       st[:-1] + acc(st[-1]) + "semos", st + "seis", st + "sen"]

    # gerundio / participio
    if "ger" in irr:
        out["gerundio"] = prefix + irr["ger"] if base not in ("ser", "ir") else irr["ger"]
    elif cls == "ar":
        out["gerundio"] = stem + "ando"
    elif vowel_stem or uir:
        out["gerundio"] = stem + "yendo"
    else:
        out["gerundio"] = (_change(stem, model, "weak") if cls == "ir" else stem) + "iendo"
    if "part" in irr:
        out["participio"] = prefix + irr["part"] if base not in ("ser", "ir", "ver") else irr["part"]
    elif cls == "ar":
        out["participio"] = stem + "ado"
    else:
        out["participio"] = stem + ("ído" if vowel_stem else "ido")
    out["vos"] = vos_forms(inf, out)
    return out


def vos_forms(inf, out):
    """Rioplatense voseo: presente from the vosotros form without the i (tenéis → tenés, tomáis → tomás,
    vivís stays), no stem change; imperativo = infinitive minus -r with a stressed vowel (tomá, tené, viví)."""
    special = {"ser": ("sos", "sé"), "ir": ("vas", "andá"), "haber": ("has", "habé")}
    if inf in special:
        pres, imp = special[inf]
    else:
        v = out["presente"][4]
        pres = v[:-3] + "ás" if v.endswith("áis") else v[:-3] + "és" if v.endswith("éis") else \
            v if v.endswith("ís") else v.replace("ais", "as").replace("eis", "es")
        stem = inf[:-1]
        one_syllable = sum(ch in "aeiouáéíóú" for ch in stem) == 1          # da, ve: no written accent
        imp = stem[:-1] + acc(stem[-1]) if stem[-1] in "aei" and not one_syllable else stem
    return {"presente": pres, "imperativo": imp}


def analyse(surface, inf, model=None):
    """Describe which form of `inf` the word is, or None. Handles enclitics (cebarse, agregándole)."""
    s = surface.lower()
    if s == inf:
        return "infinitivo"
    c = conjugate(inf, model)
    plain = conjugate(inf[:-2], model) if inf.endswith("se") and inf[-4:-2] in ("ar", "er", "ir", "ír") else c
    hits = []
    for t in TENSES + ["subjuntivo_imperfecto", "subjuntivo_imperfecto_se"]:
        ps = [PERSONS[i] for i, f in enumerate(plain[t]) if f == s]
        if ps:
            hits.append(f"{TENSE_LABEL[t]} · {' / '.join(ps)}")
    vos = plain.get("vos", {})
    if s == vos.get("presente"):
        hits = [h + " / vos" if h.startswith("presente") else h for h in hits] or ["presente · vos"]
    if hits:
        return "; ".join(hits)
    if s == vos.get("imperativo"):
        return "imperativo · vos"
    if inf == "haber" and s == "hay":
        return "presente · impersonal (there is / there are)"
    part = plain["participio"]
    pforms = {part: "m. sg.", part[:-1] + "a": "f. sg.", part + "s": "m. pl.", part[:-1] + "as": "f. pl."}
    if s in pforms:
        return "participio" + ("" if pforms[s] == "m. sg." else f" ({pforms[s]})")
    base_inf = inf[:-2] if plain is not c else inf
    for clit in ("", "me", "te", "se", "lo", "la", "le", "los", "las", "les", "nos", "os",
                 "selo", "sela", "selos", "selas", "melo", "mela", "telo"):
        if clit and not s.endswith(clit):
            continue
        core = s[:len(s) - len(clit)] if clit else s
        label = f" + {clit}" if clit else ""
        if strip_acc(core) == strip_acc(base_inf) and (clit or core == base_inf):
            return "infinitivo" + label
        if strip_acc(core) == strip_acc(plain["gerundio"]) and (clit or core == plain["gerundio"]):
            return "gerundio" + label
    return None


if __name__ == "__main__":
    checks = {
        ("tomar", "presente"): "tomo tomas toma tomamos tomáis toman",
        ("pensar", "presente"): "pienso piensas piensa pensamos pensáis piensan",
        ("hervir", "presente"): "hiervo hierves hierve hervimos hervís hierven",
        ("hervir", "preterito_indefinido"): "herví herviste hirvió hervimos hervisteis hirvieron",
        ("servir", "subjuntivo_presente"): "sirva sirvas sirva sirvamos sirváis sirvan",
        ("conocer", "presente"): "conozco conoces conoce conocemos conocéis conocen",
        ("conocer", "subjuntivo_presente"): "conozca conozcas conozca conozcamos conozcáis conozcan",
        ("atacar", "preterito_indefinido"): "ataqué atacaste atacó atacamos atacasteis atacaron",
        ("empezar", "subjuntivo_presente"): "empiece empieces empiece empecemos empecéis empiecen",
        ("incluir", "presente"): "incluyo incluyes incluye incluimos incluís incluyen",
        ("incluir", "preterito_indefinido"): "incluí incluiste incluyó incluimos incluisteis incluyeron",
        ("leer", "preterito_indefinido"): "leí leíste leyó leímos leísteis leyeron",
        ("tener", "presente"): "tengo tienes tiene tenemos tenéis tienen",
        ("mantener", "presente"): "mantengo mantienes mantiene mantenemos mantenéis mantienen",
        ("mantener", "futuro"): "mantendré mantendrás mantendrá mantendremos mantendréis mantendrán",
        ("hacer", "preterito_indefinido"): "hice hiciste hizo hicimos hicisteis hicieron",
        ("decir", "presente"): "digo dices dice decimos decís dicen",
        ("decir", "preterito_indefinido"): "dije dijiste dijo dijimos dijisteis dijeron",
        ("introducir", "preterito_indefinido"): "introduje introdujiste introdujo introdujimos introdujisteis introdujeron",
        ("introducir", "presente"): "introduzco introduces introduce introducimos introducís introducen",
        ("traer", "subjuntivo_presente"): "traiga traigas traiga traigamos traigáis traigan",
        ("poder", "presente"): "puedo puedes puede podemos podéis pueden",
        ("mover", "subjuntivo_presente"): "mueva muevas mueva movamos mováis muevan",
        ("dormir", "subjuntivo_presente"): "duerma duermas duerma durmamos durmáis duerman",
        ("seguir", "presente"): "sigo sigues sigue seguimos seguís siguen",
        ("escoger", "presente"): "escojo escoges escoge escogemos escogéis escogen",
        ("enfriar", "presente"): "enfrío enfrías enfría enfriamos enfriáis enfrían",
        ("continuar", "subjuntivo_presente"): "continúe continúes continúe continuemos continuéis continúen",
        ("ser", "subjuntivo_imperfecto"): "fuera fueras fuera fuéramos fuerais fueran",
        ("tener", "subjuntivo_imperfecto"): "tuviera tuvieras tuviera tuviéramos tuvierais tuvieran",
        ("volcar", "subjuntivo_presente"): "vuelque vuelques vuelque volquemos volquéis vuelquen",
        ("jugar", "presente"): "juego juegas juega jugamos jugáis juegan",
        ("oír", "presente"): "oigo oyes oye oímos oís oyen",
        ("estar", "subjuntivo_presente"): "esté estés esté estemos estéis estén",
        ("reír", "presente"): "río ríes ríe reímos reís ríen",
        ("reír", "futuro"): "reiré reirás reirá reiremos reiréis reirán",
        ("oír", "condicional"): "oiría oirías oiría oiríamos oiríais oirían",
        ("sonreír", "preterito_indefinido"): "sonreí sonreíste sonrio sonreímos sonreísteis sonrieron",
        ("encargarse", "preterito_indefinido"): "me encargué te encargaste se encargó nos encargamos os encargasteis se encargaron",
        ("vencer", "presente"): "venzo vences vence vencemos vencéis vencen",
        ("distinguir", "presente"): "distingo distingues distingue distinguimos distinguís distinguen",
        ("averiguar", "subjuntivo_presente"): "averigüe averigües averigüe averigüemos averigüéis averigüen",
    }
    extra = {
        ("hervir", "gerundio"): "hirviendo", ("decir", "participio"): "dicho",
        ("descubrir", "participio"): "descubierto", ("describir", "participio"): "descrito",
        ("leer", "gerundio"): "leyendo", ("ir", "gerundio"): "yendo", ("poder", "gerundio"): "pudiendo",
        ("servir", "gerundio"): "sirviendo", ("leer", "participio"): "leído",
    }
    vos_checks = {"tener": ("tenés", "tené"), "tomar": ("tomás", "tomá"), "vivir": ("vivís", "viví"),
                  "querer": ("querés", "queré"), "poder": ("podés", "podé"), "ser": ("sos", "sé"),
                  "ir": ("vas", "andá"), "decir": ("decís", "decí"), "hacer": ("hacés", "hacé"),
                  "dar": ("das", "da"), "ver": ("ves", "ve"), "dormir": ("dormís", "dormí"),
                  "estar": ("estás", "está"), "saber": ("sabés", "sabé"), "levantarse": ("te levantás", "levantate")}
    bad = 0
    for v, (pres, imp) in vos_checks.items():
        got = conjugate(v)["vos"]
        if (got["presente"], got["imperativo"]) != (pres, imp):
            bad += 1
            print(f"FAIL vos {v}: got {got}, exp {pres} / {imp}")
    for s_, v, exp in [("adquiere", "adquirir", "presente · él/ella/usted"), ("fuese", "ser", "subjuntivo imperfecto (-se) · yo / él/ella/usted"),
                       ("querés", "querer", "presente · vos"), ("vivís", "vivir", "presente · vosotros/as / vos"),
                       ("tomá", "tomar", "imperativo · vos")]:
        if analyse(s_, v) != exp:
            bad += 1
            print(f"FAIL analyse {s_}: {analyse(s_, v)}")
    for (v, t), exp in checks.items():
        got = " ".join(conjugate(v, "o>ue" if v == "volcar" else None)[t])
        if got != exp:
            bad += 1
            print(f"FAIL {v} {t}\n  got {got}\n  exp {exp}")
    for (v, t), exp in extra.items():
        got = conjugate(v)[t]
        if got != exp:
            bad += 1
            print(f"FAIL {v} {t}: got {got}, exp {exp}")
    for s, v, exp in [("agregándole", "agregar", "gerundio + le"), ("cebarse", "cebarse", "infinitivo"),
                      ("pararlo", "parar", "infinitivo + lo"), ("hay", "haber", None),
                      ("tomaban", "tomar", "pretérito imperfecto · ellos/ellas/ustedes"),
                      ("colocada", "colocar", "participio (f. sg.)")]:
        got = analyse(s, v)
        if exp and got != exp:
            bad += 1
            print(f"FAIL analyse {s}: got {got}, exp {exp}")
    print("OK" if not bad else f"{bad} failures", f"({len(checks) + len(extra)} tables checked)")
