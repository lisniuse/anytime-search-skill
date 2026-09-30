# serpkit

**English** | [简体中文](README.zh-CN.md)

Stealth browser search / crawl **CLI** (Python + Playwright). The code covers 18+ search engines (currently ~6 reliably usable — see [field-tested availability matrix](#field-tested-availability-matrix-important)), with anti-bot evasion, URL crawling, batch lane concurrency and plain-text output. Results go to stdout, ready for any script / agent / terminal user. **This repo is CLI-only — no platform integrations (Claude Code skill / MCP / IDE) ship here.** Integration is left to the user.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Options](#cli-options)
- [Usage Examples](#usage-examples)
- [Supported Search Engines](#supported-search-engines)
- [URL Crawl Mode](#url-crawl-mode)
- [Output Formats](#output-formats)
- [Session Management](#session-management)
- [Anti-Bot Measures](#anti-bot-measures)
- [CAPTCHA Handling](#captcha-handling)
- [Project Structure](#project-structure)
- [Notes](#notes)

---

## Features

- **Multi-engine**: 18+ search engines including Google, Bing, Baidu, DuckDuckGo, spanning Global / China / East Asia / Privacy categories
- **Stealth mode**: multi-layer anti-bot measures that mimic real browser behavior to bypass common bot detection
- **CAPTCHA detection**: automatically detects Google CAPTCHA (reCAPTCHA / `/sorry/` pages), exits immediately with a hint
- **URL crawling**: crawl any URL directly, returning a clean HTML body stripped of all CSS and scripts
- **Session persistence**: cookies and storage saved to local `user_data/`, keeping login state across runs
- **Flexible output**: formatted text or JSON
- **Headless / headed**: headless by default; switch to headed to watch the actual browsing
- **Browser keep-alive**: control whether the browser closes automatically after results are retrieved

---

## Installation

**Requirements:** Python 3.8+

### 1. Clone the project

```bash
git clone git@github.com:lisniuse/serpkit.git
cd serpkit
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt`:

```
playwright>=1.42.0
beautifulsoup4>=4.12.0
lxml>=5.1.0
```

### 3. Install the Playwright browser

```bash
playwright install chromium
```

> Chromium alone is enough; other browsers are not required.

---

## Quick Start

```bash
# Search with Google (default)
python search.py -q "Python asyncio tutorial"

# Search with Baidu
python search.py -q "Python 异步编程" -e baidu

# Crawl a page
python search.py -u https://example.com
```

---

## CLI Options

```
python search.py [options]
```

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--query` | `-q` | — | Search query |
| `--engine` | `-e` | `google` | Search engine name (see list below) |
| `--url` | `-u` | — | Crawl a specific URL, return clean HTML |
| `--wait-for` | — | — | Wait for a CSS selector before extracting content (URL crawl) |
| `--num-results` | `-n` | `10` | Max number of results to return |
| `--no-headless` | — | — | Run browser in headed (visible) mode |
| `--proxy` | — | — | Proxy URL, HTTP/SOCKS5 supported, e.g. `http://127.0.0.1:7890` or `socks5://user:pass@host:port` |
| `--no-auto-close` | — | — | Keep browser open after results are retrieved (press Enter to close) |
| `--json` | — | — | Output results as JSON |
| `--deep` | — | — | Deep search: crawl each result URL and replace the snippet with full-page **plain text** (strips nav/footer/tags, LLM-friendly) |
| `--deep-html` | — | — | With `--deep`: keep the old "cleaned compressed HTML" output instead of plain text |
| `--deep-workers` | — | `1` | With `--deep`: crawl concurrency, bucketed into N lanes by target domain (serial + rate-limited within a lane, parallel across lanes); 3–6 recommended |
| `--as-text` | — | — | `-u` crawl mode returns plain text; cleaned HTML by default |
| `--list-engines` | — | — | List all supported search engines and exit |
| `--clear-session` | — | — | Delete saved browser session/cookies and exit |
| `--batch-file` | — | — | Batch mode: run all queries from a JSON array file in one session, see below |
| `--workers` | — | `1` | Batch mode engine-lane concurrency: one engine = one lane (serial within, parallel across), N caps lane count |

### Batch mode `--batch-file`

Invoking the CLI per query pays a 5–8s Chromium cold start every time. Batch mode starts **one browser**, groups queries by engine locale, reuses contexts, and a single failure never aborts the batch:

```bash
cat > queries.json <<'EOF'
[
  {"query": "泰国 橡胶 减产 2026", "engine": "baidu", "num_results": 8, "tag": "ru"},
  {"query": "opec supply cut", "engine": "google", "num_results": 6, "tag": "sc"}
]
EOF
python search.py --batch-file queries.json --json
```

Output is **JSONL** (one object per line: `{index, query, engine, results, error, tag}`), easy to consume in a stream.

Add `--workers N` to enable **engine-lane concurrency**: one engine per lane (own thread + browser + session file `storage_state_<engine>.json`), **serial and rate-limited within a lane, fully parallel across lanes**, `N` capping concurrent lanes. The same engine is never concurrent (risk control is per-engine), so the best N ≈ number of distinct engines in the batch:

```bash
python search.py --batch-file queries.json --workers 6 --proxy http://127.0.0.1:7890
```

### Deep-search lanes `--deep-workers` (for `--deep`)

By default (`--deep-workers 1`) crawling is serial, reusing the single results-page tab. With `--deep-workers N`, URLs are bucketed by **target domain** (crc32) into N lanes: same domain always lands in one lane and is crawled serially with rate limiting; different domains run in parallel. One lane = one thread + its own browser (Playwright sync API pages cannot be shared across threads — same model as batch `--workers`). Baidu/Google redirect-wrapper links (`baidu.com/link?url=`, `google.com/goto?url=`) are spread by full URL instead of wrapper domain, so everything doesn't pile into one "wrapper-domain" lane and turn into fake parallelism.

```bash
python search.py -q "最新 AI 监管 政策" -e baidu -n 10 --deep --deep-workers 5 --json
```

`--workers 1` (default) runs engines one by one — the most conservative mode.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success with results |
| `1` | Argument/config error |
| `2` | CAPTCHA encountered (Google `/sorry/`) — switch engine or use `--no-headless` to solve manually |
| `3` | **Query succeeded with 0 results** (engine rate-limit soft-fail or genuinely empty) — multi-engine schedulers can use this to immediately fail over |

### Environment variables

| Variable | Purpose |
|----------|---------|
| `ASX_STATE_FILE` | Override the session state file path. **Concurrent/multi-process callers must give each process its own path**, otherwise they share one `storage_state.json` and cross-contaminate cookies |
| `PW_CHROME` | Path to a system Chrome executable (uses Playwright's bundled Chromium by default) |

---

## Usage Examples

### Basic search

```bash
# Google search (headless by default)
python search.py -q "machine learning tutorial"

# Pick an engine
python search.py -q "今日新闻" -e baidu
python search.py -q "privacy browser" -e duckduckgo
python search.py -q "latest news" -e bing

# Short aliases
python search.py -q "test" -e g      # google
python search.py -q "test" -e b      # bing
python search.py -q "test" -e ddg    # duckduckgo
```

### Browser mode control

```bash
# Headed mode (visible window, good for debugging)
python search.py -q "test query" --no-headless

# Keep the browser open after results (press Enter to close)
python search.py -q "test query" --no-auto-close

# Combine: headed + keep open
python search.py -q "test query" --no-headless --no-auto-close
```

### Result count

```bash
# Only the top 5 results
python search.py -q "python tutorial" -n 5

# Up to 20 results
python search.py -q "python tutorial" -n 20
```

### JSON output

```bash
# JSON output (easy to parse programmatically)
python search.py -q "openai api" -e google --json

# Save to a file
python search.py -q "openai api" --json > results.json
```

Example JSON structure:

```json
[
  {
    "title": "OpenAI API Reference",
    "url": "https://platform.openai.com/docs/api-reference",
    "snippet": "Describes the OpenAI API endpoints, parameters, and response objects."
  },
  ...
]
```

### URL crawling

```bash
# Crawl a page, return clean HTML body (CSS/JS stripped)
python search.py -u https://example.com

# Wait for a specific element before extracting (good for SPAs)
python search.py -u https://spa-site.com --wait-for ".main-content"

# Save the crawl to a file
python search.py -u https://example.com > page.html

# Watch the crawl in a headed browser
python search.py -u https://example.com --no-headless --no-auto-close
```

### Proxy

```bash
# Search over an HTTP proxy
python search.py -q "test" --proxy http://127.0.0.1:7890

# Crawl over a SOCKS5 proxy
python search.py -u https://example.com --proxy socks5://127.0.0.1:1080

# Authenticated proxy
python search.py -q "test" -e google --proxy socks5://user:pass@host:port
```

### Session management

```bash
# Clear saved cookies and session data
python search.py --clear-session

# List all supported search engines
python search.py --list-engines
```

---

## Supported Search Engines

Run `python search.py --list-engines` for the full list.

### Global

| Name | Engine | Notes |
|------|--------|-------|
| `google` / `g` | Google | World's largest search engine |
| `bing` / `b` | Bing | Microsoft search |
| `duckduckgo` / `ddg` | DuckDuckGo | Privacy search |
| `yahoo` | Yahoo Search | |
| `yandex` | Yandex | Russia's largest search engine |
| `ecosia` | Ecosia | Tree-planting charity search engine |
| `startpage` | Startpage | Google-backed private search |
| `brave` | Brave Search | Built by the Brave browser |
| `ask` | Ask.com | Veteran Q&A search |
| `dogpile` | Dogpile | Metasearch |
| `searx` | SearXNG | Open-source self-hosted metasearch |

### China

| Name | Engine | Notes |
|------|--------|-------|
| `baidu` | 百度 Baidu | China's largest engine; returns title, link, snippet |
| `sogou` | 搜狗 Sogou | Tencent-backed; unique WeChat content coverage |
| `360` | 360 Search (so.com) | Qihoo 360 |
| `shenma` | 神马 Shenma | Alibaba mobile search |

### East Asia

| Name | Engine | Notes |
|------|--------|-------|
| `naver` | Naver | Korea's largest search engine |
| `yahoo_jp` | Yahoo Japan | |

### Privacy

| Name | Engine | Notes |
|------|--------|-------|
| `metager` | MetaGer | German non-profit privacy search |
| `swisscows` | Swisscows | Swiss privacy search, family-friendly |

### Russia

| Name | Engine | Notes |
|------|--------|-------|
| `mail` | Mail.ru Search | |

### Field-tested availability matrix (important)

"Supported in code" ≠ "returns results in your network environment". Anti-bot policies change constantly. The table below is a **batch field test on 2026-09-30 from mainland China with a local :7890 proxy** (same queries, `-n 6`) — treat it as a selection hint and **ping each engine yourself before relying on it**:

| Engine | Direct (CN engines) | Via proxy (intl engines) | Notes |
|--------|:---:|:---:|-------|
| `baidu` | ✅ | — | 20+ back-to-back queries trigger session-wide rate limiting (empty results, soft-fail exit 3); rotate engines |
| `sogou` | ✅ | — | Stable in Chinese; unique WeChat content |
| `360` | ✅ | — | Working in Chinese |
| `shenma` | ❌ empty | — | Selectors currently broken |
| `brave` | — | ✅ | Great for English primary sources |
| `google` | — | ✅ | Needs proxy; new-version `goto` wrapper URL resolution fixed |
| `bing` | — | ✅ | Working |
| `duckduckgo` | ❌ empty | ❌ empty | Selectors rotted away; schedulers will skip it as a soft-fail |
| `startpage` / `ecosia` | ❌ empty | ❌ empty | Currently blocked outright |

> Bottom line: the advertised "18+" is **code coverage**; long-term stable availability is about **6 engines** (baidu/sogou/360 + brave/google/bing). Schedulers should parallelize across engines, serialize with rate limiting within one, and retry on exit 3 by switching engines.

---

## URL Crawl Mode

`-u` / `--url` crawls any page and returns cleaned HTML.

**Cleaning removes:**
- All `<style>` tags
- All `<link rel="stylesheet">` external stylesheet references
- All inline `style` attributes
- All `class` attributes
- All `<script>` tags
- All `<noscript>` tags
- Returns only the `<body>` internals, dropping `<head>`

**Good for:**
- Extracting article text for AI processing
- Collecting structure that doesn't depend on styling
- Analyzing page DOM structure
- Handling JS-rendered SPAs with `--wait-for`

```bash
# Crawl and extract after the .article container loads
python search.py -u https://news-site.com/article/123 --wait-for ".article-body"
```

---

## Output Formats

### Text (default)

```
============================================================
  Engine : Google
  Query  : python asyncio tutorial
  Results: 10
============================================================

[1] Python asyncio — Python 3.12 documentation
    URL: https://docs.python.org/3/library/asyncio.html
    asyncio is a library to write concurrent code using the async/await syntax...

[2] AsyncIO in Python: A Complete Walkthrough – Real Python
    URL: https://realpython.com/async-io-python/
    AsyncIO is a concurrent programming design in Python...

...
```

Each result shows: index, title, URL, snippet (displayed up to 200 chars, then truncated — unless `--deep`, which prints the full crawled content).

### JSON (`--json`)

An array of results, each with `title`, `url`, `snippet` fields for downstream processing.

---

## Session Management

Browser session data (cookies, LocalStorage, SessionStorage) is saved automatically to `user_data/storage_state.json` and reloaded on the next run, mimicking continued use of the same browser — which lowers the odds of being flagged as a bot.

- `user_data/` is gitignored and never committed
- If behavior gets weird (empty results, odd redirects), run `--clear-session` to start fresh

---

## Anti-Bot Measures

Injected automatically on every new page:

| Measure | Description |
|---------|-------------|
| Remove `navigator.webdriver` | Forces the flag to `false`, eliminating the primary automation tell |
| Fake browser plugins | Spoofs a realistic Chrome plugin list (PDF Plugin, Native Client, …) |
| Language mimicry | `navigator.languages` set per engine region |
| OS mimicry | `navigator.platform` set to `Win32` |
| Hardware info mimicry | `hardwareConcurrency=8`, `deviceMemory=8` |
| Chrome object injection | Simulates `window.chrome.runtime` and other Chrome-only objects |
| Permissions API patch | Overrides `navigator.permissions.query` to avoid anomalies |
| Canvas fingerprint noise | Tiny random pixel offsets in `toDataURL` |
| WebGL spoofing | Overrides `UNMASKED_VENDOR_WEBGL` / `UNMASKED_RENDERER_WEBGL` |
| Randomized User-Agent | Derived from the real Chromium version at runtime, picked across OS variants |
| Random viewport | Chosen from common resolutions (1920×1080, 1366×768, …) |
| Realistic headers | Full `Sec-Fetch-*` / `Sec-Ch-Ua-*` modern browser header set |
| Human-like delays | Random 0.3–2s waits after page loads, mimicking reading and interaction pacing |
| Session persistence | Reuses cookies and storage like a long-lived browser |
| Automation flags disabled | Launch arg `--disable-blink-features=AutomationControlled` |

---

## CAPTCHA Handling

When searching Google, CAPTCHA is detected at two points:

1. **After page load**: checks whether the URL redirected to `google.com/sorry/`
2. **After waiting for results**: checks the final state after async JS redirects

**Three-layer detection:**

| Layer | Signals |
|-------|---------|
| URL | Current URL contains `google.com/sorry/` or `sorry/index` |
| DOM | `#captcha-form`, `#recaptcha`, `div.g-recaptcha`, reCAPTCHA iframe, or a `/sorry/` form |
| Text | Body contains "unusual traffic", "verify you're a human", etc. |

**Example output when detected:**

```
[CAPTCHA] Google 检测到异常流量并要求验证码，无法继续搜索。
[CAPTCHA] 建议：更换网络/IP，或使用 --no-headless 手动完成验证后重试。
```

Exit code is `2`, distinguishable from:
- `0`: normal exit with results
- `1`: argument/config error
- `2`: CAPTCHA detected
- `3`: query succeeded with 0 results (rate-limit soft-fail, try another engine)

**What to do when hit by CAPTCHA:**

1. Change network path or IP (VPN node switch, mobile hotspot)
2. `--no-headless --no-auto-close` to open a headed browser and solve it manually
3. Switch engines (`bing`, `brave`, …)
4. `--clear-session` and retry

---

## Project Structure

```
serpkit/
├── search.py           # the whole CLI, single file
├── requirements.txt    # Python dependencies
├── .gitignore
├── README.md           # English
├── README.zh-CN.md     # 简体中文
└── user_data/          # browser session data (auto-created, gitignored)
    └── storage_state.json
```

---

## Notes

1. **Network environment**: some engines (Google, DuckDuckGo…) need a proxy from mainland China; Baidu/Sogou/360 may be limited from abroad.
2. **Selector decay**: engines change page structure periodically — if results come back empty, the CSS selectors for that engine likely need updating.
3. **Rate limiting**: hammering one engine can trigger throttling or CAPTCHA; pace your calls.
4. **Compliance**: respect each engine's terms of service; use for legal personal study and research only.
5. **First run**: slightly slow (Playwright init); later runs speed up thanks to session caching.
