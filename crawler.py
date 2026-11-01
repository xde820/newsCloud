# -*- coding: utf-8 -*-
"""新闻采集模块：列表页解析 + 多线程文章抓取。"""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

TIMEOUT = 10

# 明显不是正文链接的关键词
BAD_KEYWORDS = (
    "login", "register", "about", "contact", "search", "tag", "category",
    "comment", "download", "video", "photo", "gallery", "help", "faq",
    "sitemap", "rss", "app", "mobile", "mail",
)


def fetch(url, timeout=TIMEOUT):
    """请求网页并返回 HTML 文本，失败返回空字符串。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        encoding = resp.apparent_encoding or "utf-8"
        # 部分中文站点识别不准，回退到常见编码
        if encoding.lower() in ("iso-8859-1", "windows-1252"):
            encoding = "gbk" if "gb" in resp.headers.get("Content-Type", "").lower() else "utf-8"
        resp.encoding = encoding
        return resp.text
    except Exception:
        return ""


def _looks_like_article(url, anchor_text=""):
    """判断链接是否像新闻正文页，返回启发式得分。"""
    parsed = urlparse(url)
    path = parsed.path or "/"
    if not path.endswith((".html", ".htm", ".shtml", ".shtm")) and not re.search(r"/\d", path):
        score = 0
    else:
        score = 2
    low = url.lower()
    if any(bad in low for bad in BAD_KEYWORDS):
        return -1
    # 路径中含日期或长数字 ID，通常是正文
    if re.search(r"/(20\d{2})[/-]?(\d{2})", path):
        score += 3
    if re.search(r"\d{6,}", path):
        score += 2
    # 路径层级较深
    score += min(len([p for p in path.split("/") if p]), 3)
    # 锚文本较长，通常是标题
    if len(anchor_text.strip()) >= 10:
        score += 2
    return score


def extract_article_links(list_url, max_pages=1, log=None):
    """从列表页（含翻页）提取候选正文链接，按得分排序去重。"""
    candidates = {}

    def collect_from_page(page_url):
        html = fetch(page_url)
        if not html:
            if log:
                log(f"访问失败：{page_url}")
            return
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("javascript:", "#", "mailto:")):
                continue
            full = urljoin(page_url, href)
            if urlparse(full).scheme not in ("http", "https"):
                continue
            score = _looks_like_article(full, a.get_text())
            if score <= 0:
                continue
            if full not in candidates or score > candidates[full]:
                candidates[full] = score

    collect_from_page(list_url)

    if max_pages > 1:
        base = list_url.rstrip("/")
        for i in range(2, max_pages + 1):
            for pattern in (f"{base}?page={i}", f"{base}/page/{i}", f"{base}/index_{i}.html"):
                if log:
                    log(f"尝试翻页：{pattern}")
                collect_from_page(pattern)

    ranked = sorted(candidates.items(), key=lambda x: -x[1])
    return [url for url, _ in ranked]


def _clean_title(title, domain=""):
    """清理标题中的站点后缀。"""
    if not title:
        return ""
    title = re.sub(r"\s+", " ", title).strip()
    for sep in ("_", "-", "|", "—"):
        if sep in title:
            parts = [p.strip() for p in title.split(sep) if p.strip()]
            if parts:
                title = parts[0]
                break
    return title.strip()


def _extract_time(soup, text):
    """从 meta 或正文中抽取发布时间。"""
    for attr, key in (
        ("property", "article:published_time"),
        ("name", "publishdate"),
        ("name", "pubdate"),
        ("itemprop", "datePublished"),
    ):
        tag = soup.find("meta", attrs={attr: key})
        if tag and tag.get("content"):
            return tag["content"][:19]
    patterns = [
        r"20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?",
        r"20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}",
    ]
    for p in patterns:
        m = re.search(p, text or "")
        if m:
            return m.group(0).replace("年", "-").replace("月", "-").replace("日", "")
    return ""


def _extract_source(soup, domain=""):
    """抽取来源。"""
    for attr, key in (("name", "source"), ("name", "author"), ("property", "article:author")):
        tag = soup.find("meta", attrs={attr: key})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return domain or ""


def fetch_article(url):
    """抓取单篇新闻，返回 dict 或 None。"""
    html = fetch(url)
    if not html or len(html) < 200:
        return None
    soup = BeautifulSoup(html, "lxml")

    domain = urlparse(url).netloc

    # 标题
    title = ""
    if soup.title and soup.title.string:
        title = _clean_title(soup.title.string)
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = _clean_title(h1.get_text())

    # 正文：收集较长的段落
    paragraphs = []
    for p in soup.find_all("p"):
        t = p.get_text(strip=True)
        if len(t) >= 15:
            paragraphs.append(t)
    content = "\n".join(paragraphs)
    if len(content) < 60:
        return None

    publish_time = _extract_time(soup, content[:2000])
    source = _extract_source(soup, domain)

    return {
        "title": title or "(无标题)",
        "source": source,
        "publish_time": publish_time,
        "word_count": len(content),
        "content": content,
        "url": url,
    }


def collect(list_url, max_pages=1, max_articles=30, log=None, should_stop=None, workers=5):
    """执行采集，返回新闻列表。

    log:          回调函数，用于输出进度日志
    should_stop: 回调函数，返回 True 时中止采集
    """
    if log:
        log(f"开始采集：{list_url}（最多 {max_pages} 页）")

    links = extract_article_links(list_url, max_pages=max_pages, log=log)
    if not links:
        if log:
            log("未解析到任何正文链接，请检查 URL 或尝试加载示例数据。")
        return []

    if log:
        log(f"解析到 {len(links)} 条候选链接，开始抓取正文…")

    targets = links[:max_articles]
    items = []
    seen = set()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_article, url): url for url in targets}
        for future in as_completed(futures):
            if should_stop and should_stop():
                if log:
                    log("已停止采集。")
                break
            try:
                item = future.result()
            except Exception as exc:  # noqa: BLE001
                if log:
                    log(f"抓取异常：{exc}")
                continue
            if not item or item["url"] in seen:
                continue
            seen.add(item["url"])
            items.append(item)
            if log:
                log(f"已采集：{item['title'][:26]}（{item['word_count']} 字）")
            time.sleep(0.02)

    items.sort(key=lambda x: x.get("publish_time", ""), reverse=True)
    if log:
        log(f"采集完成，共获取 {len(items)} 条新闻。")
    return items
