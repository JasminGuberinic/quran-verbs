# Third-party notices

Fiʿl is built from other people's work. This file lists every source the study site and the
public pages use, the terms each is published under, and how we keep to them. We use only
what the published terms allow; nothing here rests on private permission.

Every page of the public site and the app carries the same credits in its footer
(`credits` in `src/fil/site/ui.js`; a test, `test_every_page_credits_every_source_as_its_terms_ask`,
fails the build if one goes missing).

| Source | What we use | Terms | Shipped in the site? |
|---|---|---|---|
| Quranic Arabic Corpus | morphology: verbs, forms, words of each ayah | GNU GPL v3 + QAC terms of use | derived data (cards, ayat lists) |
| Tanzil Quran text | the Arabic text (inside the corpus) | CC BY 3.0 + Tanzil terms of use | yes, verbatim words |
| Tanzil translations | ayah translations (en, tr, ur, id, ru) | Tanzil translation terms (non-commercial) | yes, per ayah, credited |
| Tanzil Quran metadata | surah lengths (ayah numbering) | CC BY 3.0 | no (used to compute numbers) |
| QuranHive Word-by-Word Audio | single recited words | CC BY 4.0 | yes, re-encoded |
| alquran.cloud / Islamic Network CDN | whole-ayah recitation, Mishary Rashid Alafasy | alquran.cloud terms | **no** — streamed at play time |
| OpenMoji 15.1 | noun pictures (emoji), recoloured | CC BY-SA 4.0 | yes, recoloured SVGs |
| Twemoji 15.1 (jdecked fork) | noun pictures (emoji), recoloured | CC BY 4.0 | yes, recoloured SVGs |
| tts_arabic (nipponjo) | the synthetic voice of practice words and sentences | code MIT; model non-commercial (see below) | yes, generated clips |
| Google Fonts (Amiri Quran, Noto Naskh Arabic, Literata, Space Grotesk, Inter, IBM Plex) | typefaces | SIL Open Font License 1.1 | **no** — loaded from fonts.googleapis.com |
| Qutrub, CAMeL Tools (calima-msa-r13), PyArabic | build-time conjugation, declension and lexicon checks | GPL / MIT, database GPL-2.0 | no (tools; only their checked outputs) |
| islam.ba, quranwbw.com, quran.com | outbound links only | — | no content copied |

---

## Quranic Arabic Corpus (morphology)

- Source: https://corpus.quran.com — licence page https://corpus.quran.com/license.jsp
  (the GNU General Public License, **version 3**, 29 June 2007; a copy is in
  [`LICENSES/GPL-3.0.txt`](LICENSES/GPL-3.0.txt)).
- We read the corpus through the fork https://github.com/mustafa0x/quran-morphology
  (QAC morphology v0.4 converted to Arabic script, with the fork's documented fixes), and
  apply our own corrections on top at load time:
  [`data/corpus_corrections.json`](data/corpus_corrections.json), loaded by
  `src/fil/corpus/corrections.py`. The corpus file itself is never edited and never
  committed (`data/qac/` is git-ignored; README says how to download it).
- How we comply:
  - every page credits "Morphology: Quranic Arabic Corpus (GNU GPL)", linked to
    https://corpus.quran.com;
  - the copyright notice below is reproduced here, in the repository that holds everything
    derived from the corpus, with the GPL text in `LICENSES/GPL-3.0.txt`;
  - modification notice: what the site shows is **modified** from QAC morphology v0.4 —
    "Quranic Arabic Corpus morphology © 2011 Kais Dukes, GNU General Public License,
    corpus.quran.com — modified: mustafa0x/quran-morphology fork plus Fiʿl corrections
    (data/corpus_corrections.json)". Its complete source — this code, our corrections, and
    the public fork it starts from — is published in this repository under the same GPL.

The corpus's own header, verbatim (from https://corpus.quran.com/download/):

```
# Quranic Arabic Corpus (Version 0.4)
# Copyright (C) 2011 Kais Dukes
# License: GNU General Public License
#
# The Quranic Arabic Corpus includes syntactic and morphological
# annotation of the Quran, and builds on the verified Arabic text
# distributed by the Tanzil project.
#
# TERMS OF USE:
#
# - Permission is granted to copy and distribute verbatim copies
# of this file, but CHANGING IT IS NOT ALLOWED.
#
# - This annotation can be used in any website or application,
# provided its source (the Quranic Arabic Corpus) is clearly
# indicated, and a link is made to http://corpus.quran.com to enable
# users to keep track of changes.
#
# - This copyright notice shall be included in all verbatim copies
# of the text, and shall be reproduced appropriately in all works
# derived from or containing substantial portion of this file.
#
# Please check updates at: http://corpus.quran.com/download
```

## Tanzil Quran text

- Source: https://tanzil.net — licence https://tanzil.net/docs/text_license
  (Creative Commons Attribution 3.0, https://creativecommons.org/licenses/by/3.0/).
- The Arabic words of each ayah reach us inside the corpus, which builds on Tanzil's text.
  We show them as they are; only our morphology corrections change, never a letter.
- How we comply: every page names Tanzil and links https://tanzil.net; the notice is
  reproduced here.

```
Tanzil Quran Text
Copyright (C) 2007-2021 Tanzil Project
License: Creative Commons Attribution 3.0

This copy of the Quran text is carefully produced, highly
verified and continuously monitored by a group of specialists
in Tanzil Project.

TERMS OF USE:

- Permission is granted to copy and distribute verbatim copies
  of this text, but CHANGING IT IS NOT ALLOWED.

- This Quran text can be used in any website or application,
  provided that its source (Tanzil Project) is clearly indicated,
  and a link is made to tanzil.net to enable users to keep
  track of changes.

- This copyright notice shall be included in all verbatim copies
  of the text, and shall be reproduced appropriately in all files
  derived from or containing substantial portion of this text.

Please check updates at: http://tanzil.net/updates/
```

## Tanzil translations

- Source and terms: https://tanzil.net/trans/ ("for non-commercial purposes only … If you
  are using more than three of the following translations in a website or application, we
  require you to put a link back to this page").
- We use five: en.pickthall, tr.yazir, ur.kanzuliman, id.indonesian, ru.krachkovsky
  (`src/fil/ayah_translations.py`). They are fetched at build time into
  `data/translations/` (git-ignored), never committed, and shown unchanged.
- How we comply: the site is free and non-commercial; every page links
  https://tanzil.net/trans/; each translation is credited by translator under every ayah.

## Tanzil Quran metadata

- https://tanzil.net/res/text/metadata/quran-data.js — "Quran Metadata (ver 1.0),
  Copyright (C) 2008-2009 Tanzil.info, License: Creative Commons Attribution 3.0".
- We use the 114 surah lengths to number each ayah 1–6236 (`src/fil/quran_numbering.py`,
  credited there), which is how the streamed recitation is addressed.

## QuranHive Word-by-Word Audio Dataset

- Dataset: https://huggingface.co/datasets/quranhive/quran_word_by_word_audio — licence and
  attribution guidelines: https://github.com/quranhive/quran-word-by-word-audio
  (Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/;
  a copy is in [`LICENSES/CC-BY-4.0.txt`](LICENSES/CC-BY-4.0.txt)).
- Required attribution, shown on every page and in the app:
  "QuranHive Word-by-Word Audio Dataset — © QuranHive, licensed under CC BY 4.0", linking
  https://quranhive.com and the licence, with the address QuranHive asks users to report
  issues to (qh@quranhive.com).
- Changes we make (CC BY 4.0 asks that they be indicated, and the footer says
  "re-encoded"): each clip used is re-encoded from 64 kb/s stereo MP3 to mono AAC at 32 kb/s
  (`fil.audio.compact_aac_command`), nothing else.
- The archive (~1.6 GB) is downloaded once into `data/quranhive/` (git-ignored);
  `fil.recitation.QuranHiveArchive` prints the download command when it is missing.
- QuranHive also asks, as a non-legal request, that the clips be treated with respect and
  never used in a way that alters sacred meaning. We play each word only as the word it is.

### How we checked that their word numbers are our word numbers

A clip named `002_255_003.mp3` must be the third word of 2:255 exactly as the corpus counts
words, or a learner would hear the wrong word. QuranHive publishes its word-to-audio mapping
(https://huggingface.co/datasets/quranhive/quran_word_by_word_audio_mapping: surah, ayah,
word, the Arabic word, the file). On 2026-11-04 we compared it with every word of the corpus
as the site joins them (`fil.study.words_of`):

- all 77,425 words in the mapping exist in the corpus at the same surah:ayah:word, and the
  only corpus words without a clip are the four of 1:1 (no verb stands there); every file
  name in the mapping is its location;
- the Arabic text agrees at every location once both are reduced to their letters: 76,325
  match exactly, character for character; the rest differ only in spelling convention
  (their text is partly in standard rather than Uthmani orthography: آيَاتِ for ءَايَٰتِ,
  أَأَنْذَرْتَهُمْ for ءَأَنذَرْتَهُمْ, final ي for ى). No word anywhere is shifted by one, which
  would have shown as thousands of mismatches; words full of clitics (فَأَسْقَيْنَٰكُمُوهُ,
  أَنُلْزِمُكُمُوهَا, وَقَالُوٓا۟) and the corpus's one two-part word (إِلْ يَاسِينَ, 37:130) line up;
- the archive holds exactly the 77,425 files of the mapping.

## Ayah recitation: alquran.cloud (Islamic Network)

- Recitation by Mishary Rashid Alafasy, streamed from the Islamic Network CDN that serves
  https://alquran.cloud: `https://cdn.islamic.network/quran/audio/64/ar.alafasy/{1..6236}.mp3`.
  Terms: https://alquran.cloud/terms-and-conditions ("You may stream, embed and download
  them for personal and educational use"; recitations remain the reciters' copyright).
- How we comply: no ayah recitation is copied into the site. The learner's browser fetches
  the ayah from the CDN when play is pressed — in the app, on the static pages and in the
  full ayat lists alike (`fil.recitation.AYAH_STREAM`). Every page credits "Recitation:
  Mishary Rashid Alafasy, streamed from alquran.cloud (Islamic Network)" with a link to
  https://alquran.cloud. The site is free and educational.
- Single words are never cut out of these ayah recordings; they come from QuranHive above.

## Noun pictures: OpenMoji and Twemoji

- Sources: OpenMoji 15.1.0, https://openmoji.org — "All emojis designed by OpenMoji – the
  open-source emoji and icon project", licensed under **CC BY-SA 4.0**
  (https://creativecommons.org/licenses/by-sa/4.0/; text in
  [`LICENSES/CC-BY-SA-4.0.txt`](LICENSES/CC-BY-SA-4.0.txt)); and Twemoji 15.1.0, the
  maintained fork https://github.com/jdecked/twemoji (graphics © 2014–2021 Twitter, © 2022–
  Jason Sofonia & Justine De Caires and contributors), licensed under **CC BY 4.0**
  (text in [`LICENSES/CC-BY-4.0.txt`](LICENSES/CC-BY-4.0.txt)).
- What we ship: `assets/nouns/<slug>.svg`, one picture per picturable noun. Each is the
  original emoji **modified**: every colour replaced by one of the site's greens
  (`fil.nouns.palette`) and the markup minified. `data/noun_pictures.json` records for every
  file the set it came from and the original codepoint.
- Share-alike: the recoloured **OpenMoji** pictures are adaptations of CC BY-SA 4.0 work and
  are shared under **CC BY-SA 4.0** too; the recoloured **Twemoji** pictures under
  **CC BY 4.0**. Neither licence reaches the rest of the repository (the pictures are
  separate files, only collected alongside it).
- How we comply: every page that shows a picture carries the credit line of
  `fil.pages.picture_credits` — set, author, licence link, "recoloured" — naming only the
  sets that page uses. Pages without pictures do not carry it.

## Synthetic voice: tts_arabic

- Every practice word, form and sentence is spoken by tts_arabic, https://github.com/nipponjo/tts_arabic
  (pinned commit in `pyproject.toml`), driven by our own phoneme reading (`fil.speech`). The clips are generated at
  build time and shipped re-encoded (`build/pages/audio/`).
- Terms, from the package's own NOTICE.md: the code is MIT; the multi-speaker FastPitch model was trained on the
  Arabic Speech Corpus by Nawar Halabi (**CC BY 4.0**, https://en.arabicspeechcorpus.com/) and on synthetic speech
  from Coqui XTTS-v2 (Coqui Public Model License, **non-commercial**), so the model is offered "for noncommercial use
  only"; its Buckwalter phonetiser (from Halabi's Arabic-Phonetiser) is **CC BY-NC 4.0**.
- How we comply: the site is free and non-commercial; every page credits the voice, the Arabic Speech Corpus and
  its licence, and says "non-commercial use" (`credits` in `src/fil/site/ui.js`). These terms are not permissive:
  the site may not be used commercially while it ships these clips.

## Typefaces: Google Fonts

- Amiri Quran, Noto Naskh Arabic, Literata, Space Grotesk, Inter and IBM Plex Sans/Mono, all under the SIL Open
  Font License 1.1. No font file is copied: the browser loads them from fonts.googleapis.com.

## Build-time tools

- Qutrub (libqutrub, GPL) and CAMeL Tools (MIT) with its morphology database calima-msa-r13 (derived from
  Buckwalter's Aramorph, GPL-2.0) generate and cross-check conjugation and declension tables; PyArabic (GPL) helps
  with spelling. None of their code or databases is shipped — only the forms that pass our gates.

## Translations used as references only

Sahih International (English) and Besim Korkut (Bosnian) are under copyright and are not shipped. They serve
only as references for single standard terms (Džennet, emanet). Ayah quotations in our own texts are in
Pickthall's words (English, shipped above) or our own translation from the Arabic (Bosnian); `fil.ayah_quotes`
fails the build otherwise. Reviewer-only `notes` in the data files may cite a classical text in a few Arabic
words; they are never rendered on a page.

## Links only

Per ayah we link to quran.com (the ayah), quranwbw.com (the ayah word by word) and, for
Bosnian readers, islam.ba (the ayah in Besim Korkut's translation with tefsir, on the
Islamic Community in Bosnia and Herzegovina's site). Nothing from these sites is copied.
