# -*- coding: utf-8 -*-
"""v2.3.0 诊断：进度行的实际几何（进度条 / 文案标签 谁在挤谁）。

起因：重设计预览图里进度文案右端被截断成 "...(57"。可能的原因至少三种：
  1) 标签的字符格不够（_pb_label_chars 算出 43 格）
  2) tk.Canvas 的**默认请求宽度是 10cm ≈ 378px**（ttk.Progressbar 不是），
     我把进度条换成 Canvas 后请求宽度暴涨，把它右侧的标签挤了出去
  3) 文案实测像素宽 > 标签像素宽
这里把三者的实际数字全量打印出来，用数据定位。
"""
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import tkinter as tk

HERE = os.getcwd()
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

TMP = tempfile.mkdtemp(prefix="v230diag_")
shutil.copy(os.path.join(HERE, "msi_mb_catalog.json"),
            os.path.join(TMP, "msi_mb_catalog.json"))
os.chdir(TMP)
CAT = json.load(io.open(os.path.join(TMP, "msi_mb_catalog.json"), encoding="utf-8"))

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


m._init_dpi()
m._apply_dpi_scale(m._DPI)
root = tk.Tk()
root.withdraw()
app = m.App(root)
app._restored = True
cancel_all(root)
root.geometry("1200x780")
root.deiconify()
for _ in range(8):
    root.update_idletasks()
    root.update()

GROUPS = {"AMI BIOS": [
    {"download_version": "7D89v1C2", "download_release": "2026-09-18",
     "download_size": 35634176, "download_url": "http://x/a.zip",
     "download_description": "d"}]}
app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    root.update()
app._enter_loading("SLUG", "BOARD")
app._apply_board(("SLUG", "BOARD", GROUPS, None, None, "com"))
for _ in range(4):
    root.update()

app._pb_compact = False
app._dl_speed = 11.4 * 1048576
app._dl_progress(38.6 * 1048576, 67.1 * 1048576)
for _ in range(20):
    app._poll_queue()
    root.update_idletasks()
    root.update()

txt = app.v_pb.get()
grid = app._pb_label_chars(False)
one = app._pb_char_px()
label_px = app._pb_label_px(False)
real = int(root.tk.call("font", "measure", app._fm_tree, txt))
row_w = app._pbar_row.winfo_width()
pb_w = app.pb.winfo_width()
lbl_w = app.lbl_pb.winfo_width()
lbl_x = app.lbl_pb.winfo_x()
pb_x = app.pb.winfo_x()

print("=== 进度行几何（1200×780，DPI %d%%）===" % int(m.DPI_SCALE * 100))
print("  文案        %r" % txt)
print("  文案实测宽  %dpx" % real)
print("  字格基准    measure('0') = %dpx ；标签格 = %d 字符 = %dpx" % (one, grid, label_px))
print("  进度行容器  %dpx（x=%d, w=%d）" % (row_w, app._pbar_row.winfo_x(),
                                          app._pbar_row.winfo_width()))
print("  进度条      x=%d w=%d  （Canvas 默认请求宽 = %d）" % (pb_x, pb_w, app.pb.winfo_reqwidth()))
print("  文案标签    x=%d w=%d  （请求 %d）" % (lbl_x, lbl_w, app.lbl_pb.winfo_reqwidth()))
print("  标签右端    %d （容器右端 %d）" % (lbl_x + lbl_w, row_w))

print("\n=== 判据 ===")
ck(real <= label_px, "文案实测宽 %d ≤ 标签像素宽 %d" % (real, label_px))
ck(grid >= 43, "默认尺寸下标签格 %d ≥ 43" % grid)
ck(lbl_w >= app.lbl_pb.winfo_reqwidth(),
   "标签没被挤压：实际宽 %d ≥ 请求宽 %d（旧版被进度条挤到 309）"
   % (lbl_w, app.lbl_pb.winfo_reqwidth()))
ck(lbl_x + lbl_w <= row_w + 1,
   "标签完整落在进度行内（右端 %d ≤ %d）" % (lbl_x + lbl_w, row_w))
ck(real <= lbl_w, "文案 %dpx 真的装得进标签实际宽 %dpx（这才是不截断的充分条件）"
   % (real, lbl_w))
ck(pb_w >= m.S(m.PB_BAR_MIN),
   "进度条宽 %d ≥ 保底 %d" % (pb_w, m.S(m.PB_BAR_MIN)))
ck(app.pb.winfo_reqwidth() <= m.S(120),
   "进度条**请求宽度**已收敛（%dpx）—— Canvas 默认是 10cm≈378px，不显式设宽会挤走右侧标签"
   % app.pb.winfo_reqwidth())
ck(app.lbl_pb.winfo_reqwidth() <= app._pb_label_px(False) + m.S(m.PB_LBL_SLACK),
   "标签请求宽 %d ≤ _pb_label_px() %d + slack %d（像素占位与公式自洽，差 %dpx 已显式建模）"
   % (app.lbl_pb.winfo_reqwidth(), app._pb_label_px(False), m.S(m.PB_LBL_SLACK),
      app.lbl_pb.winfo_reqwidth() - app._pb_label_px(False)))

# ---- 极端：最长的完整文案（上界样例）
app.v_pb.set(m.PB_TXT_FULL)
root.update()
real2 = int(root.tk.call("font", "measure", app._fm_tree, m.PB_TXT_FULL))
print("\n  上界样例    %r" % m.PB_TXT_FULL)
print("  实测宽 %d ≤ 标签 %d" % (real2, label_px))
ck(real2 <= label_px, "上界样例也放得下（%d ≤ %d）" % (real2, label_px))

app.anim.cancel("dotp")
try:
    root.destroy()
except Exception:
    pass
os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("进程行几何全部通过 ✓" if not fails
              else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
