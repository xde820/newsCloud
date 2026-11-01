# -*- coding: utf-8 -*-
"""关键词提取模块：jieba 分词 + TF-IDF + TextRank + 组合加权算法。"""

import math
import re

import jieba

jieba.setLogLevel(60)  # 关闭 jieba 的构建日志输出

# 常用中文停用词
STOPWORDS = set(
    """
    的 了 在 是 和 与 及 或 等 也 都 就 而 且 但 但 因为 所以 如果 可以 已经 通过 对于 关于
    一个 一种 一些 我们 你们 他们 她们 它们 这个 那个 这些 那些 什么 怎么 如何 为 以 从 到 把 被 让 使
    有 无 不 没有 是 非 其 之 其 并 还 又 再 更 很 太 最 也 已 会 能 要 将 正 在 中 上 下 里 后 前
    表示 认为 认为 介绍 显示 数据 表示 目前 当前 未来 未来 通过 实现 成为 提高 提升 加快 推进 构建
    不断 持续 稳步 明显 有效 显著 进一步 同时 此外 其中 随着 根据 相关 有关 方面 领域 环节 阶段
    本月 近日 今年 去年 今日 上午 下午 记者 报道 消息 获悉 了解到 表示 指出 强调 认为
    第一 第二 第三 之一 其中 部分 全部 整体 整个 各类 各种 多个 大量 不少 许多 众多
    """.split()
)

# 允许的词性（保留名词、动词、形容词、专有名词等实词）
ALLOW_POS = {"n", "nr", "ns", "nt", "nz", "vn", "v", "vd", "a", "ad", "an", "j", "l", "i", "eng"}


def is_valid_word(word):
    """过滤单字、纯标点数字与停用词。"""
    if len(word) < 2:
        return False
    if re.fullmatch(r"[\s\W\d_]+", word):
        return False
    if word in STOPWORDS:
        return False
    return True


def add_stopwords(words):
    """追加停用词。"""
    if isinstance(words, str):
        words = words.split()
    STOPWORDS.update(words)


def tokenize(text):
    """中文分词并清洗，返回有效词列表。"""
    if not text:
        return []
    return [w for w in jieba.lcut(text) if is_valid_word(w)]


def tfidf_scores(docs_tokens, candidate_scale=3):
    """在文档集合上计算 TF-IDF 权重并返回候选词词典。

    docs_tokens: List[List[str]]，每个元素为一篇文档的分词结果
    """
    doc_num = len(docs_tokens)
    if doc_num == 0:
        return {}

    # 文档频率
    df = {}
    for tokens in docs_tokens:
        for w in set(tokens):
            df[w] = df.get(w, 0) + 1

    scores = {}
    for tokens in docs_tokens:
        total = len(tokens) or 1
        tf = {}
        for w in tokens:
            tf[w] = tf.get(w, 0) + 1
        for w, count in tf.items():
            idf = math.log((doc_num + 1) / (df.get(w, 0) + 1)) + 1.0
            scores[w] = scores.get(w, 0.0) + (count / total) * idf

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return dict(ranked[: max(50, candidate_scale * 50)])


def textrank_scores(tokens, window=5, top_n=100, iterations=60, damping=0.85):
    """基于共现窗口构建词图并做 TextRank 迭代，返回词权重词典。"""
    if not tokens:
        return {}

    graph = {}
    for i, w in enumerate(tokens):
        neighbors = graph.setdefault(w, set())
        start = max(0, i - window)
        end = min(len(tokens), i + window + 1)
        for j in range(start, end):
            if j != i and tokens[j] != w:
                neighbors.add(tokens[j])

    if not graph:
        return {}

    words = list(graph.keys())
    weight = {w: 1.0 for w in words}

    for _ in range(iterations):
        new_weight = {}
        for w in words:
            neighbors = graph[w]
            if not neighbors:
                new_weight[w] = 1.0 - damping
                continue
            s = sum(weight[n] / (len(graph[n]) or 1) for n in neighbors)
            new_weight[w] = (1.0 - damping) + damping * s
        weight = new_weight

    ranked = sorted(weight.items(), key=lambda x: -x[1])
    return dict(ranked[:top_n])


def _normalize(score_dict):
    """把权重归一化到 0~1，便于不同算法结果加权融合。"""
    if not score_dict:
        return {}
    max_v = max(score_dict.values())
    if max_v <= 0:
        return {k: 0.0 for k in score_dict}
    return {k: v / max_v for k, v in score_dict.items()}


def extract_keywords(
    contents,
    top_k=20,
    method="combine",
    window=5,
    threshold=0.0,
):
    """提取关键词。

    contents: 新闻正文列表（每篇为一个字符串）
    method:   combine / tfidf / textrank
    window:   TextRank 共现窗口大小
    threshold:权重阈值，低于该值的关键词将被过滤（0 表示不过滤）

    返回 [(word, weight)]，weight 归一化到 0~1
    """
    docs_tokens = [tokenize(c) for c in contents if c]
    docs_tokens = [t for t in docs_tokens if t]
    if not docs_tokens:
        return []

    all_tokens = [w for doc in docs_tokens for w in doc]
    if not all_tokens:
        return []

    if method == "tfidf":
        raw = tfidf_scores(docs_tokens)
    elif method == "textrank":
        raw = textrank_scores(all_tokens, window=window, top_n=100)
    else:
        tfidf_raw = tfidf_scores(docs_tokens)
        textrank_raw = textrank_scores(all_tokens, window=window, top_n=100)
        tfidf_norm = _normalize(tfidf_raw)
        textrank_norm = _normalize(textrank_raw)
        raw = {}
        for w in set(tfidf_norm) | set(textrank_norm):
            raw[w] = 0.5 * tfidf_norm.get(w, 0.0) + 0.5 * textrank_norm.get(w, 0.0)

    ranked = sorted(raw.items(), key=lambda x: -x[1])[:top_k]
    if not ranked:
        return []

    # 归一化输出，便于展示与阈值过滤
    max_v = ranked[0][1]
    if max_v > 0:
        ranked = [(w, v / max_v) for w, v in ranked]
    else:
        ranked = [(w, 0.0) for w, v in ranked]

    if threshold and threshold > 0:
        ranked = [(w, v) for w, v in ranked if v >= threshold]

    return ranked


def count_word_frequency(contents):
    """统计词频，供词云直接使用。"""
    freq = {}
    for content in contents:
        for w in tokenize(content):
            freq[w] = freq.get(w, 0) + 1
    return sorted(freq.items(), key=lambda x: -x[1])
