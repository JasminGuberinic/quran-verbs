# Fiʿl — launch plan

Agreed with the project owner on 2026-11-04. **Free options only** — nothing paid, no custom domain.

## Phase 1 — now, as early as possible (in parallel with adding verbs)

| What | Free solution |
|---|---|
| Hosting | GitHub Pages at `https://jasminguberinic.github.io/quran-verbs/` — built locally, pushed to an orphan `gh-pages` branch (force-pushed, so history does not grow) |
| Found by Google / Bing | Google Search Console and Bing Webmaster Tools (the owner registers the site; free) |
| Pages per verb, sitemap, AI description | A static, pre-rendered page per verb per language (`/bs/glagol/<slug>/`, `/en/verb/<slug>/`, …) with real text: title, meaning, conjugation, ayat, practice sentences; `<title>`, meta description, `hreflang`, canonical URLs, `sitemap.xml`, `robots.txt`, schema.org structured data, Open Graph images, and `llms.txt` for AI assistants |
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
- Recitation audio (everyayah) is fine for free, non-commercial use; a monetized channel would need permission.

## Honest expectations
Search traffic takes weeks to months to build and is not guaranteed; quality content (we have it) and backlinks (from promotion) matter most.
