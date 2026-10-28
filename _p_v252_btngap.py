# -*- coding: utf-8 -*-
"""v2.5.2 门禁：底部工具条的按钮几何 + 信息不重复（带断言）。

背景（实测，见 UI规范 §11.13）：
  v2.5.1 里 `btn_cancel` 被 grid 到 **column 3**，与 `btn_open_dir` 同格 ——
  下载中两个按钮重叠 91px（取消下载盖掉打开目录 92%，重叠区两钮都可点）；
  同时 `打开目录` 与 `下载选中版本` 的缝隙是 **0px**（间距挂在 btn_open_dir 的
  **左** padx 上，口径不统一）。

本门禁断言 8 条，全部对**已布局**的几何取值，不看源码文本：
  A1 空闲态：相邻按钮缝隙都 == S(BTN_GAP)
  A2 空闲态：任何两个已映射控件不重叠
  A3 下载态：相邻按钮缝隙都 == S(BTN_GAP)（3 对）
  A4 下载态：任何两个已映射控件不重叠          ← v2.5.1 就是在这条挂的
  A5 两态下 `打开目录` 宽度一致（没有被压窄）
  A6 `下载选中版本` 右边缘贴住容器右边缘
  B1 进度行文案未被裁（lbl_pb 请求宽 <= 实际宽）
  C1 状态栏右读数不含「数据源」（该信息只由栏 3 徽章承担）
  C2 栏 3 数据源徽章在查询后含「数据源：」
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

SLUG, TITLE = "MPG-Z790-EDGE-TI-WIFI", "MPG Z790 EDGE TI WIFI"
S = m.S
# 用 getattr 兜底：v2.5.1 源码里**没有** BTN_GAP 常量，硬取会先抛 AttributeError
# 把探针自己弄挂 —— 那样负向对照会拿到一个「假红」（rc≠0 但不是断言拦下的），
# 反而证明不了门禁有效。兜底值取 10（= v2.5.2 的常量），另用 A0 单独断言常量存在。
GAP = S(getattr(m, "BTN_GAP", 10))
FAILS = []


def check(cond, label, detail=""):
    if cond:
        print("  PASS  %s" % label)
    else:
        print("FAIL  %s  %s" % (label, detail))
        FAILS.append(label)


def mapped(row):
    """返回 [(x, w, 标题)]，只含已映射（可见）的子控件，按 x 排序。"""
    out = []
    for w in row.winfo_children():
        try:
            if not w.winfo_manager():
                continue
            txt = ""
            try:
                txt = w.cget("text") or ""
            except Exception:
                pass
            out.append((w.winfo_x(), w.winfo_width(), txt))
        except Exception:
            pass
    out.sort(key=lambda t: t[0])
    return out


def btn_seq(row, names):
    """按 x 取出指定标题的按钮，返回 [(x, w, 标题)]；缺失即断言失败。

    v2.5.5：主按钮文案跟着选中版本走（「下载 7D89v1C2」），不再是固定串
    「下载选中版本」。所以对 MAIN 改按**前缀**「下载」匹配 —— 否则一旦列表里
    已经有选中行，这里就会误报「未找到」。
    """
    pool = mapped(row)
    got = {}
    for nm in names:
        for x, w, t in pool:
            if t == nm or (nm == MAIN and t.startswith("下载")):
                got[nm] = (x, w)
                break
    out = []
    for nm in names:
        if nm not in got:
            check(False, "控件 %r 已映射" % nm, "—— 未找到")
            return None
        out.append((got[nm][0], got[nm][1], nm))
    return out


def gaps(seq):
    return [seq[i][0] - (seq[i - 1][0] + seq[i - 1][1]) for i in range(1, len(seq))]


def overlaps(seq):
    hits = []
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            a, b = seq[i], seq[j]
            if not (a[0] + a[1] <= b[0] or b[0] + b[1] <= a[0]):
                hits.append((a[2], b[2],
                             min(a[0] + a[1], b[0] + b[1]) - max(a[0], b[0])))
    return hits


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
app._enter_loading(SLUG, TITLE)
app._apply_board((SLUG, TITLE, GROUPS, None, None, "com"))
pump(root, 8)
app._fit_tv_cols()
pump(root, 4)

GHOST = ("选择…", "打开目录", "取消下载")
MAIN = "下载选中版本"

print("=" * 88)
print("【A】_arow 按钮几何（左元素右 padx 统一为 BTN_GAP=%d，S() 后 = %d px）"
      % (getattr(m, "BTN_GAP", 10), GAP))
print("=" * 88)
check(hasattr(m, "BTN_GAP"), "A0 源码存在 BTN_GAP 常量", "—— 未定义（v2.5.1 及更早）")

# ---------- 空闲态 ----------
idle = mapped(app._arow)
print("  空闲态 x/w：" + "  ".join("%s=%d/%d" % (t, x, w) for x, w, t in idle if t))
idl_seq = btn_seq(app._arow, GHOST[:-1] + (MAIN,))
if idl_seq:
    g = gaps(idl_seq)
    check(len(g) == 2 and all(abs(v - GAP) == 0 for v in g),
          "A1 空闲态相邻按钮缝隙均为 %d px" % GAP,
          "实测 %r（期望 [%d, %d]）" % (g, GAP, GAP))
    ho = overlaps(idl_seq)
    check(not ho, "A2 空闲态无控件重叠", "实测重叠 %r" % (ho,))
    open_w_idle = [w for x, w, t in idl_seq if t == "打开目录"][0]

# ---------- 下载态 ----------
app._set_downloading(True)
pump(root, 8)
dl = mapped(app._arow)
print("  下载态 x/w：" + "  ".join("%s=%d/%d" % (t, x, w) for x, w, t in dl if t))
dl_seq = btn_seq(app._arow, GHOST + (MAIN,))
if dl_seq:
    g = gaps(dl_seq)
    check(len(g) == 3 and all(abs(v - GAP) == 0 for v in g),
          "A3 下载态相邻按钮缝隙均为 %d px" % GAP, "实测 %r" % (g,))
    ho = overlaps(dl_seq)
    # v2.5.1 就是在这条挂的：取消下载 1191..1290 与 打开目录 1199..1298 重叠 91px
    check(not ho, "A4 下载态无控件重叠", "实测重叠 %r" % (ho,))
    open_w_dl = [w for x, w, t in dl_seq if t == "打开目录"][0]
    if idl_seq:
        check(open_w_idle == open_w_dl,
              "A5 两态下「打开目录」宽度一致",
              "空闲 %d vs 下载 %d" % (open_w_idle, open_w_dl))
    x, w, _t = dl_seq[-1]
    rw = app._arow.winfo_width()
    check(x + w == rw, "A6 主按钮右边缘贴住容器右边缘",
          "右边缘 %d vs 容器 %d" % (x + w, rw))

# ---------- 进度行 ----------
print()
print("=" * 88)
print("【B】_prow 进度行")
print("=" * 88)
app._dl_speed = 11.4 * 1048576
app._dl_progress(38.6 * 1048576, 67.1 * 1048576)
pump(root, 12)
reqw, w = app.lbl_pb.winfo_reqwidth(), app.lbl_pb.winfo_width()
print("  胶囊条 %d px | 文案 %d px（请求 %d px）" % (app.pb.winfo_width(), w, reqw))
check(w >= reqw, "B1 进度文案未被裁", "实际 %d < 请求 %d" % (w, reqw))

# ---------- 信息不重复 ----------
print()
print("=" * 88)
print("【C】状态栏右读数已移除 / 栏 3 数据源徽章唯一承载")
print("=" * 88)
# v2.5.5：状态栏右侧那块读数（版本号 + 数据源）整块删除 —— 版本号顶栏已有，
# 数据源徽章在栏 3 标题行，状态栏再复述一遍就是第三处。这里改成反向断言：
# 属性必须**不存在**，否则说明旧读数又回来了。
check(not hasattr(app, "v_stat_right"),
      "C1 状态栏右读数已移除", "仍存在 v_stat_right")
badge = app.lbl_host.cget("text")
print("  栏3 数据源徽章 = %r" % badge)
check("数据源：" in badge, "C2 栏3 徽章含「数据源：」", "实测 %r" % badge)
# 版本号只剩顶栏一处：v2.5.5 把状态栏右读数整块删了，这里直接数「屏幕上还有
# 几个控件写着 vX.Y.Z」。恰好 1 处才算过 —— 2 处说明又重复了，0 处说明顶栏丢了。
def _walk(w, acc):
    for c in w.winfo_children():
        acc.append(c)
        _walk(c, acc)
    return acc


def _txt(w):
    try:
        return str(w.cget("text") or "")
    except Exception:
        return ""


_ver = "v%s" % m.APP_VERSION
_hits = [w for w in _walk(root, []) if _ver in _txt(w)]
print("  含 %s 的控件：%r" % (_ver, [_txt(w) for w in _hits]))
check(len(_hits) == 1, "C3 版本号在界面上恰好出现 1 处", "实测 %d 处" % len(_hits))
status_txt = ""
for _name in ("v_stat", "v_status", "_status_var"):
    _v = getattr(app, _name, None)
    try:
        if _v is not None:
            status_txt += str(_v.get())
    except Exception:
        pass
check(_ver not in status_txt, "C4 状态栏不再复述版本号", "实测 %r" % status_txt)

root.destroy()
print()
print("=" * 88)
if FAILS:
    print("FAIL 底部工具条门禁：%d 项未通过 -> %s" % (len(FAILS), ", ".join(FAILS)))
    sys.exit(1)
print("底部工具条门禁全部通过 ✓（A1-A6 / B1 / C1-C2）")
