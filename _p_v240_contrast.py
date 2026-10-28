# -*- coding: utf-8 -*-
"""视觉焕新验证 A：WCAG 对比度 + 明度阶梯 + 令牌引用完整性 + 等宽字落地。

全部从**主程序真实属性**取值（不硬编码），这样验证的是实际生效的配色。
深色主题最容易踩的坑是"看着还行"但对比度其实不合格 —— 这里逐组合算 WCAG 比值。
"""
import importlib.util
import os
import re
import sys
import tkinter as tk

HERE = os.getcwd()
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

fails = []
warns = []


def lum(h):
    def f(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def cr(a, b):
    la, lb = lum(a), lum(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def per(h):
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


G = m.__dict__

# (用途, 前景, 背景, 最小要求)
COMBOS = [
    ("窗口大标题 Title.TLabel", G["C_TEXT"], G["C_BG"], 3.0),
    ("标题栏版本小字 Ver.TLabel", G["C_DIM"], G["C_BG"], 4.5),
    ("卡片正文 Card.TLabel", G["C_TEXT"], G["C_CARD"], 4.5),
    ("卡片次级 Sub.TLabel", G["C_SUB"], G["C_CARD"], 4.5),
    ("卡片弱化 Dim.TLabel", G["C_DIM"], G["C_CARD"], 4.5),
    ("目录树芯片组 C_CHIP", G["C_CHIP"], G["C_CARD"], 4.5),
    ("目录树主板型号 C_SUB", G["C_SUB"], G["C_CARD"], 4.5),
    ("列表正文", G["C_TEXT"], G["C_CARD"], 4.5),
    ("列表行 hover", G["C_TEXT"], G["C_ROW_HOVER"], 4.5),
    ("列表选中行", G["C_TEXT"], G["C_SEL_BG"], 4.5),
    ("表头 Heading", G["C_SUB"], G["C_HEADING"], 4.5),
    # 「最新」行绿底：v2.4.0 之前**从未渲染** —— item 挂 tags=("latest","row")，
    # 两个 tag 都配了 background，而 ttk::treeview 的规则是「先创建的 tag 优先」，
    # 当时 row(先) 盖住了 latest(后)，生效的是 C_CARD。
    # v2.4.0 已修：把 latest 提到 row 之前创建（见 __init__ 注释），现在两行都真实渲染。
    # 验证见 _p_v240_latestbg.py（应用级取色，绿底 ~1.7 万像素）+ _p_v240_tagprio.py（规则）。
    ("「最新」行", G["C_GREEN"], G["C_GREEN_BG"], 4.5),
    ("「最新」行 hover", G["C_GREEN"], G["C_LATEST_HOVER"], 4.5),
    ("搜索框占位", G["C_SUB"], G["C_INSET"], 4.5),
    ("搜索框输入", G["C_TEXT"], G["C_INSET"], 4.5),
    ("次级按钮文字", G["C_TEXT"], G["C_BTN"], 4.5),
    ("主按钮白字", "#ffffff", G["C_ACCENT_BTN"], 4.5),
    ("主按钮禁用字", G["C_ACCENT_BTN_FG_DIS"], G["C_ACCENT_BTN_DIS"], 4.5),
    ("链接（打开官网）", G["C_BLUE"], G["C_CARD"], 4.5),
    ("状态栏文字", G["C_STATUS_FG"], G["C_STATUS_BG"], 4.5),
    ("状态栏右读数", G["C_DIM"], G["C_STATUS_BG"], 4.5),
    ("成功横幅", G["C_OK"], G["C_OK_BG"], 4.5),
    ("失败横幅", "#ff9b95", G["C_RED_BG"], 4.5),
    ("主板提示文字", "#a8c4dc", G["C_BLUE_BG"], 4.5),
    ("空状态图标（图形）", G["C_WATERMARK"], G["C_CARD"], 3.0),
    ("卡片 vs 窗口底（分界）", G["C_CARD"], G["C_BG"], 1.15),
    ("分隔线 vs 窗口底（图形）", G["C_BORDER"], G["C_BG"], 1.3),
]

print("=" * 82)
print("【A】WCAG 对比度（阈值：正文 4.5:1 / 大字与图形 3:1）")
print("=" * 82)
print("%-26s %-10s %-10s %-7s %s" % ("用途", "前景", "背景", "比值", "结果"))
for name, fg, bg, need in COMBOS:
    v = cr(fg, bg)
    ok = v >= need
    tag = "PASS" if ok else ("WARN" if v >= need * 0.9 else "FAIL")
    if not ok:
        (fails if v < need * 0.9 else warns).append(
            "%s %.2f < %.1f" % (name, v, need))
    print("%-26s %-10s %-10s %6.2f  %s %s" % (name, fg, bg, v, tag,
                                              "" if ok else "(需要 %.1f)" % need))

print()
print("=" * 82)
print("【B】明度阶梯（感知亮度 0.2126R+0.7152G+0.0722B）")
print("=" * 82)
LADDER = [("L0 窗口底", "C_BG"), ("L1 卡片面", "C_CARD"), ("L1' 内嵌槽", "C_INSET"),
          ("L2 浮层/按钮", "C_BTN"), ("L2' 表头", "C_HEADING"),
          ("L3 hover", "C_BTN_HOVER"), ("L3' 行 hover", "C_ROW_HOVER"),
          ("最亮 主文字", "C_TEXT")]
prev = None
for name, tok in LADDER:
    v = per(G[tok])
    d = "" if prev is None else "  (较前 %+.1f)" % (v - prev)
    print("  %-14s %-10s 亮度 %6.2f%s" % (name, G[tok], v, d))
    prev = v
print()
bd = per(G["C_CARD"]) - per(G["C_BG"])
fd = per(G["C_BTN"]) - per(G["C_CARD"])
print("  底→面 %.1f ；面→浮 %.1f  （v2.3.1 基线：%.1f / %.1f）"
      % (bd, fd, per("#23272f") - per("#16181e"), per("#2c313b") - per("#23272f")))
if bd < 8:
    fails.append("底/面明度差过小 %.1f" % bd)
if fd < 5:
    warns.append("面/浮明度差偏小 %.1f" % fd)

print()
print("=" * 82)
print("【C】颜色令牌引用完整性（有没有定义了却没人用的）")
print("=" * 82)
src = open(os.path.join(HERE, "msi_bios_checker.py"), encoding="utf-8").read()
# v2.4.0 修探针盲点（两处，都踩过）：
#
# ① 定义识别：原正则只认 `=` 后面跟十六进制字面量的定义，于是
#      C_MSI_RED = C_ACCENT
#      C_RED_HOT = C_ACCENT_HOT
#    这类**别名定义**根本进不了 names，永远不被审计 —— 而 C_RED_HOT 恰恰是本轮
#    「红色预算收紧」要盯的那个令牌。旧版把 38 个令牌报成「0 个未引用」是**假绿**，
#    连带 `if "C_RED_HOT" in unused` 成了恒假判据。改成字面量 + 别名两类都收。
#
# ② 引用计数：原用正则 `\bNAME\b` 全文件计数，**不区分注释 / 字符串与真实代码**。
#    结果我给源码补的 v2.4.0 历史注释里提到了一次 "C_RED_HOT"，就被当成了"仍在使用"
#    —— 探针立刻转 FAIL，报"红色预算没有收紧"。这是**假红**。
#    改用 tokenize 只数 NAME token，把 COMMENT / STRING 全部剔除。
names = sorted(set(re.findall(
    r'^(C_[A-Z_0-9]+)\s*=\s*(?:"#|C_[A-Z_0-9]+\b)', src, re.M)))


def code_name_counts(source):
    """统计**真实代码**里每个标识符出现次数（剔除注释与字符串字面量）。"""
    import io as _io
    import tokenize as _tok
    cnt = {}
    for t in _tok.generate_tokens(_io.StringIO(source).readline):
        if t.type == _tok.NAME:
            cnt[t.string] = cnt.get(t.string, 0) + 1
    return cnt


CODE = code_name_counts(src)
unused = []
for n in names:
    uses = CODE.get(n, 0) - 1          # 减去定义处那一次
    if uses <= 0:
        unused.append(n)
print("  定义 %d 个令牌（含别名定义）；未被引用的 %d 个：%s"
      % (len(names), len(unused), "、".join(unused) or "无 ✓"))
print("  （引用计数已剔除注释 / 字符串，只数真实代码里的 NAME token）")
if "C_RED_HOT" in unused:
    print("  ⇒ C_RED_HOT 已退出使用：红色预算确实收紧了（这是本轮的设计目标）")
else:
    fails.append("C_RED_HOT 仍被引用 —— 红色预算没有收紧到预期")

print()
print("=" * 82)
print("【D】等宽字落地")
print("=" * 82)
# 必须**模拟 main() 的真实顺序**才能验出真值：_init_dpi() 时还没有 Tk root，
# _rebuild_fonts() 拿不到字族列表、只能走兜底；tk.Tk() 之后的 _apply_dpi_scale()
# 才会重算并探测到真字族。只 import 模块而不建 root 的话，FONT_MONO 会停在
# 兜底值 'Consolas' —— 看着像 bug，其实只是探针没走真实启动路径。
print("  （模块级 import 后，未建 root）FONT_MONO -> %r" % (m.FONT_MONO,))
root = tk.Tk()
root.withdraw()
m._apply_dpi_scale(m._DPI)          # ← main() 里 tk.Tk() 之后的那一步
fam = m._mono_family()
print("  （建 root 并 _apply_dpi_scale 后）FONT_MONO -> %r" % (m.FONT_MONO,))
print("  _mono_family() -> %r" % fam)
if m.FONT_MONO[0] != "Cascadia Mono":
    fails.append("等宽字未命中 Cascadia Mono（得到 %r）" % m.FONT_MONO[0])
print("  界面字族        -> %r" % m._ui_font_family())
print("  → 与 _ui_font_family() 是同一套「兜底 + 建窗后重算」机制，行为一致")
root.destroy()

print()
if fails:
    print("失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails)))
if warns:
    print("提示 %d 项：\n  - %s" % (len(warns), "\n  - ".join(warns)))
print("验证 A %s" % ("全部通过 ✓" if not fails else "未通过 ✗"))
sys.exit(1 if fails else 0)
