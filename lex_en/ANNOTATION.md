# Annotation rules — English texts (learner: native Spanish speaker from Argentina, level B1)

Same file layout as the Spanish lexicon (`lex/ANNOTATION.md`), but in `lex_en/`:
`lex_en/parts/partN.forms.json`, `partN.lemmas.json`, `partN.names.json`. Check with
`python3 tools/check_part.py N lex_en/missing_<id>.tsv --en`.

**Glosses are in Spanish — Rioplatense (Argentina).** Use the words an Argentine uses: *auto, celular,
computadora, colectivo, manejar, pileta, frutilla, departamento, remera, pollera, durazno, papa, jugo, plata
(money)*; second person with **vos** (*vos sabés, querés, tenés*; imperatives *mirá, fijate, andá*). Where a
gloss is a verb, give the infinitive. Several senses → separate with `; `.

**Lemma key** `<lemma>.<pos>`; pos `v n adj adv prep conj pron det num interj other` (as in Spanish).
- `v`: base form (`go.v`). Irregular forms are built in (`tools/english.py`, ~170 verbs); add `"past"`, `"pp"`
  only for verbs missing there; `"double": true` for doubling in multi-syllable verbs (prefer → preferred).
- `n`: singular; `"pl"` only when irregular and not in the built-in list.
- `adj`/`adv`: comparatives are built in (big → bigger, happy → happier, important → more important);
  `"cmp"`, `"sup"` only for exceptions.
- no gender, no articles.

**Forms** — `"surface": ["lemma.pos", "Spanish gloss in context"]`, optional 3rd element = manual analysis,
only where the engine can't recognise the form:
- contractions are one word: `don't` → `["do.v", "no (do + not)", "contraction: do not"]`, `it's` →
  `["be.v", "es; está", "contraction: it is"]`, `else's` → `["else.adv", "de otro (somebody else's = de otra persona)", "possessive 's"]`;
- pronouns / determiners / prepositions: their own lemma (`the.det`, `you.pron`, `of.prep`);
- `I` (capital) is a word, not a name.
- The Spanish gloss must fit the context (*keep going* → «seguir adelante»; *a while* → «un rato»).

**Phrases** (`lex/phrases/<id>.json`, same format as Spanish): types `idiom`, `collocation`, **`phrasal`**
(phrasal verbs: *put off, give up, end up, get rid of, figure out, break down, carry on, deal with*),
`grammar` (with `explain` in plain **Spanish**, e.g. present perfect, used to, going to, first conditional).
`en` = the Spanish (Rioplatense) meaning. `key` = citation form (`put off`, `get rid of`, `take a deep breath`).
Not marked: plain connectors (however, because, so). Phrasal verbs split by an object («put it off») are
matched with gaps (up to 5 words).
