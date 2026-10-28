# -*- coding: utf-8 -*-
"""v2.3.0 重设计预览：把新版界面离屏渲染成 PNG（供人工评审）。

为什么不用"截图工具手工截"：手工截依赖窗口位置/遮挡/缩放，不可复现。这里在受控
尺寸下建窗、把状态摆到目标形态、等弹簧全部静止，再按 **客户区** 精确抓图，
同一命令任何时候跑出来的图都可逐像素比较。
"""
import ctypes
import io
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.getcwd()
sys.path.insert(0, HERE)

from PIL import ImageGrab                       # noqa: E402

import importlib.util                           # noqa: E402
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

import tkinter as tk                            # noqa: E402

u32 = ctypes.windll.user32
OUT = os.path.join(HERE, "预览图")
if not os.path.isdir(OUT):
    os.makedirs(OUT)

TMP = tempfile.mkdtemp(prefix="v230render_")
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
], "Beta BIOS": [
    {"download_version": "7D89v1D0(Beta)", "download_release": "2026-09-30",
     "download_size": 35912000, "download_url": "https://download.msi.com/bos_exe/mb/7D89v1D0.zip",
     "download_description": "Beta: support new CPU."},
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


def wait_mapped(root, widgets, timeout=3.0):
    """等这些控件全部 winfo_ismapped() 为真；超时返回 False。

    为什么需要：`build()` 走的是 withdraw() → deiconify()，映射是异步的；
    而且窗口由**后台进程**创建时，系统随时可能把它压成 iconic
    （实测 state=iconic、rooty=-32000，此时所有子控件 ismapped 全为 0）。
    探针原来只 pump 固定次数就断言 ismapped，会随机红：
    2026-10-28 实测同一份源码、同一解释器连跑 3 次得到 2 红 1 绿，
    失败项恒为「分隔条未布局 / 栏3 未布局」这两条 ismapped 断言。
    这里每轮先把窗口纠回 normal，再判条件；几何数值本身不受影响。
    """
    end = time.time() + timeout
    while time.time() < end:
        try:
            if root.state() != "normal":
                root.deiconify()
                root.state("normal")
                root.lift()
        except Exception:
            pass
        pump(root, 1, 0.02)
        if all(w.winfo_ismapped() for w in widgets):
            return True
    return False


def client_rect(root):
    """窗口**客户区**在屏幕上的物理像素矩形（DPI 感知下即屏幕像素）。"""
    import ctypes.wintypes as wt
    hwnd = u32.GetAncestor(root.winfo_id(), 2)      # GA_ROOT
    rc = wt.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(rc))
    pt = wt.POINT(0, 0)
    u32.ClientToScreen(hwnd, ctypes.byref(pt))
    return hwnd, (pt.x, pt.y, pt.x + rc.right, pt.y + rc.bottom)


def shot(root, name):
    hwnd, box = client_rect(root)
    u32.SetForegroundWindow(hwnd)
    root.lift()
    pump(root, 4, 0.05)
    img = ImageGrab.grab(bbox=box, all_screens=True)
    path = os.path.join(OUT, name)
    img.save(path)
    print("      %s  %dx%d  %d bytes" % (name, img.width, img.height,
                                         os.path.getsize(path)))
    return path


def build(w, h, dpi=96):
    root = tk.Tk()
    root.withdraw()
    # v2.4.0 更正顺序：_apply_dpi_scale 必须放在 tk.Tk() **之后**，与 main() 保持一致。
    # 它内部会重跑 _rebuild_fonts()，而 _ui_font_family() / _mono_family() 都要读 Tk 的
    # 字族列表 —— 在 Tk 之前调用只能拿到兜底首选值。旧顺序下 _ui_font_family() 的
    # 兜底恰好也是 "Microsoft YaHei UI"（与真实值相同）所以一直没露馅；v2.4.0 加了
    # 等宽读数 FONT_MONO 就暴露了：兜底是 Consolas，真值是 Cascadia Mono。
    m._apply_dpi_scale(dpi)
    app = m.App(root)
    app._restored = True
    cancel_all(root)
    root.geometry("%dx%d+40+40" % (w, h))
    root.deiconify()
    root.attributes("-topmost", True)
    pump(root)
    return root, app


m._init_dpi()
m._apply_dpi_scale(m._DPI)

# ---------------------------------------------------------------- 1) 空状态
print("=== [1] 空状态（首次打开）===")
root, app = build(1200, 780, m._DPI)
app._set_status("就绪", "info")
pump(root, 8)
shot(root, "预览_1_空状态_1200x780.png")

# ---------------------------------------------------------------- 2) 主界面
print("\n=== [2] 主界面：选中型号 + 下载进行中 + 结果横幅 ===")
app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
# 选中目录树里的一款主板（让左栏呈现"已使用"的样子）
pid = app.cat_tree.get_children("")
if pid:
    kids = app.cat_tree.get_children(pid[0])
    if kids:
        app.cat_tree.item(pid[0], open=True)
        app.cat_tree.selection_set(kids[0])
        app.cat_tree.see(kids[0])
pump(root, 4)
SLUG, TITLE = "MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI"
app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, GROUPS, None, None, "com"))
pump(root, 6)
app._fit_tv_cols()                  # 与真实运行一致：按容器比例分配列宽
pump(root, 4)
rows = app.tv.get_children()
if rows:
    app.tv.selection_set(rows[1] if len(rows) > 1 else rows[0])
app._set_downloading(True)
app._dl_speed = 11.4 * 1048576
app._dl_progress(38.6 * 1048576, 67.1 * 1048576)
app._set_status("正在下载 7D89v1B1.zip …", "run")
app._toast_show("✓ 上一步：目录已更新（501 款主板 / 20 条中国站补录）", ok=True)
pump(root, 14, 0.05)                # 让弹簧全部静止
shot(root, "预览_2_主界面下载中_1200x780.png")

# ---------------------------------------------------------------- 3) 窄窗口
print("\n=== [3] 最小支持窗口 1100×760（进度文案自动压短）===")
app._toast_hide(animate=False)
pump(root, 3)
# 缩到 1100 宽：目标是**客户区**尺寸，SetWindowPos 设的是外框 → 需加回边框
import ctypes.wintypes as _wt
hwnd, box = client_rect(root)
fr = _wt.RECT()
u32.GetWindowRect(hwnd, ctypes.byref(fr))
bx = (fr.right - fr.left) - (box[2] - box[0])
by = (fr.bottom - fr.top) - (box[3] - box[1])
u32.SetWindowPos(hwnd, 0, fr.left, fr.top, 1100 + bx, 760 + by, 0x0004 | 0x0010)
pump(root, 8, 0.05)
app._fit_progress_text()
pump(root, 6, 0.05)
shot(root, "预览_3_窄窗口1100.png")
print("      进度条容器宽 %dpx，进度文案%s"
      % (app._pbar_row.winfo_width(), "压短" if app._pb_compact else "完整"))

# ---------------------------------------------------------------- 3b) 宽屏
print("\n=== [3b] 宽屏 1600×900（左栏按比例变宽 + slug 副标题出现）===")
u32.SetWindowPos(hwnd, 0, fr.left, fr.top, 1600 + bx, 900 + by, 0x0004 | 0x0010)
pump(root, 10, 0.05)
app._fit_progress_text()
pump(root, 6, 0.05)
L = app._lf.winfo_width()
print("      左栏 %dpx 右栏 %dpx（v2.3.1：左栏比例项 %s）"
      % (L, app._rf.winfo_width(), "生效" if L > 420 else "未生效"))
print("      slug 副标题 %s" % ("显示" if not app._sub_hidden else "已被让路隐藏"))
print("      进度条 value=%.3f%% 宽=%dpx（图中填充比例应与此一致）"
      % (float(app.pb["value"]), app.pb.winfo_width()))
shot(root, "预览_4_宽屏1600.png")
# 缩回最小尺寸，后面的收尾断言仍按窄场景检查
u32.SetWindowPos(hwnd, 0, fr.left, fr.top, 1100 + bx, 760 + by, 0x0004 | 0x0010)
pump(root, 8, 0.05)
app._fit_progress_text()
pump(root, 4)

# ---------------------------------------------------------------- 4) 收尾
print("\n=== [4] 收尾 ===")
ck(len(app.tv.get_children()) >= 3, "主界面列表已渲染（%d 行）"
   % len(app.tv.get_children()))
ck(app.tv.winfo_width() > 400, "列表宽度正常（%d）" % app.tv.winfo_width())
bad = []


def walk(w, path="root"):
    for ch in w.winfo_children():
        p = "%s/%s" % (path, ch.winfo_class())
        if ch.winfo_manager() and ch.winfo_ismapped():
            if ch.winfo_width() < 1 or ch.winfo_height() < 1:
                bad.append("%s %dx%d" % (p, ch.winfo_width(), ch.winfo_height()))
        walk(ch, p)


walk(app._sky)
ck(not bad, "无 0 尺寸的已布局控件（%s）" % (bad[:3] or "OK"))
ck(not app.anim._items, "无残留的定时曲线动画（%r）" % (list(app.anim._items),))
# 状态点呼吸是有意常驻的（任务进行中"还在动"的反馈），只允许它一条
ck(set(app.anim._springs) <= {"dotp"},
   "除状态点呼吸外无在跑弹簧（%r）" % (sorted(app.anim._springs),))

try:
    root.destroy()
except Exception:
    pass
os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)

print("\n预览图目录：%s" % OUT)
for n in sorted(os.listdir(OUT)):
    print("  " + n)
print("\n" + ("预览渲染完成 ✓" if not fails
              else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
