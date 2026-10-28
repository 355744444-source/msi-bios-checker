# -*- coding: utf-8 -*-
"""v2.5.0 三栏布局体检：建窗 → 填目录 → 选芯片组 → 量三栏几何与选择链。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

src = io.open(os.path.join(HERE, "_p_v230_render.py"), encoding="utf-8").read()
cut = src.index("# ---------------------------------------------------------------- 1) 空状态")
_ns = {"__name__": "_rp", "__file__": os.path.join(HERE, "_p_v230_render.py")}
exec(compile(src[:cut], "_rp", "exec"), _ns)
build, pump, wait_mapped, CAT, GROUPS = (
    _ns["build"], _ns["pump"], _ns["wait_mapped"], _ns["CAT"], _ns["GROUPS"])

import msi_bios_checker as m

m._init_dpi()
m._apply_dpi_scale(m._DPI)
root, app = build(m.WIN_W, m.WIN_H, m._DPI)
app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
pump(root, 6)

print("=" * 76)
print("三栏几何（客户区 %dx%d）" % (root.winfo_width(), root.winfo_height()))
print("=" * 76)
for nm, w in (("栏1 _lf 导航", app._lf), ("分隔条1", app._split),
              ("栏2 _mf 型号", app._mf), ("分隔条2", app._split2),
              ("栏3 _rf 明细", app._rf)):
    print("  %-14s x=%-5d y=%-4d w=%-5d h=%-4d" % (
        nm, w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height()))

body = app._body
print("  body 宽 = %d" % body.winfo_width())
tot = (app._lf.winfo_width() + app._split.winfo_width()
       + app._mf.winfo_width() + app._split2.winfo_width()
       + app._rf.winfo_width())
print("  ⇒ 三栏+两条分隔条合计 = %d（body 内容宽应为 %d）"
      % (tot, body.winfo_width() - 40))

print()
print("=" * 76)
print("栏1 导航树")
print("=" * 76)
plats = app.cat_tree.get_children("")
print("  平台 %d 个；顶层条目:" % len(plats))
for p in plats:
    print("    %-28s 子项 %d" % (app.cat_tree.item(p, "text"),
                                 len(app.cat_tree.get_children(p))))
print("  iid_chip 记录 %d 个芯片组" % len(app.iid_chip))
print("  #0 列宽 = %d" % int(app.cat_tree.column("#0", "width")))

print()
print("=" * 76)
print("选一个芯片组 → 栏2 应被填充")
print("=" * 76)
first_c = None
for p in plats:
    ks = app.cat_tree.get_children(p)
    if ks:
        first_c = ks[0]
        break
if first_c:
    app.cat_tree.selection_set(first_c)
    pump(root, 4)
    cs, boards = app.iid_chip[first_c]
    print("  选中 %r" % app.cat_tree.item(first_c, "text"))
    print("  栏2 行数 = %d（该组 boards = %d）"
          % (len(app.board_tree.get_children()), len(boards)))
    print("  栏2 计数标签 = %r" % app.v_board_n.get())
    print("  栏2 #0 列宽 = %d" % int(app.board_tree.column("#0", "width")))
    print("  栏2 前 3 行:")
    for iid in app.board_tree.get_children()[:3]:
        print("    %r" % app.board_tree.item(iid, "text"))
    print("  iid_board = %d 条" % len(app.iid_board))

print()
print("=" * 76)
print("栏3 表格列宽（420px 窗口下应不再截断）")
print("=" * 76)
app._fit_tv_cols()
pump(root, 4)
print("  表格容器 = %d" % app.tv.winfo_width())
print("  列宽 = %s" % [int(app.tv.column(c, "width"))
                       for c in ("ver", "date", "size", "note")])
print("  合计 = %d" % sum(int(app.tv.column(c, "width"))
                         for c in ("ver", "date", "size", "note")))

fails = []


def ck(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


print()
print("=" * 76)
print("搜索（q='z790'）应同时作用于两栏")
print("=" * 76)
app.v_search.set("z790")
pump(root, 10, 0.05)
app._search_q = "z790"
app._populate_tree()
pump(root, 6)
# ⚠ 必须重新取平台 iid —— _populate_tree 重建了整棵树，旧的 iid 全部失效
#（第一版探针就是拿旧 plats 去 get_children，抛 TclError: Item I001 not found）
plats2 = app.cat_tree.get_children("")
n_chip = sum(len(app.cat_tree.get_children(pp)) for pp in plats2)
print("  栏1 芯片组数 = %d" % n_chip)
print("  v_cat = %r" % app.v_cat.get())
print("  栏2 行数 = %d；v_board_n = %r"
      % (len(app.board_tree.get_children()), app.v_board_n.get()))

print()
print("=" * 76)
print("断言")
print("=" * 76)
ck(n_chip > 0, "搜索后栏 1 仍有命中芯片组（%d 个）" % n_chip)
ck(app.v_cat.get().startswith("命中"), "v_cat 显示为命中计数：%r" % app.v_cat.get())

root.destroy()


# ============================================================ 几何断言（三栏）
# 期望值来源：常量区宽度账（WIN_W 1440 -> body 内容宽 1360）
m._init_dpi()
m._apply_dpi_scale(m._DPI)
root, app = build(m.WIN_W, m.WIN_H, m._DPI)
app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
pump(root, 8)

print()
print("=" * 76)
print("三栏几何断言（1440×820）")
print("=" * 76)
# 映射是异步的（withdraw→deiconify 后 Windows 要几十毫秒才真正映射子控件），
# 先等到关键容器 ismapped 再读几何，避免 ismapped 类断言随机红。见 wait_mapped 注释。
wait_mapped(root, [app._split, app._split2, app._rf], timeout=3.0)
body_w = app._body.winfo_width()
content = body_w - m.S(m.BODY_PAD_X) * 2
nav = app._lf.winfo_width()
brd = app._mf.winfo_width()
det = app._rf.winfo_width()
sp1 = app._split.winfo_width()
sp2 = app._split2.winfo_width()

ck(nav + sp1 + brd + sp2 + det == content,
   "三栏 + 两条分隔条 = body 内容宽（%d + %d + %d + %d + %d = %d，应为 %d）"
   % (nav, sp1, brd, sp2, det, nav + sp1 + brd + sp2 + det, content))
ck(sp1 == m.S(m.SPLIT_W) and sp2 == m.S(m.SPLIT_W),
   "两条分隔条宽均 = S(SPLIT_W)（实测 %d / %d）" % (sp1, sp2))
ck(app._split.winfo_ismapped() and app._split2.winfo_ismapped(),
   "两条分隔条均已布局（ismapped）")
ck(app._split.winfo_height() == app._lf.winfo_height()
   and app._split2.winfo_height() == app._mf.winfo_height(),
   "分隔条高度与其左侧卡片同高")
# 栏宽必须落在各自 [MIN, MAX] 内（卡片宽口径）
ck(m.S(m.NAV_COL_MIN) <= nav <= m.S(m.NAV_COL_MAX),
   "栏 1 宽 %d 在 [%d, %d] 内" % (nav, m.S(m.NAV_COL_MIN), m.S(m.NAV_COL_MAX)))
ck(m.S(m.BOARD_COL_MIN) <= brd <= m.S(m.BOARD_COL_MAX),
   "栏 2 宽 %d 在 [%d, %d] 内" % (brd, m.S(m.BOARD_COL_MIN), m.S(m.BOARD_COL_MAX)))
ck(det >= m.S(m.DETAIL_MIN),
   "栏 3 宽 %d ≥ 保底 %d（BIOS 明细不被挤破）" % (det, m.S(m.DETAIL_MIN)))
# 栏 3 表格：四列必须装得下（这是三栏重构的核心收益）
# ⚠ 必须先喂数据：没加载主板时 _show_empty(True) 会把列表容器 grid_remove，
#   tv.winfo_width() 返回 1 —— 第一版探针就是漏了这步，断言拿 1 去比 754 而假红。
app._enter_loading("MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI")
app._apply_board(("MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI",
                  GROUPS, None, None, "com"))
pump(root, 6)
app._fit_tv_cols()
pump(root, 6)
_dz = getattr(app, "_detail_zone", None)
if _dz is not None:
    wait_mapped(root, [_dz], timeout=3.0)      # 同上：喂完数据后才映射
tvw = app.tv.winfo_width()
cols = [int(app.tv.column(c, "width")) for c in ("ver", "date", "size", "note")]
ck(sum(cols) <= tvw, "BIOS 表四列合计 %d ≤ 容器 %d（不横向溢出）" % (sum(cols), tvw))
ck(sum(cols) >= tvw - 8, "BIOS 表四列占满容器（%d / %d）" % (sum(cols), tvw))

# 底部工具条：跨三栏、在状态栏上方
abar = app._abar
ck(abar.winfo_width() >= content,
   "底部工具条跨全宽（%d ≥ %d）" % (abar.winfo_width(), content))
ck(app._arow.winfo_width() > 0 and app._prow.winfo_width() > 0,
   "工具条两行（操作行 / 进度行）均已布局")
ck(abar.winfo_rooty() > app._rf.winfo_rooty(),
   "工具条位于三栏卡片**下方**（工具条 y=%d > 卡片底 y=%d）"
   % (abar.winfo_rooty(), app._rf.winfo_rooty()))

# 详情面板存在且在栏 3 内
ck(hasattr(app, "_detail_zone") and app._detail_zone.winfo_ismapped(),
   "栏 3 详情面板已布局")

root.destroy()

print()
if fails:
    print("失败 %d 项：" % len(fails))
    for f in fails:
        print("  - " + f)
    raise SystemExit(1)
print("三栏体检 + 几何断言全部通过 ✓")

