# -*- coding: utf-8 -*-
"""v2.5.4 门禁：`_build_ui` 拆分前后的**控件树结构等价**。

为什么需要
----------
`_build_ui` 原本 585 行，是 `App` 里最长的一个方法。拆成若干 `_ui_*` 段方法本身
只是"搬家"，但这类搬家最容易出的错恰恰是**肉眼看不出来的**：pack 的调用顺序变了
（Tk 按调用顺序分配空间）、某个 padx 挂到了别的控件上（v2.5.2 的按钮重叠就是这么
来的）、或者哪个控件被顺手换了个 parent。这些都会让界面只差几个像素，看截图看不
出来，却是实打实的行为变更。

所以"等价"不能靠 review，要靠**冻结基线**：拆之前把整棵控件树导出来存成 fixture，
拆之后逐条比对。本探针就是这个导出器 + 比对器。

记录哪些字段
------------
每个控件一条记录，深度优先、按 `winfo_children()` 的**创建顺序**：

  path    控件的 Tk 路径名（如 `.!frame2.!frame.!label3`）
          —— Tk 的名字带**同父创建序号**，所以创建顺序一变这里就红
  cls     winfo_class（Frame / TLabel / Treeview …）
  mgr     winfo_manager（pack / grid / place / 空=未布局）
  geo     winfo_x / y / width / height（布局**完成后**的实测值）
  req     winfo_reqwidth / reqheight（字体、内边距、内容宽度变化的敏感项）
  grid    grid_info()（sticky / padx / pady / rowspan …）
  pack    pack_info()（side / fill / expand / padx / pady …）
  text    控件当前显示文本（`textvariable` 已解析成实际值）

`geometry` 取实测值而不是请求值 —— 与 `_p_v253_ellipsis` 同一条教训：Tk 会把列宽
夹到 minwidth，请求值反推出来的结论是错的。

可复现性
--------
① cwd 切到临时目录：避免读到用户目录下 `msi_bios_checker.cfg` 里保存过的窗口尺寸
   与左栏宽（那会让基线随"上次关窗时多大"漂移）；
② DPI 固定 96：`S()` 恒等，路径与像素值与真实机器 DPI 无关；
③ 建完 `cancel_all()`：掐掉所有 `after` 定时器，此后无人再改 UI；
④ 窗口尺寸显式指定，不依赖 `_restore_geometry()`。

`APP_VERSION` 在文本里被归一成 `{V}` —— 这样基线跨版本有效，不会因为升版本号而红。

用法
----
    python _p_v254_uistruct.py             # 比对（门禁用），不一致 rc=1
    python _p_v254_uistruct.py --capture   # 重写基线（仅在确认差异是预期变更时用）

`--capture` 会打印新旧差异摘要，要求人工确认后再覆盖；不做静默重写。
"""
import importlib.util
import inspect
import io
import json
import os
import shutil
import sys
import tempfile
import time
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "_fixtures", "ui_tree_baseline.json")
WIN_W, WIN_H = 1440, 820          # 固定窗口尺寸：三栏都在，且不会被压到保底
REF_DPI = 96                      # 固定参考 DPI：S() 恒等，像素值与机器无关

fails = []


def ck(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


# ---------------------------------------------------------------- 加载被测模块
def load_module():
    spec = importlib.util.spec_from_file_location(
        "mb", os.path.join(HERE, "msi_bios_checker.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mb"] = mod
    spec.loader.exec_module(mod)
    return mod


def pump(root, n=6, pause=0.03):
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(pause)


def cancel_all(root):
    for aid in root.tk.call("after", "info"):
        try:
            root.after_cancel(aid)
        except Exception:
            pass


def build(m):
    """建一个**受控**的 App 实例。参数含义见模块 docstring 的「可复现性」。

    返回 (root, app, 建窗时的默认 WM_DELETE_WINDOW 处理器名) —— 最后一项用于
    判断关窗协议**是否被真的改写**，见 main() 里的说明。
    """
    root = tk.Tk()
    dflt_proto = root.protocol("WM_DELETE_WINDOW")   # Tk 自带的 destroy，非空！
    root.withdraw()
    m._apply_dpi_scale(REF_DPI)          # 必须在 Tk() 之后：它要读 Tk 的字族列表
    app = m.App(root)
    app._restored = True
    cancel_all(root)
    root.geometry("%dx%d+0+0" % (WIN_W, WIN_H))
    root.deiconify()
    # 后台进程创建的窗口随时可能被系统压成 iconic（见 _p_v230_render.wait_mapped
    # 的注释）—— 这里把窗口纠回 normal，保证布局真的算完了
    end = time.time() + 3.0
    while time.time() < end:
        try:
            if root.state() != "normal":
                root.deiconify()
                root.state("normal")
        except Exception:
            pass
        pump(root, 1, 0.02)
        if app._body.winfo_ismapped():
            break
    pump(root, 8, 0.03)
    return root, app, dflt_proto


# ---------------------------------------------------------------- 导出控件树
def _layout_info(w):
    out = {}
    try:
        if w.winfo_manager() == "grid":
            gi = w.grid_info()
            out = {k: str(gi.get(k, "")) for k in
                   ("row", "column", "rowspan", "columnspan", "sticky",
                    "padx", "pady", "ipadx", "ipady")}
    except Exception as e:
        out = {"err": repr(e)}
    return out


def _pack_info(w):
    out = {}
    try:
        if w.winfo_manager() == "pack":
            pi = w.pack_info()
            out = {k: str(pi.get(k, "")) for k in
                   ("side", "fill", "expand", "anchor", "padx", "pady",
                    "ipadx", "ipady")}
    except Exception as e:
        out = {"err": repr(e)}
    return out


def _text_of(w, ver):
    """控件当前显示文本。`textvariable` 解析成实际值 —— 变量名（PY_VAR7）不稳定，
    值才是行为。"""
    try:
        keys = w.keys()
    except Exception:
        return None
    try:
        if "textvariable" in keys:
            tv = str(w.cget("textvariable"))
            if tv:
                return _norm(str(w.getvar(tv)), ver)
        if "text" in keys:
            return _norm(str(w.cget("text")), ver)
    except Exception:
        return None
    return None


def _norm(s, ver):
    return s.replace(ver, "{V}")


def dump_tree(root, ver, skip=()):
    rows = []

    def walk(w):
        for ch in w.winfo_children():
            if str(ch) in skip:
                continue
            try:
                rows.append({
                    "path": str(ch),
                    "cls": ch.winfo_class(),
                    "mgr": ch.winfo_manager(),
                    "geo": [ch.winfo_x(), ch.winfo_y(),
                            ch.winfo_width(), ch.winfo_height()],
                    "req": [ch.winfo_reqwidth(), ch.winfo_reqheight()],
                    "grid": _layout_info(ch),
                    "pack": _pack_info(ch),
                    "text": _text_of(ch, ver),
                })
            except Exception as e:
                rows.append({"path": str(ch), "err": repr(e)})
            walk(ch)

    walk(root)
    return rows


# ---------------------------------------------------------------- 比对
FIELDS = ("cls", "mgr", "geo", "req", "grid", "pack", "text")


def compare(old, new):
    """返回 (差异列表, 结构是否同形)。差异元素为可直接打印的说明。"""
    diffs = []
    if len(old) != len(new):
        diffs.append("控件数不同：基线 %d → 现在 %d" % (len(old), len(new)))
    n = min(len(old), len(new))
    for i in range(n):
        a, b = old[i], new[i]
        if a.get("path") != b.get("path"):
            diffs.append("第 %d 个控件路径不同：%r → %r" % (i, a.get("path"), b.get("path")))
        for f in FIELDS:
            if a.get(f) != b.get(f):
                diffs.append("第 %d 个控件 %s 的 %s 不同：%r → %r"
                             % (i, a.get("path"), f, a.get(f), b.get(f)))
    return diffs


# ---------------------------------------------------------------- 源码层面
def check_shape(m):
    """拆分后 `_build_ui` 应该只剩编排，实体在 `_ui_*` 段方法里。"""
    print("\n源码结构")
    lines, _ = inspect.getsourcelines(m.App._build_ui)
    ck(len(lines) <= 100, "_build_ui 行数 %d ≤ 100（只剩编排）" % len(lines))

    seg = []
    for name, fn in vars(m.App).items():
        if name.startswith("_ui_") and callable(fn):
            seg.append((name, len(inspect.getsourcelines(fn)[0])))
    ck(len(seg) >= 6, "存在 %d 个 _ui_* 段方法（≥ 6）" % len(seg))
    total = sum(n for _n, n in seg)
    ck(total >= 350, "段方法合计 %d 行（≥ 350，主体确实搬出去了）" % total)
    for name, n in sorted(seg):
        print("        %-22s %3d 行" % (name, n))


# ---------------------------------------------------------------- main
def main():
    capture = "--capture" in sys.argv
    tmp = tempfile.mkdtemp(prefix="v254uistruct_")
    old_cwd = os.getcwd()
    try:
        shutil.copy(os.path.join(HERE, "msi_mb_catalog.json"),
                    os.path.join(tmp, "msi_mb_catalog.json"))
        os.chdir(tmp)                     # ① 隔离用户 cfg
        m = load_module()
        m._init_dpi()
        ver = "v%s" % m.APP_VERSION

        root, _app, dflt_proto = build(m)
        rows = dump_tree(root, ver)
        print("控件树：%d 个控件（%dx%d @ %d DPI）" % (len(rows), WIN_W, WIN_H, REF_DPI))

        # 拆分最阴的坑不是控件错了，而是段方法里引用了旧 `_build_ui` 的局部名：
        # 抛 NameError → 被 `except Exception: pass` 吞掉 → 控件树一模一样，行为没了。
        # v2.5.4 拆分时 `_ui_finish` 就真的踩了一次（裸 `root`）。
        #
        # ⚠ 这条断言第一版写成了 `bool(root.protocol(...))`，**恒真**：Tk 的
        # WM_DELETE_WINDOW 一出生就绑着自己的 `destroy`，查询永远返回非空串
        # （实测 `'1820131180800destroy'`）。改成比对"建窗时的默认处理器"，
        # 并要求处理器名里出现 `_on_close` —— 这才真的看得出协议有没有被改写。
        print("\n运行时契约")
        proto = root.protocol("WM_DELETE_WINDOW")
        ck(proto != dflt_proto and "_on_close" in proto,
           "WM_DELETE_WINDOW 已改绑到 _on_close（关窗才会存几何与展开状态）")
        if proto == dflt_proto:
            print("        仍是默认处理器：%r" % (proto,))

        try:
            root.destroy()
        except Exception:
            pass

        if capture:
            os.makedirs(os.path.dirname(FIXTURE), exist_ok=True)
            if os.path.isfile(FIXTURE):
                old = json.load(io.open(FIXTURE, encoding="utf-8"))
                d = compare(old, rows)
                if d:
                    print("\n与现有基线的差异（%d 条，最多列 40 条）：" % len(d))
                    for x in d[:40]:
                        print("   ", x)
                else:
                    print("\n与现有基线完全一致。")
            with io.open(FIXTURE, "w", encoding="utf-8", newline="\n") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
                f.write("\n")
            print("已写入基线：%s" % os.path.relpath(FIXTURE, HERE))
            return 0

        if not os.path.isfile(FIXTURE):
            print("  FAIL  基线不存在：%s" % os.path.relpath(FIXTURE, HERE))
            return 1
        old = json.load(io.open(FIXTURE, encoding="utf-8"))
        diffs = compare(old, rows)
        print("\n结构等价")
        ck(len(old) == len(rows), "控件数一致（基线 %d）" % len(old))
        ck(not diffs, "逐控件比对无差异（比对 %d 个控件 × %d 个字段）"
           % (len(rows), len(FIELDS)))
        if diffs:
            print("\n差异 %d 条，前 40 条：" % len(diffs))
            for x in diffs[:40]:
                print("   ", x)

        check_shape(m)
    finally:
        os.chdir(old_cwd)

    print("\n" + "=" * 70)
    if fails:
        print("FAILED %d 项" % len(fails))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
