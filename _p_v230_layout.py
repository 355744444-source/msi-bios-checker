# -*- coding: utf-8 -*-
"""v2.3.x 布局体检：量出主窗口的布局树、真实几何与「行距节奏」。

为什么不用肉眼看预览图："有点挤/有点空"是主观描述，改不出确定的数值。
先把每个容器的 x/y/w/h、卡片内边距、行间距序列、列宽合计全部落成数字，
任何"布局调整"都先有基线，改完再拿同一张表对比（同一命令可复现）。

用法：
  python _p_v230_layout.py             # 1200x780（最小支持尺寸）
  python _p_v230_layout.py -w 1440 -H 900
"""
import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import time

import importlib.util

HERE = os.getcwd()
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

import tkinter as tk                            # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("-w", type=int, default=1200)
ap.add_argument("-H", "--height", type=int, default=780)
args = ap.parse_args()

TMP = tempfile.mkdtemp(prefix="v230layout_")
shutil.copy(os.path.join(HERE, "msi_mb_catalog.json"),
            os.path.join(TMP, "msi_mb_catalog.json"))
os.chdir(TMP)
CAT = json.load(io.open(os.path.join(TMP, "msi_mb_catalog.json"), encoding="utf-8"))
GROUPS = {"AMI BIOS": [
    {"download_version": "7D89v1C2", "download_release": "2026-09-18",
     "download_size": 35634176, "download_url": "https://download.msi.com/bos_exe/mb/7D89v1C2.zip",
     "download_description": "Improve memory compatibility and system stability."},
    {"download_version": "7D89v1B1", "download_release": "2026-06-02",
     "download_size": 34575400, "download_url": "https://download.msi.com/bos_exe/mb/7D89v1B1.zip",
     "download_description": "Update CPU microcode. Fix S3 resume issue."},
    {"download_version": "7D89v1A0", "download_release": "2026-03-11",
     "download_size": 33891200, "download_url": "https://download.msi.com/bos_exe/mb/7D89v1A0.zip",
     "download_description": "First release."},
]}


def cancel_all(root):
    for aid in root.tk.call("after", "info"):
        try:
            root.after_cancel(aid)
        except Exception:
            pass


def pump(root, n=6, pause=0.03):
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(pause)


m._init_dpi()
m._apply_dpi_scale(m._DPI)

root = tk.Tk()
root.withdraw()
app = m.App(root)
app._restored = True
cancel_all(root)
root.geometry("%dx%d+40+40" % (args.w, args.height))
root.deiconify()
pump(root, 6)

app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
SLUG, TITLE = "MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI"
app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, GROUPS, None, None, "com"))
pump(root, 6)
app._fit_tv_cols()
pump(root, 4)
rows = app.tv.get_children()
if rows:
    app.tv.selection_set(rows[1] if len(rows) > 1 else rows[0])
app._set_downloading(True)
app._dl_speed = 11.4 * 1048576
app._dl_progress(38.6 * 1048576, 67.1 * 1048576)
app._toast_show("✓ 上一步：目录已更新（501 款主板 / 20 条中国站补录）", ok=True)
pump(root, 10, 0.05)

CW, CH = root.winfo_width(), root.winfo_height()
print("=" * 82)
print("窗口客户区 = %dx%d    DPI=%s    缩放 S(1)=%.3f" % (CW, CH, m._DPI, m.S(1)))
print("=" * 82)


def g(w):
    try:
        return (w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height())
    except Exception:
        return None


def row(label, w, indent=2, ref=None):
    v = g(w)
    if v is None:
        return None
    x, y, ww, hh = v
    extra = ""
    if ref is not None:
        extra = "  (左距 %d)" % (x - ref[0])
    print("%s%-22s %-11s x=%-5d y=%-5d w=%-5d h=%-5d%s"
          % (" " * indent, label, w.winfo_class(), x, y, ww, hh, extra))
    return v


print("\n【A】顶层骨架（坐标相对客户区）")
sky = row("_sky", app._sky, 0)
brand = row("_brand(渐隐条)", app._brand)
body = row("_body", app._body, 0)
lf = row("_lf 左卡片", app._lf, 0)
split = row("_split 分隔条", app._split, 0)
rf = row("_rf 右卡片", app._rf, 0)

print("\n【B】头部区")
for ch in app._sky.winfo_children():
    if ch.winfo_class() == "TFrame" and ch.winfo_y() > (brand[1] + brand[3]) \
            and ch.winfo_y() < body[1]:
        row("head", ch)
        for c2 in ch.winfo_children():
            row("  └", c2, 8)
        break
row("btn_settings", app.btn_settings)

print("\n【C】左卡片内部（目录树）")
row("_search_wrap", app._search_wrap, 4)
row("ent_search", app.ent_search, 6)
row("cat_tree", app.cat_tree, 4)
row("btn_cat_refresh", app.btn_cat_refresh, 4)

print("\n【D】右卡片内部（相对右卡片原点，行距才有意义）")
rx0, ry0 = app._rf.winfo_rootx(), app._rf.winfo_rooty()


def rel(w):
    """把控件换算成「相对右卡片原点」的矩形 —— 子控件的 winfo_x/y 是相对各自
    父容器的，直接相减会得到负数（这是本探针第一版的 bug）。"""
    return (w.winfo_rootx() - rx0, w.winfo_rooty() - ry0,
            w.winfo_width(), w.winfo_height())


seq = []
for label, w in (("_title_row", app._title_row),
                 ("_list_zone", app._list_zone),
                 ("tv(BIOS列表)", app.tv),
                 ("orow(操作行)", app.btn_pick.master),
                 ("_pbar_row", app._pbar_row),
                 ("_toast(横幅)", app._toast)):
    x, y, ww, hh = rel(w)
    print("    %-16s x=%-5d y=%-5d w=%-5d h=%-5d" % (label, x, y, ww, hh))
    seq.append((label, (x, y, ww, hh)))

print("\n    行距（上一行的下边缘 → 下一行的上边缘）：")
for i in range(1, len(seq)):
    a, b = seq[i - 1][1], seq[i][1]
    print("      %-14s → %-14s  %+d px" % (seq[i - 1][0], seq[i][0],
                                           b[1] - (a[1] + a[3])))

print("\n【D2】右卡片内的固定行高（决定「底部区域占多高」）")
for label, w in (("btn_pick", app.btn_pick), ("btn_open_dir", app.btn_open_dir),
                 ("btn_cancel", app.btn_cancel), ("btn_dl(主按钮)", app.btn_dl),
                 ("_pbar_row", app._pbar_row), ("pb(胶囊条)", app.pb),
                 ("lbl_pb(文案)", app.lbl_pb)):
    x, y, ww, hh = rel(w)
    print("    %-16s x=%-5d y=%-5d w=%-5d h=%-5d" % (label, x, y, ww, hh))

# 左右卡片底部剩余空间（**全部用相对右卡片的坐标**；混用相对/绝对坐标会算出假数据）
print("\n【D3】右卡片纵向留白")
tb = rel(app._toast)
print("    右卡片高 %d，最后一行(_toast)底 %d ⇒ 卡片底部内边距 = %d px（S(16)=%d）"
      % (app._rf.winfo_height(), tb[1] + tb[3],
         app._rf.winfo_height() - (tb[1] + tb[3]), m.S(16)))
tz = rel(app._list_zone)
to = rel(app.btn_pick.master)
print("    列表区底 %d ⇒ 操作行顶 %d：中间 %d px = 分隔线(1) + 行距"
      % (tz[1] + tz[3], to[1], to[1] - (tz[1] + tz[3])))
tp = rel(app._pbar_row)
print("    操作行底 %d ⇒ 进度行顶 %d：间距 %d px"
      % (to[1] + to[3], tp[1], tp[1] - (to[1] + to[3])))

print("\n【E】左右栏比例与外边距")
bx, by, bw, bh = body
lx, ly, lw, lh = lf
rx, ry, rw, rh = rf
print("  左栏宽 = %d px    右栏宽 = %d px" % (lw, rw))
print("  左:右  = %.1f%% : %.1f%%" % (100.0 * lw / (lw + rw), 100.0 * rw / (lw + rw)))
print("  _body 左外边距(到左卡片) = %d px   右外边距 = %d px"
      % (lx - bx, bx + bw - (rx + rw)))
print("  两卡片之间的分隔条宽 = %d px（v2.3.1：可拖拽；原为 12px 固定空隙）"
      % (rx - (lx + lw)))
_rf_bottom_rel = ly + lh          # 卡片底（相对 body）
print("  body 高 %d：卡片顶 y=%d、底 y=%d ⇒ 上留白 %d px，下留白 %d px"
      % (bh, ly, _rf_bottom_rel, ly, bh - _rf_bottom_rel))
print("    （body 的 padding 是 (左%d, 上%d, 右%d, 下%d)，实测与之相符）"
      % (m.S(20), m.S(8), m.S(20), m.S(6)))
print("  卡片内边距 = S(16) = %d px（实测内容起点偏移应等于它）" % m.S(16))
print("  左卡片内容左起 = %d px" % (app.cat_tree.winfo_x()))

print("\n【F】列表列宽")
cols = list(app.tv["columns"])
ws = [int(app.tv.column(c, "width")) for c in cols]
print("  列          = %s" % cols)
print("  列宽        = %s" % ws)
print("  合计        = %d px     tv 实际宽 = %d px    差 = %d px"
      % (sum(ws), app.tv.winfo_width(), app.tv.winfo_width() - sum(ws)))
try:
    _tv_row_h = int(root.tk.call("ttk::style", "lookup", "Treeview", "-rowheight"))
except Exception:
    _tv_row_h = 0
print("  rowheight   = %s px   可视高 %d px → 约 %.1f 行"
      % (_tv_row_h, app.tv.winfo_height(), app.tv.winfo_height() / float(_tv_row_h or 1)))

print("\n【G】纵向空间账（客户区高度 %d）" % CH)
used = [("头部+品牌条", brand[3] + (body[1] - (brand[1] + brand[3]))),
        ("body", bh),
        ("状态栏区", CH - (body[1] + bh))]
acc = 0
for name, h in used:
    acc += h
    print("  %-14s %5d px   (%4.1f%%)" % (name, h, 100.0 * h / CH))
print("  %-14s %5d px" % ("合计", acc))
print("  左卡片高 %d px（占 body %.0f%%）  右卡片高 %d px" % (lh, 100.0 * lh / bh, rh))
print("\n布局体检完成（纯度量，无断言）")
try:
    root.destroy()
except Exception:
    pass
os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(0)
