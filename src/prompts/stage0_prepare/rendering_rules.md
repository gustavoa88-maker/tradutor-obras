Respond with ONLY a JSON array, no prose, no code fence. Each element:
{"source": "<expression exactly as written in the $source_name text>", "target": "<the $target_name rendering>", "kind": "person|place|organisation|work|term|other", "mode": "exact|inflectable|preferred|preserve"}

Rules:
- One element per distinct term that genuinely needs cross-chapter consistency. Do not repeat.
- "source" must be copied character for character from the document. Never invent or normalize a source spelling.
- Preserve the NUCLEUS of true proper names, not every descriptive named expression.
- Personal names, surnames, romanized names, and opaque invented name nuclei normally use "preserve": copy the source into "target" character for character.
- A "preserve" entry MUST have identical source and target. Example: Wang => Wang | preserve; Wang Lin => Wang Lin | preserve.
- If a phrase mixes a proper-name nucleus with translatable words, protect only the nucleus. Example: for "Ji Realm", emit Ji => Ji | preserve and let "Realm" be translated normally. For "Fellow Daoist Wang", protect Wang only; do not protect "Fellow Daoist".
- Do NOT preserve an entire expression merely because it names a sect, organisation, technique, artefact, place, rank, realm, title, faction, or group. If its words carry ordinary semantic meaning, they should normally be translated. Examples such as "Heavenly Fate Sect", "Heaven Defying Bead", "Star Constellation Sect", and descriptive place names should remain translatable unless they contain a separate proper-name nucleus.
- A common word can still be a per-book proper-name exception when the context clearly promotes that exact spelling/capitalisation to a formal name. In that case use "preserve" only for that exact form; ordinary lowercase/common uses remain translatable.
- Leave titles and honorifics out of preserved names. Write "Wang", not "Senior Wang", "Fellow Daoist Wang", "Elder Wang", "Lord Wang", or similar forms.
- "target" is the base form only. Do not add grammatical endings, articles, or explanations.
- Distinct personal names must remain distinct. Do not merge or translate romanizations merely because another spelling seems more familiar.
Choose "mode" per term:
- "preserve": never translate this exact proper-name nucleus or explicit contextual exception; source and target must be identical.
- "exact": a genuinely translatable fixed target must appear letter for letter every time.
- "inflectable": use this translated lexical choice while allowing target-language grammatical inflection.
- "preferred": prefer this translated rendering where it fits, but allow context to choose another natural rendering.
- If nothing needs a glossary constraint, respond with [].

## genre_line

The document is: $genre.
