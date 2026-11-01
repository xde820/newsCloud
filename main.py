# -*- coding: utf-8 -*-
"""主程序：中文新闻稿词云可视化与关键词提取系统（Tkinter 桌面端）。"""

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PIL import Image, ImageTk  # noqa: E402

import cloud  # noqa: E402
import crawler  # noqa: E402
import dataio  # noqa: E402
import demo_data  # noqa: E402
import keywords as kw  # noqa: E402

BG = "#F7FAFB"
ACCENT = "#0E7C86"


# ---------------------------------------------------------------- 新闻采集
class CollectionTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.stop_flag = False
        self.msg_queue = queue.Queue()
        self._build()

    def _build(self):
        top = ttk.Frame(self, padding=(10, 10, 10, 6))
        top.pack(fill="x")

        ttk.Label(top, text="新闻列表页 URL：").pack(side="left")
        self.url_var = tk.StringVar(value="https://news.sina.com.cn/")
        ttk.Entry(top, textvariable=self.url_var, width=58).pack(
            side="left", padx=6, fill="x", expand=True
        )

        ttk.Label(top, text="最大页数：").pack(side="left", padx=(10, 0))
        self.pages_var = tk.IntVar(value=1)
        ttk.Spinbox(top, from_=1, to=20, textvariable=self.pages_var, width=5).pack(side="left")

        bar = ttk.Frame(self, padding=(10, 0, 10, 8))
        bar.pack(fill="x")
        self.collect_btn = ttk.Button(bar, text="开始采集", command=self.start_collect)
        self.collect_btn.pack(side="left")
        self.stop_btn = ttk.Button(bar, text="停止采集", command=self.stop_collect, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        ttk.Button(bar, text="加载示例数据（15 条）", command=self.load_demo).pack(side="left")

        self.log_text = scrolledtext.ScrolledText(self, height=20, wrap="word", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def start_collect(self):
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning("提示", "请输入合法的 http/https 地址。")
            return

        self.stop_flag = False
        self.collect_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        pages = int(self.pages_var.get())

        def worker():
            items = crawler.collect(
                url,
                max_pages=pages,
                log=lambda m: self.msg_queue.put(("log", m)),
                should_stop=lambda: self.stop_flag,
            )
            self.msg_queue.put(("done", items))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll)

    def stop_collect(self):
        self.stop_flag = True
        self._log("正在停止…")

    def _poll(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                else:
                    self._finish(payload)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _finish(self, items):
        if items:
            self.app.news.extend(items)
            self.app.refresh_data()
        self.collect_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        messagebox.showinfo("采集完成", f"共获取 {len(items)} 条新闻。")

    def load_demo(self):
        items = demo_data.get_demo_news()
        self.app.news.extend(items)
        self.app.refresh_data()
        self._log(f"已加载 {len(items)} 条示例数据。")
        messagebox.showinfo("提示", f"已加载 {len(items)} 条示例数据。")


# ---------------------------------------------------------------- 数据管理
class DataTab(ttk.Frame):
    COLUMNS = ("no", "title", "source", "time", "wc")

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        bar = ttk.Frame(self, padding=(10, 10, 10, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="刷新", command=self.refresh).pack(side="left")
        ttk.Button(bar, text="清空数据", command=self.clear).pack(side="left", padx=8)
        ttk.Button(bar, text="保存为 CSV", command=self.save_csv).pack(side="left")
        ttk.Button(bar, text="加载 CSV", command=self.load_csv).pack(side="left", padx=8)

        self.total_var = tk.StringVar(value="共 0 条")
        ttk.Label(bar, textvariable=self.total_var).pack(side="right")

        wrap = ttk.Frame(self, padding=(10, 0, 10, 10))
        wrap.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(wrap, columns=self.COLUMNS, show="headings")
        heads = {"no": "#", "title": "标题", "source": "来源", "time": "发布时间", "wc": "正文字数"}
        widths = {"no": 40, "title": 460, "source": 120, "time": 150, "wc": 90}
        for c in self.COLUMNS:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor="center" if c != "title" else "w")

        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, item in enumerate(self.app.news, start=1):
            self.tree.insert(
                "",
                "end",
                values=(i, item["title"], item.get("source", ""), item.get("publish_time", ""), item.get("word_count", 0)),
            )
        self.total_var.set(f"共 {len(self.app.news)} 条")

    def clear(self):
        if not self.app.news:
            return
        if messagebox.askyesno("确认", f"确定清空全部 {len(self.app.news)} 条数据吗？"):
            self.app.news.clear()
            self.app.refresh_data()

    def save_csv(self):
        if not self.app.news:
            messagebox.showwarning("提示", "当前没有数据可保存。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV 文件", "*.csv")])
        if path:
            dataio.save_csv(path, self.app.news)
            messagebox.showinfo("成功", f"已保存到：\n{path}")

    def load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")])
        if not path:
            return
        items = dataio.load_csv(path)
        self.app.news.extend(items)
        self.app.refresh_data()
        messagebox.showinfo("成功", f"已加载 {len(items)} 条数据。")


# -------------------------------------------------------------- 关键词提取
class KeywordTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.canvas = None
        self._build()

    def _build(self):
        bar = ttk.Frame(self, padding=(10, 10, 10, 6))
        bar.pack(fill="x")

        ttk.Label(bar, text="算法：").pack(side="left")
        self.method_var = tk.StringVar(value="组合算法")
        ttk.Combobox(
            bar, textvariable=self.method_var, width=10, state="readonly",
            values=["组合算法", "TF-IDF", "TextRank"],
        ).pack(side="left")

        ttk.Label(bar, text="关键词数量：").pack(side="left", padx=(14, 0))
        self.topk_var = tk.IntVar(value=20)
        ttk.Spinbox(bar, from_=5, to=100, textvariable=self.topk_var, width=6).pack(side="left")

        ttk.Label(bar, text="共现窗口：").pack(side="left", padx=(14, 0))
        self.window_var = tk.IntVar(value=5)
        ttk.Spinbox(bar, from_=2, to=20, textvariable=self.window_var, width=6).pack(side="left")

        ttk.Label(bar, text="权重阈值：").pack(side="left", padx=(14, 0))
        self.threshold_var = tk.DoubleVar(value=0.0)
        ttk.Spinbox(bar, from_=0.0, to=1.0, increment=0.05, textvariable=self.threshold_var, width=6).pack(side="left")

        ttk.Button(bar, text="开始提取", command=self.extract).pack(side="left", padx=14)

        body = ttk.Frame(self, padding=(10, 0, 10, 10))
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        cols = ("rank", "word", "weight", "dist")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        heads = {"rank": "排名", "word": "关键词", "weight": "权重", "dist": "分布"}
        widths = {"rank": 50, "word": 120, "weight": 90, "dist": 180}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor="center")
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        right = ttk.Frame(body)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))
        self.chart_frame = ttk.Frame(right)
        self.chart_frame.pack(fill="both", expand=True)

    def extract(self):
        if not self.app.news:
            messagebox.showwarning("提示", "暂无数据，请先采集新闻或加载示例数据。")
            return

        method_map = {"组合算法": "combine", "TF-IDF": "tfidf", "TextRank": "textrank"}
        contents = [n["content"] for n in self.app.news]

        try:
            results = kw.extract_keywords(
                contents,
                top_k=int(self.topk_var.get()),
                method=method_map[self.method_var.get()],
                window=int(self.window_var.get()),
                threshold=float(self.threshold_var.get()),
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("提取失败", str(exc))
            return

        self.app.keyword_result = results

        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, (word, weight) in enumerate(results, start=1):
            bar_len = int(round(weight * 24))
            self.tree.insert("", "end", values=(i, word, f"{weight:.4f}", "█" * max(bar_len, 1)))

        self._draw_chart(results)
        if not results:
            messagebox.showinfo("提示", "未提取到关键词，请调整参数。")

    def _draw_chart(self, results):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        if not results:
            return

        data = list(results[:15])[::-1]
        words = [w for w, _ in data]
        weights = [v for _, v in data]

        fp = cloud.get_font_properties()
        fig = Figure(figsize=(6.0, 4.6), dpi=100)
        ax = fig.add_subplot(111)
        pos = list(range(len(words)))
        ax.barh(pos, weights, color=ACCENT)
        ax.set_yticks(pos)
        if fp is not None:
            ax.set_yticklabels(words, fontproperties=fp)
        ax.set_xlabel("归一化权重", fontproperties=fp)
        ax.set_title("Top 15 关键词权重分布", fontproperties=fp)
        ax.set_xlim(0, 1.05)
        fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)


# ------------------------------------------------------------------ 词云生成
class CloudTab(ttk.Frame):
    BG_OPTIONS = ["white", "black", "#F7FAFB", "transparent"]

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.wc = None
        self.photo = None
        self._build()

    def _build(self):
        bar = ttk.Frame(self, padding=(10, 10, 10, 6))
        bar.pack(fill="x")

        ttk.Label(bar, text="宽度：").pack(side="left")
        self.width_var = tk.IntVar(value=800)
        ttk.Spinbox(bar, from_=400, to=2000, textvariable=self.width_var, width=7).pack(side="left")

        ttk.Label(bar, text="高度：").pack(side="left", padx=(12, 0))
        self.height_var = tk.IntVar(value=600)
        ttk.Spinbox(bar, from_=300, to=2000, textvariable=self.height_var, width=7).pack(side="left")

        ttk.Label(bar, text="背景色：").pack(side="left", padx=(12, 0))
        self.bg_var = tk.StringVar(value="white")
        ttk.Combobox(bar, textvariable=self.bg_var, width=12, state="readonly", values=self.BG_OPTIONS).pack(side="left")

        ttk.Label(bar, text="最大词数：").pack(side="left", padx=(12, 0))
        self.maxw_var = tk.IntVar(value=200)
        ttk.Spinbox(bar, from_=20, to=500, textvariable=self.maxw_var, width=7).pack(side="left")

        bar2 = ttk.Frame(self, padding=(10, 0, 10, 8))
        bar2.pack(fill="x")
        ttk.Label(bar2, text="形状：").pack(side="left")
        self.shape_var = tk.StringVar(value="矩形")
        ttk.Combobox(bar2, textvariable=self.shape_var, width=8, state="readonly", values=cloud.SHAPES).pack(side="left")

        ttk.Label(bar2, text="配色方案：").pack(side="left", padx=(12, 0))
        self.cmap_var = tk.StringVar(value="viridis")
        ttk.Combobox(bar2, textvariable=self.cmap_var, width=12, state="readonly", values=cloud.COLORMAPS).pack(side="left")

        ttk.Button(bar2, text="生成词云", command=self.generate).pack(side="left", padx=14)
        ttk.Button(bar2, text="随机配色", command=self.random_color).pack(side="left")
        ttk.Button(bar2, text="保存词云", command=self.save).pack(side="left", padx=8)

        self.preview = ttk.Label(self, text="（词云预览区）", background=BG, anchor="center")
        self.preview.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _ensure_keywords(self):
        """优先使用关键词提取结果，否则临时用词频统计。"""
        if self.app.keyword_result:
            return self.app.keyword_result
        if not self.app.news:
            messagebox.showwarning("提示", "暂无数据，请先采集新闻或加载示例数据。")
            return None
        freq = kw.count_word_frequency([n["content"] for n in self.app.news])
        if not freq:
            messagebox.showwarning("提示", "未统计到有效词语。")
            return None
        return [(w, float(c)) for w, c in freq[:200]]

    def generate(self):
        data = self._ensure_keywords()
        if not data:
            return
        try:
            self.wc = cloud.generate_wordcloud(
                data,
                width=int(self.width_var.get()),
                height=int(self.height_var.get()),
                background_color=self.bg_var.get(),
                max_words=int(self.maxw_var.get()),
                colormap=self.cmap_var.get(),
                shape=self.shape_var.get(),
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("生成失败", str(exc))
            return

        img = self.wc.to_image()
        preview = img.copy()
        preview.thumbnail((620, 470))
        self.photo = ImageTk.PhotoImage(preview)
        self.preview.config(image=self.photo, text="")

    def random_color(self):
        self.cmap_var.set(cloud.random_colormap(exclude=self.cmap_var.get()))
        self.generate()

    def save(self):
        if self.wc is None:
            messagebox.showwarning("提示", "请先生成词云。")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG 图片", "*.png")])
        if path:
            self.wc.to_file(path)
            messagebox.showinfo("成功", f"已保存到：\n{path}")


# -------------------------------------------------------------------- 主应用
class App:
    def __init__(self, root):
        self.root = root
        self.news = []
        self.keyword_result = []

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.collection_tab = CollectionTab(nb, self)
        self.data_tab = DataTab(nb, self)
        self.keyword_tab = KeywordTab(nb, self)
        self.cloud_tab = CloudTab(nb, self)

        nb.add(self.collection_tab, text="新闻采集")
        nb.add(self.data_tab, text="数据管理")
        nb.add(self.keyword_tab, text="关键词提取")
        nb.add(self.cloud_tab, text="词云生成")

    def refresh_data(self):
        self.data_tab.refresh()


def main():
    root = tk.Tk()
    root.title("中文新闻稿词云可视化与关键词提取系统")
    root.geometry("1120x760")
    root.minsize(1000, 680)
    try:
        root.configure(background=BG)
    except Exception:  # noqa: BLE001
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
