# Annotation rules (lex/parts/partN.*.json)

Each batch = three files. Checked by `python3 tools/check_part.py N <word list>`.

- `partN.forms.json` — `"surface": ["lemmaKey", "English in this context"]`, optional 3rd element =
  manual analysis, only when the checker can't recognise a legitimately unusual form
  (apocopes *buen, gran, primer*; superlatives *fortísimos*).
- `partN.lemmas.json` — every lemma the batch's forms reference.
- `partN.names.json` — proper names and non-Spanish words (get no card, no popup).

**Lemma key** `<dictionary form>.<pos>`; pos: `v n adj adv prep conj pron det num interj other`.
- all: `en` — short gloss, senses separated by `; `.
- `n`: `g` = `m` | `f` | `m/f`; `art: "el"` for *el agua*-type nouns; `pl` only when not regular.
- `adj`: masculine singular; `f` when not -o→-a and not invariable (*español → española*); `pl` when irregular.
- `v`: infinitive; reflexive (`encargarse.v`) only for pronominal verbs with their own meaning;
  `m` = stem-change model `e>ie`, `e>ie,i`, `o>ue`, `o>ue,u`, `e>i`, `u>ue`, `í`, `ú`.
  Spelling changes and ~30 irregular verbs (+ prefixed families) are built into `tools/conjugate.py`.

**Forms**
- English fits the context and the form (*tomaban* → "they used to drink").
- Verb + enclitics (*cultivarla, agregándole*) → the verb lemma; analysis is automatic.
- Participles: verbal/passive use → verb lemma; purely adjectival → adjective lemma.
- `la las lo los` → article reading under the plain key + pronoun reading under `"la#pron"` etc.;
  the build picks the pronoun reading before a verb automatically.
- One entry per surface (most frequent meaning); per-occurrence fixes go to `lex/overrides/<id>.json`:
  `[{"p": line_no, "w": "hace", "n": 1, "form": ["hacer.v", "ago (desde hace)"]}]`.

## Phrases (`lex/phrases/<id>.json`)
```json
[{"key": "tomar una decisión", "type": "collocation", "en": "to make a decision",
  "occ": [{"p": 33, "words": ["tomaron", "decisión"]}]},
 {"key": "hay que + infinitivo", "type": "grammar", "en": "one has to …",
  "explain": "Impersonal obligation …", "occ": [{"p": 26, "words": ["hay", "que", "mover"]}]}]
```
- `type`: `idiom` (fixed, meaning not the sum of words), `collocation` (typical partnership, verb in
  the infinitive in `key`), `grammar` (pattern + required `explain`, 1–2 English sentences).
- Not marked: plain connectors / compound prepositions (sin embargo, por lo tanto, es decir, debido a,
  acerca de, a través de, en cuanto a, por otro lado, así como, según), names, citations.
- `p` = line number in `inputs/<id>.txt`; `words` = the occurrence's words as written, in order;
  up to 5 other words may sit between them. One entry per expression, all occurrences in `occ`.
- The build reports every occurrence it can't find (`! phrase …`).
