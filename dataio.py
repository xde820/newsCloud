# -*- coding: utf-8 -*-
"""数据持久化模块：CSV 保存与加载。"""

import csv

FIELDS = ["title", "source", "publish_time", "word_count", "content", "url"]


def save_csv(path, news):
    """把新闻列表保存为 CSV（utf-8-sig 便于 Excel 打开）。"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for item in news:
            writer.writerow({k: item.get(k, "") for k in FIELDS})
    return path


def load_csv(path):
    """从 CSV 加载新闻列表。"""
    out = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            content = row.get("content") or ""
            try:
                word_count = int(row.get("word_count") or 0)
            except ValueError:
                word_count = len(content)
            if not word_count:
                word_count = len(content)
            out.append(
                {
                    "title": row.get("title") or "(无标题)",
                    "source": row.get("source") or "",
                    "publish_time": row.get("publish_time") or "",
                    "word_count": word_count,
                    "content": content,
                    "url": row.get("url") or "",
                }
            )
    return out
