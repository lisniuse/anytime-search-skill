---
name: anytime-search
description: Use a stealth Playwright browser to search 18+ search engines (Google, Bing, Baidu, DuckDuckGo, etc.) or crawl any URL. Invoke when the user asks you to search the web, look something up online, fetch a webpage, or when web search results would help answer a question.
---

# Anytime Search Skill

Stealth browser search and web crawling tool using Playwright. Supports 18+ search engines with anti-bot detection evasion.

## Setup (one-time)

```bash
cd D:/dev/github/anytime-search-skill
pip install -r requirements.txt
playwright install chromium
```

## Search

```bash
python D:/dev/github/anytime-search-skill/search.py -q "<query>" [options]
```

### Key options

| Option | Default | Description |
|--------|---------|-------------|
| `-q` / `--query` | — | Search query (required for search mode) |
| `-e` / `--engine` | `google` | Engine name: `google`/`g`, `bing`/`b`, `baidu`, `duckduckgo`/`ddg`, `yahoo`, `yandex`, `brave`, `sogou`, `360`, `naver`, etc. |
| `-n` / `--num-results` | `10` | Max results to return |
| `--json` | off | Output as JSON array `[{title, url, snippet}]` |
| `--deep` | off | Crawl each result URL and return full page content instead of snippet |
| `--proxy` | — | Proxy URL, e.g. `http://127.0.0.1:7890` or `socks5://user:pass@host:port` |
| `--no-headless` | off | Show browser window (useful for manual CAPTCHA solving) |

### Examples

```bash
# Default Google search
python D:/dev/github/anytime-search-skill/search.py -q "Python asyncio tutorial"

# Use Bing, return 5 results as JSON
python D:/dev/github/anytime-search-skill/search.py -q "latest news" -e bing -n 5 --json

# Search Baidu (Chinese)
python D:/dev/github/anytime-search-skill/search.py -q "Python 异步编程" -e baidu

# Deep search: get full page content for each result
python D:/dev/github/anytime-search-skill/search.py -q "openai api docs" --deep
```

## Crawl a URL

```bash
python D:/dev/github/anytime-search-skill/search.py -u <URL> [--wait-for "<CSS_SELECTOR>"]
```

Returns cleaned HTML body (scripts, styles, images removed). Use `--wait-for` for SPAs.

```bash
# Crawl a page
python D:/dev/github/anytime-search-skill/search.py -u https://example.com

# Wait for dynamic content to load
python D:/dev/github/anytime-search-skill/search.py -u https://spa-site.com --wait-for ".main-content"
```

## Supported engines

**Global:** `google`, `bing`, `duckduckgo`, `yahoo`, `yandex`, `ecosia`, `startpage`, `brave`, `ask`, `dogpile`, `searx`
**China:** `baidu`, `sogou`, `360`, `shenma`
**East Asia:** `naver`, `yahoo_jp`
**Privacy:** `metager`, `swisscows`
**Russia:** `mail`
**Shortcuts:** `g`=google, `b`=bing, `ddg`=duckduckgo

Run `python D:/dev/github/anytime-search-skill/search.py --list-engines` for the full list.

## Output format

**Text (default):**
```
[1] Page Title
    URL: https://...
    Snippet text...
```

**JSON (`--json`):**
```json
[{"title": "...", "url": "https://...", "snippet": "..."}]
```

## CAPTCHA handling

If Google returns a CAPTCHA, the script exits with code `2` and prints suggestions. Try:
1. Switch engine: `-e bing` or `-e duckduckgo`
2. Run with `--no-headless` to manually solve it
3. Run `--clear-session` to reset cookies and retry
