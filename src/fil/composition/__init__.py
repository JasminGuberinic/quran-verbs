"""Composed glosses: a Quranic form's meaning built from its parts, not written by hand.

A form such as فَقَالُوا۟ is a proclitic (فَ "so"), a verb cell (past, "they", active) and
no object. English is conjugated by rule from the verb's meaning; Bosnian conjugation is
too irregular for rules, so each verb carries a small paradigm — the Bosnian of exactly
the cells the Quran uses it in — written once and stored in data/bs_paradigms.json.

    decomposition   the corpus segments of a word → its parts (or why it cannot be split)
    english         a verb cell, in English, with its proclitic words
    bosnian         a paradigm cell, with its proclitic words and the clitics moved after them
    paradigms       the stored Bosnian paradigms: parsed and validated
    senses          a polysemous verb's senses and the sense chosen for each place it stands in
    corrections     a composed gloss corrected in context, for a whole form or one place
    compose         a form → its {en, bs} gloss (a polysemous verb's: place by place), or the reason it keeps
                    its grammar label

Pure: segments, meanings and paradigms in; glosses and skip reasons out.
"""
