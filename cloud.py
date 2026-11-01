# -*- coding: utf-8 -*-
"""词云生成模块：字体查找、形状蒙版、词云渲染。"""

import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw
from wordcloud import WordCloud

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\simkai.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

COLORMAPS = [
    "viridis", "plasma", "inferno", "magma", "cividis",
    "ocean", "gist_earth", "terrain", "Set2", "tab10", "Dark2",
]

SHAPES = ["矩形", "圆形", "星形", "心形"]


def find_chinese_font():
    """查找系统中可用的中文字体，找不到返回 None。"""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def get_font_properties():
    """给 matplotlib 用的中文字体属性（返回 None 表示使用默认）。"""
    from matplotlib import font_manager

    font_path = find_chinese_font()
    if font_path:
        return font_manager.FontProperties(fname=font_path)
    return None


def make_mask(shape, width, height):
    """根据形状生成词云蒙版矩阵，矩形返回 None。"""
    if shape in (None, "", "矩形"):
        return None

    img = Image.new("L", (max(width, 100), max(height, 100)), 0)
    draw = ImageDraw.Draw(img)
    w, h = img.size

    if shape == "圆形":
        margin = 6
        draw.ellipse([margin, margin, w - margin, h - margin], fill=255)

    elif shape == "星形":
        cx, cy = w / 2, h / 2
        outer = min(w, h) / 2 - 6
        inner = outer * 0.42
        points = []
        for i in range(10):
            radius = outer if i % 2 == 0 else inner
            angle = math.pi / 2 + i * math.pi / 5
            points.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
        draw.polygon(points, fill=255)

    elif shape == "心形":
        # 心形参数方程
        cx, cy = w / 2, h / 2 * 0.95
        scale = min(w, h) / 26.0
        points = []
        for i in range(720):
            t = i * math.pi / 360
            x = 16 * (math.sin(t) ** 3)
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            points.append((cx + x * scale, cy + y * scale))
        draw.polygon(points, fill=255)

    return np.array(img)


def generate_wordcloud(
    keywords,
    width=800,
    height=600,
    background_color="white",
    max_words=200,
    colormap="viridis",
    shape="矩形",
    font_path=None,
):
    """根据关键词权重生成词云对象。

    keywords: [(word, weight)]
    """
    if not keywords:
        raise ValueError("关键词列表为空，请先执行关键词提取。")

    freq = {str(w): float(s) for w, s in keywords if w}
    if not freq:
        raise ValueError("关键词列表为空，请先执行关键词提取。")

    font = font_path or find_chinese_font()
    mask = make_mask(shape, width, height)

    transparent = background_color == "transparent"

    kwargs = {
        "font_path": font,
        "background_color": None if transparent else background_color,
        "max_words": max_words,
        "colormap": colormap,
        "prefer_horizontal": 0.85,
        "relative_scaling": 0.5,
        "mode": "RGBA" if transparent else "RGB",
        "scale": 2,
    }

    if mask is not None:
        kwargs["mask"] = mask
    else:
        kwargs["width"] = width
        kwargs["height"] = height

    wc = WordCloud(**kwargs)
    wc.generate_from_frequencies(freq)
    return wc


def random_colormap(exclude=None):
    """随机返回一个配色方案。"""
    pool = [c for c in COLORMAPS if c != exclude]
    return random.choice(pool) if pool else "viridis"
