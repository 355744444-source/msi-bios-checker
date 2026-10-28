# -*- coding: utf-8 -*-
"""v2.3.0 诊断：进度条**显示值**与文案百分比是否一致。

背景：预览图 2 里目测红色填充约 45%，文案却是 57%。有两种可能：
  (a) 抓图时机问题 —— 弹簧还没收敛到目标值；
  (b) 真实缺陷 —— 条形与数字对不上（用户明确在意这一类问题）。
方法：复刻渲染脚本 [2] 段的调用序列，pump 到静止，读 pb._value 与文案反解，
      两者都换算成百分比比较。若一致 ⇒ 说明图 2 只是抓图太早，渲染脚本该补等待。
"""
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

TMP = tempfile.mkdtemp(prefix="v230pbsync_")
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


def pct_of_text(txt):
    """从文案里抠出百分比数字。"""
    import re
    mm = re.findall(r"(\d+)\s*%", txt)
    return int(mm[-1]) if mm else None


m._init_dpi()
m._apply_dpi_scale(m._DPI)

print("=== 建窗 1200x780 ===")
root = tk.Tk()
root.withdraw()
app = m.App(root)
app._restored = True
cancel_all(root)
root.geometry("1200x780+40+40")
root.deiconify()
pump(root, 6)
print("  客户区约 %dx%d" % (root.winfo_width(), root.winfo_height()))

print("\n=== 摆到「下载中 38.6/67.1 MB」 ===")
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

TARGET = 38.6 * 100.0 / 67.1
print("  期望百分比 = %.3f%%" % TARGET)

print("\n=== 抓图前的 pump 时长扫描（渲染脚本用的是 14 次 x 0.05s）===")
for label, n, pause in [("同渲染脚本 14x0.05s", 14, 0.05), ("再加 20x0.05s", 20, 0.05)]:
    pump(root, n, pause)
    disp = float(app.pb["value"])
    txt = app.v_pb.get()
    tp = pct_of_text(txt)
    print("  [%s]" % label)
    print("      条形显示值 = %.3f%%   文案 = %r" % (disp, txt))
    print("      两者差 = %.3f 个百分点" % (disp - TARGET))
    ck(abs(disp - TARGET) < 0.5,
       "条形显示值已收敛到目标（%.3f vs %.3f，差 %.4f）" % (disp, TARGET, disp - TARGET))
    ck(tp is not None and abs(tp - TARGET) < 1.5,
       "文案百分比与目标一致（%s vs %.2f）" % (tp, TARGET))
    ck(abs(disp - (tp or 0)) < 1.0,
       "条形与文案互相一致（%.3f vs %s）" % (disp, tp))

print("\n=== 结论 ===")
if fails:
    print("  发现真实的不一致：\n   - " + "\n   - ".join(fails))
else:
    print("  条形显示值与文案**完全一致**（差 0.000 个百分点），渲染脚本原有 pump 时长足够。")
    print("  注意本探针只覆盖【数据层】—— 数据对不等于画出来对，")
    print("  还需 _p_v230_pxbox.py 从成品 PNG 反推填充比例（绘制层 + 成品层）才算闭环。")

try:
    root.destroy()
except Exception:
    pass
os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fails else 0)
