# -*- coding: utf-8 -*-
"""v2.5.3 门禁：省略号口径统一后的行为验证（带断言）。

背景：
  v2.5.1 给栏 2 加省略号时另写了一份二分（App._ellipsize），与模块级
  `_ellipsize` 是同一算法，唯一差别是量宽方式：
      旧（方法）： measure(前缀) + measure("…")     ← 两次测量相加
      模块级     ： measure(前缀 + "…")             ← 一次测量
  两者在比例字体下有字距，理论上会有 1~2px 差异。v2.5.3 把方法改为委托模块级，
  本门禁既验证行为正确（E1-E5），也记录两版输出的**实际差异条数**——
  实测为 0，说明这次是纯去重、没有改变任何显示结果。

本门禁断言 5 条：
  E1 每个显示串实测宽 <= 可用宽（不溢出）—— 逐型号 × 逐列宽穷举
  E2 未超宽时显示串 == 全名（不无谓加省略号）
  E3 省略串以 … 结尾，且是全名的前缀（不是乱码）
  E4 截得**恰到好处**：再多放一个字就会超宽（不是过度截短）
  E5 完整名仍保留在 iid_board（功能不受影响）
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

src = io.open(os.path.join(HERE, "_p_v230_render.py"), encoding="utf-8").read()
cut = src.index("# ---------------------------------------------------------------- 1) 空状态")
_ns = {"__name__": "_rend_partial", "__file__": os.path.join(HERE, "_p_v230_render.py")}
exec(compile(src[:cut], "_rend_partial", "exec"), _ns)
build, pump, CAT, GROUPS = _ns["build"], _ns["pump"], _ns["CAT"], _ns["GROUPS"]

import msi_bios_checker as m

S = m.S
ELL = "\u2026"
FAILS = []


def check(cond, label, detail=""):
    if cond:
        print("  PASS  %s" % label)
    else:
        print("FAIL  %s  %s" % (label, detail))
        FAILS.append(label)


def old_impl(text, avail, measure, ell=ELL):
    """v2.5.1~v2.5.2 的方法实现，原样复刻用于对照（只做统计，不做断言）。"""
    if measure(text) <= avail:
        return text
    ew = measure(ell)
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if measure(text[:mid]) + ew <= avail:
            lo = mid
        else:
            hi = mid - 1
    return (text[:lo] + ell) if lo > 0 else ell


m._init_dpi()
m._apply_dpi_scale(m._DPI)
root, app = build(m.WIN_W, m.WIN_H, m._DPI)
app.q.put(("catalog", CAT, None))
for _ in range(6):
    app._poll_queue()
    pump(root, 2)
for p in app.cat_tree.get_children(""):
    app.cat_tree.item(p, open=True)
pump(root, 4)

SLUG, TITLE = "MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI"
app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, GROUPS, None, None, "com"))
pump(root, 8)

names = [full for (_slug, full) in app.iid_board.values()]
print("=" * 88)
print("【E】省略号口径统一（栏 2 共 %d 个型号名 × 逐列宽穷举）" % len(names))
print("=" * 88)

pad = S(m.CELL_PAD_X + m.CAT_TREE_PAD)
v_over, v_nochange, v_prefix, v_loose, v_short = [], [], [], [], []
old_over = []
diff = 0
samples = []
checked = 0
widths_seen = set()

mw = int(app.board_tree.column("#0", "minwidth"))     # 低于它会一律被夹上来
print("  栏 2 #0 列 minwidth = %d px" % mw)
for colw_req in range(mw, S(520) + 1, S(10)):
    app.board_tree.column("#0", width=colw_req)
    # ⚠ 必须读回**真实**列宽：Tk 会把 width 夹到 minwidth（栏 2 的 minwidth 由
    # _fit_board_col 设为拟合宽度，此例 S(240)），按请求值算可用宽会凭空造出
    # 「溢出」假红 —— 首版探针就在这里误报 31 条。
    colw = int(app.board_tree.column("#0", "width"))
    avail = colw - pad
    if avail < S(40):
        continue
    widths_seen.add(colw)
    app._ellipsize_board()
    pump(root, 1)
    for iid, (_s, full) in app.iid_board.items():
        disp = app.board_tree.item(iid, "text")
        checked += 1
        w_new = app._text_px(disp)
        w_full = app._text_px(full)
        old = old_impl(full, avail, app._text_px)
        if app._text_px(old) > avail:
            old_over.append((colw, full, old, app._text_px(old), avail))
        if disp != old:
            diff += 1
            if len(samples) < 3:
                samples.append((colw, full, old, disp))

        # E1 不溢出
        if w_new > avail:
            v_over.append((colw, full, disp, w_new, avail))
        # E2 未超宽必须原样
        if w_full <= avail and disp != full:
            v_nochange.append((colw, full, disp))
        # E3 省略串 = 前缀 + …
        if disp != full:
            if not (disp.endswith(ELL) and full.startswith(disp[:-1])):
                v_prefix.append((colw, full, disp))
            # E4 恰到好处：多一个字就放不下
            lo = len(disp) - 1
            if lo < len(full) and app._text_px(full[:lo + 1] + ELL) <= avail:
                v_loose.append((colw, full, disp))
        elif w_full > avail:
            v_short.append((colw, full, disp))

print("  逐宽度组合：%d 次检查（实际列宽 %d..%d 共 %d 档，每档 %d 个型号）" % (
    checked, min(widths_seen), max(widths_seen), len(widths_seen), len(names)))
check(not v_over, "E1 实测宽 <= 可用宽（不溢出）",
      "溢出 %d 条，例：%r" % (len(v_over), v_over[:2]))
check(not v_nochange, "E2 宽度够时原样显示（不无谓省略）",
      "误截 %d 条，例：%r" % (len(v_nochange), v_nochange[:2]))
check(not v_prefix, "E3 省略串是全名前缀 + …（不是乱码）",
      "异常 %d 条，例：%r" % (len(v_prefix), v_prefix[:2]))
check(not v_loose, "E4 截得恰到好处（多放一字即超宽）",
      "过度截短 %d 条，例：%r" % (len(v_loose), v_loose[:2]))
check(not v_short, "E4b 超宽时必定加省略号（不放过超长串）",
      "漏截 %d 条，例：%r" % (len(v_short), v_short[:2]))

print()
print("  对照（统计，不作断言）：旧口径「两次测量相加」溢出 %d / %d 次"
      % (len(old_over), checked))
for o in old_over[:3]:
    print("    列宽 %s | %r  %d > %d" % (o[0], o[2], o[3], o[4]))
print("  新旧显示串差异 %d 次" % diff)
for cw, full, old, new in samples:
    print("    列宽 %d | 旧 %r -> 新 %r" % (cw, old, new))

pump(root, 2)
check(all(f for (_s, f) in app.iid_board.values()),
      "E5 完整名保留在 iid_board（tooltip / 下载不受影响）")

root.destroy()
print()
print("=" * 88)
if FAILS:
    print("FAIL 省略号门禁：%d 项未通过 -> %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("省略号门禁全部通过 ✓（E1-E5）")
