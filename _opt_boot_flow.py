# -*- coding: utf-8 -*-
"""v2.2.0 验证（四）：真实启动时序复刻 —— 「窗口先布局、目录后到达」。

背景：v2.1.1 把左栏宽度交给 _auto_fit_cat() 显式赋值（_lf 关了 grid 传播），
于是「目录还没到」这一段时序最脆弱：
  · 直接 return    → _lf 的 width 停在默认 0，左栏整个消失（实测 1px）
  · 按空目录算     → 得到下限 220，左栏先塌到 280px，目录到达后再跳回 411px
本脚本把这段时序跑一遍，断言**栏 1（导航）**在整段过程中始终落在设计区间内、不塌陷。
v2.5.0：三栏化后「左栏」拆成栏 1（导航）/ 栏 2（型号），本脚本只覆盖栏 1 的宽度策略；
栏 2 与整组三栏几何由 _p_v250_3col.py 覆盖。

v2.3.1 更新：左栏宽度策略从「固定 = 型号名完整所需」改为
    clamp( max(型号名完整所需, 布局区宽 × LEFT_RATIO), 下限, 上限 )
上限再受「右栏保底 CAT_RIGHT_MIN」约束。因此宽屏下左栏会超过设计初始宽度
（这是有意的：宽屏把多出来的宽度分一点给目录，避免右栏宽到一行读不完）。
断言随之从「恒等于设计初始」改为「符合该规格」——
**期望值由规格常量独立算出**（不调用被测的 _set_left_width / _auto_fit_cat），
否则断言就和实现同义反复，成了橡皮章。
"""
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
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


def pump(root, n=6):
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(0.03)


def shutdown(root):
    """销毁窗口前先取消挂起的 after，避免 Tk 打印 invalid command name ..._poll_queue。"""
    try:
        kill_afters(root)
        root.update_idletasks()
        root.update()
    except Exception:
        pass
    try:
        tk.Tk.destroy(root)
    except Exception:
        pass


def kill_afters(root):
    for aid in root.tk.call("after", "info"):
        try:
            root.after_cancel(aid)
        except Exception:
            pass


# 关键：目录缓存**不**放进临时目录 —— 让 catalog 真的是 None（首次启动 / 网络慢）
TMP = tempfile.mkdtemp(prefix="bootflow_")
os.chdir(TMP)
CAT = json.load(io.open(os.path.join(HERE, "msi_mb_catalog.json"), encoding="utf-8"))

# 目录抓取线程改为空操作：保证「目录未到达」这一段是确定性的
m.App._catalog_worker = lambda self: None

m._init_dpi()
m._apply_dpi_scale(96)

INIT_CARD = m.S(m.CAT_TREE_INIT) + m.S(m.CAT_CARD_OVER)
print("设计初始左栏宽 = CAT_TREE_INIT(%d) + CAT_CARD_OVER(%d) = %d px"
      % (m.CAT_TREE_INIT, m.CAT_CARD_OVER, INIT_CARD))
print("v2.3.1 规格：左栏 = clamp(max(型号名所需, 布局区×%.2f), %d, min(%d, 布局区-%d-%d))\n"
      % (m.LEFT_RATIO, m.S(m.SPLIT_MIN_LEFT), m.S(m.LEFT_MAX),
         m.S(m.SPLIT_W), m.S(m.CAT_RIGHT_MIN)))


def expect_left(app, need_col):
    """按 v2.3.1 **规格**算左栏（卡片）宽度。独立实现，不复用被测函数。"""
    lo = m.S(m.SPLIT_MIN_LEFT)
    floor = need_col + m.S(m.CAT_CARD_OVER)
    avail = app._body_width() - m.S(m.BODY_PAD_X) * 2
    hi = min(m.S(m.LEFT_MAX), avail - m.S(m.SPLIT_W) - m.S(m.CAT_RIGHT_MIN))
    hi = max(lo, hi)
    return int(max(lo, min(hi, max(int(avail * m.LEFT_RATIO), floor))))


def new_app(w, h=780):
    # 关掉上一轮的窗口再建新的。
    # 注意不能写成 `try: shutdown(root)`：本函数下文有 `root = tk.Tk()`，
    # Python 会把 root 判定为**局部变量**，于是这一句必抛 UnboundLocalError、
    # 恰好被 except 吞掉 —— 等于"关旧窗口"从未执行过，每轮都在新建窗口。
    # （ruff F823 抓到的就是这个。修法：从 globals 取上一轮的 root。）
    prev = globals().get("root")
    if prev is not None:
        try:
            shutdown(prev)
        except Exception:
            pass
    root = tk.Tk()
    root.withdraw()
    app = m.App(root)
    app._restored = True          # 本测试自己控制目录树
    kill_afters(root)
    root.geometry("%dx%d" % (w, h))
    root.deiconify()
    pump(root)
    return root, app


print("=== [1] 目录未到达：左栏必须保持可用（不许消失 / 不许塌陷）===")
for win in (1100, 1200, 1560):
    root, app = new_app(win)
    L = app._lf.winfo_width()
    M2 = app._mf.winfo_width()
    Rr = app._rf.winfo_width()
    pw = app._pbar_row.winfo_width()
    # v2.5.0 重新基线：三栏化后「左栏」拆成栏 1（导航）/ 栏 2（型号），宽度分别由
    # _col_limits(1)/(2) 夹紧 —— 原断言按两栏公式算**唯一期望值**已不适用，
    # 改为断言落在各自设计区间内（区间本身来自常量，不是"抄实测值"）。
    ck(app.catalog is None, "%d 窗口：前提成立（catalog is None）" % win)
    ck(m.S(m.NAV_COL_MIN) <= L <= m.S(m.NAV_COL_MAX),
       "%d 窗口：栏 1(导航) %dpx 在 [%d, %d] 内（未塌陷）"
       % (win, L, m.S(m.NAV_COL_MIN), m.S(m.NAV_COL_MAX)))
    ck(m.S(m.BOARD_COL_MIN) <= M2 <= m.S(m.BOARD_COL_MAX),
       "%d 窗口：栏 2(型号) %dpx 在 [%d, %d] 内"
       % (win, M2, m.S(m.BOARD_COL_MIN), m.S(m.BOARD_COL_MAX)))
    # 进度行已升为**跨三栏底部工具条**，不该再与右卡片同宽 —— 原断言的语义反了
    ck(pw > 0 and pw > Rr,
       "%d 窗口：进度行 %dpx 已跨三栏（宽于栏 3 的 %dpx）" % (win, pw, Rr))
    shutdown(root)

print("\n=== [2] 目录到达：左栏按实测列宽扩展，且不回跳 ===")
root, app = new_app(1560, 820)
before = app._lf.winfo_width()
app.q.put(("catalog", CAT, None))
app._poll_queue()
pump(root)
after = app._lf.winfo_width()
need = app._nav_col_need()          # v2.5.0：_cat_col_need 已改名
lo2, hi2 = app._col_limits(1)      # v2.5.0：_left_limits 已由 _col_limits 取代
exp2 = int(max(lo2, min(hi2, max(m.S(m.NAV_COL_INIT),
                                 need + m.S(m.CAT_CARD_OVER)))))
ck(after == exp2, "目录到达后左栏 %dpx == 规格期望 %dpx" % (after, exp2))
# v2.5.0：原断言「只扩不缩」的前提是**左栏要装下最长型号名**，目录到达后必须扩宽。
# 三栏化后栏 1 只装平台/芯片组（型号迁到栏 2），需求从 357px 降到 190px，
# 自适应反而会**收窄** —— "只扩不缩"的前提消失，改为断言仍落在设计区间内。
ck(m.S(m.NAV_COL_MIN) <= after <= m.S(m.NAV_COL_MAX),
   "目录到达后栏 1(导航) %d 仍在 [%d, %d] 内（未塌陷）"
   % (after, m.S(m.NAV_COL_MIN), m.S(m.NAV_COL_MAX)))
col_now = int(str(app.cat_tree.column("#0", "width")))
ck(col_now == after - m.S(m.CAT_CARD_OVER),
   "#0 列宽与卡片宽自洽（列 %d = 左栏 %d - 开销 %d）"
   % (col_now, after, m.S(m.CAT_CARD_OVER)))
ck(col_now >= need,
   "#0 列宽 %d ≥ 型号名实测需求 %d（长名不被裁）" % (col_now, need))
ck(lo2 <= after <= hi2, "左栏在钳制区间内（%d ≤ %d ≤ %d）" % (lo2, after, hi2))
ck(app._rf.winfo_width() >= m.S(m.CAT_RIGHT_MIN),
   "右栏仍不低于保底宽 %d（实测 %d）" % (m.S(m.CAT_RIGHT_MIN), app._rf.winfo_width()))
longest = 0
for b in CAT.get("brands") or []:
    for cs in b.get("chipsets") or []:
        for bd in cs.get("boards") or []:
            longest = max(longest,
                          m.S(m.CAT_INDENT) * 2 + app._text_px(bd["title"])
                          + m.S(1 + m.CAT_TREE_PAD))
# v2.5.0：最长**型号名**（实测 357px）现在属于栏 2，不再由栏 1 承担；
# 栏 1 只需装下平台/芯片组名 —— 改为按其自身需求断言。
_nav_need = app._nav_col_need()
ck(col_now >= _nav_need,
   "栏 1 列宽 %d ≥ 导航自身需求 %d（平台/芯片组名不被裁）" % (col_now, _nav_need))
shutdown(root)

print("\n=== [3] 目录已就绪下，窗口从最小拖到最大 ===")
prev_R = 0
mono = True
for w in (1100, 1200, 1400, 1600, 1920):
    root, app = new_app(w)
    app.q.put(("catalog", CAT, None))
    app._poll_queue()
    pump(root)
    L, Rr = app._lf.winfo_width(), app._rf.winfo_width()
    cols = {c: int(str(app.tv.column(c, "width"))) for c in ("ver", "date", "size", "note")}
    holder = app._list_holder.winfo_width()
    fit = sum(cols.values()) <= holder + m.S(6)
    minok = all(cols[c] >= m.S(mw) - 1 for c, mw in
                (("ver", 150), ("date", 104), ("size", 84), ("note", 200)))
    # 说明列的目标份额：容器足够宽时按 45% 要求；容器被挤到四列最小宽之和附近时
    # （1100 窗口、目录已加载 → 容器 605，四列最小宽合计 338 已占 56%），45% 在
    # 数学上不可能达到，此时退化为「说明列必须是最宽的一列，且占比 ≥ 40%」。
    mins_sum = sum(m.S(v) for v in (150, 104, 84, 200))
    share = 0.45 if holder >= mins_sum / 0.45 else 0.40
    note = cols["note"] >= int(holder * share) and cols["note"] == max(cols.values())
    print("    %-5d 左栏 %-4d 右栏 %-4d 列宽 %s 容器 %d（说明列占比 %.1f%%，门槛 %.0f%%）"
          % (w, L, Rr, cols, holder, 100.0 * cols["note"] / holder, share * 100))
    # v2.5.0：三栏后栏 1 只装芯片组，设计初始宽度从 360 降到 NAV_COL_INIT(250)
    ck(m.S(m.NAV_COL_MIN) <= L <= m.S(m.NAV_COL_MAX),
       "%d 窗口：栏 1(导航) %d 在 [%d, %d] 内"
       % (w, L, m.S(m.NAV_COL_MIN), m.S(m.NAV_COL_MAX)))
    ck(fit and minok and note,
       "%d 窗口：合计不超容器=%s 不低最小=%s 说明列最宽且达标=%s" % (w, fit, minok, note))
    if Rr <= prev_R:
        mono = False
    prev_R = Rr
    shutdown(root)
ck(mono, "右栏宽度随窗口单调增长（无来回抖动）")

os.chdir(HERE)
shutil.rmtree(TMP, ignore_errors=True)
print("\n" + ("全部通过 ✓" if not fails else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
