#!/usr/bin/env python3
"""
Anytime Search Skill - Stealth browser search via Playwright
Usage:
  python search.py -q "search query"
  python search.py -q "search query" -e bing
  python search.py -u https://example.com
  python search.py --list-engines
"""

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Tuple

try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser
except ImportError:
    print("[ERROR] playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup, Comment, Tag, NavigableString
except ImportError:
    print("[ERROR] beautifulsoup4 not installed. Run: pip install beautifulsoup4 lxml")
    sys.exit(1)

# ─────────────────────────── Paths ────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
USER_DATA_DIR = SCRIPT_DIR / "user_data"
USER_DATA_DIR.mkdir(exist_ok=True)

# ─────────────────────── Search Engines ───────────────────────
ENGINES: Dict[str, Dict] = {
    # ── Global ──
    "google": {
        "name": "Google",
        "search_url": "https://www.google.com/search?q={query}&hl=en",
        "input_selector": 'textarea[name="q"], input[name="q"]',
        "result_containers": ["#search .g", "#rso .g", "div[data-hveid]"],
        "title_sel": "h3",
        "link_sel": "a[href]",
        "snippet_sel": [".VwiC3b", ".s3v9rd", ".IsZvec", "[data-sncf]", ".st"],
        "wait_for": "#search, #rso",
    },
    "bing": {
        "name": "Bing",
        "search_url": "https://www.bing.com/search?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": ["#b_results .b_algo"],
        "title_sel": "h2",
        "link_sel": "h2 a",
        "snippet_sel": [".b_caption p", ".b_algoSlug"],
        "wait_for": "#b_results",
    },
    "duckduckgo": {
        "name": "DuckDuckGo",
        "search_url": "https://duckduckgo.com/?q={query}&kl=us-en",
        "input_selector": 'input[name="q"]',
        "result_containers": ['article[data-testid="result"]'],
        "title_sel": "a[data-testid='result-title-a']",
        "link_sel": "a[data-testid='result-title-a']",   # href 直接是真实 URL
        "snippet_sel": [],          # class 全为动态 hash，走 snippet_nav 提取
        "snippet_nav": "title_h2_parent_next_sibling",   # h2 的父 div 的 next sibling div
        "wait_for": 'article[data-testid="result"]',
    },
    "yahoo": {
        "name": "Yahoo Search",
        "search_url": "https://search.yahoo.com/search?p={query}",
        "input_selector": 'input[name="p"]',
        "result_containers": [".algo"],
        "title_sel": "h3.title",
        "link_sel": "a[href]",          # 部分结果为 r.search.yahoo.com 跳转，在 extract_results 里解码
        "snippet_sel": ["div.compText p"],
        "wait_for": ".algo",
    },
    "yandex": {
        "name": "Yandex",
        "search_url": "https://yandex.com/search/?text={query}",
        "input_selector": 'input[name="text"]',
        "result_containers": ["li.serp-item"],
        "title_sel": "a.OrganicTitle-Link",
        "link_sel": "a.OrganicTitle-Link",  # href 直接是真实 URL
        "snippet_sel": ["span.OrganicTextContentSpan", ".organic__text"],
        "wait_for": "li.serp-item",
    },
    "ecosia": {
        "name": "Ecosia",
        "search_url": "https://www.ecosia.org/search?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": ["article.result"],
        "title_sel": "a.result__link",
        "link_sel": "a.result__link",   # href 直接是真实 URL
        "snippet_sel": ["p.web-result__description"],
        "wait_for": "article.result",
    },
    "startpage": {
        "name": "Startpage",
        "search_url": "https://www.startpage.com/search?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": [".result"],
        "title_sel": "a.result-title",
        "link_sel": "a.result-title",   # href 直接是真实 URL
        "snippet_sel": ["p.description"],
        "wait_for": ".result",
    },
    "brave": {
        "name": "Brave Search",
        "search_url": "https://search.brave.com/search?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": ['div.snippet[data-type="web"]'],
        "title_sel": "div.title.search-snippet-title",
        "link_sel": "a.l1",            # href 直接是真实 URL
        "snippet_sel": ["div.generic-snippet div.content", "div.content.desktop-default-regular"],
        "wait_for": 'div.snippet[data-type="web"]',
    },
    "ask": {
        "name": "Ask.com",
        "search_url": "https://www.ask.com/web?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": [".result"],
        "title_sel": "a.result-title-link",
        "link_sel": "a.result-title-link",  # href 直接是真实 URL
        "snippet_sel": ["p.result-abstract"],
        "wait_for": ".result",
    },
    "dogpile": {
        "name": "Dogpile",
        "search_url": "https://www.dogpile.com/serp?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": [".web-bing__result"],
        "title_sel": "a.web-bing__title",
        "link_sel": "a.web-bing__title",
        "snippet_sel": [".web-bing__description"],
        "wait_for": ".resultlist",
    },
    "searx": {
        "name": "SearXNG (searx.be)",
        "search_url": "https://searx.be/search?q={query}&format=html",
        "input_selector": 'input[name="q"]',
        "result_containers": [".result"],
        "title_sel": "h3",
        "link_sel": "h3 a",
        "snippet_sel": [".content"],
        "wait_for": "#results",
    },
    # ── China ──
    "baidu": {
        "name": "Baidu",
        "search_url": "https://www.baidu.com/s?wd={query}",
        "input_selector": 'input[name="wd"], #kw',
        "result_containers": ["#content_left .result", ".c-container"],
        "title_sel": "h3",
        "link_sel": "h3 a",
        "snippet_sel": ['[class*="summary-text_"]', ".c-abstract", ".c-span9"],
        "wait_for": "#content_left",
    },
    "sogou": {
        "name": "Sogou",
        "search_url": "https://www.sogou.com/web?query={query}",
        "input_selector": 'input[name="query"], #query',
        "result_containers": [".vrwrap"],
        "title_sel": "h3.vr-title",
        "link_sel": "h3.vr-title a",
        "snippet_sel": ["div.fz-mid.space-txt", "p.star-wiki"],
        "wait_for": ".vrwrap",
        "base_url": "https://www.sogou.com",  # for relative /link?url= hrefs
    },
    "360": {
        "name": "360 Search (so.com)",
        "search_url": "https://www.so.com/s?q={query}",
        "input_selector": 'input[name="q"], #input',
        # 只匹配普通结果项，排除广告/推荐/AI卡片等混入项
        "result_containers": ["ul.result > li.res-list"],
        "title_sel": "h3.res-title a",
        "link_sel": "h3.res-title a",
        "link_attr": "data-mdurl",   # 真实 URL 在 data-mdurl，href 是 360 跳转链接
        "snippet_sel": [".res-list-summary", ".res-desc"],
        "wait_for": "ul.result",
    },
    "shenma": {
        "name": "Shenma (sou.com)",
        "search_url": "https://m.sm.cn/s?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": [".result-item"],
        "title_sel": "h3",
        "link_sel": "a",
        "snippet_sel": [".abstract"],
        "wait_for": ".results",
    },
    # ── Russia / Eastern Europe ──
    "mail": {
        "name": "Mail.ru Search",
        "search_url": "https://go.mail.ru/search?q={query}",
        "input_selector": 'input[name="q"]',
        "result_containers": [".result__body"],
        "title_sel": "h3",
        "link_sel": "a",
        "snippet_sel": [".result__annotation"],
        "wait_for": ".results",
    },
    # ── Korea / Japan ──
    "naver": {
        "name": "Naver",
        "search_url": "https://search.naver.com/search.naver?query={query}",
        "input_selector": 'input[name="query"]',
        "result_containers": [".total_wrap", ".g_highlight"],
        "title_sel": "a.total_tit",
        "link_sel": "a.total_tit",
        "snippet_sel": [".dsc_txt_wrap"],
        "wait_for": "#main_pack",
    },
    "yahoo_jp": {
        "name": "Yahoo Japan",
        "search_url": "https://search.yahoo.co.jp/search?p={query}",
        "input_selector": 'input[name="p"]',
        "result_containers": [".w"],
        "title_sel": "h3",
        "link_sel": "h3 a",
        "snippet_sel": [".hd"],
        "wait_for": "#contents",
    },
    # ── Privacy-focused ──
    "metager": {
        "name": "MetaGer",
        "search_url": "https://metager.org/meta/meta.ger3?eingabe={query}",
        "input_selector": 'input[name="eingabe"]',
        "result_containers": [".result"],
        "title_sel": "h2",
        "link_sel": "a.result-link",
        "snippet_sel": [".result-description"],
        "wait_for": ".results",
    },
    "swisscows": {
        "name": "Swisscows",
        "search_url": "https://swisscows.com/en/web?query={query}",
        "input_selector": 'input[name="query"]',
        "result_containers": [".web-results article"],
        "title_sel": "h2",
        "link_sel": "a",
        "snippet_sel": [".description"],
        "wait_for": ".web-results",
    },
}

# Aliases
ENGINES["ddg"] = ENGINES["duckduckgo"]
ENGINES["g"] = ENGINES["google"]
ENGINES["b"] = ENGINES["bing"]

# ──────────────────────── Stealth JS ──────────────────────────
STEALTH_INIT_SCRIPT = """
() => {
    // Remove webdriver flag
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true
    });

    // Mock plugins
    const makePluginArray = () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ];
        const arr = plugins.map(p => {
            const plugin = Object.create(Plugin.prototype);
            Object.defineProperty(plugin, 'name', { get: () => p.name });
            Object.defineProperty(plugin, 'filename', { get: () => p.filename });
            Object.defineProperty(plugin, 'description', { get: () => p.description });
            Object.defineProperty(plugin, 'length', { get: () => 1 });
            return plugin;
        });
        arr.__proto__ = PluginArray.prototype;
        return arr;
    };
    try {
        Object.defineProperty(navigator, 'plugins', { get: makePluginArray });
    } catch(e) {}

    // Mock languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });

    // Mock platform
    try {
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
        });
    } catch(e) {}

    // Mock hardwareConcurrency
    try {
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
        });
    } catch(e) {}

    // Mock deviceMemory
    try {
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
        });
    } catch(e) {}

    // Chrome runtime mock
    if (!window.chrome) {
        window.chrome = {
            app: { isInstalled: false, InstallState: {}, RunningState: {} },
            runtime: {
                PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' },
                PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                RequestUpdateCheckStatus: { THROTTLED: 'throttled', NO_UPDATE: 'no_update', UPDATE_AVAILABLE: 'update_available' },
                OnInstalledReason: { INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update' },
                OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
                connect: () => {},
                sendMessage: () => {},
            },
            csi: () => {},
            loadTimes: () => ({
                commitLoadTime: 0,
                connectionInfo: 'h2',
                finishDocumentLoadTime: 0,
                finishLoadTime: 0,
                firstPaintAfterLoadTime: 0,
                firstPaintTime: 0,
                navigationType: 'Other',
                npnNegotiatedProtocol: 'h2',
                requestTime: Date.now() / 1000,
                startLoadTime: 0,
                wasAlternateProtocolAvailable: false,
                wasFetchedViaSpdy: true,
                wasNpnNegotiated: true,
            }),
        };
    }

    // Permissions override
    const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
    if (originalQuery) {
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);
    }

    // Canvas fingerprint noise
    const toBlob = HTMLCanvasElement.prototype.toBlob;
    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
    const getImageData = CanvasRenderingContext2D.prototype.getImageData;
    const noisify = (canvas, ctx) => {
        const shift = { r: Math.floor(Math.random()*10)-5, g: Math.floor(Math.random()*10)-5, b: Math.floor(Math.random()*10)-5, a: 0 };
        const width = canvas.width, height = canvas.height;
        if (width && height) {
            const imageData = ctx.getImageData(0, 0, width, height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] = imageData.data[i] + shift.r;
                imageData.data[i+1] = imageData.data[i+1] + shift.g;
                imageData.data[i+2] = imageData.data[i+2] + shift.b;
            }
            ctx.putImageData(imageData, 0, 0);
        }
    };
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        noisify(this, this.getContext('2d'));
        return toDataURL.apply(this, arguments);
    };

    // WebGL vendor/renderer override
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };
    try {
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter2.call(this, parameter);
        };
    } catch(e) {}
}
"""

# ──────────────────────── User Agents ─────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 800},
]


# ──────────────────────── HTML Cleaner ────────────────────────

# 直接整体移除的标签（非展示性）
_REMOVE_TAGS = {
    "script", "noscript", "style", "link", "meta",
    "img", "picture", "source", "svg", "canvas",
    "video", "audio", "track",
    "iframe", "frame", "frameset", "embed", "object", "param",
    "map", "area",
    "template", "slot", "shadow",
    "figure", "figcaption",  # 通常包裹图片
    "input", "button", "select", "option", "optgroup",
    "textarea", "form", "label", "fieldset", "legend",
    "dialog", "menu",
}

# 保留白名单属性（去掉一切其他属性，包括自定义属性）
_KEEP_ATTRS: Dict[str, set] = {
    "a":         set(),
    "td":        {"colspan", "rowspan"},
    "th":        {"colspan", "rowspan", "scope"},
    "ol":        {"start", "type"},
    "li":        {"value"},
    "blockquote":{"cite"},
    "q":         {"cite"},
    "time":      {"datetime"},
    "data":      {"value"},
    "ins":       {"datetime"},
    "del":       {"datetime"},
}


def _is_empty_tag(tag: Tag) -> bool:
    """判断标签是否无有效内容（无文本、无有意义的子元素）。"""
    return not tag.get_text(strip=True)



def _remove_empty_tags(soup) -> None:
    """
    循环移除无内容的标签，直到没有可移除的为止。
    每轮自底向上处理，确保父节点在子节点清空后也能被移除。
    void 元素（br/hr/wbr）本身无子节点但有展示意义，保留。
    """
    VOID_ELEMENTS = {"br", "hr", "wbr"}
    changed = True
    while changed:
        changed = False
        for tag in soup.find_all(True):
            if tag.name in VOID_ELEMENTS:
                continue
            if _is_empty_tag(tag):
                tag.decompose()
                changed = True


def clean_html(html: str) -> str:
    """
    深度清洗 HTML，只保留纯展示文本结构：
    - 移除所有非展示标签（script/style/img/svg/iframe 等）
    - 移除所有元素的全部属性（仅保留少量语义必要属性，如 a[href]）
    - 移除无效 href（javascript:、#、空值）
    - 递归移除内容为空的标签
    - 只返回 <body> 内容
    """
    soup = BeautifulSoup(html, "lxml")

    # 1. 整体移除非展示标签（含其子树）
    for tag_name in _REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 2. 遍历所有剩余元素，清空属性（保留白名单）
    for tag in soup.find_all(True):
        allowed = _KEEP_ATTRS.get(tag.name, set())
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in allowed}

    # 3. 移除 HTML 注释
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 4. 递归移除空标签（自底向上，直到稳定）
    _remove_empty_tags(soup)

    # 4. 只返回 body 内容
    body = soup.find("body")
    raw = str(body) if body else str(soup)

    # 5. 压缩 HTML：合并连续空白/换行为单个空格，去掉标签间多余空白
    compressed = re.sub(r'>\s+<', '><', raw)       # 标签之间的空白
    compressed = re.sub(r'\s{2,}', ' ', compressed) # 标签内连续空白
    return compressed.strip()


# ─────────────────────── Result Parsing ───────────────────────
def extract_results(page: Page, engine_cfg: Dict, max_results: int = 10) -> List[Dict]:
    """Extract search results from the current page."""
    results = []
    html = page.content()
    soup = BeautifulSoup(html, "lxml")

    containers = []
    for sel in engine_cfg["result_containers"]:
        found = soup.select(sel)
        if found:
            containers = found
            break

    for container in containers[:max_results]:
        title = ""
        url = ""
        snippet = ""

        # Title
        title_el = container.select_one(engine_cfg["title_sel"])
        if title_el:
            title = title_el.get_text(strip=True)

        # URL
        link_sel = engine_cfg["link_sel"]
        link_attr = engine_cfg.get("link_attr", "href")  # 默认取 href，可配置为 data-mdurl 等
        link_el = container.select_one(link_sel)
        if link_el:
            href = link_el.get(link_attr) or link_el.get("href", "")
            if href and not href.startswith("#"):
                # Clean Google redirect URLs
                if "google.com/url?" in href:
                    m = re.search(r"[?&]url=([^&]+)", href)
                    if m:
                        href = urllib.parse.unquote(m.group(1))
                elif href.startswith("/url?"):
                    m = re.search(r"[?&]url=([^&]+)", href)
                    if m:
                        href = urllib.parse.unquote(m.group(1))
                # Clean Yahoo redirect URLs (r.search.yahoo.com/.../RU=<encoded-url>/...)
                elif "r.search.yahoo.com" in href:
                    m = re.search(r"[/;]RU=([^/;]+)", href)
                    if m:
                        href = urllib.parse.unquote(m.group(1))
                # Resolve relative URLs (e.g. Sogou /link?url=...)
                elif href.startswith("/") and engine_cfg.get("base_url"):
                    href = engine_cfg["base_url"] + href
                url = href

        # Snippet — 优先使用 snippet_nav 导航，fallback 到 snippet_sel
        snippet_nav = engine_cfg.get("snippet_nav", "")
        if snippet_nav == "title_h2_parent_next_sibling":
            # DuckDuckGo: a[data-testid=result-title-a] -> h2 -> div(title wrapper) -> next div = snippet
            title_a_el = container.select_one(engine_cfg["title_sel"])
            if title_a_el:
                h2 = title_a_el.find_parent("h2")
                title_wrapper = h2.find_parent("div") if h2 else None
                snip_div = title_wrapper.find_next_sibling("div") if title_wrapper else None
                if snip_div:
                    snippet = snip_div.get_text(strip=True)
        if not snippet:
            for snip_sel in engine_cfg["snippet_sel"]:
                snip_el = container.select_one(snip_sel)
                if snip_el:
                    snippet = snip_el.get_text(strip=True)
                    break

        if title or url:
            results.append({"title": title, "url": url, "snippet": snippet})

    return results


# ───────────────────── Browser Setup ──────────────────────────
def _parse_proxy(proxy_url: str) -> dict:
    """
    将代理 URL 解析为 Playwright proxy dict。
    支持格式：
      http://host:port
      http://user:pass@host:port
      socks5://host:port
      socks5://user:pass@host:port
    """
    parsed = urllib.parse.urlparse(proxy_url)
    scheme = parsed.scheme or "http"
    host = parsed.hostname or ""
    port = parsed.port
    server = f"{scheme}://{host}" + (f":{port}" if port else "")
    proxy: dict = {"server": server}
    if parsed.username:
        proxy["username"] = urllib.parse.unquote(parsed.username)
    if parsed.password:
        proxy["password"] = urllib.parse.unquote(parsed.password)
    return proxy


def create_context(
    playwright_instance,
    headless: bool,
    proxy_url: Optional[str] = None,
) -> Tuple[Browser, BrowserContext]:
    ua = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)

    browser = playwright_instance.chromium.launch(
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-dev-shm-usage",
            "--lang=en-US,en",
        ],
    )

    ctx_kwargs: dict = dict(
        user_agent=ua,
        viewport=viewport,
        locale="en-US",
        timezone_id="America/New_York",
        permissions=[],
        java_script_enabled=True,
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        storage_state=_load_storage_state(),
    )

    if proxy_url:
        ctx_kwargs["proxy"] = _parse_proxy(proxy_url)

    context = browser.new_context(**ctx_kwargs)

    # Inject stealth script on every new page
    context.add_init_script(STEALTH_INIT_SCRIPT)

    return browser, context


def _storage_state_path() -> Path:
    return USER_DATA_DIR / "storage_state.json"


def _load_storage_state() -> Optional[dict]:
    p = _storage_state_path()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_storage_state(context: BrowserContext) -> None:
    try:
        state = context.storage_state()
        with open(_storage_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def human_delay(min_ms: int = 300, max_ms: int = 1200) -> None:
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


# ─────────────────── CAPTCHA Detection ───────────────────────
def check_google_captcha(page: Page) -> None:
    """Detect Google CAPTCHA / unusual traffic page and exit immediately if found."""
    current_url = page.url

    # URL-based detection: Google redirects to /sorry/ on CAPTCHA
    if "google.com/sorry/" in current_url or "sorry/index" in current_url:
        print("[CAPTCHA] Google 检测到异常流量并要求验证码，无法继续搜索。", file=sys.stderr)
        print("[CAPTCHA] 建议：更换网络/IP，或使用 --no-headless 手动完成验证后重试。", file=sys.stderr)
        sys.exit(2)

    # DOM-based detection
    captcha_signals = [
        "#captcha-form",           # /sorry/ 页面表单
        "#recaptcha",              # reCAPTCHA 容器
        "iframe[src*='recaptcha']",# reCAPTCHA iframe
        "iframe[src*='google.com/recaptcha']",
        "div.g-recaptcha",
        "form[action*='/sorry/']",
    ]
    for sel in captcha_signals:
        try:
            el = page.query_selector(sel)
            if el:
                print("[CAPTCHA] Google 要求完成验证码，无法继续搜索。", file=sys.stderr)
                print("[CAPTCHA] 建议：更换网络/IP，或使用 --no-headless 手动完成验证后重试。", file=sys.stderr)
                sys.exit(2)
        except Exception:
            pass

    # Text-based detection (page body)
    try:
        body_text = page.inner_text("body") or ""
        captcha_phrases = [
            "unusual traffic from your computer",
            "systems have detected unusual traffic",
            "please solve this CAPTCHA",
            "verify you're a human",
        ]
        lower = body_text.lower()
        for phrase in captcha_phrases:
            if phrase in lower:
                print("[CAPTCHA] Google 页面包含验证码提示，无法继续搜索。", file=sys.stderr)
                print("[CAPTCHA] 建议：更换网络/IP，或使用 --no-headless 手动完成验证后重试。", file=sys.stderr)
                sys.exit(2)
    except Exception:
        pass


# ──────────────── Deep Crawl (reuse page object) ──────────────
def _crawl_url_with_page(page: Page, url: str) -> str:
    """复用已有 page 对象爬取一个 URL，返回清洗后的压缩 HTML。"""
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    human_delay(800, 1800)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    human_delay(300, 700)
    return clean_html(page.content())


# ───────────────────── Search Function ────────────────────────
def do_search(
    query: str,
    engine_key: str = "google",
    headless: bool = True,
    max_results: int = 10,
    output_format: str = "text",
    auto_close: bool = True,
    deep: bool = False,
    proxy_url: Optional[str] = None,
) -> List[Dict]:
    engine_cfg = ENGINES.get(engine_key.lower())
    if not engine_cfg:
        print(f"[ERROR] Unknown engine '{engine_key}'. Use --list-engines to see options.")
        sys.exit(1)

    encoded = urllib.parse.quote_plus(query)
    url = engine_cfg["search_url"].format(query=encoded)

    with sync_playwright() as pw:
        browser, context = create_context(pw, headless, proxy_url=proxy_url)
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(800, 2000)

            # Google CAPTCHA check (URL may have already changed to /sorry/)
            if engine_key.lower() in ("google", "g"):
                check_google_captcha(page)

            # Wait for results
            wait_sel = engine_cfg.get("wait_for", "body")
            try:
                page.wait_for_selector(wait_sel, timeout=15000)
            except Exception:
                pass

            # Second check after page settles (in case redirect happened after JS)
            if engine_key.lower() in ("google", "g"):
                check_google_captcha(page)

            human_delay(500, 1000)
            results = extract_results(page, engine_cfg, max_results)

            # Deep search: crawl each result URL and replace snippet with page content
            if deep:
                for i, r in enumerate(results):
                    if not r.get("url"):
                        continue
                    print(
                        f"[DEEP] ({i+1}/{len(results)}) Crawling {r['url']} ...",
                        file=sys.stderr,
                    )
                    try:
                        r["snippet"] = _crawl_url_with_page(page, r["url"])
                    except Exception as e:
                        print(f"[DEEP] 爬取失败: {e}", file=sys.stderr)
                        r["snippet"] = ""

            if not auto_close:
                print("[INFO] 浏览器保持打开，按 Enter 键关闭...", file=sys.stderr)
                input()

        finally:
            _save_storage_state(context)
            context.close()
            browser.close()

    return results


# ─────────────────────── URL Crawl ────────────────────────────
def do_crawl(
    url: str,
    headless: bool = True,
    wait_for: Optional[str] = None,
    auto_close: bool = True,
    proxy_url: Optional[str] = None,
) -> str:
    with sync_playwright() as pw:
        browser, context = create_context(pw, headless, proxy_url=proxy_url)
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1000, 2500)

            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10000)
                except Exception:
                    pass

            # Scroll to trigger lazy-load
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            human_delay(500, 1000)

            html = page.content()

            if not auto_close:
                print("[INFO] 浏览器保持打开，按 Enter 键关闭...", file=sys.stderr)
                input()

        finally:
            _save_storage_state(context)
            context.close()
            browser.close()

    return clean_html(html)


# ──────────────────────── Output ──────────────────────────────
def print_results(results: List[Dict], engine_name: str, query: str, fmt: str = "text", deep: bool = False) -> None:
    if fmt == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print(f"\n{'='*60}")
    print(f"  Engine : {engine_name}")
    print(f"  Query  : {query}")
    print(f"  Results: {len(results)}")
    if deep:
        print(f"  Mode   : deep (full page content)")
    print(f"{'='*60}\n")

    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['title']}")
        if r["url"]:
            print(f"    URL: {r['url']}")
        if r["snippet"]:
            if deep:
                # 深度模式：完整输出爬取内容，不截断
                print(r["snippet"])
            else:
                snippet = r["snippet"]
                if len(snippet) > 200:
                    snippet = snippet[:197] + "..."
                print(f"    {snippet}")
        print()


# ──────────────────────── CLI ─────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Stealth browser search via Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python search.py -q "python asyncio tutorial"
  python search.py -q "weather today" -e bing
  python search.py -q "最新新闻" -e baidu --no-headless
  python search.py -u https://example.com
  python search.py --list-engines
  python search.py -q "news" -e google --json
        """,
    )

    p.add_argument("-q", "--query", help="Search query")
    p.add_argument(
        "-e",
        "--engine",
        default="google",
        metavar="ENGINE",
        help="Search engine to use (default: google)",
    )
    p.add_argument("-u", "--url", help="Crawl a specific URL and return clean HTML body")
    p.add_argument(
        "--wait-for",
        metavar="CSS_SELECTOR",
        help="Wait for this CSS selector before extracting content (URL crawl)",
    )
    p.add_argument(
        "-n",
        "--num-results",
        type=int,
        default=10,
        metavar="N",
        help="Max results to return (default: 10)",
    )
    p.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        default=True,
        help="Run browser in headed (visible) mode",
    )
    p.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Output results as JSON",
    )
    p.add_argument(
        "--list-engines",
        action="store_true",
        help="List all supported search engines and exit",
    )
    p.add_argument(
        "--proxy",
        metavar="URL",
        default=None,
        help="Proxy URL, e.g. http://127.0.0.1:7890 or socks5://user:pass@host:port",
    )
    p.add_argument(
        "--deep",
        action="store_true",
        default=False,
        help="Deep search: crawl each result URL and replace snippet with full page content",
    )
    p.add_argument(
        "--no-auto-close",
        dest="auto_close",
        action="store_false",
        default=True,
        help="Keep browser open after results are retrieved (press Enter to close)",
    )
    p.add_argument(
        "--clear-session",
        action="store_true",
        help="Delete saved browser session/cookies and exit",
    )
    return p


def list_engines() -> None:
    aliases = {"ddg", "g", "b"}
    print("\nSupported search engines:\n")
    seen = set()
    # Group by region
    groups = {
        "Global": ["google", "bing", "duckduckgo", "yahoo", "yandex", "ecosia", "startpage", "brave", "ask", "dogpile", "searx"],
        "China":  ["baidu", "sogou", "360", "shenma"],
        "East Asia": ["naver", "yahoo_jp"],
        "Privacy": ["metager", "swisscows"],
        "Russia": ["mail"],
    }
    for region, keys in groups.items():
        print(f"  [{region}]")
        for k in keys:
            if k in ENGINES and k not in seen:
                seen.add(k)
                print(f"    {k:<14} {ENGINES[k]['name']}")
        print()
    print("  Shortcuts: g=google, b=bing, ddg=duckduckgo\n")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_engines:
        list_engines()
        return

    if args.clear_session:
        sp = _storage_state_path()
        if sp.exists():
            sp.unlink()
            print("[INFO] Session cleared.")
        else:
            print("[INFO] No saved session found.")
        return

    if args.url:
        # URL crawl mode
        print(f"[INFO] Crawling: {args.url}", file=sys.stderr)
        html = do_crawl(args.url, headless=args.headless, wait_for=args.wait_for, auto_close=args.auto_close, proxy_url=args.proxy)
        print(html)
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    engine_key = args.engine.lower()
    engine_cfg = ENGINES.get(engine_key)
    if not engine_cfg:
        print(f"[ERROR] Unknown engine '{args.engine}'. Use --list-engines to see options.")
        sys.exit(1)

    print(f"[INFO] Searching '{args.query}' on {engine_cfg['name']} ...", file=sys.stderr)

    results = do_search(
        query=args.query,
        engine_key=engine_key,
        headless=args.headless,
        max_results=args.num_results,
        auto_close=args.auto_close,
        deep=args.deep,
        proxy_url=args.proxy,
    )

    fmt = "json" if args.output_json else "text"
    print_results(results, engine_cfg["name"], args.query, fmt=fmt, deep=args.deep)


if __name__ == "__main__":
    main()
