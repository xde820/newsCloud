# 中文新闻稿词云可视化与关键词提取系统

基于 Python + Tkinter 的桌面应用，实现「新闻采集 → 数据管理 → 关键词提取 → 词云生成」的完整流水线。

## 一、功能结构

- **新闻采集**：输入列表页 URL 与最大页数，多线程抓取正文，解析标题 / 来源 / 发布时间 / 正文字数，支持停止采集；内置 15 条示例数据便于离线演示。
- **数据管理**：表格展示（标题 / 来源 / 时间 / 字数），支持清空、保存为 CSV、加载 CSV。
- **关键词提取**：支持「组合算法 / TF-IDF / TextRank」三种算法，可调关键词数量、TextRank 共现窗口、权重阈值；结果以排名列表 + 权重柱状图呈现。
- **词云生成**：可调尺寸、背景色、最大词数、形状（矩形 / 圆形 / 星形 / 心形）、配色方案，支持随机配色、预览与保存 PNG。

## 二、技术栈

| 模块 | 技术 |
| --- | --- |
| 界面 | Python 3 + Tkinter / ttk |
| 采集 | requests、BeautifulSoup、lxml、ThreadPoolExecutor |
| 分词 | jieba |
| 关键词 | 自建 TF-IDF、TextRank（共现窗口 + PageRank 迭代）、组合加权 |
| 可视化 | matplotlib（柱状图）、wordcloud（词云）、Pillow（形状蒙版） |
| 存储 | CSV（utf-8-sig） |

## 三、安装与运行

需要 Python 3.8+ 且包含 tkinter（标准安装默认自带）。

```bash
# 方式一：直接使用本项目自带的隔离环境（已装好全部依赖）
.venv/Scripts/python.exe main.py

# 方式二：用自己的环境
pip install -r requirements.txt
python main.py
```

## 四、无界面逻辑测试

```bash
python test_logic.py
```

会打印三种算法的 Top 15 关键词，并在 `outputs/` 下生成三种形状的词云图与 CSV 文件。

## 五、说明

- 采集模块使用启发式解析，不同站点效果有差异；若目标站点解析不到内容，可改用「加载示例数据」或在 `crawler.py` 中按站点补充选择器。
- 词云需要中文字体，程序会自动查找系统字体（Windows 优先 `msyh.ttc`）；若乱码请手动指定 `font_path`。
- 关键词提取在文档集合上计算 TF-IDF，TextRank 基于全部分词结果的共现窗口构图，两者归一化后加权得到「组合算法」结果。
