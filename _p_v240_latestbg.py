# -*- coding: utf-8 -*-
"""「最新」行绿底是否真的画出来了？（应用级取色，纯 ASCII 输出）

背景：列表 item 挂 tags=("latest", "row")，两个 tag 都 configure 了 background。
实测规则（见 _p_v240_tagprio.py）：ttk::treeview **先创建的 tag 优先级更高**。
主程序里 row(2022行) 先于 latest(2024行) 创建 -> 生效的是 row 的 C_CARD，
latest 的 C_GREEN_BG 从不渲染。

本探针在**真实应用**上取色验证这一点，而不是在玩具窗口里。

判定：
  - 配置层：latest 的 background 应当是 C_GREEN_BG（配置确实存在）
  - 渲染层：成品图里 C_GREEN_BG 的像素数
      0  -> 已确认的既有缺陷（当前状态）
      >0 -> 说明已修复（那时应把本探针改成断言 >0）

取色方法：纵向剖面扫描列表区，逐 y 取"行内左侧一点"的色。
不用 tv.bbox() —— 它的 y 与 winfo_rooty() 差一个表头高度，会取错行。
"""
import os
import sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import msi_bios_checker as m
import importlib.util

spec = importlib.util.spec_from_file_location(
    "_rend", os.path.join(HERE, "_p_v230_render.py"))

# 复用渲染脚本的建窗/取图工具（它 import 时不会执行主流程：主流程在文件尾部，
# 但为了安全这里只借用其函数定义，所以用 exec 取源码前缀）。
src = open(os.path.join(HERE, "_p_v230_render.py"), encoding="utf-8").read()
cut = src.index("# ---------------------------------------------------------------- 1) 空状态")
ns = {"__name__": "_rend_partial", "__file__": os.path.join(HERE, "_p_v230_render.py")}
exec(compile(src[:cut], "_rend_partial", "exec"), ns)
build = ns["build"]
pump = ns["pump"]
CAT = ns["CAT"]
GROUPS = ns["GROUPS"]
# SLUG/TITLE 在渲染脚本里定义在截面之后（第 149 行），取不到，这里直接给出。
SLUG, TITLE = "MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI"

m._init_dpi()
m._apply_dpi_scale(m._DPI)

root, app = build(1200, 780, m._DPI)
app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, GROUPS, None, None, "com"))
pump(root, 6)
app._fit_tv_cols()
pump(root, 4)

rows = app.tv.get_children()
print("rows = %d" % len(rows))
if rows:
    print("  row0 tags = %r" % (app.tv.item(rows[0], "tags"),))
# 关键：让选中行**不是** row0，否则选中态会盖掉一切，看不出 tag 冲突。
if len(rows) > 1:
    app.tv.selection_set(rows[1])
pump(root, 10, 0.05)

GREEN_BG = m.C_GREEN_BG
CARD = m.C_CARD
print("C_GREEN_BG = %s   C_CARD = %s" % (GREEN_BG, CARD))

# ---- 配置层
try:
    cfg_latest = app.tv.tag_configure("latest", "background")
    cfg_row = app.tv.tag_configure("row", "background")
except tk.TclError:
    cfg_latest = cfg_row = None
print("configured: latest.bg=%s  row.bg=%s" % (cfg_latest, cfg_row))

# ---- 渲染层
from PIL import ImageGrab


def grab_app(root, w=1200, h=780, tries=20):
    """抓应用窗口，并**校验抓到的确实是本应用**。

    坑：ImageGrab 抓被遮挡的窗口会拿到桌面画面，实测杂值形如 #0a0c10 / #12161d ——
    既不是测试色也不是任何令牌色。若不校验，探针会据此得出"绿底 0 像素"的**假结论**
    （第一次跑本探针就踩了：那次其实只是窗口没到前台）。
    校验方式：表头色 C_HEADING(#32363a) 必须在图中出现足够多次 —— 它是列表区顶部
    一整条 39px 高的色带，只要有几十个像素命中就说明抓的是本应用。
    """
    head = m.C_HEADING
    hr = tuple(int(head[i:i + 2], 16) for i in (1, 3, 5))
    last = None
    for k in range(tries):
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        pump(root, 8, 0.05)
        x0 = root.winfo_rootx()
        y0 = root.winfo_rooty()
        im = ImageGrab.grab(bbox=(x0, y0, x0 + w, y0 + h))
        px = im.load()
        hit = 0
        for y in range(120, 560, 3):
            for x in range(430, 1160, 7):
                c = px[x, y]
                if all(abs(a - b) <= 2 for a, b in zip(c[:3], hr)):
                    hit += 1
        last = (im, px, hit)
        if hit >= 40:
            return im, px, k + 1
    return last[0], last[1], -1


im, px, tries_used = grab_app(root)
print("grab valid after %d tries (header color hits)" % tries_used)

if tries_used < 0:
    print("  ABORT: could not capture the app window (got the desktop instead).")
    print("         previous probe run hit exactly this and silently reported a")
    print("         false 0-pixel result -- that is why this guard exists.")
    root.destroy()
    raise SystemExit(2)


def norm(c):
    return "#%02x%02x%02x" % c[:3]


# 全图统计与目标色相近的像素（容差 2，避免 ClearType 边缘干扰）
def near(c, ref):
    r = tuple(int(ref[i:i + 2], 16) for i in (1, 3, 5))
    return all(abs(a - b) <= 2 for a, b in zip(c[:3], r))


cnt_green = sum(1 for y in range(im.size[1]) for x in range(im.size[0])
                if near(px[x, y], GREEN_BG))
cnt_card = sum(1 for y in range(im.size[1]) for x in range(im.size[0])
               if near(px[x, y], CARD))
print("pixels ~C_GREEN_BG = %d      pixels ~C_CARD = %d" % (cnt_green, cnt_card))

# ---- 逐行底色剖面（x 取表格右侧空白处，避开文字）
prof = []
prev = None
start = None
for y in range(150, 600):
    c = norm(px[1150, y])
    if c != prev:
        if prev is not None and y - start >= 4:
            prof.append((start, y - 1, prev))
        prev = c
        start = y
if prev is not None:
    prof.append((start, 599, prev))
print("vertical profile @x=1150:")
for s, e, c in prof:
    tag = ""
    if near(tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)), GREEN_BG):
        tag = "  <- C_GREEN_BG"
    elif near(tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)), CARD):
        tag = "  <- C_CARD"
    print("   y %4d..%4d  %s  h=%d%s" % (s, e, c, e - s + 1, tag))

print()
fails = []
if cnt_green == 0:
    fails.append("C_GREEN_BG configured but 0 px painted (shadowed by 'row' tag)")
    print("  VERDICT: C_GREEN_BG is configured but NEVER painted.")
    print("           root cause: tag priority = earlier-created wins")
    print("           fix: create 'latest' BEFORE 'row' in App.__init__")
else:
    print("  VERDICT: C_GREEN_BG IS painted (%d px) -> latest-row highlight works"
          % cnt_green)

# 第一行（★ 最新行）的色带本身必须是 C_GREEN_BG
first = next((c for s, e, c in prof if s > 189), None)
print("  first data band after the header = %s" % first)


def hexeq(c, ref):
    return c is not None and c.lower() == ref.lower()


if not hexeq(first, GREEN_BG):
    fails.append("first row band is %s, expected C_GREEN_BG %s" % (first, GREEN_BG))

print()
if fails:
    print("  FAIL")
    for f in fails:
        print("    " + f)
else:
    print("  latest-row background probe PASS")
root.destroy()
raise SystemExit(1 if fails else 0)
