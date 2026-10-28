# -*- coding: utf-8 -*-
"""视觉焕新探针 C：进度文案换等宽字的落地评估。

要回答：
  1. 换 Cascadia Mono 后，PB_TXT_FULL / PB_TXT_SHORT 的实测像素宽变化多少？
     （直接决定 _pb_label_chars 的字符格 → 决定进度条能剩多宽 → 决定是否提前"压短"）
  2. 数字宽度是否真的与 Microsoft YaHei UI 一致（零漂移）？
  3. Cascadia Mono 没有中文字形，"剩"字回退后长什么样？（渲染图 + 取色验证有没有豆腐块）
"""
import ctypes
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from PIL import ImageGrab

HERE = os.getcwd()

PB_TXT_FULL = "88.8 / 188.8 MB   188.8 MB/s   剩 1:59:59   (100%)"
PB_TXT_SHORT = "188.8 MB/s  100%"
UI = "Microsoft YaHei UI"
CANDS = ["Cascadia Mono", "Consolas", "Cascadia Code"]

u32 = ctypes.windll.user32


def pump(root, n=6, pause=0.04):
    import time
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(pause)


def main():
    root = tk.Tk()
    root.title("mono-probe")
    root.geometry("900x430+80+80")
    root.configure(bg="#17191b")

    st = ttk.Style()
    for t in ("alt", "clam", "xpnative", "default"):
        try:
            st.theme_use(t)
            break
        except Exception:
            continue
    st.configure(".", background="#17191b", foreground="#e6e9ee")
    st.configure("TLabel", background="#17191b", foreground="#e6e9ee")

    print("=" * 78)
    print("【A】进度文案样例的实测像素宽（size=-16，96 DPI）")
    print("=" * 78)
    base = tkfont.Font(family=UI, size=-16)
    b_full = base.measure(PB_TXT_FULL)
    b_short = base.measure(PB_TXT_SHORT)
    print("%-18s  FULL=%4dpx  SHORT=%4dpx   measure('0')=%dpx" % (UI, b_full, b_short,
                                                                  base.measure("0")))
    rows = []
    for n in CANDS:
        f = tkfont.Font(family=n, size=-16)
        mf, ms, m0 = f.measure(PB_TXT_FULL), f.measure(PB_TXT_SHORT), f.measure("0")
        rows.append((n, mf, ms, m0))
        print("%-18s  FULL=%4dpx(%+.1f%%)  SHORT=%4dpx(%+.1f%%)   measure('0')=%dpx" % (
            n, mf, 100.0 * (mf - b_full) / b_full, ms, 100.0 * (ms - b_short) / b_short, m0))

    # 数字零漂移验证
    print()
    print("【B】数字零漂移验证（逐串比对 YaHei UI）")
    for n, _, _, _ in rows:
        f = tkfont.Font(family=n, size=-16)
        same = []
        for s in ("0123456789", "88.8", "188.8", "1:59:59", "100%"):
            a, b = base.measure(s), f.measure(s)
            same.append("%s:%s" % (s, "同" if a == b else "%+d" % (b - a)))
        print("  %-16s %s" % (n, "  ".join(same)))

    # 渲染对照
    print()
    print("【C】渲染对照（含中文回退观察）")
    wrap = ttk.Frame(root, padding=18)
    wrap.pack(fill="both", expand=True)
    samples = [
        (UI, "基准"),
        ("Cascadia Mono", "等宽"),
        ("Consolas", "等宽备选"),
    ]
    labs = []
    for i, (fam, tag) in enumerate(samples):
        ttk.Label(wrap, text="%s (%s)" % (fam, tag),
                  font=(UI, -12)).grid(row=i * 2, column=0, sticky="w", pady=(8, 2))
        for j, txt in enumerate((PB_TXT_FULL, PB_TXT_SHORT, "剩 1:59:59 中文 汉字")):
            w = tk.Label(wrap, text=txt, font=(fam, -16), bg="#1e2023",
                         fg="#e6e9ee", padx=8, pady=4)
            w.grid(row=i * 2 + 1, column=j, sticky="w", padx=(0, 10))
            labs.append((fam, j, w))

    pump(root, 12, 0.05)
    hwnd = u32.GetAncestor(root.winfo_id(), 2)
    u32.SetForegroundWindow(hwnd)
    root.lift()
    pump(root, 6, 0.05)

    import ctypes.wintypes as wt2
    rc = wt2.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(rc))
    pt = wt2.POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(pt))
    box = (pt.x, pt.y, pt.x + rc.right, pt.y + rc.bottom)
    img = ImageGrab.grab(bbox=box, all_screens=True)
    out = os.path.join(HERE, "_vis_probe_mono.png")
    img.save(out)
    print("  截图 -> %s (%dx%d)" % (out, img.width, img.height))
    for fam, j, w in labs:
        print("    %-16s 列%d  标签实测 %dx%d" % (fam, j, w.winfo_width(), w.winfo_height()))
    root.destroy()
    print()
    print("探针 C 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
