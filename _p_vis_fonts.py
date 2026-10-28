# -*- coding: utf-8 -*-
"""视觉焕新探针 A：本机字体资产盘点（界面字族 + 等宽字族）。

只做测量、不做断言 —— 输出一份可引用的字体可用性报告。
关键判据：
  1. 字族是否真实存在（Tk font families）
  2. 是否等宽（'0'×10 与 'i'×10 宽度是否相等、且 '0'/'i' 单字宽相等）
  3. 深色背景下的中文可读性靠渲染图人工判断，本探针只负责"有没有"
用法: python _p_vis_fonts.py [-v]
"""
import sys
import tkinter as tk
import tkinter.font as tkfont

# 界面字族候选（按优先级）
UI_CANDS = [
    "Microsoft YaHei UI", "Microsoft YaHei", "MSYH",
    "MiSans", "MiSans VF", "MiSans Normal",
    "HarmonyOS Sans SC", "HarmonyOS Sans",
    "Source Han Sans SC", "Source Han Sans CN", "Noto Sans SC",
    "Alibaba PuHuiTi", "Alibaba PuHuiTi 3.0", "OPPO Sans",
    "Sarasa Gothic SC", "Sarasa UI SC",
    "Inter", "Segoe UI Variable Text", "Segoe UI",
    "SimHei", "SimSun",
]

# 等宽字族候选（数字/速度/百分比用）
MONO_CANDS = [
    "Cascadia Mono", "Cascadia Code", "Consolas",
    "Sarasa Mono SC", "Sarasa Term SC",
    "JetBrains Mono", "Fira Code", "Source Code Pro", "IBM Plex Mono",
    "DejaVu Sans Mono", "Courier New", "Lucida Console",
    "Noto Sans Mono CJK SC", "Microsoft YaHei Mono",
]

SAMPLES = [
    ("汉字", "微星主板BIOS下载工具"),
    ("拉丁", "MPG Z790 EDGE TI WIFI"),
    ("数字", "0123456789"),
    ("符号", "↗ ↻ ● ◎ ⏱ · ×"),
]


def main():
    verbose = "-v" in sys.argv
    root = tk.Tk()
    root.withdraw()
    fams = set(str(x) for x in root.tk.call("font", "families"))
    print("本机字族总数: %d" % len(fams))
    print()

    def probe(name):
        """返回 (存在, 是否等宽, {'0'x10宽, 'i'x10宽, 单字宽, 汉字宽})。"""
        if name not in fams:
            return (False, None, None)
        f = tkfont.Font(family=name, size=-16)
        w0 = f.measure("0" * 10)
        wi = f.measure("i" * 10)
        w1 = f.measure("0")
        whz = f.measure("微星主板")
        # 等宽判据：10 个不同字符等宽 → 0/i 等宽；且单字宽 = 十个字宽/10
        is_mono = (w0 == wi) and (abs(w0 / 10.0 - w1) < 0.6)
        return (True, is_mono, (w0, wi, w1, whz))

    print("=" * 78)
    print("【A】界面字族候选")
    print("=" * 78)
    print("%-26s %-6s %-6s %s" % ("字族", "存在", "等宽", "度量(0x10 / ix10 / 0 / 汉字4)"))
    ui_ok = []
    for n in UI_CANDS:
        ex, mono, m = probe(n)
        tag = "YES" if ex else "-"
        print("%-26s %-6s %-6s %s" % (
            n, tag, ("Y" if mono else "n") if ex else "-",
            ("%d/%d/%d/%d" % m) if m else ""))
        if ex:
            ui_ok.append(n)
    print()
    print("  ⇒ 可用的界面字族: %s" % (", ".join(ui_ok) or "(无)"))

    print()
    print("=" * 78)
    print("【B】等宽字族候选")
    print("=" * 78)
    print("%-26s %-6s %-6s %s" % ("字族", "存在", "等宽", "度量(0x10 / ix10 / 0 / 汉字4)"))
    mono_ok = []
    for n in MONO_CANDS:
        ex, mono, m = probe(n)
        tag = "YES" if ex else "-"
        print("%-26s %-6s %-6s %s" % (
            n, tag, ("Y" if mono else "n") if ex else "-",
            ("%d/%d/%d/%d" % m) if m else ""))
        if ex and mono:
            mono_ok.append(n)
    print()
    print("  ⇒ 可用的等宽字族: %s" % (", ".join(mono_ok) or "(无)"))

    if verbose:
        print()
        print("=" * 78)
        print("【C】候选字族的样例文本度量（换字族后布局漂移评估）")
        print("=" * 78)
        base = "Microsoft YaHei UI"
        ref = tg = tkfont.Font(family=base, size=-16)
        print("%-26s %s" % ("字族", " ".join("%s(%dpx)" % (k, ref.measure(v))
                                             for k, v in SAMPLES)))
        print("%-26s %s" % (base + " [基准]",
                            " ".join("%s(%dpx)" % (k, ref.measure(v))
                                     for k, v in SAMPLES)))
        for n in ui_ok:
            if n == base:
                continue
            f = tkfont.Font(family=n, size=-16)
            cells = []
            for k, v in SAMPLES:
                a, b = ref.measure(v), f.measure(v)
                d = b - a
                cells.append("%s(%dpx,%+.1f%%)" % (k, b, 100.0 * d / max(a, 1)))
            print("%-26s %s" % (n, " ".join(cells)))

    root.destroy()


if __name__ == "__main__":
    main()
