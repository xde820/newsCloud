# -*- coding: utf-8 -*-
"""无界面逻辑测试：验证关键词提取、词云生成与 CSV 存取是否可以正常运行。"""

import os

os.environ.setdefault("MPLBACKEND", "Agg")

import cloud  # noqa: E402
import dataio  # noqa: E402
import demo_data  # noqa: E402
import keywords  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs")
os.makedirs(OUT, exist_ok=True)


def main():
    news = demo_data.get_demo_news()
    print(f"示例数据条数：{len(news)}")
    contents = [n["content"] for n in news]

    for label, method in (("组合算法", "combine"), ("TF-IDF", "tfidf"), ("TextRank", "textrank")):
        res = keywords.extract_keywords(contents, top_k=15, method=method, window=5, threshold=0.0)
        print(f"\n[{label}] Top 15 关键词：")
        for i, (w, s) in enumerate(res, 1):
            print(f"  {i:>2}. {w:<10} {s:.4f}")

    res = keywords.extract_keywords(contents, top_k=60, method="combine")
    for shape in ("矩形", "圆形", "星形"):
        wc = cloud.generate_wordcloud(res, width=1000, height=700, shape=shape, colormap="viridis")
        path = os.path.join(OUT, f"wordcloud_{shape}.png")
        wc.to_file(path)
        print(f"\n词云已保存：{path}")

    csv_path = os.path.join(OUT, "news.csv")
    dataio.save_csv(csv_path, news)
    loaded = dataio.load_csv(csv_path)
    print(f"\nCSV 存取测试：保存 {len(news)} 条，加载 {len(loaded)} 条，首条标题：{loaded[0]['title']}")
    print("\n全部逻辑测试通过。")


if __name__ == "__main__":
    main()
