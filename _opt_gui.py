# -*- coding: utf-8 -*-
"""v2.2.0 验证（三）：GUI 层 —— 并发行为、状态持久化、UI 布局。

在临时目录里跑（配置/日志/catalog 都在那儿），不污染项目目录。
"""
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import tkinter as tk

HERE = os.getcwd()
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

fails = []


def ck(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def pump(root, n=4):
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(0.03)


def settle(app, root, n=3):
    """排空「队列 + after」：_set_status / catalog 结果都是排队下发，
    测试里 cancel_all 掉了 _poll_queue，必须显式泵一次。"""
    for _ in range(n):
        app._poll_queue()
        pump(root, 2)
    cancel_all(root)


def cancel_all(root):
    for aid in root.tk.call("after", "info"):
        try:
            root.after_cancel(aid)
        except Exception:
            pass


TMP = tempfile.mkdtemp(prefix="optgui_")
shutil.copy(os.path.join(HERE, "msi_mb_catalog.json"), os.path.join(TMP, "msi_mb_catalog.json"))
os.chdir(TMP)
CAT = json.load(io.open(os.path.join(TMP, "msi_mb_catalog.json"), encoding="utf-8"))
CFG = os.path.join(TMP, "msi_bios_checker.cfg")

m._init_dpi()
m._apply_dpi_scale(m._DPI)
root = tk.Tk()
root.withdraw()
app = m.App(root)
cancel_all(root)
app._restored = True                     # 本测试自己控制目录树，不走"恢复上次型号"


def build(win_w, win_h, dpi=96):
    """按要求尺寸重建窗口（同一进程内重建 Tk）。"""
    global root, app
    try:
        root.destroy()
    except Exception:
        pass
    m._apply_dpi_scale(dpi)
    root = tk.Tk()
    root.withdraw()
    app = m.App(root)
    app._restored = True
    cancel_all(root)
    root.geometry("%dx%d" % (win_w, win_h))
    root.deiconify()
    pump(root)
    return root, app


print("=== [1] 在途计数（旧版布尔 busy 会让先结束者提前解禁）===")
app._inflight = 0
app._set_inflight(1)
app._set_inflight(1)
ck(str(app.btn_dl.cget("state")) == "disabled", "两条在途期间主按钮禁用")
app._set_inflight(-1)
ck(str(app.btn_dl.cget("state")) == "disabled",
   "其中一条结束（旧版布尔会在这里就解禁）→ 仍禁用")
app._set_inflight(-1)
# v2.5.5：主按钮的解禁条件除了「无在途」还要求「有选中且有下载链接」
# （文案也跟着版本号走，见 _sync_dl_btn）。旧版只切 state，空选状态下也会
# 解禁成可点 —— 点下去弹「请先选择版本」，是个假可用态。
ck(str(app.btn_dl.cget("state")) == "disabled",
   "全部结束后无选中 → 仍禁用（v2.5.5：不再出现假可用态）")
app._set_inflight(-1)
ck(app._inflight == 0, "计数不会变成负数")

print("\n=== [1b] 主按钮：有选中才解禁，文案带版本号 ===")
_FAKE_IT = {"download_version": "7D89v1C2", "download_url": "https://x/y.zip"}
app._iid_item["_probe"] = _FAKE_IT
app.tv.insert("", "end", iid="_probe", values=("7D89v1C2", "2026-09-18", "34.0 MB", "probe"))
app.tv.selection_set("_probe")
pump(root)
ck(str(app.btn_dl.cget("state")) == "normal", "选中带下载链接的版本 → 解禁")
ck("7D89v1C2" in str(app.btn_dl.cget("text")),
   "主按钮文案带版本号（%r）" % (app.btn_dl.cget("text"),))
ck(str(app.btn_dl.cget("bg")).lower() == m.C_ACCENT_BTN.lower(),
   "可用态底色为主按钮红")
app._set_inflight(1)
ck(str(app.btn_dl.cget("state")) == "disabled", "重新有在途 → 立刻禁用")
app._set_inflight(-1)
ck(str(app.btn_dl.cget("state")) == "normal", "在途结束后恢复")
app.tv.selection_remove("_probe")
pump(root)
ck(str(app.btn_dl.cget("state")) == "disabled", "取消选中 → 禁用")

print("\n=== [2] 目录抓取去重（4 个入口统一）===")
calls = []


def stub_catalog():
    calls.append(1)
    time.sleep(0.25)
    app.q.put(("catalog", CAT, None))


app._catalog_worker = stub_catalog
r1 = app._start_catalog()
r2 = app._start_catalog()
ck(r1 is True and r2 is False, "第一次启动返回 True，第二次被拒")
time.sleep(0.45)
settle(app, root)
ck(len(calls) == 1, "两次触发只真正抓取一次（实测 %d 次）" % len(calls))
ck(app._cat_busy is False, "抓取结束后在途标记自动释放")
r3 = app._start_catalog()
ck(r3 is True, "释放后可以再次启动")
time.sleep(0.45)
settle(app, root)

print("\n=== [3] 型号请求单飞 + 面板缓存 ===")
real_thread = threading.Thread
spawned = []


def fake_thread(*a, **k):
    spawned.append(1)
    return real_thread(*a, **k)


app._panel_inflight.clear()
app._panel_cache.clear()
threading.Thread = fake_thread
try:
    app._panel_inflight["SLUG-A"] = True
    app._load_board("SLUG-A", "测试板 A")
    ck(len(spawned) == 0, "同型号已在途 → 不再发第二次请求（旧版 A→B→A 会重发）")

    groups = {"AMI BIOS": [{"download_version": "1.0", "download_release": "2026-01-01",
                            "download_size": 1048576, "download_url": "http://x/y.zip",
                            "download_description": "说明"}]}
    app._panel_cache.put("SLUG-B", (time.time(), groups, None, "com"))
    spawned.clear()
    app._load_board("SLUG-B", "测试板 B")
    ck(len(spawned) == 0, "面板缓存命中 → 零网络请求")
    settle(app, root)
    ck(len(app.tv.get_children()) == 1, "命中缓存后列表已渲染（%d 行）"
       % len(app.tv.get_children()))
    ck("内存缓存" in app.v_status.get(), "状态栏标明来源为内存缓存（%r）" % app.v_status.get())

    app._panel_cache.clear()
    spawned.clear()
    app._load_board("SLUG-C", "测试板 C")
    ck(len(spawned) == 1, "无缓存时正常发起一次请求")
    ck("SLUG-C" in app._panel_inflight, "在途标记已登记")
    app._apply_board(("SLUG-C", "测试板 C", groups, None, None, "com"))
    ck("SLUG-C" not in app._panel_inflight, "结果到达后在途标记清除")
    ck(app._panel_cache.get("SLUG-C") is not None, "结果已写入内存缓存")
finally:
    threading.Thread = real_thread

print("\n=== [4] UI 布局：BIOS 表列宽按容器比例分配 ===")
for win, dpi in ((1200, 96), (1100, 96), (1800, 144)):
    root, app = build(win, 780 if win != 1800 else 1100, dpi)
    app._fit_tv_cols()
    pump(root)
    W = app._list_holder.winfo_width()
    cols = {c: int(str(app.tv.column(c, "width"))) for c in ("ver", "date", "size", "note")}
    mins = {"ver": 150, "date": 104, "size": 84, "note": 200}
    ok_sum = sum(cols.values()) <= W + m.S(6)
    ok_min = all(cols[c] >= m.S(mins[c]) - 1 for c in cols)
    ok_note = cols["note"] >= int(W * 0.45)
    ck(ok_sum and ok_min and ok_note,
       "%dx%d(dpi%d): 列宽 %s 容器 %d（合计不超宽=%s 不低最小=%s 说明列≥45%%=%s）"
       % (win, 1100 if win == 1800 else 780, dpi, cols, W, ok_sum, ok_min, ok_note))

m._apply_dpi_scale(96)
print("\n=== [5] UI 布局：型号标题超长省略 ===")
long_title = "MPG Z790 EDGE MONSTER HUNTER EDITION WIFI DDR5 " * 3
app._show_board_title(long_title)
pump(root)
shown = app.v_board_title.get()
ck(shown != long_title and shown.endswith("…"),
   "超长标题被省略（显示 %d 字 → %r）" % (len(shown), shown[:40]))
ck(app._title_full == long_title, "完整文本保留在 _title_full（供后续复制/展示）")
mn = m._ellipsize(long_title, m.S(300), app._fm_title, root)
ck(len(mn) < len(long_title), "省略函数按真实字模工作（%d → %d 字）" % (len(long_title), len(mn)))
app._show_board_title("B760M MORTAR")
ck(app.v_board_title.get() == "B760M MORTAR", "短标题原样显示")

print("\n=== [6] UI 布局：空状态垂直居中 ===")
app._show_empty(True, title="未选择")
pump(root)
H = app._list_holder.winfo_height()
cy = app._empty_inner.winfo_y() + app._empty_inner.winfo_height() / 2.0
ck(H > m.S(200) and abs(cy - H * 0.45) <= 10,
   "空状态块中心贴合容器 45%% 高度（实测 %.0f / %.0f，容器高 %d）" % (cy, H * 0.45, H))

print("\n=== [7] UI 布局：进度文案窄/宽窗口切换 ===")
# v2.5.0 重新基线：进度行已升为**跨三栏底部工具条**，不再受右卡片宽度约束。
# 旧版在 1100 窗口下进度行只有 670px（右卡片内），会被压短；现在有 1060px，
# 完整文案（上界 448px）绰绰有余 —— 「最小窗口必然压短」这个前提消失了。
root, app = build(1100, 760)
app._fit_progress_text()
ck(app._pb_compact is False,
   "最小窗口 1100 下进度行 %dpx 已够完整文案（工具条跨三栏的收益）"
   % app._pbar_row.winfo_width())
ck(int(str(app.lbl_pb.cget("width"))) == app._pb_label_chars(False),
   "标签宽度为完整文案字格（实测 %d 字符）" % int(str(app.lbl_pb.cget("width"))))
root, app = build(1500, 900)
app._fit_progress_text()
ck(app._pb_compact is False, "宽窗口 → 完整文案")
ck(int(str(app.lbl_pb.cget("width"))) == app._pb_label_chars(False),
   "标签宽度恢复完整文案字格（实测 %d 字符）" % int(str(app.lbl_pb.cget("width"))))
# ---- v2.2.2 回归门禁 ----
# v2.2.1 的实机日志出现过「进度文案压短（进度行 699px / 需要 728px）」：默认 1200×780
# 在「目录加载完成、左栏由 360 扩到 417px」之后进度行掉到 699px，被旧阈值 728px 击穿，
# 进度条**永久**降级成短文案 —— 而窗口其实够宽。这里把「默认尺寸必须显示完整文案」
# 钉成断言，防止再退化（判据见源码 _fit_progress_text / _pb_label_px）。
# v2.5.0：默认窗口从 1200×780 改为 1440×820（三栏装不下 1200），断言同步。
root, app = build(m.WIN_W, m.WIN_H)
app.q.put(("catalog", CAT, None))
settle(app, root)
app._fit_progress_text()
need = (m.S(12) + app._pb_label_px(False) + m.S(m.PB_LBL_SLACK)
        + m.S(m.PB_BAR_MIN))
ck(app._pb_compact is False,
   "默认 %d×%d + 目录已加载 → 完整文案（进度行 %dpx / 需 %dpx）"
   % (m.WIN_W, m.WIN_H, app._pbar_row.winfo_width(), need))
# v2.3.0：进度条由 ttk.Progressbar 换成自绘 Canvas（胶囊）后，必须按**控件的真实
# 宽度**断言。用公式反推是查不出"控件被邻居挤扁"的 —— 就踩过这个坑：Tk Canvas 的
# 默认请求宽是 10cm≈378px，把右侧文案标签挤到 309px（需要 391px）导致文案被裁。
bar = app.pb.winfo_width()
ck(bar >= m.S(m.PB_BAR_MIN),
   "默认尺寸下进度条实际宽 %dpx ≥ 保底 %dpx" % (bar, m.S(m.PB_BAR_MIN)))
ck(app.lbl_pb.winfo_width() >= app.lbl_pb.winfo_reqwidth(),
   "进度文案标签未被挤压（实际 %d ≥ 请求 %d）"
   % (app.lbl_pb.winfo_width(), app.lbl_pb.winfo_reqwidth()))
ck(app.lbl_pb.winfo_x() + app.lbl_pb.winfo_width() <= app._pbar_row.winfo_width() + 1,
   "进度文案标签完整落在进度行内（右端 %d ≤ %d）"
   % (app.lbl_pb.winfo_x() + app.lbl_pb.winfo_width(),
      app._pbar_row.winfo_width()))
txt_px = int(root.tk.call("font", "measure", app._fm_tree, app.v_pb.get() or "0"))
ck(txt_px <= app.lbl_pb.winfo_width(),
   "文案实测 %dpx 装得进标签实际 %dpx（不截断的充分条件）"
   % (txt_px, app.lbl_pb.winfo_width()))
ck(app.pb.winfo_reqwidth() <= m.S(120),
   "进度条请求宽度已收敛（%dpx ≤ %d）—— Canvas 默认请求宽是 10cm≈378px"
   % (app.pb.winfo_reqwidth(), m.S(120)))
app._pb_compact = True
app._dl_speed = 3 * 1048576
app._dl_progress(5 * 1048576, 10 * 1048576)
ck(app.v_pb.get().count("%") == 1 and "MB/s" in app.v_pb.get(),
   "短文案格式正确（%r）" % app.v_pb.get())
app._pb_compact = False
app._dl_speed = 3 * 1048576
app._dl_progress(5 * 1048576, 10 * 1048576)
ck("/" in app.v_pb.get() and "剩" in app.v_pb.get(),
   "完整文案格式正确（%r）" % app.v_pb.get())

print("\n=== [8] 布局体检：无幽灵控件 / 右栏不被挤压 ===")
root, app = build(1100, 760)
bad = []


def walk(w, path="root"):
    for ch in w.winfo_children():
        mgr = ch.winfo_manager()
        p = "%s/%s" % (path, ch.winfo_class())
        if mgr and ch.winfo_ismapped():
            if ch.winfo_width() < 1 or ch.winfo_height() < 1:
                bad.append("%s %dx%d" % (p, ch.winfo_width(), ch.winfo_height()))
        walk(ch, p)


walk(app._sky)
ck(not bad, "无 0 尺寸的已布局控件（%s）" % (bad[:3] or "OK"))
ck(app._rf.winfo_width() >= app._rf.winfo_reqwidth() or app._rf.winfo_width() > m.S(500),
   "右栏宽度充足（%d，请求 %d）" % (app._rf.winfo_width(), app._rf.winfo_reqwidth()))

print("\n=== [9] 目录树展开状态持久化 ===")
app.catalog = CAT
app._populate_tree()
pump(root)
pid = app.cat_tree.get_children("")[0]
cid = app.cat_tree.get_children(pid)[0]
app.cat_tree.item(cid, open=True)
app._on_cat_open()
name = re.sub(r"（\d+ 款）$", "", str(app.cat_tree.item(cid, "text"))).strip()
ck(name in (app.cfg.get("expanded") or []), "展开的芯片组已写入设置（%s）" % name)
loaded = json.load(io.open(CFG, encoding="utf-8"))
ck(name in (loaded.get("expanded") or []), "同一份记录已落盘")
app.cfg["expanded"] = [name]
app._populate_tree()
pump(root)
pid2 = app.cat_tree.get_children("")[0]
hit = [c for c in app.cat_tree.get_children(pid2)
       if str(app.cat_tree.item(c, "text")).startswith(name)]
# v2.5.0：三栏化后**芯片组已是叶子节点**（型号迁到栏 2），不再有展开状态；
# 平台节点恒以 open=True 插入，且 _populate_tree 不再套用 cfg.expanded。
# 原断言「重建后该芯片组仍保持展开」的前提消失 —— 改为断言平台节点恒展开。
_plats = app.cat_tree.get_children("")
ck(_plats and all(bool(app.cat_tree.item(_p, "open")) for _p in _plats),
   "重建目录树后 %d 个平台节点仍全部展开（芯片组已无展开态）" % len(_plats))

print("\n=== [10] 状态持久化：上次型号 / 保存目录 / 窗口几何 ===")
root, app = build(1200, 780, 96)     # 固定 100% 缩放：几何按设计像素存取
app._enter_loading("MPG-Z790-EDGE", "MPG Z790 EDGE")
pump(root)
cfg = json.load(io.open(CFG, encoding="utf-8"))
ck(cfg.get("last_slug") == "MPG-Z790-EDGE", "上次查看的型号已落盘（%r）" % cfg.get("last_slug"))
app._persist(last_dir="D:\\biosdl")
app.last_dir = "D:\\biosdl"
root.geometry("1300x820")
pump(root)
before = (root.winfo_width(), root.winfo_height())
app._on_close()                      # 触发关窗保存（会 destroy）
cfg = json.load(io.open(CFG, encoding="utf-8"))
win = cfg.get("win")
ck(isinstance(win, list) and len(win) == 4 and win[0] > 0 and win[1] > 0,
   "关窗时窗口几何已落盘 %r（实际 %dx%d）" % (win, before[0], before[1]))

root2 = tk.Tk()
root2.withdraw()
app2 = m.App(root2)
cancel_all(root2)
root2.deiconify()
pump(root2)
geo = root2.geometry()
ck(geo.startswith("%dx%d" % (win[0], win[1])),
   "重启后恢复上次窗口尺寸（期望 %dx%d，实测 %s）" % (win[0], win[1], geo))
ck(app2.last_dir == "D:\\biosdl", "重启后恢复上次保存目录（%r）" % app2.last_dir)
ck(app2.v_dir.get() == "D:\\biosdl", "保存目录已显示在界面上（%r）" % app2.v_dir.get())
try:
    root2.destroy()
except Exception:
    pass

os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("全部通过 ✓" if not fails else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
