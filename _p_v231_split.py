# -*- coding: utf-8 -*-
"""v2.3.1 分隔条行为探针：拖拽 / 钳制 / 用户宽度优先 / 双击重置。

为什么必须实测而不是"看着能拖"：
  ① 拖动改的是 _lf 的显式 width，而 _auto_fit_cat 也在写同一个值 —— 谁赢取决于
     调用顺序，肉眼看不出来（表现为"改窗口大小后宽度莫名其妙弹回去"）；
  ② 上下限钳制要保证「右栏不低于 CAT_RIGHT_MIN」且「左栏不低于可用下限」，
     极端窗口下这两个约束会互相矛盾，需要明确谁让路；
  ③ 列宽与卡片宽是同一个约束的两头，只改一头会出现"树右侧留白"或"型号名被裁"。
"""
import json
import os
import shutil
import sys
import tempfile
import time
import types

import importlib.util

HERE = os.getcwd()
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

import tkinter as tk                            # noqa: E402

TMP = tempfile.mkdtemp(prefix="v231split_")
shutil.copy(os.path.join(HERE, "msi_mb_catalog.json"),
            os.path.join(TMP, "msi_mb_catalog.json"))
os.chdir(TMP)
CAT = json.load(open(os.path.join(TMP, "msi_mb_catalog.json"), encoding="utf-8"))

fails = []


def ck(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def cancel_all(root):
    for aid in root.tk.call("after", "info"):
        try:
            root.after_cancel(aid)
        except Exception:
            pass


def pump(root, n=5, pause=0.02):
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(pause)


def ev(x_root):
    """伪造一个只带 x_root 的事件对象（探针不需要真鼠标）。"""
    return types.SimpleNamespace(x_root=x_root, y_root=0, x=0, y=0)


m._init_dpi()
m._apply_dpi_scale(m._DPI)

root = tk.Tk()
root.withdraw()
app = m.App(root)
app._restored = True
cancel_all(root)
root.geometry("1200x780+40+40")
root.deiconify()
pump(root, 8)
app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
pump(root, 6)

print("=== [0] 分隔条已创建且可见 ===")
ck(hasattr(app, "_split"), "存在 _split 分隔条")
rect = (app._split.winfo_x(), app._split.winfo_y(),
        app._split.winfo_width(), app._split.winfo_height())
print("      分隔条 body 内几何 x=%d y=%d w=%d h=%d" % rect)
ck(app._split.winfo_ismapped(), "分隔条已布局（ismapped）")
ck(app._split.winfo_width() == m.S(m.SPLIT_W),
   "分隔条宽 = S(SPLIT_W) = %dpx（实测 %d）" % (m.S(m.SPLIT_W), app._split.winfo_width()))
ck(app._split.winfo_height() == app._lf.winfo_height(),
   "分隔条与左卡片等高（%d vs %d）"
   % (app._split.winfo_height(), app._lf.winfo_height()))
ck(app._split_line.winfo_height() == app._split.winfo_height(),
   "细线竖向铺满（%d vs %d）"
   % (app._split_line.winfo_height(), app._split.winfo_height()))

print("\n=== [1] 三列几何自洽（左 + 分隔条 + 右 = 布局区）===")
bw = app._body.winfo_width()
pad = m.S(20) * 2
lw = app._lf.winfo_width()
sw = app._split.winfo_width()
rw = app._rf.winfo_width()
print("      body %d（含左右 padding %d）  左 %d + 分隔条 %d + 右 %d = %d"
      % (bw, pad, lw, sw, rw, lw + sw + rw))
ck(lw + sw + rw == bw - pad,
   "三列宽之和 + padding = body 宽（%d == %d）" % (lw + sw + rw + pad, bw))
lo, hi = app._left_limits()
print("      左栏宽度限 = [%d, %d]   当前 %d" % (lo, hi, lw))
ck(lo <= lw <= hi, "当前宽度在限内（%d ≤ %d ≤ %d）" % (lo, lw, hi))
ck(rw >= m.S(m.CAT_RIGHT_MIN), "右栏 ≥ CAT_RIGHT_MIN（%d ≥ %d）"
   % (rw, m.S(m.CAT_RIGHT_MIN)))

print("\n=== [2] 拖动：+80px（刻意不触及上限，上限行为在 [4] 单独测）===")
w0 = app._lf.winfo_width()
D = 80
ck(w0 + D <= hi, "起点 %d + 位移 %d ≤ 上限 %d（否则测的就是钳制而非跟手）"
   % (w0, D, hi))
app._split_press(ev(700))
app._split_motion(ev(700 + D))
pump(root, 3)
w1 = app._lf.winfo_width()
print("      拖前 %d → 拖后 %d（期望 +%d = %d）" % (w0, w1, D, w0 + D))
ck(abs(w1 - (w0 + D)) <= 1, "拖动位移 1:1 跟手（实测 +%d）" % (w1 - w0))
ck(app._left_user_w == w1, "用户宽度已记录（%s）" % app._left_user_w)
app._split_release(ev(700 + D))

print("\n=== [3] 用户宽度优先于自适应 ===")
app._auto_fit_cat()                 # 模拟窗口尺寸变化触发的自适应
pump(root, 2)
ck(app._lf.winfo_width() == w1,
   "自适应没有覆盖用户宽度（%d == %d）" % (app._lf.winfo_width(), w1))
col = int(str(app.cat_tree.column("#0", "width")))
ck(col == max(m.S(m.CAT_TREE_MIN), w1 - m.S(m.CAT_CARD_OVER)),
   "目录树列宽与卡片宽同步（列 %d = 卡片 %d - 开销 %d）"
   % (col, w1, m.S(m.CAT_CARD_OVER)))

print("\n=== [4] 钳制：拖到极限之外 ===")
app._split_press(ev(700))
app._split_motion(ev(700 + 5000))   # 想拖到 +5000px
pump(root, 2)
wmax = app._lf.winfo_width()
print("      猛拖 +5000 → 实际 %d（上限 %d）" % (wmax, hi))
ck(wmax <= hi, "不超上限（%d ≤ %d）" % (wmax, hi))
ck(app._rf.winfo_width() >= m.S(m.CAT_RIGHT_MIN),
   "右栏仍不低于保底（%d ≥ %d）" % (app._rf.winfo_width(), m.S(m.CAT_RIGHT_MIN)))
app._split_motion(ev(700 - 5000))   # 想拖到 -5000px
pump(root, 2)
wmin = app._lf.winfo_width()
print("      猛拖 -5000 → 实际 %d（下限 %d）" % (wmin, lo))
ck(wmin >= lo, "不低于下限（%d ≥ %d）" % (wmin, lo))
ck(wmin <= wmax, "下限 ≤ 上限")
app._split_release(ev(0))

print("\n=== [5] 双击重置回自适应 ===")
app._split_reset()
pump(root, 4)
print("      重置后宽 %d，_left_user_w=%s" % (app._lf.winfo_width(), app._left_user_w))
ck(app._left_user_w == 0, "用户宽度已清空")
need = app._cat_col_need() if app.catalog else m.S(m.CAT_TREE_INIT)
floor = need + m.S(m.CAT_CARD_OVER)
_avail = app._body_width() - m.S(m.BODY_PAD_X) * 2      # 比例基数是内容宽
ratio_w = int(_avail * m.LEFT_RATIO)
expect = int(max(lo, min(hi, min(m.S(m.LEFT_MAX), max(ratio_w, floor)))))
ck(app._lf.winfo_width() == expect,
   "重置到自适应值（实测 %d = 期望 %d）" % (app._lf.winfo_width(), expect))
col2 = int(str(app.cat_tree.column("#0", "width")))
ck(col2 >= need, "列宽 ≥ 型号名实测需求（%d ≥ %d，型号名不被裁）" % (col2, need))

print("\n=== [6] 宽度随窗口单调变化（无来回抖动）===")
seq = []
for w in (1100, 1200, 1400, 1600, 1920, 1600, 1200, 1100):
    root.geometry("%dx780+40+40" % w)
    pump(root, 5, 0.03)
    app._auto_fit_cat()
    pump(root, 3)
    seq.append((w, app._lf.winfo_width(), app._rf.winfo_width()))
    print("      窗口 %-5d → 左 %-4d 右 %-4d" % seq[-1])
grow = [r for (_w, _l, r) in seq[:5]]
ck(all(grow[i + 1] > grow[i] for i in range(len(grow) - 1)),
   "右栏随窗口单调增长（%s）" % grow)
ck(seq[0][1] == seq[7][1], "同一窗口宽度下左栏宽可复现（%d == %d）"
   % (seq[0][1], seq[7][1]))
ck(all(m.S(m.SPLIT_MIN_LEFT) <= l <= m.S(m.LEFT_MAX) for (_w, l, _r) in seq),
   "所有尺寸下左栏都在 [%d, %d] 内" % (m.S(m.SPLIT_MIN_LEFT), m.S(m.LEFT_MAX)))
# 宽屏下比例项应当开始起作用（左栏超过"型号名所需"）
w1920 = [l for (w, l, _r) in seq if w == 1920][0]
ck(w1920 > floor, "1920 窗口下左栏 %d > 型号名所需 %d（比例项生效）" % (w1920, floor))

print("\n" + ("分隔条行为全部通过 ✓" if not fails
              else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
try:
    root.destroy()
except Exception:
    pass
os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fails else 0)
