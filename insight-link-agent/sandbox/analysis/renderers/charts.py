"""受限参数化图表；模型无需执行任意代码即可生成常用学情可视化。"""

import math


KINDS = {"line", "bar", "pie", "bar_horizontal", "donut", "scatter", "histogram",
         "radar", "heatmap", "grouped_bar", "stacked_bar"}


def numbers(values, *, count=None, maximum=1000):
    """拒绝布尔、非有限值及过大数组，避免隐式转换掩盖数据问题。"""
    if not isinstance(values, list) or not 1 <= len(values) <= maximum:
        raise ValueError(f"数值数组需要 1–{maximum} 项")
    if count is not None and len(values) != count:
        raise ValueError("数值与标签维度不一致")
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or not -1e12 < value < 1e12 for value in values):
        raise ValueError("图表数值必须是有限数字且绝对值小于一万亿")
    return [float(value) for value in values]


def labels(values, *, count=None, maximum=30, optional=False):
    """校验标签长度和维度；不自动截断或丢弃标签。"""
    if optional and values in (None, []):
        return []
    if not isinstance(values, list) or not 1 <= len(values) <= maximum:
        raise ValueError(f"标签需要 1–{maximum} 项")
    if count is not None and len(values) != count:
        raise ValueError("标签数量与数据维度不一致")
    if any(not isinstance(value, str) or not value.strip() or len(value) > 80 for value in values):
        raise ValueError("标签不能为空且最多 80 字符")
    return values


def datasets(values, *, count):
    """校验分组/堆叠数据系列，每组数值均须与分类标签一一对应。"""
    if not isinstance(values, list) or not 1 <= len(values) <= 6:
        raise ValueError("分组数据需要 1–6 个系列")
    result = []
    for item in values:
        if (not isinstance(item, dict) or not isinstance(item.get("name"), str)
                or not item["name"].strip() or len(item["name"]) > 60):
            raise ValueError("每个系列需要不超过 60 字符的名称")
        ys = numbers(item.get("values"), count=count, maximum=30)
        result.append((item["name"], ys))
    return result


def validate(payload):
    """绘图前校验所有分支，测试可独立验证而无需加载 matplotlib。"""
    kind, title = payload.get("chart_type"), payload.get("title")
    if kind not in KINDS:
        raise ValueError("不支持的图表类型")
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        raise ValueError("图表标题需要 1–160 字符")
    raw_labels = payload.get("labels", [])
    values, series, matrix, xs = [], [], [], []
    if kind == "heatmap":
        source = payload.get("matrix")
        if not isinstance(source, list) or not 1 <= len(source) <= 30:
            raise ValueError("热力图需要 1–30 行矩阵")
        matrix = [numbers(row, maximum=30) for row in source]
        if any(len(row) != len(matrix[0]) for row in matrix):
            raise ValueError("热力图矩阵必须为矩形")
        axis_labels = labels(raw_labels, count=len(matrix[0]), optional=True)
        row_labels = labels(payload.get("y_labels", []), count=len(matrix), optional=True)
        return kind, axis_labels, values, series, matrix, xs, row_labels
    if kind in {"grouped_bar", "stacked_bar"}:
        axis_labels = labels(raw_labels)
        series = datasets(payload.get("series"), count=len(axis_labels))
    elif kind == "scatter":
        values = numbers(payload.get("values"))
        xs = numbers(payload.get("x_values"), count=len(values)) if payload.get("x_values") else list(range(1, len(values) + 1))
        axis_labels = labels(raw_labels, count=len(values), maximum=1000, optional=True)
    elif kind == "histogram":
        values = numbers(payload.get("values"))
        bins = payload.get("bins", 10)
        if isinstance(bins, bool) or not isinstance(bins, int) or not 1 <= bins <= 50:
            raise ValueError("直方图 bins 需要 1–50 的整数")
        axis_labels = []
    else:
        axis_labels = labels(raw_labels, maximum=12 if kind == "radar" else 30)
        values = numbers(payload.get("values"), count=len(axis_labels), maximum=30)
        if kind in {"pie", "donut"} and (any(value < 0 for value in values) or sum(values) <= 0):
            raise ValueError("饼图/环形图数值必须非负且总和大于零")
        if kind == "radar" and (len(values) < 3 or any(value < 0 for value in values)):
            raise ValueError("雷达图需要 3–12 个非负维度")
    return kind, axis_labels, values, series, matrix, xs, []


def render_chart(payload, output):
    """使用无界面 Agg 后端输出 PNG；不读取文件、网络或外部绘图脚本。"""
    kind, axis_labels, values, series, matrix, xs, row_labels = validate(payload)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    fonts = ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "DejaVu Sans"]
    installed = {font.name for font in font_manager.fontManager.ttflist}
    plt.rcParams["font.sans-serif"] = [name for name in fonts if name in installed]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["text.parse_math"] = False
    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained",
                           subplot_kw={"projection": "polar"} if kind == "radar" else {})
    try:
        if kind == "line":
            ax.plot(axis_labels, values, marker="o", linewidth=2)
        elif kind == "bar":
            ax.bar(axis_labels, values)
        elif kind == "bar_horizontal":
            ax.barh(axis_labels, values)
            ax.invert_yaxis()
        elif kind in {"pie", "donut"}:
            ax.pie(values, labels=axis_labels, autopct="%1.1f%%",
                   wedgeprops={"width": .42} if kind == "donut" else None)
        elif kind == "scatter":
            ax.scatter(xs, values, alpha=.75)
            if axis_labels and len(axis_labels) <= 30:
                for x, y, label in zip(xs, values, axis_labels):
                    ax.annotate(label, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8)
        elif kind == "histogram":
            ax.hist(values, bins=payload.get("bins", 10), edgecolor="white")
            ax.set_ylabel("频数")
        elif kind == "radar":
            angles = [index * 2 * math.pi / len(values) for index in range(len(values))]
            ax.plot(angles + angles[:1], values + values[:1], linewidth=2)
            ax.fill(angles + angles[:1], values + values[:1], alpha=.2)
            ax.set_xticks(angles, axis_labels)
        elif kind == "heatmap":
            image = ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
            fig.colorbar(image, ax=ax)
            ax.set_xticks(range(len(matrix[0])), axis_labels or [str(i + 1) for i in range(len(matrix[0]))])
            ax.set_yticks(range(len(matrix)), row_labels or [str(i + 1) for i in range(len(matrix))])
        elif kind == "grouped_bar":
            width = .8 / len(series)
            for index, (name, ys) in enumerate(series):
                positions = [x - .4 + width / 2 + index * width for x in range(len(axis_labels))]
                ax.bar(positions, ys, width=width, label=name)
            ax.set_xticks(range(len(axis_labels)), axis_labels)
            ax.legend()
        elif kind == "stacked_bar":
            positive, negative = [0.] * len(axis_labels), [0.] * len(axis_labels)
            for name, ys in series:
                bottoms = [positive[i] if y >= 0 else negative[i] for i, y in enumerate(ys)]
                ax.bar(axis_labels, ys, bottom=bottoms, label=name)
                for i, y in enumerate(ys):
                    if y >= 0:
                        positive[i] += y
                    else:
                        negative[i] += y
            ax.legend()
        if kind not in {"pie", "donut", "radar", "heatmap"}:
            ax.tick_params(axis="x", rotation=30)
            ax.grid(axis="x" if kind == "bar_horizontal" else "y", alpha=.2)
        ax.set_title(payload["title"])
        fig.savefig(output / "chart.png", dpi=140)
    finally:
        plt.close(fig)
    return "图表已生成"
