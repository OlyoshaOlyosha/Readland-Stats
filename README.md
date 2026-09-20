# Readlang Stats

**English** · [Русский](README.ru.md)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A local dashboard for your [Readlang](https://readlang.com/) CSV export:
spaced-repetition analytics, review scheduling, and a built-in editor with an
LLM-assisted bulk-edit workflow. Runs entirely on `localhost` — no data leaves
your machine.

## Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Install](#install)
- [Prepare your data](#prepare-your-data)
- [Run](#run)
- [Usage](#usage)
- [Bulk editing with an LLM](#bulk-editing-with-an-llm)
- [Files and backups](#files-and-backups)
- [Project layout](#project-layout)
- [Development](#development)
- [License](#license)

---

## Features

**Overview** · **Calendar** · **Words** · **Editor** · **Settings** — five screens, each focused on one question. Details in [Usage → Tabs](#tabs).

### Cross-cutting

- **Copy as Markdown** — every major tab has a button that copies its numbers and tables as Markdown. Handy for pasting into notes, an Obsidian vault, or an LLM chat.
- **Bilingual UI** — English and Russian out of the box. Adding a language is two steps (drop `static/i18n/xx.json`, add `"xx"` to `SUPPORTED` in `static/i18n.js`).
- **Local-only** — the app binds to `127.0.0.1` and never sends your data anywhere. The only outbound request is the Chart.js CDN on first page load.

---

## Screenshots

### Overview — KPIs and charts
![Overview tab](docs/screenshots/01-overview.png)
*Word states, memory quality, activity load, CEFR profile, easiness by level, and interval distribution.*

### Calendar — what's due and what's overdue
![Calendar tab](docs/screenshots/02-calendar.png)
*60-day review forecast, 365-day load heatmap, words due today/tomorrow, and the overdue backlog.*

### Words — find the hardest entries
![Words tab](docs/screenshots/03-words.png)
*Scatter plot (attempts × easiness, colored by CEFR level) next to a sortable table of the hardest words.*

### Editor — inline and bulk edits
![Editor tab](docs/screenshots/04-editor.png)
*Inline editing with live context preview, plus JSON export/import for the LLM-assisted bulk-edit workflow.*

### Settings
![Settings tab](docs/screenshots/05-settings.png)
*UI language, SRS thresholds, CEFR dataset reload, and data-file info.*

---

## Requirements

- **Python 3.10 or newer**.
- A Readlang CSV export placed at `data/user/readlang-data.txt`.
- A modern browser.

The first page load pulls Chart.js and the datalabels plugin from
`cdn.jsdelivr.net`, so an internet connection is needed once. After that
everything runs offline.

---

## Install

```bash
git clone https://github.com/OlyoshaOlyosha/Readland-Stats
cd Readland-Stats

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
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

Auto-reload is disabled by default (`DEBUG = False` in `app/config.py`). Enable
it there if you're hacking on the backend.

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

The Editor tab has a three-step workflow for cleaning up many words at once:
export the current filter as JSON, hand it to an LLM, paste the reply back,
review a char-level diff, apply. The backend takes one backup and writes
once — invalid items are skipped, valid ones are applied.

<details>
<summary>Full workflow, JSON format, and conflict rules</summary>

### 1. Export JSON

Click **Export JSON** in the Editor. The current filter's words are copied to
your clipboard as a JSON array of `{ word, translation, contexts }` objects,
sorted by difficulty.

### 2. Paste back

Click **Paste JSON**, send the array to an LLM, and paste its reply into the
textarea. The reply must be the same array:

- `word` is the **anchor** — it identifies the row and must not change.
- To **rename**, add a `new_word` field (the new form must appear in the new
  contexts, or the row is flagged `not_in_context`).
- Line breaks inside strings must be escaped as `\n`.

### 3. Preview and apply

Click **Parse & Preview**. Each changed field shows an inline character-level
diff (red = removed, green = added). Rows with conflicts (empty value,
duplicate word, word not present in contexts) are not auto-selected — fix or
uncheck them. Use the chips to filter by field or jump to conflicts, and the
selection buttons to bulk-toggle rows.

When you click **Apply**, the backend writes everything in **one** pass:

- takes **one backup** of the CSV under `data/backups/`
- applies all valid changes
- returns a per-item result; failures are reported as a toast

</details>

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
├── requirements.txt     # fastapi, uvicorn[standard]
└── pyproject.toml       # Ruff config only
```

---

## Development

### Run with auto-reload

1. Set `DEBUG = True` in `app/config.py`.
2. Run `python main.py` — Uvicorn will reload on every save.

### Lint and format

```bash
ruff check .
ruff format .
```

Ruff is configured for `py310`, 120-char lines, and a mix of pycodestyle,
Pyflakes, bugbear, and tryceratops rules — see `pyproject.toml`.

### Architecture

Everything runs in a single process — no database, no background jobs.
The flow is one-directional:

```
data/user/readlang-data.txt
        │
        ▼
   data_manager   parses only the "Your words" section
        │
        ▼
      stats       pure-Python analytics, no pandas
        │
        ▼
       api        FastAPI endpoints under /api/*
        │
        ▼
   static/app.js  fetches JSON, renders tables and Chart.js plots
```

Settings are persisted to `data/settings.json`; every write goes through
`data_manager.backup_csv()` first, so backups always exist under
`data/backups/`.

### Adding a language

1. Drop `static/i18n/xx.json` next to `en.json` / `ru.json`.
2. Add `"xx"` to the `SUPPORTED` array at the top of `static/i18n.js`.

The Settings language switcher picks it up automatically.

### Contributing

Issues and pull requests are welcome. There's no formal process yet — for
anything non-trivial, open an issue first so we can agree on the shape before
you write code. Small fixes (typos, docs, obvious bugs) can go straight to a PR.

---

## License

MIT — see [LICENSE](LICENSE).
