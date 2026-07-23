# NEKYIA — The Catalogue of Souls

> *Sing in me, Muse, and through me tell the story.*

An emotive web app that presents Malaysian cause-of-death data as a voyage
through the underworld, structured after **Book XI of Homer's *Odyssey*** — the
*Nekyia*, in which Odysseus descends to the edge of the world to speak with
the dead.

Each of the **748,934** records becomes a soul on its journey home to Ithaka.
The experience is bilingual (**English + Bahasa Malaysia**), dark and oceanic
in tone, with gold accents. It is built as an act of data *and* reverence —
remembrance, not surveillance.

---

## The seven books

| Book | Title | What it shows |
|------|-------|---------------|
| **I**    | The Invocation        | The grand total, counted up like a roll-call of the dead |
| **V**    | The Sea of Souls      | An animated particle field — one spark per ~1000 deaths, coloured by fate |
| **XI**   | The Fates That Claim Us | Seven archetypal fates (heart, breath, cancer, metabolic, pestilence, violence, dawn) |
| **IX**   | The Voyage of Years   | An SVG area chart of deaths by age, split by gender |
| **III**  | The Archipelago       | The states and districts of Malaysia, grouped by region |
| **XI**   | The Descent           | **Interactive** — filter and summon individual anonymised souls |
| **XXIII**| The Return            | A closing dedication |

The seven fates are the thematic spine of the piece:

- ❦ **The Heart & Its Vessels** — 35% (ischaemic, stroke, hypertension)
- ≈ **The Failing Breath** — 24% (pneumonia, COPD, TB)
- ✶ **The Long Shadow** — 18% (cancers)
- ☣ **Pestilence** — 8% (Covid-19, HIV, hepatitis)
- ⚔ **Violence & Chance** — 7% (transport, self-harm, drowning)
- ◈ **The Body's Rebellion** — 5% (diabetes, liver, kidney)
- ☾ **The Dawn & the Unknown** — 3% (perinatal, congenital, Alzheimer's)

---

## Run it

Requires **Python 3.10+**. Uses a virtual environment (already created at
`.venv/`).

```bash
# from the project root
source .venv/Scripts/activate    # Git Bash on Windows
#   — or:  .venv\Scripts\activate   (cmd / PowerShell)

python app.py
```

Then open **http://127.0.0.1:5000**.

First run loads the cache once (~2 s); subsequent requests are instant.

### Architecture: precomputed cache

The app reads a **precomputed cache** (`data_cache/`) rather than loading
the parquet at runtime. This keeps memory and cold-start time low — crucial
for serverless/free-tier hosting.

- `data_cache/aggregations.json` — every precomputed view the API serves (~20 KB)
- `data_cache/souls.npz` — 748,934 rows as compact int arrays (~1 MB)

**Runtime dependencies** (installed in production):

- `flask`   — web framework
- `gunicorn` — production WSGI server
- `numpy`   — soul-pool for the interactive Descent endpoint

**Precompute dependencies** (only needed locally to regenerate the cache):

- `pandas`  — data wrangling
- `pyarrow` — parquet engine
- `numpy`   — array serialization

To recreate the venv and regenerate the cache from scratch:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install flask pandas pyarrow numpy
python precompute.py     # regenerates data_cache/
```

---

## Project layout

```
cod/
├── cod-data.parquet        # the source data (748,934 rows × 6 cols)
├── data_cache/             # precomputed cache (committed; runtime reads this)
│   ├── aggregations.json   #   every precomputed view (~20 KB)
│   └── souls.npz           #   748,934 rows as int arrays (~1 MB)
├── precompute.py           # regenerate data_cache/ from the parquet (local only)
├── data.py                 # runtime data layer: reads cache, samples souls
├── app.py                  # Flask app: one page + JSON API
├── templates/
│   └── index.html          # the single-page voyage (7 books)
├── static/
│   ├── styles.css          # dark oceanic + gold aesthetic
│   └── app.js              # sea canvas, fates, voyage chart, archipelago, descent
└── README.md
```

## The data

Source columns (Malay):

| Column          | Means            | Example            |
|-----------------|------------------|--------------------|
| `umur`          | age              | `64`               |
| `jantina`       | gender           | `Lelaki` / `Perempuan` |
| `negeri`        | state            | `Selangor`         |
| `daerah`        | district         | `Petaling`         |
| `etnik`         | ethnicity        | `Melayu`           |
| `sebab_kematian`| cause of death   | `Ischaemic Heart Diseases` |

The data is **anonymised** — no names, dates, or free text. The interactive
"Descent" surfaces one real row at a time, but presented as a mythic persona,
never as a re-identification vector.

---

## A note on tone

This project sits at an unusual intersection: open government mortality
microdata, presented with literary gravity. The intent is to make statistics
*feel* — to recover, however partially, the human weight that 748,934 as a
number cannot carry. Every figure here was a person. The Odyssey framing is a
way of taking that seriously without being mawkish.

> *Each number here was a name; each name, a life that loved and was loved.*
