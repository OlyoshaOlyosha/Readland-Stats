# Readlang Stats

A local web dashboard for your [Readlang](https://readlang.com/) vocabulary export.

It reads the CSV file you export from Readlang, computes spaced-repetition
analytics (status distribution, CEFR profile, review load, streaks, difficult
words, and more), and gives you a built-in editor for cleaning up words,
translations, and contexts — including an LLM-assisted bulk-edit workflow.

Everything runs on your machine. No data leaves `localhost`.

---

## Features

- **Overview** — KPI cards and charts: word states (new / learning / young /
  mature), memory quality (avg easiness, total attempts, avg CEFR level,
  attempts-to-consolidate), activity (streaks, overdue, avg daily load),
  CEFR profile, easiness histogram, interval distribution, weekly pace,
  hour-of-day activity, cumulative growth, and a 365-day activity heatmap.
- **Calendar** — upcoming reviews for the next 60 days, a 365-day review-load
  heatmap, words due today/tomorrow, and a list of overdue words.
- **Words** — sortable, filterable, paginated table of every reviewed word
  with difficulty score (`attempts / easiness`), plus an interactive scatter
  plot (attempts × easiness, colored by CEFR level). The X axis can switch
  between attempts, word length, and context length.
- **Editor** — inline editing of any word's word / translation / contexts with
  live context preview and backend validation, JSON export of the current
  filter, and a paste-JSON bulk-edit flow for LLM-driven cleanup.
- **Settings** — switch UI language (English / Russian), adjust SRS
  thresholds, reload the CEFR dataset, and see info about the data file
  (path, size, last modified, word count).
- **Copy as Markdown** — every major tab has a button that copies the current
  numbers and tables as Markdown, handy for pasting into notes or an LLM chat.

---

## Requirements

- **Python 3.10 or newer** (the project targets `py310`).
- A Readlang CSV export placed at `data/user/readlang-data.txt`.
- A modern browser. An internet connection is needed on first load — Chart.js
  and the datalabels plugin are loaded from `cdn.jsdelivr.net`.

---

## Install

The project intentionally ships with no locked dependency list; the only
runtime dependencies are FastAPI (which brings Pydantic and Starlette) and
Uvicorn.

```bash
git clone https://github.com/OlyoshaOlyosha/Readland-Stats
cd Readland-Stats

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install fastapi uvicorn
```

---

## Prepare your data

### 1. Readlang export (required)

In Readlang, export your words as CSV and save the file as:

```
data/user/readlang-data.txt
```

The app parses only the `Your words (csv format)` section and leaves every
other section of the file byte-identical when writing back. Blank rows are
ignored.

### 2. CEFR dataset (optional)

To see CEFR levels next to each word, place a CSV at:

```
data/cefr_mega_dataset.csv
```

Column names are matched case-insensitively and flexibly:

- word column: `word`, `headword`, `term`, or `lemma`
- level column: `cefr`, `cefr_level`, or `level`
- level values: `A1`, `A2`, `B1`, `B2`, `C1`, `C2`

If the file is missing or unreadable, the app still works — every word is
just shown as having an unknown level. You can reload the dataset without
restarting via **Settings → Reload CEFR dataset**.

---

## Run

```bash
python main.py
```

Then open <http://127.0.0.1:8000> in your browser.

The launcher runs Uvicorn against `app.main:app` on `127.0.0.1:8000`. Auto‑reload
is disabled by default (`DEBUG = False` in `app/config.py`); enable it there
if you're hacking on the backend.

---

## Usage

### Tabs

| Tab | What it shows |
|---|---|
| **Overview** | All-time KPIs, status/quality/activity cards, and a grid of charts covering easiness, intervals, recall ease, weekly pace, time of day, CEFR, velocity, and a yearly activity heatmap. |
| **Calendar** | Forward-looking view: reviews due in the next 60 days, a 365-day review-load heatmap, words due today/tomorrow, and overdue words. |
| **Words** | Filter by level, status, or free text; sort by word, translation, level, attempts, easiness, or difficulty; change page size; switch the scatter plot's X axis. |
| **Editor** | Edit any word's word / translation / contexts. Renaming a word requires the new form to appear in the contexts — the backend rejects mismatches. |
| **Settings** | Language switch, SRS thresholds, CEFR dataset reload, data file info. |

### SRS thresholds

Two thresholds drive the status buckets:

- **`mature_days`** (default **21**) — interval (in days) at or above which a
  word is counted as *mature*.
- **`young_days`** (default **1**) — lower bound for the *young* bucket;
  intervals below this but non-empty are *learning*.

Change them in **Settings → Review thresholds**. Values are clamped to at
least `1` and stored in `data/settings.json`.

### Keyboard shortcuts

- `1`–`5` — switch to the corresponding tab.
- `/` — focus the active tab's search box.
- `Esc` — close the edit or bulk-edit modal.

---

## Bulk editing with an LLM

The Editor tab has a two-step workflow for cleaning up many words at once:

1. **Export JSON.** Click **Export JSON** in the Editor. The current filter's
   words are copied to your clipboard as a JSON array of
   `{ word, translation, contexts }` objects, sorted by difficulty.
2. **Paste back.** Click **Paste JSON**, send the array to an LLM, and paste
   its reply into the textarea. The reply must be the same array:
   - `word` is the **anchor** — it identifies the row and must not change.
   - To **rename**, add a `new_word` field (the new form must appear in the
     new contexts, or the row is flagged `not_in_context`).
   - Line breaks inside strings must be escaped as `\n`.
3. **Preview and apply.** Click **Parse & Preview**. Each changed field shows
   an inline character-level diff (red = removed, green = added). Rows with
   conflicts (empty value, duplicate word, word not present in contexts) are
   not auto-selected — fix or uncheck them. Use the chips to filter by field
   or jump to conflicts, and the selection buttons to bulk-toggle rows.

When you click **Apply**, the backend writes everything in **one** pass:

- takes **one backup** of the CSV under `data/backups/`
- applies all valid changes
- returns a per-item result; failures are reported as a toast

Invalid items are skipped, valid ones are applied.

---

## Files and backups

| Path | Purpose |
|---|---|
| `data/user/readlang-data.txt` | Your Readlang export. Only the `Your words` section is rewritten. |
| `data/cefr_mega_dataset.csv` | Optional CEFR lookup dataset. |
| `data/settings.json` | Persisted UI language, `mature_days`, `young_days`. |
| `data/backups/` | Timestamped CSV backups created before any write. Format: `readlang-data-YYYYMMDD-HHMMSS.txt`. |

Backups are created automatically by the single-word editor **and** the bulk
editor — you always have the pre-edit state on disk.

---

## Project layout

```
Readland-Stats/
├── app/                 # FastAPI application
│   ├── api.py           # HTTP endpoints (words, stats, settings, CEFR)
│   ├── cefr.py          # CEFR CSV loader + word/phrase lookup
│   ├── config.py        # Paths, host/port, SRS thresholds
│   ├── data_manager.py  # Read/write the Readlang CSV, backups
│   ├── main.py          # FastAPI app: routes, static mount, index page
│   ├── models.py        # WordEntry dataclass (mirrors a CSV row)
│   ├── settings.py      # settings.json read/write with cache
│   └── stats.py         # All analytics (pure Python, no pandas)
├── data/                # User data + backups (gitignored)
├── static/              # JS/CSS/i18n
│   ├── i18n/{en,ru}.json
│   ├── app.js
│   ├── i18n.js
│   └── style.css
├── web/index.html       # The single HTML page
├── main.py              # `python main.py` launcher
└── pyproject.toml       # Ruff config only
```

---

## Development

Lint and format:

```bash
ruff check .
ruff format .
```

Ruff is configured for `py310`, 120-char lines, and a mix of pycodestyle,
Pyflakes, bugbear, and tryceratops rules — see `pyproject.toml`.

### Adding a language

1. Drop `static/i18n/xx.json` next to `en.json` / `ru.json`.
2. Add `"xx"` to the `SUPPORTED` array at the top of `static/i18n.js`.

The Settings language switcher picks it up automatically.
