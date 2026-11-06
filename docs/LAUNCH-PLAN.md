# Fiʿl — launch plan

**Order (owner, 2026-11-04): functionality first.** 1) verbs to ~400–500 → 2) nouns & adjectives ("Phase 3" below) → 3) stories & dialogues ("Phase 4") → 4) translation into the remaining 13 languages → 5) promotion & videos. Until step 4, every batch is bs + en (required) + tr (Turkish, done by a cheaper model right after each batch; it also has a free ayah translation).

Agreed with the project owner on 2026-11-04. **Free options only** — nothing paid, no custom domain.

## Phase 1 — now, as early as possible (in parallel with adding verbs)

| What | Free solution |
|---|---|
| Hosting | GitHub Pages at `https://jasminguberinic.github.io/quran-verbs/` — built locally, pushed to an orphan `gh-pages` branch (force-pushed, so history does not grow) |
| Found by Google / Bing | Google Search Console and Bing Webmaster Tools (the owner registers the site; free) |
| Pages per verb, sitemap, AI description | A static, pre-rendered page per verb per language (`/bs/glagol/<slug>/`, `/en/verb/<slug>/`, …) with real text: title, meaning, conjugation, ayat, practice sentences; `<title>`, meta description, `hreflang`, canonical URLs, `sitemap.xml`, `robots.txt`, schema.org structured data, Open Graph images, and `llms.txt` for AI assistants |
| Honest `<lastmod>` | Each sitemap address carries the day its content last really changed, not the build date: `fil pages` fingerprints every sitemap page (sound file names, which follow audio re-encodes, are ignored) and keeps fingerprint + date in the committed `data/page_versions.json` — commit it with the content that moved it (`fil.pages.freshness`) |
| IndexNow (Bing, Yandex, Seznam, Naver, …) | `fil pages --deploy` publishes, then POSTs the addresses this build changed to `api.indexnow.org` (key file `d66ea097dffafa6511a406e8667931ad.txt` at the site root, named by `keyLocation` because the site is in a subfolder). A failed ping is printed, never fails the deploy. What is announced: the pages this build changed, plus every page whose `<lastmod>` differs from the live sitemap read just before the push (so changes recorded by an earlier, undeployed `fil pages` are not lost; the first deploy after this landed announces every page, as the old sitemap had no dates). `--no-ping` skips it; `--ping-all` announces every sitemap page (`fil.pages.indexnow`) |
| Size | Audio as separate, de-duplicated files (not base64 inside the cards) so ~500 verbs fit GitHub's limits |

## Phase 2 — only when the site is fully complete

Start promotion **only after**: all target verbs (~400–500) are in, every language is translated, everything is tested and polished. Not before.

### Promotion (free channels)
- **Communities** (the owner posts; Claude prepares the texts, adapted to each community's rules, in Bosnian and English):
  Reddit (r/learn_arabic, r/Quran…), Facebook groups for learning Arabic, džemati / mektebi / medrese / Arabic teachers (a short letter), Discord servers.
- **Open source**: "Show HN" on Hacker News; awesome lists on GitHub (awesome-arabic etc.) — also bring backlinks.
- **Timing**: Ramadan is the best moment for a campaign.

### "Verb of the day" short videos
- `fil video`: generates vertical (9:16) 20–30 s videos per verb, fully automatically and locally with free tools (ffmpeg, free fonts): the verb with its pronunciation and meaning, three main forms with audio, an ayah recited by Alafasy with the verb highlighted, and an ending "learn all verbs free → link". Any language; a caption and hashtags per video.
- First 3 sample videos for the owner to approve, then all.
- Publishing: YouTube Shorts fully automatic via the free YouTube Data API (one-time OAuth by the owner); Facebook / Instagram via Meta Business Suite scheduling and TikTok via TikTok Studio — the owner schedules a week at a time (~15 min).
- Recitation audio: ayat stream from alquran.cloud (personal and educational use; recitations stay the reciters' copyright), single words are QuranHive (CC BY 4.0, credit required). A monetized channel would need to re-check both terms (see THIRD_PARTY_NOTICES.md).

## Honest expectations
Search traffic takes weeks to months to build and is not guaranteed; quality content (we have it) and backlinks (from promotion) matter most.

## Phase 3 — nouns and adjectives (after the verbs, before promotion)

Owner's idea (2026-11-04): teach every Quranic word, not only verbs — nouns, adjectives, objects — in their real forms, with translations and usage together with the verbs.
- **Data:** the Quranic Arabic Corpus tags every noun/adjective with root, lemma, case (NOM/ACC/GEN), gender, number (incl. broken plurals), definiteness and tanwīn; `src/fil/vocabulary.py` already builds a Quranic word bank.
- **Noun card:** lemma, meaning, gender; singular / dual / plural; the three cases with audio (recitation where the Quran has the form, checked speech otherwise) and example ayat.
- **Adjectives:** agreement with the noun (gender, number, case, definiteness).
- **Practice sentences combining verbs and nouns** — e.g. أَكَلَ الْوَلَدُ التُّفَّاحَ (subject in -u, object in -a), جَلَسَ عَلَى الشَّجَرَةِ (genitive after a preposition) — through the same gate and blind review.
- **New exercises:** "which case?", "complete the ending", "match the adjective to the noun".
- Same tooling pattern as verbs (batches by frequency, en + bs first, bulk translation later).

## Phase 4 — stories and dialogues (after phase 3, before promotion)

Owner's idea (2026-11-04): short stories and conversations built only from Quranic vocabulary (verbs, nouns, adjectives), for reading practice.
- **Graded:** each text uses only words the learner has met so far (the first ones only the top verbs and commonest nouns); every new text adds a few words.
- **Word by word:** tap a word for its meaning, form/case and pronunciation; a translation per sentence in every learner language.
- **Audio** for the whole text with the same vowel-checked speech.
- **Comprehension questions** after each text.
- Every sentence goes through the same gate and blind review, under the same content policy (no Quranic wording, gentle everyday content).
