# -*- coding: utf-8 -*-
"""视觉焕新探针 B：卡片"材质"实现的可行性实测。

要回答三个问题：
  1. ttk.Frame 在 alt 主题下，relief=groove/ridge/raised/sunken + lightcolor/darkcolor
     到底能不能画出"上受光 / 下背光"的立体边？（能不能纯样式层做材质）
  2. bordercolor（1px 同色描边）是否生效？
  3. 三级明度阶梯（底 / 面 / 浮）在真实渲染下的对比是否够辨层级、又不刺眼？

做法：把 6 种卡片配置并排渲染，抓客户区截图，再**按控件真实屏幕矩形取色**逐个读边
框像素。不靠目测 —— 目测在深色低对比下极不可靠（本项目已栽过三次）。
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import tkinter as tk
from tkinter import ttk

from PIL import ImageGrab

HERE = os.getcwd()

# ---- 石墨精工：候选三级明度阶梯（中性，饱和度 <= 1.5%）----
C0 = "#131417"      # L0 窗口底
C1 = "#1c1e21"      # L1 卡片面
C2 = "#24272b"      # L2 浮层（表头 / 次级按钮）
BORDER = "#33373d"
LIGHT = "#343941"   # 受光边（比面部亮两档）
DARK = "#0e0f11"    # 背光边（比底还暗）

CASES = [
    ("flat/bw0  (现状)", dict(background=C1, borderwidth=0, relief="flat")),
    ("solid/bw1", dict(background=C1, borderwidth=1, relief="solid",
                       bordercolor=BORDER)),
    ("groove/bw1", dict(background=C1, borderwidth=1, relief="groove",
                        lightcolor=LIGHT, darkcolor=DARK)),
    ("ridge/bw1", dict(background=C1, borderwidth=1, relief="ridge",
                       lightcolor=LIGHT, darkcolor=DARK)),
    ("raised/bw1", dict(background=C1, borderwidth=1, relief="raised",
                        lightcolor=LIGHT, darkcolor=DARK)),
    ("sunken/bw1", dict(background=C1, borderwidth=1, relief="sunken",
                        lightcolor=LIGHT, darkcolor=DARK)),
]

u32 = ctypes.windll.user32
fails = []
pixels = {}


def pump(root, n=6, pause=0.03):
    import time
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(pause)


def client_rect(root):
    hwnd = u32.GetAncestor(root.winfo_id(), 2)
    rc = wt.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(rc))
    pt = wt.POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(pt))
    return hwnd, (pt.x, pt.y, pt.x + rc.right, pt.y + rc.bottom)


def main():
    root = tk.Tk()
    root.title("vis-probe")
    root.configure(bg=C0)
    root.geometry("760x560+60+60")

    st = ttk.Style()
    for tname in ("alt", "clam", "xpnative", "default"):
        try:
            st.theme_use(tname)
            break
        except Exception:
            continue
    active_theme = st.theme_use()
    st.configure(".", background=C0, foreground="#e8eaf0")
    st.configure("TFrame", background=C0)
    st.configure("TLabel", background=C0, foreground="#e8eaf0")
    st.configure("In.TLabel", background=C1, foreground="#e8eaf0")

    wrap = ttk.Frame(root, padding=(16, 16))
    wrap.pack(fill="both", expand=True)
    wrap.columnconfigure(0, weight=1)
    wrap.columnconfigure(1, weight=1)
    wrap.rowconfigure(0, weight=1)
    wrap.rowconfigure(1, weight=1)
    wrap.rowconfigure(2, weight=1)

    boxes = []
    for i, (name, cfg) in enumerate(CASES):
        sn = "Card%d.TFrame" % i
        st.configure(sn, **cfg)
        cell = ttk.Frame(wrap)
        cell.grid(row=i // 2, column=i % 2, sticky="nsew",
                  padx=6, pady=6)
        cell.columnconfigure(0, weight=1)
        cell.rowconfigure(0, weight=1)
        f = ttk.Frame(cell, style=sn, padding=(0, 0))
        f.grid(row=0, column=0, sticky="nsew")
        ttk.Label(f, text="  卡片材质：%s  " % name,
                  style="In.TLabel").pack(anchor="w", pady=8, padx=8)
        boxes.append((name, f))

    # 阶梯对照条
    strip = ttk.Frame(root, padding=(16, 0, 16, 14))
    strip.pack(fill="x")
    for i, (lbl, col) in enumerate([("L0 底 " + C0, C0), ("L1 面 " + C1, C1),
                                    ("L2 浮 " + C2, C2),
                                    ("受光 " + LIGHT, LIGHT),
                                    ("背光 " + DARK, DARK),
                                    ("边 " + BORDER, BORDER)]):
        sw = tk.Frame(strip, bg=col, height=40, width=110)
        sw.pack(side="left", padx=(0, 4))
        sw.pack_propagate(False)
        tk.Label(sw, text=lbl, bg=col, fg="#e8eaf0",
                 font=("Microsoft YaHei UI", -12)).place(x=4, y=20)

    pump(root, 10, 0.05)
    u32.SetForegroundWindow(u32.GetAncestor(root.winfo_id(), 2))
    root.lift()
    pump(root, 6, 0.05)
    hwnd, box = client_rect(root)
    img = ImageGrab.grab(bbox=box, all_screens=True)
    out = os.path.join(HERE, "_vis_probe_cards.png")
    img.save(out)
    print("主题=%s  截图 %dx%d -> %s" % (active_theme, img.width, img.height, out))

    # ---- 取色：每个卡片的左边缘 / 上边缘 / 内部 ----
    print()
    print("%-20s %-14s %-14s %-14s %s" % ("配置", "左边(1px)", "上边(1px)", "内部", "判定"))
    for name, f in boxes:
        rx = f.winfo_rootx() - box[0]
        ry = f.winfo_rooty() - box[1]
        w, h = f.winfo_width(), f.winfo_height()

        def px(x, y):
            return img.getpixel((min(max(x, 0), img.width - 1),
                                 min(max(y, 0), img.height - 1)))

        left = px(rx, ry + h // 2)
        top = px(rx + w // 2, ry)
        inner = px(rx + w // 2, ry + h // 2)
        bot = px(rx + w // 2, ry + h - 1)
        has_edge = (left != inner) or (top != inner)
        print("%-20s %-14s %-14s %-14s %s | 下边 %s" % (
            name, str(left), str(top), str(inner),
            "有边" if has_edge else "无边", str(bot)))

    # 阶梯实测色
    print()
    print("阶梯条取色（应等于各自配置值）:")
    for i, (lbl, col) in enumerate([("L0", C0), ("L1", C1), ("L2", C2),
                                    ("受光", LIGHT), ("背光", DARK),
                                    ("边", BORDER)]):
        got = img.getpixel((16 + i * 114 + 40, box[3] - box[1] - 34))
        want = tuple(int(col[j:j + 2], 16) for j in (1, 3, 5))
        ok = all(abs(got[k] - want[k]) <= 2 for k in range(3))
        print("  %-4s 期望 %s  实测 %s  %s" % (lbl, want, got[:3],
                                             "OK" if ok else "DIFF"))
        if not ok:
            fails.append("阶梯色 %s 渲染不符" % lbl)

    root.destroy()
    print()
    print("探针 B 完成（%s）" % ("全部符合" if not fails else "有 %d 项偏差" % len(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
