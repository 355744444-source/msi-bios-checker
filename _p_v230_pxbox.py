# -*- coding: utf-8 -*-
"""v2.3.0 诊断：用**控件真实屏幕几何**在预览图里精确采样进度条。

前两次尝试的教训：
  - 只信内部状态（pb["value"]=57.526）—— 证明不了"画出来"是对的；
  - 盲扫"红色最多的行"—— 取到了别的红色元素（按钮/反锯齿文字），得出 97.7% 的假结论。
所以这里先问 Tk 要进度条的**真实屏幕矩形**，再把客户区原点减掉，得到图内坐标，
最后只在该矩形内逐列判断"这一列有没有红色填充"。这样既不会认错元素，也不会算错分母。
"""
import argparse
import ctypes
import io
import json
import os
import shutil
import sys
import tempfile
import time

import ctypes.wintypes as wt
import importlib.util

ap = argparse.ArgumentParser()
ap.add_argument("-w", type=int, default=1200)
ap.add_argument("-H", "--height", type=int, default=780)
ap.add_argument("-i", "--image", default="预览_2_主界面下载中_1200x780.png")
ap.add_argument("--no-toast", action="store_true",
                help="构建时不显示结果横幅。横幅在弹性行的下游，会把列表区压小、"
                     "进度条随之上移；采样行必须与目标预览图的状态一致")
args = ap.parse_args()

HERE = os.getcwd()
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

import tkinter as tk                            # noqa: E402

u32 = ctypes.windll.user32
TMP = tempfile.mkdtemp(prefix="v230px_")
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
]}
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


def pump(root, n=6, pause=0.03):
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
    return hwnd, pt.x, pt.y


def pix(img, x, y):
    px = img.get(x, y)
    if isinstance(px, str):
        return tuple(int(t) for t in px.split())
    return tuple(px)


def is_red(c):
    r, g, b = c
    return r > 110 and r > g + 45 and r > b + 45


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
app._set_status("正在下载 7D89v1B1.zip …", "run")
if not args.no_toast:
    app._toast_show("✓ 上一步：目录已更新（501 款主板 / 20 条中国站补录）", ok=True)
pump(root, 14, 0.05)

hwnd, cx0, cy0 = client_rect(root)
# 进度条相对**客户区**的矩形（图内坐标）
bx = app.pb.winfo_rootx() - cx0
by = app.pb.winfo_rooty() - cy0
bw, bh = app.pb.winfo_width(), app.pb.winfo_height()
print("客户区原点 (屏幕) = (%d, %d)" % (cx0, cy0))
print("进度条  图内矩形 x=%d y=%d w=%d h=%d（客户区实际 %dx%d）"
      % (bx, by, bw, bh, root.winfo_width(), root.winfo_height()))
disp = float(app.pb["value"])
print("条形显示值 = %.4f%%   文案 = %r" % (disp, app.v_pb.get()))

path = os.path.join(HERE, "预览图", args.image)
if os.path.isfile(path):
    img = tk.PhotoImage(file=path)
    print("\n读回预览图 %dx%d" % (img.width(), img.height()))
    ymid = by + bh // 2
    # 只扫进度条的纵向中线上那一行、且在进度条横向范围内 —— 绝不越界认错元素
    seq = []
    for x in range(bx, bx + bw):
        seq.append(is_red(pix(img, x, ymid)))
    nred = sum(seq)
    first_red = seq.index(True) if True in seq else None
    last_red = (len(seq) - 1 - seq[::-1].index(True)) if True in seq else None
    print("  采样行 y=%d（进度条纵向中线）" % ymid)
    print("  该行进度条范围内红色列数 = %d / %d" % (nred, bw))
    if first_red is not None:
        print("  红色区间 x %d..%d（相对进度条左端 %d..%d）"
              % (bx + first_red, bx + last_red, first_red, last_red))
    got = 100.0 * nred / bw if bw else 0.0
    print("  ⇒ 实测填充 %.2f%%   期望 %.2f%%" % (got, disp))
    ck(abs(got - disp) < 3.0, "图中填充与显示值一致（%.2f vs %.2f）" % (got, disp))
    # 顺带验证圆角：胶囊左端第 1 列应比中线窄
    col_h = 0
    for yy in range(by, by + bh):
        if is_red(pix(img, bx + 1, yy)):
            col_h += 1
    ck(col_h < bh, "左端首列红高 %d < 进度条高 %d（圆头存在）" % (col_h, bh))
else:
    print("找不到预览图 %s" % path)

try:
    root.destroy()
except Exception:
    pass
os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("像素几何验证通过 ✓" if not fails else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
