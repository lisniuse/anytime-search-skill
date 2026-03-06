# Anytime Search Skill

基于 [Playwright](https://playwright.dev/python/) 的隐身浏览器搜索工具，支持 18+ 个主流搜索引擎、反爬虫检测规避、网页内容爬取，结果直接输出到控制台。

---

## 目录

- [功能特性](#功能特性)
- [安装](#安装)
- [快速开始](#快速开始)
- [命令行参数](#命令行参数)
- [使用示例](#使用示例)
- [支持的搜索引擎](#支持的搜索引擎)
- [网页爬取模式](#网页爬取模式)
- [输出格式](#输出格式)
- [会话管理](#会话管理)
- [反爬虫机制](#反爬虫机制)
- [验证码处理](#验证码处理)
- [项目结构](#项目结构)
- [注意事项](#注意事项)

---

## 功能特性

- **多搜索引擎**：支持 Google、Bing、百度、DuckDuckGo 等 18+ 个搜索引擎，覆盖全球、中国、东亚、隐私向等多个类别
- **隐身模式**：内置多层反爬虫措施，模拟真实浏览器行为，绕过常见的机器人检测
- **验证码检测**：自动检测 Google 验证码（reCAPTCHA / `/sorry/` 页面），立即退出并提示用户
- **网页爬取**：支持直接爬取任意 URL，返回去除所有 CSS 样式和脚本的纯净 HTML body
- **会话持久化**：Cookie 和 Storage 保存在本地 `user_data/` 目录，跨次运行保持登录状态
- **灵活输出**：支持格式化文本和 JSON 两种输出格式
- **无头/有头**：默认无头运行，可切换为有头模式查看实际浏览过程
- **浏览器保持**：可控制结果获取后是否自动关闭浏览器

---

## 安装

**环境要求：** Python 3.8+

### 1. 克隆项目

```bash
git clone https://github.com/your-username/anytime-search-skill.git
cd anytime-search-skill
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 内容：

```
playwright>=1.42.0
beautifulsoup4>=4.12.0
lxml>=5.1.0
```

### 3. 安装 Playwright 浏览器

```bash
playwright install chromium
```

> 只需安装 Chromium 即可，其他浏览器不是必须的。

---

## 快速开始

```bash
# 使用 Google 搜索（默认）
python search.py -q "Python asyncio 教程"

# 使用百度搜索
python search.py -q "Python 异步编程" -e baidu

# 爬取网页内容
python search.py -u https://example.com
```

---

## 命令行参数

```
python search.py [选项]
```

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--query` | `-q` | — | 搜索关键词 |
| `--engine` | `-e` | `google` | 搜索引擎名称（见下方列表） |
| `--url` | `-u` | — | 直接爬取指定 URL，返回纯净 HTML |
| `--wait-for` | — | — | 爬取 URL 时等待指定 CSS 选择器出现再提取内容 |
| `--num-results` | `-n` | `10` | 最多返回的结果数量 |
| `--no-headless` | — | — | 以有头（可见窗口）模式运行浏览器 |
| `--proxy` | — | — | 代理 URL，支持 HTTP/SOCKS5，如 `http://127.0.0.1:7890` 或 `socks5://user:pass@host:port` |
| `--no-auto-close` | — | — | 获取结果后保持浏览器打开，按 Enter 键才关闭 |
| `--json` | — | — | 以 JSON 格式输出结果 |
| `--list-engines` | — | — | 列出所有支持的搜索引擎并退出 |
| `--clear-session` | — | — | 删除已保存的浏览器会话/Cookie 并退出 |

---

## 使用示例

### 基本搜索

```bash
# Google 搜索（默认无头）
python search.py -q "machine learning tutorial"

# 指定搜索引擎
python search.py -q "今日新闻" -e baidu
python search.py -q "privacy browser" -e duckduckgo
python search.py -q "latest news" -e bing

# 使用简写别名
python search.py -q "test" -e g      # google
python search.py -q "test" -e b      # bing
python search.py -q "test" -e ddg    # duckduckgo
```

### 控制浏览器模式

```bash
# 有头模式（显示浏览器窗口，方便调试）
python search.py -q "test query" --no-headless

# 获取结果后保持浏览器打开（按 Enter 才关闭）
python search.py -q "test query" --no-auto-close

# 组合使用：有头模式 + 保持打开
python search.py -q "test query" --no-headless --no-auto-close
```

### 控制结果数量

```bash
# 只返回前 5 条结果
python search.py -q "python tutorial" -n 5

# 返回最多 20 条结果
python search.py -q "python tutorial" -n 20
```

### JSON 输出

```bash
# 输出 JSON（方便程序解析）
python search.py -q "openai api" -e google --json

# 保存到文件
python search.py -q "openai api" --json > results.json
```

JSON 输出结构示例：

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

### 网页爬取模式

```bash
# 爬取网页，返回去除 CSS/JS 的纯净 HTML body
python search.py -u https://example.com

# 等待特定元素加载后再提取（适用于 SPA 单页应用）
python search.py -u https://spa-site.com --wait-for ".main-content"

# 爬取结果保存到文件
python search.py -u https://example.com > page.html

# 爬取时保持浏览器打开查看
python search.py -u https://example.com --no-headless --no-auto-close
```

### 代理

```bash
# 使用 HTTP 代理搜索
python search.py -q "test" --proxy http://127.0.0.1:7890

# 使用 SOCKS5 代理爬取网页
python search.py -u https://example.com --proxy socks5://127.0.0.1:1080

# 带认证的代理
python search.py -q "test" -e google --proxy socks5://user:pass@host:port
```

### 会话管理

```bash
# 清除已保存的 Cookie 和会话数据
python search.py --clear-session

# 查看所有支持的搜索引擎
python search.py --list-engines
```

---

## 支持的搜索引擎

运行 `python search.py --list-engines` 查看完整列表。

### 全球 (Global)

| 引擎名 | 搜索引擎 | 说明 |
|--------|----------|------|
| `google` / `g` | Google | 全球最大搜索引擎 |
| `bing` / `b` | Bing | 微软搜索引擎 |
| `duckduckgo` / `ddg` | DuckDuckGo | 隐私保护搜索 |
| `yahoo` | Yahoo Search | 雅虎搜索 |
| `yandex` | Yandex | 俄罗斯最大搜索引擎 |
| `ecosia` | Ecosia | 植树公益搜索引擎 |
| `startpage` | Startpage | 基于 Google 的隐私搜索 |
| `brave` | Brave Search | Brave 浏览器自研搜索 |
| `ask` | Ask.com | 老牌问答搜索 |
| `dogpile` | Dogpile | 元搜索引擎 |
| `searx` | SearXNG | 开源自托管元搜索 |

### 中国 (China)

| 引擎名 | 搜索引擎 | 说明 |
|--------|----------|------|
| `baidu` | 百度 | 中国最大搜索引擎，返回标题、链接、摘要 |
| `sogou` | 搜狗 | 腾讯旗下搜索引擎 |
| `360` | 360搜索 (so.com) | 奇虎360搜索 |
| `shenma` | 神马搜索 | 阿里巴巴旗下移动搜索 |

### 东亚 (East Asia)

| 引擎名 | 搜索引擎 | 说明 |
|--------|----------|------|
| `naver` | Naver | 韩国最大搜索引擎 |
| `yahoo_jp` | Yahoo Japan | 日本雅虎搜索 |

### 隐私向 (Privacy)

| 引擎名 | 搜索引擎 | 说明 |
|--------|----------|------|
| `metager` | MetaGer | 德国非营利隐私搜索 |
| `swisscows` | Swisscows | 瑞士隐私搜索，家庭友好 |

### 俄罗斯 (Russia)

| 引擎名 | 搜索引擎 | 说明 |
|--------|----------|------|
| `mail` | Mail.ru Search | 俄罗斯 Mail.ru 搜索 |

---

## 网页爬取模式

使用 `-u` / `--url` 参数可爬取任意网页，返回经过清洗的 HTML 内容：

**清洗内容包括：**
- 移除所有 `<style>` 标签
- 移除所有 `<link rel="stylesheet">` 外部样式表引用
- 移除所有元素的 `style` 内联样式属性
- 移除所有元素的 `class` 属性
- 移除所有 `<script>` 脚本标签
- 移除所有 `<noscript>` 标签
- 只返回 `<body>` 内部内容，去掉 `<head>`

**适用场景：**
- 提取文章正文供 AI 处理
- 采集不依赖样式的结构化数据
- 分析页面 DOM 结构
- 配合 `--wait-for` 处理 JavaScript 渲染的单页应用

```bash
# 爬取并提取 .article 容器加载完毕后的内容
python search.py -u https://news-site.com/article/123 --wait-for ".article-body"
```

---

## 输出格式

### 文本格式（默认）

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

每条结果包含：
- 序号
- 标题
- URL
- 摘要（最长显示 200 字符，超出截断）

### JSON 格式（`--json`）

返回结果数组，每项包含 `title`、`url`、`snippet` 三个字段，方便程序进一步处理。

---

## 会话管理

浏览器会话数据（Cookie、LocalStorage、SessionStorage）自动保存在 `user_data/storage_state.json`，下次运行时自动加载，模拟持续使用同一浏览器的行为，有助于降低被检测为机器人的概率。

- `user_data/` 目录已加入 `.gitignore`，不会提交到版本库
- 如遇到异常行为（如搜索结果不正常、被重定向），可用 `--clear-session` 清除会话重新开始

---

## 反爬虫机制

脚本内置以下反爬虫措施，在每个新页面加载时自动注入：

| 措施 | 说明 |
|------|------|
| 移除 `navigator.webdriver` | 将该标志设为 `false`，消除自动化浏览器的主要特征 |
| 模拟浏览器插件 | 伪造 Chrome PDF Plugin、Native Client 等真实浏览器插件列表 |
| 模拟系统语言 | `navigator.languages` 设为 `['en-US', 'en']` |
| 模拟操作系统 | `navigator.platform` 设为 `Win32` |
| 模拟硬件信息 | CPU 核心数 `hardwareConcurrency=8`，内存 `deviceMemory=8` |
| 注入 Chrome 对象 | 模拟 `window.chrome.runtime` 等 Chrome 专有对象 |
| 权限 API 修复 | 覆盖 `navigator.permissions.query` 避免异常行为 |
| Canvas 指纹噪声 | 在 `toDataURL` 时对像素数据加入随机微小偏移 |
| WebGL 信息伪装 | 覆盖 `UNMASKED_VENDOR_WEBGL` 和 `UNMASKED_RENDERER_WEBGL` |
| 随机 User-Agent | 从 Chrome/Firefox/Safari 多个真实 UA 中随机选取 |
| 随机视口尺寸 | 从常见分辨率中随机选取（1920×1080、1366×768 等） |
| 真实请求头 | 设置完整的 `Sec-Fetch-*`、`Sec-Ch-Ua-*` 等现代浏览器请求头 |
| 人类操作延迟 | 页面加载后随机等待 0.3~2 秒，模拟人工阅读和操作节奏 |
| 会话持久化 | 复用 Cookie 和 Storage，模拟长期使用同一浏览器 |
| 禁用自动化标志 | 启动参数 `--disable-blink-features=AutomationControlled` |

---

## 验证码处理

当使用 Google 搜索时，脚本会在两个时间点自动检测验证码：

1. **页面加载后**：检测 URL 是否跳转至 `google.com/sorry/`
2. **结果等待后**：检测 JS 异步重定向后的最终状态

**三层检测逻辑：**

| 检测层 | 信号 |
|--------|------|
| URL 检测 | 当前 URL 包含 `google.com/sorry/` 或 `sorry/index` |
| DOM 检测 | 页面存在 `#captcha-form`、`#recaptcha`、`div.g-recaptcha`、reCAPTCHA iframe 或 `/sorry/` 表单 |
| 文本检测 | 页面正文包含 "unusual traffic"、"verify you're a human" 等关键词 |

**检测到验证码时的输出示例：**

```
[CAPTCHA] Google 检测到异常流量并要求验证码，无法继续搜索。
[CAPTCHA] 建议：更换网络/IP，或使用 --no-headless 手动完成验证后重试。
```

程序退出码为 `2`，可在脚本中区分：
- `0`：正常退出
- `1`：参数错误
- `2`：检测到验证码

**遇到验证码的解决方案：**

1. 更换网络环境或 IP（切换 VPN 节点、热点等）
2. 使用 `--no-headless --no-auto-close` 打开有头浏览器，手动完成验证后再运行
3. 使用其他搜索引擎（如 `bing`、`duckduckgo`、`brave`）作为替代
4. 使用 `--clear-session` 清除旧会话后重试

---

## 项目结构

```
anytime-search-skill/
├── search.py           # 主脚本
├── requirements.txt    # Python 依赖
├── .gitignore
├── README.md
└── user_data/          # 浏览器会话数据（自动创建，已 gitignore）
    └── storage_state.json
```

---

## 注意事项

1. **网络环境**：部分搜索引擎（如 Google、DuckDuckGo）在中国大陆网络环境下需要代理才能访问；百度、搜狗、360 等在境外网络下可能受限。
2. **选择器时效**：搜索引擎会不定期更改页面结构，如遇结果为空，可能需要更新对应引擎的 CSS 选择器。
3. **频率限制**：频繁请求同一搜索引擎可能触发限流或验证码，建议合理控制调用频率。
4. **法律合规**：请遵守各搜索引擎的服务条款，仅用于合法、个人学习和研究目的。
5. **首次运行**：首次运行速度稍慢（Playwright 初始化），后续运行会因会话缓存加快。
