# -*- coding: utf-8 -*-
"""钉死 Tk ttk::treeview 的 tag 优先级规则（纯 ASCII 输出）。

疑问：item 同时挂 ("latest", "row")，两个 tag 都 configure 了 background，
      实际生效的是哪一个？取决于「创建顺序」还是「在 tags 列表里的顺序」？

做法：建两个 Treeview 做对照实验 ——
  A) 先 configure "row"，再 configure "latest"  （= 主程序当前的顺序）
  B) 先 configure "latest"，再 configure "row"  （= 交换后的顺序）
每组都把 (row, latest) 的 bg 设成两个肉眼可分辨的极端色，然后实际取像素。
"""
import time
import tkinter as tk
from tkinter import ttk

COL_ROW = "#ff0000"       # row 的 bg
COL_LATEST = "#0000ff"    # latest 的 bg
COL_PAD = "#00ff00"       # 窗口底（用来防止取到窗口背景）

root = tk.Tk()
root.geometry("360x200+40+40")
root.configure(bg=COL_PAD)


def make_panel(parent, row_first, label):
    """row_first=True 时 row 先建（主程序当前顺序），否则 latest 先建。"""
    fr = tk.Frame(parent, bg=COL_PAD)
    fr.pack(side="left", padx=6, pady=6)
    tk.Label(fr, text=label, bg=COL_PAD, fg="#000000").pack()
    tv = ttk.Treeview(fr, columns=("a",), show="headings", height=1)
    tv.heading("a", text="col")
    tv.column("a", width=120)

    def cfg_row():
        tv.tag_configure("row", background=COL_ROW, foreground="#ffffff")

    def cfg_latest():
        tv.tag_configure("latest", background=COL_LATEST, foreground="#ffffff")

    if row_first:
        cfg_row()
        cfg_latest()
    else:
        cfg_latest()
        cfg_row()

    iid = tv.insert("", "end", values=("x",), tags=("latest", "row"))
    tv.pack()
    tv.update_idletasks()
    tv.update()
    return tv, iid


tvA, iidA = make_panel(root, True, "A: row 先建")
tvB, iidB = make_panel(root, False, "B: latest 先建")
# 必须置顶 + pump 若干轮再抓图 —— 否则 ImageGrab 拿到的是**被遮挡的桌面**，
# 实测会读出 #0a0c10 / #12161d 这种既不是测试色、也不是任何令牌色的杂值。
root.deiconify()
root.lift()
root.attributes("-topmost", True)
for _ in range(24):
    root.update_idletasks()
    root.update()
    time.sleep(0.05)


def sample(tv, iid):
    """取该行内部的像素色（往里偏 40px，避开边框与文字）。"""
    try:
        bb = tv.bbox(iid, "a")
    except Exception:
        bb = None
    if not bb:
        return None
    x = tv.winfo_rootx() + bb[0] + 8
    y = tv.winfo_rooty() + bb[1] + bb[3] // 2
    from PIL import ImageGrab
    im = ImageGrab.grab(bbox=(x, y, x + 4, y + 1))
    return "#%02x%02x%02x" % im.getpixel((1, 0))[:3]


NAMES = {COL_ROW: "row(red)", COL_LATEST: "latest(blue)"}
fails = []
obs = {}
for key, label, tv, iid in (("A", "A: row first, latest second", tvA, iidA),
                            ("B", "B: latest first, row second", tvB, iidB)):
    c = sample(tv, iid)
    obs[key] = c
    print("  %-30s sampled bg %s -> %s" % (label, c, NAMES.get(c, "?unknown")))

print()
# 判据：先创建者优先。A 应先建的 row 赢（红），B 应后建的对照里 latest 赢（蓝）。
if obs["A"] == COL_ROW and obs["B"] == COL_LATEST:
    print("  RULE: EARLIER-created tag wins (creation order, not tags= list order)")
else:
    fails.append("tag priority rule mismatch: A=%s B=%s" % (obs["A"], obs["B"]))

# 再断言一次：把同一个 item 的 tags= 列表顺序反过来，结果不应改变
# （即优先级与 tags= 书写顺序无关）。
tvA.item(iidA, tags=("row", "latest"))
for _ in range(6):
    root.update()
    time.sleep(0.03)
c2 = sample(tvA, iidA)
print("  A panel with tags= reversed to ('row','latest') -> %s" % c2)
if c2 != COL_ROW:
    fails.append("priority seems to follow tags= order, not creation order "
                 "(got %s)" % c2)
else:
    print("  RULE: tags= list order does NOT affect priority  -> confirmed")

print()
print("  Main program uses shape A (tag_configure line: row 2022 < latest 2024),")
print("  and BOTH configure background -> the later-created 'latest' C_GREEN_BG")
print("  is shadowed by 'row' C_CARD, i.e. the green highlight never renders.")
print()
if fails:
    print("  FAIL")
    for f in fails:
        print("    " + f)
else:
    print("  tag priority probe PASS")
root.destroy()
raise SystemExit(1 if fails else 0)
