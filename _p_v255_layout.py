# -*- coding: utf-8 -*-
"""v2.5.5 门禁：右栏表高自适应 / 标题测量口径 / 主操作唯一 / footer 让路。

这批改动全部是「观感 + 让路优先级」，没有一条能被字符串断言直接证明，
所以这里全部落到**实测几何与实测配置**上，并且每条都写清「旧版会怎样」——
避免写成恒真式。

七个判据（任一 FAIL 即整体 FAIL）：

  1. 标题测量字体与渲染字体同族 / 同字号 / 同字重
     旧版 `font create` 漏了 `-weight bold`：measure 299px，实际 reqwidth 322px，
     23px 缺口让「测着放得下」的名字被硬切。判据是两者的差 <= TITLE_MEASURE_SLACK。
  2. 1180 最小窗下，标题要么完整、要么带省略号 —— 不允许硬切
     旧版在 1180 下标题被砍成「MPG Z790 EDGE TI WI」，且徽章一个像素都不让。
  3. 3 行数据时表高 == 3 行 + 表头（误差 2px），余量沉到卡片底部
     旧版 weight=1，表高 368px、表内 278px 空白（75%）。
  4. 12 行数据时详情区底部不得越出卡片内边界
     旧版 TV_HEAD_H=26（实测 43），多算半行，详情区被顶出卡片 11px。
  5. 主操作唯一：详情槽按钮不得使用主按钮红；底部主按钮禁用/可用两态底色必须不同
     旧版详情槽和工具条各有一个亮红按钮，禁用态与可用态同为亮色。
  6. 栏 2 footer 两段文案之和不得超出 footer 宽（旧版硬切成「目录：2026-10-」）
  7. 喂 `{}`（有页面、无 BIOS 分组）不得停在「查询中」
     旧版 parse_bios_groups 返回 {} 时 self.badges[0] 抛 IndexError，被 _dispatch
     的 except 吞掉 —— 不报错、不恢复，界面永久「查询中」。

用法：
    CODEBUDDY_SESSION_ID= CLAUDE_SESSION_ID= PYTHONPATH=_testenv <py> _p_v255_layout.py
输出纯 ASCII，失败行以 FAIL 开头（_gate_all.py 靠这个判据）。
"""
import ctypes
import ctypes.wintypes as wt
import importlib.util
import os
import shutil
import sys
import tempfile
import time
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

FAILS = []


def check(name, ok, detail=""):
    print("  %-46s %s%s" % (name, "ok" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


TMP = tempfile.mkdtemp(prefix="v255gate_")
shutil.copy(os.path.join(HERE, "msi_mb_catalog.json"),
            os.path.join(TMP, "msi_mb_catalog.json"))
os.chdir(TMP)


def groups(n):
    return {"AMI BIOS": [
        {"download_version": "7D89v1C%d" % (9 - i),
         "download_release": "2026-09-%02d" % (18 - i),
         "download_size": 35634176 + i,
         "download_url": "https://download.msi.com/bos_exe/mb/7D89v1C%d.zip" % (9 - i),
         "download_description": ("Improve memory compatibility and system stability. "
                                  "Update CPU microcode. Fix S3 resume issue. "
                                  "Support new Ryzen 9000 series processors.")}
        for i in range(n)
    ]}


root = tk.Tk()
root.withdraw()
m._apply_dpi_scale(96)          # 固定 1.0 缩放，几何断言才有确定值
app = m.App(root)
app._restored = True
for aid in root.tk.call("after", "info"):
    try:
        root.after_cancel(aid)
    except Exception:
        pass
root.geometry("1500x820+40+40")
root.deiconify()


def pump(n=8, pause=0.03):
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(pause)


pump()
TITLE = "MPG Z790 EDGE TI WIFI"
SLUG = "MPG-Z790-EDGE-TI-WIFI"

u32 = ctypes.windll.user32


def resize(cw, ch):
    hwnd = u32.GetAncestor(root.winfo_id(), 2)
    fr = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(fr))
    rc = wt.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(rc))
    bx = (fr.right - fr.left) - rc.right
    by = (fr.bottom - fr.top) - rc.bottom
    u32.SetWindowPos(hwnd, 0, fr.left, fr.top, cw + bx, ch + by, 0x0004 | 0x0010)
    pump(14)


# ---------------------------------------------------------------- 1 字体口径
print("[1] title measure font matches Board.TLabel")
# 不能直接比 `-size == -26`：Tk 的 `font actual -size` 会把像素尺寸**换算成磅**
# 再返回（-26px @96dpi → 19pt），直接比会误报。做法是现场用 FONT_BOARD 建一个
# 参照字体，两边都走 font actual 归一化，再逐属性比 —— 这样比的是"同一个字体描述"，
# 而不是两种量纲。
_ref = "v255RefBoard"
try:
    root.tk.call("font", "delete", _ref)
except Exception:
    pass
try:
    root.tk.call("font", "create", _ref,
                 "-family", m.FONT_BOARD[0], "-size", m.FONT_BOARD[1],
                 "-weight", m.FONT_BOARD[2])
except Exception as e:
    print("  reference font create err: %r" % (e,))
for opt in ("-family", "-size", "-weight", "-slant", "-underline"):
    try:
        a = str(root.tk.call("font", "actual", app._fm_title, opt))
        b = str(root.tk.call("font", "actual", _ref, opt))
        check("%s %r == %r" % (opt, a, b), a == b)
    except Exception as e:
        check("%s readable" % opt, False, repr(e))
# 再加一条不看描述、只看结果的：两字体渲染同一串的宽度必须一致（容差 0）
try:
    ma = int(root.tk.call("font", "measure", app._fm_title, TITLE))
    mb = int(root.tk.call("font", "measure", _ref, TITLE))
    check("measure(%s) equal: %d == %d" % ("title font", ma, mb), ma == mb)
except Exception as e:
    check("measure comparable", False, repr(e))
try:
    root.tk.call("font", "delete", _ref)
except Exception:
    pass

# ---------------------------------------------------------------- 数据上屏
app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, groups(3), None, None, "com"))
pump()
app._fit_tv_cols()
pump(4)
rows = app.tv.get_children()
if rows:
    app.tv.selection_set(rows[0])
    app.tv.focus(rows[0])
pump()
app._fit_tv_height()
pump(4)

# ---------------------------------------------------------------- 2 measure 余量
print("[2] measure vs real reqwidth gap <= TITLE_MEASURE_SLACK")
try:
    meas = int(root.tk.call("font", "measure", app._fm_title, TITLE))
    real = app.lbl_board_title.winfo_reqwidth()
    gap = real - meas
    check("gap=%d <= %d" % (gap, m.TITLE_MEASURE_SLACK),
          0 <= gap <= m.TITLE_MEASURE_SLACK, "measure=%d reqwidth=%d" % (meas, real))
except Exception as e:
    check("gap measurable", False, repr(e))

# ---------------------------------------------------------------- 3 表高 = 3 行
print("[3] 3 rows -> table height == 3 rows + header")
try:
    tv_h = app.tv.winfo_height()
    head = app.tv.winfo_reqheight() - (app._tv_h or 3) * m.S(m.TV_ROWH)
    want = 3 * m.S(m.TV_ROWH) + head
    check("tv_h=%d == %d (+-2)" % (tv_h, want), abs(tv_h - want) <= 2)
    rf_h = app._rf.winfo_height()
    dz = app._detail_zone
    bottom = dz.winfo_y() + dz.winfo_height()
    check("detail bottom %d <= card %d" % (bottom, rf_h - m.S(16)), bottom <= rf_h - m.S(16) + 1)
    spare = rf_h - m.S(16) - bottom
    check("spare >= 0 (%d)" % spare, spare >= 0)
except Exception as e:
    check("3-row geometry", False, repr(e))

# ---------------------------------------------------------------- 5 主操作唯一
print("[4] primary action is unique")
try:
    check("detail button not accent red",
          str(app.btn_det_dl.cget("bg")).lower() != m.C_ACCENT_BTN.lower(),
          "bg=%s" % app.btn_det_dl.cget("bg"))
    check("bottom button enabled (selected)",
          str(app.btn_dl.cget("state")) == "normal" and
          str(app.btn_dl.cget("bg")).lower() == m.C_ACCENT_BTN.lower(),
          "state=%s bg=%s" % (app.btn_dl.cget("state"), app.btn_dl.cget("bg")))
    check("bottom button text carries version",
          str(app.btn_dl.cget("text")).startswith("下载 7D89"),
          "text=%r" % app.btn_dl.cget("text"))
    app.tv.selection_remove(*app.tv.selection())
    pump()
    app._show_detail(None)
    pump()
    check("bottom button disabled (no selection)",
          str(app.btn_dl.cget("state")) == "disabled" and
          str(app.btn_dl.cget("bg")).lower() == m.C_ACCENT_BTN_DIS.lower(),
          "state=%s bg=%s" % (app.btn_dl.cget("state"), app.btn_dl.cget("bg")))
except Exception as e:
    check("primary button states", False, repr(e))

# ---------------------------------------------------------------- 2' 1180 标题
print("[5] 1180x760: title not hard-cut, badge yields first")
resize(1180, 760)
app._fit_board_title()
pump(6)
try:
    shown = app.v_board_title.get()
    lw = app.lbl_board_title.winfo_width()
    req = app.lbl_board_title.winfo_reqwidth()
    check("title fits its label (no hard cut)", lw >= req - 1, "w=%d reqw=%d shown=%r" % (lw, req, shown))
    check("shown is full or ellipsized",
          shown == TITLE or shown.endswith("\u2026"), "shown=%r" % (shown,))
    check("badge yielded (hidden) at 1180", bool(getattr(app, "_host_hidden", False)),
          "host_hidden=%r" % (getattr(app, "_host_hidden", None),))
    check("open-site button still visible",
          bool(app.btn_openpage.winfo_manager()) and app.btn_openpage.winfo_width() > m.S(60),
          "w=%d" % app.btn_openpage.winfo_width())
except Exception as e:
    check("1180 title", False, repr(e))

# ---------------------------------------------------------------- 6 footer 让路
print("[6] column-2 footer must not clip (1180 narrow / 1500 wide)")
FULL_UPD = "目录: 2026-10-07 11:46"


def _pw(s):
    if not s:
        return 0
    return int(root.tk.call("font", "measure", app._fm_mono, s))


def _footer_state():
    # 必须同时驱动**真源**：_fit_mfoot 从 self.cat_updated 取完整串，
    # 只改显示变量的话它什么都不做（第一版门禁就是这么假绿的）。
    app.cat_updated = "2026-10-07 11:46"
    app.v_cat.set("共 501 款")
    app.v_cat_upd.set(FULL_UPD)
    pump(4)
    app._fit_mfoot()
    pump(4)
    fw = app._mfoot.winfo_width()
    cat_w = app._lbl_cat.winfo_reqwidth()
    return fw, cat_w, app.v_cat_upd.get()


try:
    gap = m.S(14)
    fw, cat_w, shown = _footer_state()
    fits_full = cat_w + gap + _pw(FULL_UPD) <= fw
    check("1180: content %d <= footer %d" % (cat_w + gap + _pw(shown), fw),
          cat_w + gap + _pw(shown) <= fw, "shown=%r" % (shown,))
    if fits_full:
        check("1180: full timestamp kept (fits)", shown == FULL_UPD, "shown=%r" % (shown,))
    else:
        check("1180: degraded instead of clipped",
              bool(shown) and shown != FULL_UPD, "shown=%r" % (shown,))
        check("1180: date part survived",
              shown.rstrip(")").replace("目录: ", "").replace("目录 ", "")[:4].isdigit(),
              "shown=%r" % (shown,))
    resize(1500, 820)
    fw2, cat_w2, shown2 = _footer_state()
    check("1500: full timestamp restored", shown2 == FULL_UPD, "shown=%r" % (shown2,))
except Exception as e:
    check("footer fit", False, repr(e))

# ---------------------------------------------------------------- 4 12 行不溢出
print("[7] 12 rows @1180: detail must stay inside the card")
# 必须回到最小窗再压：1500 宽下 12 行只是「表变高」，永远塞得下，
# 断言会因为「没到边界」而恒真。1180x760 才是旧版把详情顶出卡片的那个尺寸。
resize(1180, 760)
app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, groups(12), None, None, "com"))
pump(6)
app._fit_tv_cols()
pump(4)
rows = app.tv.get_children()
if rows:
    app.tv.selection_set(rows[0])
    app.tv.focus(rows[0])
pump()
app._fit_tv_height()
pump(4)
try:
    rf_h = app._rf.winfo_height()
    dz = app._detail_zone
    bottom = dz.winfo_y() + dz.winfo_height()
    check("tv_h=%r <= TV_MAX_ROWS" % (app._tv_h,),
          app._tv_h is None or app._tv_h <= m.TV_MAX_ROWS)
    check("detail bottom %d <= card inner %d" % (bottom, rf_h - m.S(16)),
          bottom <= rf_h - m.S(16) + 1, "rf_h=%d" % rf_h)
except Exception as e:
    check("12-row geometry", False, repr(e))

# ---------------------------------------------------------------- 7 {} 不死锁
print("[8] empty groups {} must not hang in loading state")
app._enter_loading(SLUG, TITLE)
pump(2)
app._apply_board((SLUG, TITLE, {}, None, None, "com"))
pump(6)
try:
    check("empty box shown", bool(app._empty_box.winfo_manager()))
    check("loading lock released", app._loading_slug is None,
          "_loading_slug=%r" % (app._loading_slug,))
    check("empty copy is a conclusion",
          "暂无" in app._empty_box_lbl1.cget("text"),
          "lbl1=%r" % app._empty_box_lbl1.cget("text"))
    check("empty copy does not repeat board name",
          TITLE not in (app._empty_box_lbl1.cget("text") or ""),
          "lbl1=%r" % app._empty_box_lbl1.cget("text"))
except Exception as e:
    check("empty-state branch", False, repr(e))

root.destroy()

print("-" * 62)
if FAILS:
    for n in FAILS:
        print("FAIL  %s" % n)
    print("RESULT: FAIL (%d)" % len(FAILS))
    sys.exit(1)
print("RESULT: OK (all v2.5.5 UI invariants hold)")
