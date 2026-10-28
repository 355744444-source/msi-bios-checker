# -*- coding: utf-8 -*-
"""v2.5.0 布局重构前的量化诊断（不靠肉眼）。

【A】目录树：缩进到底多大 / 列宽需求 vs 实得 / 型号名宽度分布
【B】BIOS 表：4 列「分配 vs 内容真正需要」
【C】进度行：胶囊条 vs 文案的宽度分配
【D】纵向账：右卡片里「非列表」占掉多少
【E】信息重复：同一件事在几处同时显示

设计约束：本探针只做**度量与打印**，不改任何东西 —— 结论必须可复算。
"""
import io
import os
import sys
import tkinter.font as tkfont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

src = io.open(os.path.join(HERE, "_p_v230_render.py"), encoding="utf-8").read()
cut = src.index("# ---------------------------------------------------------------- 1) 空状态")
_ns = {"__name__": "_rend_partial", "__file__": os.path.join(HERE, "_p_v230_render.py")}
exec(compile(src[:cut], "_rend_partial", "exec"), _ns)
build, pump, CAT, GROUPS = _ns["build"], _ns["pump"], _ns["CAT"], _ns["GROUPS"]

import msi_bios_checker as m

SLUG, TITLE = "MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI"
S = m.S

m._init_dpi()
m._apply_dpi_scale(m._DPI)
root, app = build(1200, 780, m._DPI)

app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)

for p in app.cat_tree.get_children(""):
    app.cat_tree.item(p, open=True)
pump(root, 4)

app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, GROUPS, None, None, "com"))
pump(root, 6)
app._fit_tv_cols()
pump(root, 4)


def px(font, s):
    return font.measure(str(s))


# ================================================================ 【A】
print("=" * 88)
print("【A】目录树：缩进 / 列宽需求 / 型号名宽度分布")
print("=" * 88)
try:
    ind_style = m.ttk.Style().lookup("Cat.Treeview", "indent")
except Exception as e:
    ind_style = "<读不到 %r>" % (e,)
print("  源码常量 CAT_INDENT = %r   →   S(CAT_INDENT) = %r" % (m.CAT_INDENT, S(m.CAT_INDENT)))
print("  样式 Cat.Treeview 的 indent 实测 = %r" % (ind_style,))


def first_item_at(level):
    for p in app.cat_tree.get_children(""):
        if level == 0:
            return p
        for c in app.cat_tree.get_children(p):
            if level == 1:
                return c
            for b in app.cat_tree.get_children(c):
                return b
    return None


xs = {}
print("  各级文本起点（bbox x，相对树控件）：")
for lv, nm in ((0, "platform"), (1, "chipset"), (2, "board")):
    it = first_item_at(lv)
    if it is None:
        print("    level %d %-9s <无此级>" % (lv, nm))
        continue
    bb = app.cat_tree.bbox(it)
    if not bb:
        # bbox 对**未滚动到可视区**的项返回空 —— 先 see() 把它滚进来再量，
        # 否则会把"没露出来"误读成"未布局"。
        app.cat_tree.see(it)
        pump(root, 4)
        bb = app.cat_tree.bbox(it)
    if not bb:
        print("    level %d %-9s <仍不可见>" % (lv, nm))
        continue
    xs[lv] = bb[0]
    print("    level %d %-9s x=%-5d  text=%r"
          % (lv, nm, bb[0], app.cat_tree.item(it, "text")))
if 0 in xs and 1 in xs:
    d1 = xs.get(1, 0) - xs.get(0, 0)
    d2 = xs.get(2, 0) - xs.get(1, 0) if 2 in xs else None
    print("  ⇒ 实测逐级缩进：platform→chipset %+d px%s"
          % (d1, ("，chipset→board %+d px" % d2) if d2 is not None else ""))
    if d1 == 0 and d2 == 0:
        print("  ⇒ 三级**完全无缩进** —— 层级只靠展开箭头 + 字色表达")

need = app._cat_col_need()
colw = int(app.cat_tree.column("#0", "width"))
over = m.CAT_CARD_OVER
print()
print("  _cat_col_need() = %d px ；+CAT_CARD_OVER(%d) = %d px   ← 左栏「硬底线」"
      % (need, over, need + S(over)))
print("  左卡片实际宽 = %d px ；树 #0 列实际宽 = %d px"
      % (app._lf.winfo_width(), colw))

tf = tkfont.Font(font=m.ttk.Style().lookup("Cat.Treeview", "font"))
ind = S(m.CAT_INDENT)
pad = S(1 + m.CAT_TREE_PAD)
allw = []
for b in (app.catalog or {}).get("brands") or []:
    for cs in b.get("chipsets") or []:
        for bd in cs.get("boards") or []:
            allw.append(px(tf, bd["title"]) + ind * 2 + pad)
allw.sort()


def pct(p):
    return allw[min(len(allw) - 1, int(len(allw) * p))] if allw else 0


print()
print("  型号名所需宽度（全量 %d 条，含缩进）：" % len(allw))
print("    P50=%d  P75=%d  P90=%d  P95=%d  P99=%d  max=%d"
      % (pct(.50), pct(.75), pct(.90), pct(.95), pct(.99), allw[-1]))
print("    ⇒ 按 max 定宽需 %d px；按 P90 定宽只需 %d px（差 %d px）"
      % (allw[-1], pct(.90), allw[-1] - pct(.90)))
ok = sum(1 for n in allw if n <= colw)
print("    ⇒ 当前 #0 列 %d px 能完整显示 %d/%d 条 = %.1f%%"
      % (colw, ok, len(allw), 100.0 * ok / max(1, len(allw))))

# ================================================================ 【B】
print()
print("=" * 88)
print("【B】BIOS 表：分配 vs 内容真正需要")
print("=" * 88)
tv = app.tv
cols = ("ver", "date", "size", "note")
alloc = dict((c, int(tv.column(c, "width"))) for c in cols)
ttf = tkfont.Font(font=m.ttk.Style().lookup("Treeview", "font"))
rows = tv.get_children()
print("  表宽 %d px ；列宽合计 %d px ；数据行 %d 行"
      % (tv.winfo_width(), sum(alloc.values()), len(rows)))
print()
print("  %-6s %-7s %-9s %-9s %-7s %s" % ("列", "分配", "表头需要", "内容需要", "缺口", "最长内容"))
trunc = 0
short = 0
for c in cols:
    hw = px(ttf, tv.heading(c, "text")) + 24
    mx, mxv = 0, ""
    for iid in rows:
        v = str(tv.set(iid, c))
        w = px(ttf, v) + 24
        if w > mx:
            mx, mxv = w, v
    nd = max(hw, mx)
    gap = alloc[c] - nd
    if gap < 0:
        trunc += 1
        short += -gap
    print("  %-6s %-7d %-9d %-9d %+d     %s" % (c, alloc[c], hw, mx, gap, mxv[:36]))
print()
print("  ⇒ 4 列中 %d 列被截断，合计缺 %d px" % (trunc, short))

# ================================================================ 【C】【D】
print()
print("=" * 88)
print("【C】进度行横向分配   /   【D】右卡片纵向账")
print("=" * 88)
pw = app._pbar_row.winfo_width()
print("  进度行容器 %d px：胶囊条 %d px (%.0f%%) | 文案 %d px (%.0f%%)"
      % (pw, app.pb.winfo_width(), 100.0 * app.pb.winfo_width() / pw,
         app.lbl_pb.winfo_width(), 100.0 * app.lbl_pb.winfo_width() / pw))
app._toast_show("✓ 上一步：目录已更新（501 款主板 / 20 条中国站补录）", ok=True)
pump(root, 16, 0.05)
non_list = 0
for nm, w in (("标题行", app._title_row), ("操作行", app._orow),
              ("进度行", app._pbar_row), ("横幅", app._toast)):
    print("  %-8s y=%-5d h=%-5d" % (nm, w.winfo_y(), w.winfo_height()))
    non_list += w.winfo_height()
rh = app._rf.winfo_height()
print("  列表区   y=%-5d h=%-5d" % (app._list_zone.winfo_y(), app._list_zone.winfo_height()))
print("  ⇒ 非列表固定行 %d px（右卡片 %.0f%%）；列表 %d px（%.0f%%）"
      % (non_list, 100.0 * non_list / rh,
         app._list_zone.winfo_height(), 100.0 * app._list_zone.winfo_height() / rh))

# ================================================================ 【E】
print()
print("=" * 88)
print("【E】同一件事在几处同时显示")
print("=" * 88)
app._set_downloading(True)
app._dl_speed = 11.4 * 1048576
app._dl_progress(38.6 * 1048576, 67.1 * 1048576)
app._set_status("正在下载 7D89v1B1.zip …", "run")
pump(root, 14, 0.05)
sel = app.tv.selection()
print("  ① BIOS 表选中行   = %r" % (app.tv.set(sel[0], "ver") if sel else "—"))
print("  ② 进度条右侧文案  = %r" % app.v_pb.get())
print("  ③ 最底部状态栏    = %r" % app.v_status.get())
print("  ④ 保存目录行      = %r" % app.v_dir.get())
print("  ⇒ 版本号/进度在三处重复，其中 ②③ 语义高度重叠。")

root.destroy()
print()
print("诊断完成")
