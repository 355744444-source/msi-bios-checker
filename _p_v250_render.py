# -*- coding: utf-8 -*-
"""v2.5.0 三栏布局实拍渲染。"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

src = io.open(os.path.join(HERE, "_p_v230_render.py"), encoding="utf-8").read()
cut = src.index("# ---------------------------------------------------------------- 1) 空状态")
_ns = {"__name__": "_rp", "__file__": os.path.join(HERE, "_p_v230_render.py")}
exec(compile(src[:cut], "_rp", "exec"), _ns)
build, pump, shot = _ns["build"], _ns["pump"], _ns["shot"]
CAT, GROUPS = _ns["CAT"], _ns["GROUPS"]
import msi_bios_checker as m

SLUG, TITLE = "MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI"
m._init_dpi()
m._apply_dpi_scale(m._DPI)
root, app = build(m.WIN_W, m.WIN_H, m._DPI)
app._restored = True

app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
pump(root, 6)

# 选中含目标型号的芯片组 -> 栏2
ciid = app._nav_iid_of_slug(SLUG)
if ciid is None:
    for p in app.cat_tree.get_children(""):
        ks = app.cat_tree.get_children(p)
        if ks:
            ciid = ks[0]
            break
app.cat_tree.selection_set(ciid)
app.cat_tree.see(ciid)
pump(root, 6)
print("栏1 选中 = %r" % app.cat_tree.item(ciid, "text"))

# 栏2 选中目标型号 -> 栏3
pick = None
for iid, (s, _t) in app.iid_board.items():
    if s == SLUG:
        pick = iid
        break
if pick is None:
    ks = app.board_tree.get_children()
    pick = ks[0] if ks else None
if pick:
    app.board_tree.selection_set(pick)
    app.board_tree.see(pick)
    pump(root, 4)
    print("栏2 选中 = %r" % app.board_tree.item(pick, "text"))

app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, GROUPS, None, None, "com"))
pump(root, 6)
app._fit_tv_cols()
pump(root, 4)
rows = app.tv.get_children()
if len(rows) > 1:
    app.tv.selection_set(rows[1])
app._set_downloading(True)
app._dl_speed = 11.4 * 1048576
app._dl_progress(38.6 * 1048576, 67.1 * 1048576)
app._set_status("正在下载 7D89v1B1.zip …", "run")
app._toast_show("✓ 上一步：目录已更新（501 款主板 / 20 条中国站补录）", ok=True)
pump(root, 16, 0.05)
shot(root, "预览_1_三栏_1500x820.png")

app._toast_hide(animate=False)
pump(root, 4)
app._fit_progress_text()
pump(root, 8, 0.05)

print()
print("三栏几何：")
for nm, w in (("栏1 导航", app._lf), ("分隔条1", app._split),
              ("栏2 型号", app._mf), ("分隔条2", app._split2),
              ("栏3 明细", app._rf)):
    print("  %-10s x=%-5d w=%-5d" % (nm, w.winfo_x(), w.winfo_width()))
print("栏3 表格容器 = %d  列宽 = %s"
      % (app.tv.winfo_width(),
         [int(app.tv.column(c, "width")) for c in ("ver", "date", "size", "note")]))
shot(root, "预览_2_三栏无横幅_1500x820.png")

print()
print("收尾自检：")
print("  PASS 弹窗/弹簧无残留" if not app.anim.busy() else "  WARN 弹簧仍在跑")
root.destroy()
print("渲染完成")
