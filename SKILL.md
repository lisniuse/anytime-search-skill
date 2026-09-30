---
name: anytime-search
description: Use a stealth Playwright browser to search multiple engines (realistically stable: baidu/sogou/360 for Chinese, brave/google/bing for English) or crawl any URL. Supports batch mode. Invoke when the user asks you to search the web, look something up online, fetch a webpage, or when web search results would help answer a question.
---

# Anytime Search Skill

Stealth browser search and web crawling tool using Playwright, with anti-bot evasion, batch mode, and engine-aware locale.

## Setup (one-time)

```bash
cd D:/dev/github/anytime-search-skill
pip install -r requirements.txt
playwright install chromium
```

## Search

```bash
PYTHONIOENCODING=utf-8 python D:/dev/github/anytime-search-skill/search.py -q "<query>" [options]
```

### Key options

| Option | Default | Description |
|--------|---------|-------------|
| `-q` / `--query` | — | Search query (required for search mode) |
| `-e` / `--engine` | `google` | See engine table below |
| `-n` / `--num-results` | `10` | Max results to return |
| `--json` | off | Output as JSON array `[{title, url, snippet}]` |
| `--deep` | off | Crawl each result URL, return full page content instead of snippet |
| `-u` / `--url` | — | Crawl a URL directly (returns cleaned HTML body; `--wait-for CSS` for SPAs) |
| `--proxy` | — | e.g. `http://127.0.0.1:7890` or `socks5://user:pass@host:port` |
| `--batch-file` | — | Batch mode, see below |
| `--no-headless` | off | Show browser window (manual CAPTCHA solving) |
| `--clear-session` | — | Reset cookies/session and exit |

### Exit codes (contract for callers/schedulers)

| Code | Meaning |
|------|---------|
| `0` | Success with results |
| `1` | Bad arguments/config |
| `2` | CAPTCHA encountered (switch engine or `--no-headless`) |
| `3` | **Query succeeded but 0 results** (engine throttling soft-fail, or genuinely empty) — retry on another engine |

### Engines: realistic availability (2026-09-30 measured)

The code covers 18+ engines, but only ~6 are reliably working. Pick accordingly:

- **Chinese queries (no proxy needed):** `baidu`, `sogou`, `360` ✅
  - baidu returns empty (exit 3) after ~20 rapid consecutive queries — spread load or rotate engines.
  - `shenma` ❌ dead.
- **English queries (needs proxy, e.g. 7890):** `google`, `bing`, `brave` ✅
  - `duckduckgo` / `startpage` / `ecosia` ❌ currently return empty — avoid.
- Locale/timezone/Accept-Language are auto-injected per engine region (zh-CN for Baidu/Sogou/360, etc.) — no action needed.

### Recommended query style

Narrow, concrete combinations beat vague words:
`{origin/chokepoint} {subject} {trigger} {year}` — e.g. `泰国 橡胶 厄尔尼诺 干旱 减产 2026`,
`Guinea bauxite export quota 2026`. Generic words ("black swan", "supply disruption") return junk.

## Batch mode

One browser session for many queries (no per-query cold-start). Input: JSON array; output: JSONL (one object per line: `{index, query, engine, results, error, tag}`); a failed query never aborts the batch.

```bash
cat > queries.json <<'EOF'
[
  {"query": "泰国 橡胶 割胶 降雨 2026", "engine": "sogou", "num_results": 8, "tag": "ru"},
  {"query": "opec supply cut 2026", "engine": "google", "num_results": 6, "tag": "sc"}
]
EOF
PYTHONIOENCODING=utf-8 python D:/dev/github/anytime-search-skill/search.py --batch-file queries.json --proxy http://127.0.0.1:7890
```

## Concurrency

To run queries in parallel safely, give each process its own session state file:

```bash
ASX_STATE_FILE=./data/states/zh_sogou.json python search.py -q "..." -e sogou
```

Rule of thumb: parallel ACROSS engines, serial WITHIN one engine (respect its rate).
`PW_CHROME=<path>` optionally launches with your system Chrome instead of bundled Chromium (more realistic fingerprint).

## Windows pitfalls

- **GBK console**: always set `PYTHONIOENCODING=utf-8`, or use `--json` (pure ASCII-safe piping).
- Large `--deep`/`-u` outputs may be truncated by the tool harness into a temp file — read that file.
- Google CAPTCHA → exit 2 → switch engine (`-e bing`) or `--no-headless`, or `--clear-session`.
