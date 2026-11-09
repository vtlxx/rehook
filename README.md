# ReHook — hook generator for creative modifications

## Quick start for designers

ReHook takes the script of a winning ad and suggests ~20 new openings (the first 3 seconds) for it. You work with it on a web page in your browser.

**You need:** a Mac, the Terminal app (Applications → Utilities → Terminal) and an Anthropic API key from your team lead. Without a key, only a demo with pre-recorded answers works.

### First time only (about 5 minutes)

Open Terminal, paste each line, and press Enter after each one.

1. Install the `uv` tool, which sets up Python for you:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   When it finishes, close Terminal and open it again.
2. Download ReHook into the `rehook` folder in your home folder:
   ```bash
   git clone https://github.com/vtlxx/rehook.git ~/rehook
   ```
   If macOS offers to install "command line developer tools", agree, wait for it to finish and run the line again.
3. Install what ReHook needs:
   ```bash
   cd ~/rehook && uv venv --python 3.12 && uv pip install -r requirements.txt
   ```
4. Save your API key (replace `PASTE-YOUR-KEY-HERE` with the key, keep the quotes):
   ```bash
   echo 'ANTHROPIC_API_KEY=PASTE-YOUR-KEY-HERE' > ~/rehook/.env
   ```
   The key stays only on your computer.

### Every time

Paste this in Terminal and press Enter:

```bash
cd ~/rehook && set -a; [ -f .env ] && . ./.env; set +a; .venv/bin/streamlit run app.py
```

The page opens in your browser at http://localhost:8501. Keep the Terminal window open while you work; to stop, click it and press `Ctrl+C`.

### On the page

1. **Winner script:** pick a sample, upload your `.txt` script, or paste its text. The script must start with a line like `WINNER_ID: 044`, followed by lines with timecodes (`[0-3s] VO: "…"`); see `examples/winner_044.txt`.
2. **Brand brief:** pick the brief for the product.
3. Untick **Mock** (it is only a demo, and works only for winner 012). Leave it ticked if you just want to look around without a key.
4. Optional: under **Launch history**, upload the hooks already launched for this winner and an Ads Manager export, so ReHook doesn't repeat them and numbers new ads correctly.
5. Press **Generate** and wait about half a minute (one run costs about $0.15).
6. Read the cards. Each one has the voice-over 🎙, on-screen text 🔤 and first frame 🎬. Red ⚠️ lines mean "check this before use": wrong price, a banned word or a promise the brand can't make, too many words.
7. Tick the variants you will make and press **Download selected as CSV**. The IDs in the file (`SL_W044_AI_H04_…`) are the ad names for Ads Manager. **Download brief.md** gives a full brief with the breakdown of the winner.

**If something goes wrong:**
- *"mock fixtures exist only for winner 012"*: untick Mock.
- *"ANTHROPIC_API_KEY is not set"*: do step 4 of the first-time setup, stop the page with `Ctrl+C` and start it again.
- *"command not found: uv"*: close Terminal, open it again and retry; if it still fails, repeat step 1.
- *"WINNER_ID line not found"*: add a `WINNER_ID: …` line at the top of the script.

Ready-made files to try the page with are in [`examples/`](examples/README.md).

## What it is and what problem it solves

SockLock (magnetic socks on subscription, traffic from Meta) wants to grow spend from $400k to $800k a month within six months without letting ROMI drop below 125%. That takes ~500 creative modifications a month instead of 240. Six motion designers spend ~3 h per modification, and half of that time goes into coming up with new hooks for the winning ad's script by hand.

ReHook takes the winner's script and in about half a minute produces ~20 **distinct** openings for the ad (voice-over for the first ~3 s, on-screen text, a description of the first frame). It checks them against the brand brief, drops variants that are too similar to each other or to hooks already launched, and writes a brief for the designer. The designer picks and edits instead of writing from scratch.

**Expected effect.** If time per modification drops from 3 to 1.5 h, the team makes 343 modifications instead of 240, which is ≈ +$46k EGP a month (pessimistic scenario +$10k, optimistic +$90k). Caveat: −50% time is an optimistic assumption. Controlled studies of AI tools for designers and IT specialists measured time savings of ~20–30%, so the pilot below targets −30%.

## Installation

You need Python 3.11+ (check with `python3 --version`; on macOS the system Python is usually 3.9). The simplest way to get a newer one is [uv](https://docs.astral.sh/uv/) (`brew install uv`), which downloads Python 3.12 by itself.

```bash
git clone git@github.com:vtlxx/rehook.git
cd rehook
uv venv --python 3.12             # or, with Python 3.11+ installed: python3.12 -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt   # or: pip install -r requirements.txt
```

Check that everything works without an API key (all tests, plus a demo on recorded model replies):

```bash
pytest -q
python -m rehook generate --winner data/winner_012.txt --brand data/brand.yaml \
  --history data/launched.csv --ads data/ads_export.csv --mock
streamlit run app.py              # designer page at http://localhost:8501
```

The real model needs an Anthropic API key. Set it in the current terminal, or put it in a `.env` file in the project root (it is in `.gitignore`) and load it before running:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
set -a && . ./.env && set +a
```

Every command below runs from the project root with the environment activated (`source .venv/bin/activate`).

The default model is `claude-sonnet-5-5`. The model and the prices per 1M tokens are constants at the top of `rehook/llm.py`; the `--model` flag overrides the model.

## Usage

### `generate` — hook variants for a winner

```bash
python -m rehook generate \
  --winner data/winner_012.txt \
  --brand data/brand.yaml \
  --history data/launched.csv \
  --ads data/ads_export.csv
```

Without a key, on recorded model replies (for demos and tests):

```bash
python -m rehook generate --winner data/winner_012.txt --brand data/brand.yaml \
  --history data/launched.csv --ads data/ads_export.csv --mock
```

Flags: `--n 20` (how many variants to keep), `--out out/`, `--sim-threshold 0.5` (similarity threshold), `--seed 42` (shuffle order during scoring), `--model`. Mock fixtures exist only for winner 012 with `--n 20` and the default similarity threshold.

Output in `out/`:
- `variants.csv` — selected variants with an Ads Manager ID (`SL_W012_AI_H11_pain-lost-sock`), angle, hook type, score, similarity and flags;
- `rejected.csv` — dropped variants and the reason (`similar_to_launched:<ad_name>`, `duplicate_of:<id>`, `below_top_n`);
- `brief.md` — the designer's brief: winner breakdown, the unchanged part of the script, variants by angle, flags marked ⚠️;
- in the console — how many were generated, dropped and kept, tokens per step, cost and time.

Real run for winner 012 (`claude-sonnet-5-5`, 10 calls, no retries or top-up): 30 generated → 20 selected across 6 angles, 1 dropped as similar to a launched hook, 6 flagged for designer review; **$0.15–0.16 and 28–33 s** over two runs.

### Designer page

```bash
streamlit run app.py
```

This opens `http://localhost:8501`. Under **Winner script** the designer chooses the source (a sample from `data/`, an uploaded `.txt` file, or pasted text), picks a brief and presses **Generate**. Mock mode has recorded replies only for winner 012; for any other script, untick Mock. Variants appear as cards grouped by angle, with a score and ⚠️ flags (price, banned words and claims, length). The designer ticks the variants they want, and **Download selected as CSV** returns `variants.csv` with only those; next to it are a button for `brief.md` and the list of dropped variants with reasons. Launch history (`launched.csv`, `ads_export.csv`) can be uploaded; otherwise the files in `data/` are used. Ready-made files for trying the page (a new winner, its launch history, a broken script, a holiday brief) and test scenarios are in [`examples/`](examples/README.md).

The core is the same as in the CLI: the page only calls `run_generate`. Without `ANTHROPIC_API_KEY` in the environment, mock mode is on (recorded replies for winner 012). To work with the real model, start the page with the key, for example from `.env`:

```bash
set -a && . ./.env && set +a && streamlit run app.py
```

### `report` — AI modifications vs manual ones

```bash
python -m rehook report --ads data/ads_export.csv
```

Flags: `--ltv 68`, `--min-spend 500`, `--min-romi 1.25`, `--meta-undercount 0.12` (`0` turns the correction off), `--out out/`. Prints an AI vs MAN table and saves `out/report.csv`.

### Input files and how to use your own

| File | Contents |
|---|---|
| `winner_*.txt` | Winner script with timecodes; first line `WINNER_ID: 012`. `[0-3s]` lines are the hook; everything from second 3 on stays unchanged. |
| `brand.yaml` | Product, offer, allowed prices (`price_rules`), facts (`facts`), banned claims and words, tone, word limits, personas. |
| `launched.csv` | `ad_name,hook_vo,on_screen_text` — hooks already launched (full name as in Ads Manager). New variants must not be similar to them. |
| `ads_export.csv` | A regular Ads Manager export: `ad_name,spend,purchases,impressions,clicks`. |

Ad names: `SL_W{winner}_{AI|MAN}_H{nn}_{slug}`. `report` uses them to tell AI modifications from manual ones, and `generate` continues the numbering so it doesn't collide with launched ads. The data in `data/` is synthetic; `ads_export.csv` is produced by `scripts/make_ads_export.py`.

## How it works

1. **Winner breakdown** (model): the ad's hook/problem/demo/offer/cta structure and why it worked.
2. **Angle matrix** (model): 6 angles; every pair differs in at least 2 of 4 dimensions (pain, persona, emotion, first-frame format), at least 4 different frame formats, one "safe" angle close to the winner. Code checks these rules.
3. **Generation** (model, 6 parallel calls, one per angle): 5 variants per angle, with different hook types inside an angle (question, confession, bold statement, POV, contrast, number, curiosity). The prompt gets the brief, the breakdown, and the best and worst launched hooks by ROMI.
4. **Code checks**: length, prices other than the allowed one, banned words, short banned claims ("free", "lifetime"), ALL CAPS. Variants are flagged, not removed.
5. **Claim check** (model): any statement beyond the brief's facts; the model quotes the offending phrase.
6. **Similarity filter** (code): TF-IDF on character n-grams + cosine, compared between variants and against history; of a similar pair, the variant with the better score stays.
7. **Scoring** (model): 5 criteria at 1–5 each (stops the scroll, specificity, clear in 3 s, tone, likeness to winners); code computes the 1–10 total; variants are presented in shuffled order. Runs before step 6, in parallel with step 5.
8. **Selection and export**: top n, but at least 2 and at most ⌈n/6⌉+1 per angle. If too few variants survive the filter, first one top-up round for the short angles, with a list of what must not be repeated.

About 10 model calls in total. Model replies are JSON; if the JSON is broken or fails validation, there is one retry with the error text. Prompts live in `prompts/*.md`.

## How to measure success

**Pilot: 2 weeks, 2 designers, crossover design.** Each designer makes 20 modifications with the tool and 20 by hand, from the same winners, alternating by winner or by day. This keeps the difference between designers from mixing with the tool's effect (critical with only two people). Time per modification comes from task-tracker timestamps, not self-reports. IDs go in ad names; `report` runs weekly.

**The pilot succeeds if:**
1. time per modification is at least 30% lower — the main metric, measured reliably;
2. designers use the tool in ≥ 80% of modifications;
3. performance shows no clear failure: the share of AI modifications that reached scaling is not below the lower bound of the 95% Wilson interval for manual ones (`report` prints it).

**Why not "no more than 10% worse".** On Meta about 5% of creatives reach scaling (Motion's benchmark across 578k ads). With 40 modifications per group that's 2–4 "winners". At 2 out of 40, the 95% interval for the share runs from 1.4% to 16.5%, so any difference drowns in noise. Confirming a relative difference of no more than 10% at a share of ~20% would take ~5,000 modifications per group. So the final business metric is **winners per month** (volume × share): the tool raises volume, and we recompute the metric as data accumulates.

**Definitions.** ROMI = LTV revenue / spend, i.e. `purchases_adj × LTV / spend` (1.35 = 135%, the way the team counts it). Meta sees ~12% fewer purchases than the backend, so `purchases_adj = purchases / (1 − 0.12)`. The correction is the same for both groups and doesn't affect the AI vs MAN comparison, only which ads pass the ROMI ≥ 1.25 threshold.

## Limitations

- **Similarity is text-only.** Meta Andromeda also compares images and audio; the required variety of first-frame formats across angles partly covers this. The 0.5 threshold is our own heuristic, tuned on ~20 labelled pairs (`tests/test_similarity.py`): Meta doesn't publish a threshold. The corpus is small, so IDF is unstable, and the same pair can get a slightly different similarity in different runs.
- **The model's score is only an ordering, not a forecast.** Both people and models are bad at guessing which hook will win (in headline experiments people guessed almost at random). The test decides.
- **The model's claim check can be wrong**, which is why code also catches short banned words.
- **The data is synthetic**; the numbers in `report` are illustrative.

## Next iteration

- Angle weights that adapt to `report` results.
- First-frame similarity checks on images.
- Localizing variants to DE/FR with the same pipeline.
- Verbalized sampling: ask the model for more candidates with a "typicality" estimate and take the less typical ones; research shows this noticeably increases diversity.

## Development

```bash
pytest -q
```

Tests cover the code checks, the similarity filter with calibration pairs, selection, the `report` formulas, the retry on broken JSON, the top-up round, an end-to-end `generate --mock` run, and the designer page (via Streamlit AppTest, without a browser).
