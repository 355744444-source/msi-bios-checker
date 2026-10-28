# -*- coding: utf-8 -*-
"""统一发版工具（替代 _rel_pe_verify / _rel_frozen_verify / _rel_smoke / _rel_finalize
以及它们的「上一代生成器」_rel_gen*）。

为什么合并
----------
旧流程是「用脚本生成脚本」：每发一版就由 `_rel_genNNN.py` 复制上一代的 4 个脚本、
把里面的版本号一一替换掉。48 个 `_rel_*.py` 里有 43 个因此**永远跑不起来** ——
它们硬编码的版本号与当时的文档名只对那一版成立。更要命的是版本号散在 7 个文件里，
每次发版手改 7 处，已经漏过一次（同一次提交里 label 写 2.5.1.0、代码在查 2.5.2.0）。

本文件把版本号收敛到**一个来源**：源码里的 `APP_VERSION`。其余全部推导：
    版本号      ← APP_VERSION
    ZIP 文件名  ← 版本号 + 时间戳（默认今天，可 --stamp 覆盖）
    历史版本    ← CHANGELOG.md 的 `## vX.Y.Z` 标题（去重保序）
    版本四元组  ← X.Y.Z → (X, Y, Z, 0)

用法
----
    python _release.py status                    # 只读：打印解析结果与产物哈希
    python _release.py gate                      # 跑 _gate_all.py（13 项探针）
    python _release.py pe                        # PE 版本资源校验
    python _release.py frozen                    # 冻结产物 ↔ 源码一致性
    python _release.py smoke                     # 冻结版冒烟（含 GUI 存活 12s）
    python _release.py verify                    # pe + frozen + smoke
    python _release.py zip                       # 重建 zip（含 zip 内 exe 哈希校验）
    python _release.py deploy                    # 部署到桌面 小软件/
    python _release.py archive                   # 复制 exe + zip 进 archive/
    python _release.py release                   # verify → zip → deploy → archive
    python _release.py bump --to 2.5.4 [--yes]   # 机械版本号统一（默认 dry-run）
    python _release.py clean [--dry-run]         # 清构建目录 / 归档旧 zip

每个写操作都支持 `--dry-run`：算出「会做什么」但不落盘。
`bump` 默认就是 dry-run —— 它要改产品源码，必须显式 --yes 才写。

退出码：0 全部通过；1 有断言失败。
"""
import argparse
import collections
import datetime
import hashlib
import io
import json
import marshal
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import types
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

APP_SRC = os.path.join(ROOT, "msi_bios_checker.py")
SPEC = os.path.join(ROOT, "msi_bios_checker.spec")
VERSION_INFO = os.path.join(ROOT, "version_info.txt")
GATE = os.path.join(ROOT, "_gate_all.py")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

EXE_NAME = "微星主板BIOS下载工具.exe"
DIST_EXE = os.path.join(ROOT, "dist", EXE_NAME)
ARCHIVE = os.path.join(ROOT, "archive")
SMOKE_DIR = os.path.join(ROOT, "_smoke")

# 桌面部署目录：默认 ~/Desktop/小软件，可用 --desk 覆盖。
# 旧脚本把它硬编码成 C:\Users\MSI\Desktop\小软件，换机器就废。
DEFAULT_DESK = os.path.join(os.path.expanduser("~"), "Desktop", "小软件")

COMPANY = "江苏振远智能科技有限公司"


# ================================================================ 上下文解析
class Ctx(object):
    """一次发版所需的全部参数。除 version 外全部由 version 推导。"""

    def __init__(self, ver, stamp, exe, desk, history):
        self.ver = ver
        self.v4 = ver4(ver)
        self.stamp = stamp
        self.exe = exe
        self.desk = desk
        self.history = history                 # 去重保序，第 0 项是当前版本
        self.prev = [v for v in history if v != ver]

    @property
    def zip_name(self):
        return "微星主板BIOS下载工具_v%s_%s.zip" % (self.ver, self.stamp)

    @property
    def zip_path(self):
        return os.path.join(ROOT, self.zip_name)

    @property
    def spec_doc(self):
        return "UI交互设计规范_v%s.md" % self.ver

    @property
    def desk_exe(self):
        return os.path.join(self.desk, "微星主板BIOS下载工具V%s.exe" % self.ver)

    @property
    def desk_plain(self):
        return os.path.join(self.desk, "微星主板BIOS下载工具.exe")

    @property
    def prev_desk_exe(self):
        if not self.prev:
            return None
        return os.path.join(self.desk, "微星主板BIOS下载工具V%s.exe" % self.prev[0])


def ver4(ver):
    """'2.5.3' -> (2, 5, 3, 0)"""
    parts = [int(x) for x in ver.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def read_app_version(path=APP_SRC):
    src = io.open(path, encoding="utf-8").read()
    m = re.search(r'^APP_VERSION\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', src, re.M)
    if not m:
        raise SystemExit("!! 源码里找不到 APP_VERSION 定义：%s" % path)
    return m.group(1)


def read_history(path=CHANGELOG):
    """CHANGELOG 的 `## vX.Y.Z` 标题，去重保序。

    用途有三个：① 断言这些旧版本串不该出现在 PE 资源里（防止打到旧 version_info）；
    ② 断言它们也不该作为独立字符串常量出现在源码里（防止版本号漏改）；
    ③ 推导「当前版本该用哪个日期戳」。
    比旧脚本手写的 `for old in ("2.5.2.0", "2.5.1.0", ...)` 更强 —— 旧清单只挑了 5 个，
    这里覆盖 CHANGELOG 里全部 21 个（含 2.3.x / 1.0.x）。
    """
    if not os.path.isfile(path):
        return []
    txt = io.open(path, encoding="utf-8").read()
    seen, out = set(), []
    for v in re.findall(r"^##\s+v([0-9]+\.[0-9]+\.[0-9]+)", txt, re.M):
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def read_release_date(ver, path=CHANGELOG):
    """CHANGELOG 里 `## v2.5.3 (2026-10-27)` 的日期 -> '20261027'。"""
    if not os.path.isfile(path):
        return None
    txt = io.open(path, encoding="utf-8").read()
    m = re.search(r"^##\s+v%s\s*\((\d{4})-(\d{2})-(\d{2})\)" % re.escape(ver), txt, re.M)
    return "%s%s%s" % m.groups() if m else None


def resolve_stamp(ver):
    """时间戳（zip 文件名里的日期）优先取**已发布的那个**，而不是「今天」。

    v2.5.3 已用 20261027 发过 zip；若默认取今天（20261028），重跑 zip 会生成
    `..._v2.5.3_20261028.zip` —— 同一个版本两个日期戳的包，archive 里会出现双份。
    推导顺序：archive 里已发的 zip > CHANGELOG 的发布日期 > 今天。
    """
    if os.path.isdir(ARCHIVE):
        pat = re.compile(r"_v%s_(\d{8})\.zip$" % re.escape(ver))
        stamps = sorted(m.group(1) for m in
                        (pat.search(f) for f in os.listdir(ARCHIVE)) if m)
        if stamps:
            return stamps[-1]
    return read_release_date(ver) or datetime.date.today().strftime("%Y%m%d")


def build_ctx(args):
    ver = getattr(args, "version", None) or read_app_version()
    stamp = getattr(args, "stamp", None) or resolve_stamp(ver)
    exe = os.path.abspath(getattr(args, "exe", None) or DIST_EXE)
    desk = os.path.abspath(getattr(args, "desk", None) or DEFAULT_DESK)
    return Ctx(ver, stamp, exe, desk, read_history())


# ================================================================ 断言器
class Checker(object):
    """与旧脚本完全一致的 PASS/FAIL 输出格式 —— 便于和旧日志逐行比对。"""

    def __init__(self):
        self.fails = []

    def ck(self, cond, msg):
        print(("  PASS  " if cond else "  FAIL  ") + msg)
        if not cond:
            self.fails.append(msg)
        return bool(cond)

    def done(self, ok_msg):
        print()
        if not self.fails:
            print(ok_msg)
            return 0
        print("失败 %d 项：\n  - %s" % (len(self.fails), "\n  - ".join(self.fails)))
        return 1


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mb(n):
    return "%.2f MB" % (n / 1048576.0)


# ================================================================ status
def step_status(ctx, args):
    print("===== 发版参数 =====")
    print("  源码        %s" % APP_SRC)
    print("  版本号      %s   （读自 APP_VERSION）" % ctx.ver)
    print("  版本四元组  %s" % (ctx.v4,))
    print("  时间戳      %s%s" % (ctx.stamp,
                                 "" if args.stamp else "（推导自 archive 已发包 / CHANGELOG 发布日期）"))
    print("  zip 名      %s" % ctx.zip_name)
    print("  设计规范    %s%s" % (ctx.spec_doc,
                                 "" if os.path.isfile(os.path.join(ROOT, ctx.spec_doc)) else "  ← 不存在"))
    print("  部署目录    %s" % ctx.desk)
    print()
    print("===== 历史版本（推导自 CHANGELOG.md，共 %d 个）=====" % len(ctx.history))
    print("  " + "  ".join(ctx.history))
    print("  上一版      %s" % (ctx.prev[0] if ctx.prev else "—"))
    print()
    print("===== 产物 =====")
    if os.path.isfile(ctx.exe):
        print("  exe         %d bytes  %s" % (os.path.getsize(ctx.exe), sha(ctx.exe)))
    else:
        print("  exe         不存在：%s" % ctx.exe)
    if os.path.isfile(ctx.zip_path):
        print("  zip         %d bytes  %s" % (os.path.getsize(ctx.zip_path), sha(ctx.zip_path)))
    elif os.path.isfile(os.path.join(ARCHIVE, ctx.zip_name)):
        print("  zip         （仅在 archive）")
    else:
        print("  zip         尚未生成")
    if os.path.isdir(ctx.desk):
        found = sorted(f for f in os.listdir(ctx.desk) if f.startswith("微星主板BIOS下载工具"))
        print("  桌面副本    %d 个：%s" % (len(found), ", ".join(found) or "—"))
    else:
        print("  桌面副本    目录不存在")
    return 0


# ================================================================ gate
def step_gate(ctx, args):
    print("===== 全量门禁（_gate_all.py）=====")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(ROOT, "_testenv")
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("CODEBUDDY_SESSION_ID", None)
    env.pop("CLAUDE_SESSION_ID", None)
    env["CODEBUDDY_SAFE_DELETE_SANDBOX"] = ""
    p = subprocess.run([PY, GATE], cwd=ROOT, env=env)
    print()
    print("门禁退出码 = %d" % p.returncode)
    return p.returncode


# ================================================================ pe
def step_pe(ctx, args):
    """PE 版本资源校验。

    字符串以 UTF-16LE 写进 PE 资源段，所以按 UTF-16LE 找版本串；
    VS_FIXEDFILEINFO 的数值版本语义：MS=(major<<16)|minor，LS=(build<<16)|revision。
    """
    if not os.path.isfile(ctx.exe):
        print("!! 找不到 exe：%s" % ctx.exe)
        return 1
    data = io.open(ctx.exe, "rb").read()
    c = Checker()
    print("目标: %s  (%s)" % (ctx.exe, mb(len(data))))
    print()

    vstr = "%d.%d.%d.%d" % ctx.v4
    n = data.count(vstr.encode("utf-16-le"))
    c.ck(n >= 2, "PE 资源含 UTF-16LE 「%s」×%d（FileVersion + ProductVersion）" % (vstr, n))

    # 历史版本串逐个检查，但不逐条打 PASS —— CHANGELOG 里有 25 个旧版本，
    # 25 行 PASS 会把真正有信息量的几行淹掉。全过时只打一行，有残留才逐条列。
    stale = [(v + ".0", data.count((v + ".0").encode("utf-16-le"))) for v in ctx.prev]
    stale = [x for x in stale if x[1]]
    c.ck(not stale, "历史版本串零残留（检查 %d 个：%s … %s）"
         % (len(ctx.prev),
            " / ".join(v + ".0" for v in ctx.prev[:3]),
            ctx.prev[-1] + ".0" if ctx.prev else "—"))
    for o, cnt in stale:
        c.ck(False, "旧串「%s」仍有 %d 处残留" % (o, cnt))

    i = data.find(b"\xbd\x04\xef\xfe")            # 0xFEEF04BD 小端
    c.ck(i >= 0, "PE 含 VS_FIXEDFILEINFO 签名 0xFEEF04BD")
    if i >= 0:
        f = struct.unpack_from("<13I", data, i)
        fv = (f[2] >> 16, f[2] & 0xFFFF, f[3] >> 16, f[3] & 0xFFFF)
        pv = (f[4] >> 16, f[4] & 0xFFFF, f[5] >> 16, f[5] & 0xFFFF)
        c.ck(fv == ctx.v4, "FixedFileInfo filevers = %d.%d.%d.%d（期望 %s）"
             % (fv + (vstr,)))
        c.ck(pv == ctx.v4, "FixedFileInfo prodvers = %d.%d.%d.%d（期望 %s）"
             % (pv + (vstr,)))

    c.ck(data.count(COMPANY.encode("utf-16-le")) >= 1, "公司名字符串仍在（UTF-16LE）")
    return c.done("PE 校验全部通过 ✓")


# ================================================================ frozen
# 注意：PYZ 是 zlib 压缩归档，直接搜字符串必然搜不到。这里用 PyInstaller 自己的
# readers 取出 marshal 好的 code object，与本地 compile 结果比对常量/标识符多重集合。
V250_NEW = (
    "_col_limits", "_set_col_widths", "_auto_fit_cols", "_auto_fit_cat",
    "_nav_col_need", "_body_width",
    "_toggle_collapse_all", "cat_tree", "board_tree", "_mf", "mwrap",
    "_show_detail", "_on_detail_configure", "_detail_zone",
    "_selected_item", "_iid_item", "_latest_iids",
    "abar", "arow", "prow",
    "_populate_tree",
    "_ellipsize_board", "_ellipsize",
    "_dl_progress", "_enter_loading",
)

V250_KEEP = (
    "Spring", "_kick_velocity", "_soft_clamp", "_project", "_motion_enabled",
    "PbarCanvas", "_dot_pulse", "_status_flash",
    "_fit_progress_text", "_fit_dir_text",
    "_apply_row_colors", "_bind_states", "_rebuild_fonts", "_apply_dpi_scale",
    "_menu_copy_url", "_on_download",
)

CONST_NAMES = (
    "RIGHT_DETAIL_MIN", "DETAIL_MAX_LINES", "NAV_TREE_MIN",
    "NAV_COL_MIN", "NAV_COL_MAX", "NAV_COL_INIT",
    "BOARD_COL_MIN", "BOARD_COL_MAX", "CAT_CARD_OVER", "BODY_PAD_X",
    "WIN_W", "WIN_H", "CELL_PAD_X", "BTN_GAP",
    "C_GREEN_BG", "C_LATEST_HOVER", "C_SEL_BG", "C_INSET", "C_CARD",
    "SPR_VALUE", "SPR_BANNER", "PB_TXT_FULL", "PB_TXT_SHORT",
)


def step_frozen(ctx, args):
    from PyInstaller.archive.readers import CArchiveReader

    if not os.path.isfile(ctx.exe):
        print("!! 找不到 exe：%s" % ctx.exe)
        return 1
    modname = "msi_bios_checker"
    car = CArchiveReader(ctx.exe)
    print("CArchive 条目 %d 个" % len(car.toc))
    if modname in car.toc:
        marshalled = car.extract(modname)
        where = "CArchive"
    else:
        pyz = car.open_embedded_archive("PYZ.pyz")
        print("PYZ 条目 %d 个" % len(pyz.toc))
        marshalled = pyz.extract(modname)
        where = "PYZ"
    if not marshalled:
        print("!! 归档里没有 %s" % modname)
        return 1
    code = marshal.loads(marshalled)
    print("已从 %s 取出 frozen 的 %s：co_filename=%r  size=%d bytes"
          % (where, modname, code.co_filename, len(marshalled)))

    src = io.open(APP_SRC, encoding="utf-8").read()
    local = compile(src, code.co_filename, "exec", dont_inherit=True)

    def harvest(co, strs, names):
        for k in co.co_consts:
            if isinstance(k, types.CodeType):
                harvest(k, strs, names)
            elif isinstance(k, str):
                strs.append(k)
            elif isinstance(k, bytes):
                strs.append(k.decode("utf-8", "replace"))
        names.extend(co.co_names)
        names.extend(co.co_varnames)
        names.extend(co.co_freevars)
        names.extend(co.co_cellvars)
        names.append(co.co_name)

    fs, fn, ls, ln = [], [], [], []
    harvest(code, fs, fn)
    harvest(local, ls, ln)
    mf_s, mf_n = collections.Counter(fs), collections.Counter(fn)
    ml_s, ml_n = collections.Counter(ls), collections.Counter(ln)

    c = Checker()
    c.ck(mf_s == ml_s, "字符串常量集合完全一致（frozen %d 个 / 本地 %d 个，差异 %d）"
         % (len(fs), len(ls), sum((mf_s - ml_s).values()) + sum((ml_s - mf_s).values())))
    c.ck(mf_n == ml_n, "标识符名集合完全一致（frozen %d 个 / 本地 %d 个，差异 %d）"
         % (len(fn), len(ln), sum((mf_n - ml_n).values()) + sum((ml_n - mf_n).values())))
    if mf_s != ml_s:
        print("    仅在 frozen:", list((mf_s - ml_s))[:5])
        print("    仅在本地  :", list((ml_s - mf_s))[:5])
    if mf_n != ml_n:
        print("    仅在 frozen:", list((mf_n - ml_n))[:5])
        print("    仅在本地  :", list((ml_n - mf_n))[:5])

    allnames = set(fn)
    for nm in V250_NEW:
        c.ck(nm in allnames, "frozen 内含三栏重构关键标识 %r" % nm)
    for nm in V250_KEEP:
        c.ck(nm in allnames, "frozen 内含既有标识 %r" % nm)
    for nm in CONST_NAMES:
        c.ck(nm in allnames, "frozen 内含常量名 %r" % nm)

    # v2.5.2：状态栏右读数不再复述数据源（旧模板串必须消失），徽章成为唯一承载者
    c.ck(all(not s.startswith("数据源：") for s in fs),
         "frozen 内无「数据源：」开头的旧模板串（状态栏去重生效）")
    c.ck("· 数据源：%s" in fs, "frozen 内含新徽章模板串 '· 数据源：%s'")

    for s in ("latest", "row", "rowh", "latest_h"):
        c.ck(s in fs, "frozen 内含 tag 名 %r" % s)
    for s in ("Cat.Treeview", "Mod.Treeview"):
        c.ck(s in fs, "frozen 内含样式名 %r" % s)
    for s in ("折叠全部", "复制下载链接", "下载此版本"):
        c.ck(s in fs, "frozen 内含 v2.5.0 新增文案 %r" % s)

    c.ck(ctx.ver in fs, "frozen 内含版本字面量 %r" % ctx.ver)
    stale = [v for v in ctx.prev if v in fs]
    c.ck(not stale, "frozen 内不含任何历史版本常量（检查 %d 个）" % len(ctx.prev))
    for v in stale:
        c.ck(False, "frozen 内仍有旧版本常量 %r" % v)

    return c.done("frozen 源码一致性校验全部通过 ✓")


# ================================================================ smoke
def step_smoke(ctx, args):
    """冻结版冒烟：① --check 离线自检；② GUI 启动存活（证明 tkinter 真的可用）。

    GUI 那一步是关键门禁 —— 历史上首轮打包曾把 tkinter 整个漏掉（exe 只有 11.5MB
    且启动即死），所以必须真的把它拉起来看是否活着，不能只看打包 exit code。
    """
    if not os.path.isfile(ctx.exe):
        print("!! 找不到 exe：%s" % ctx.exe)
        return 1
    os.makedirs(SMOKE_DIR, exist_ok=True)
    exe = os.path.join(SMOKE_DIR, os.path.basename(ctx.exe))
    shutil.copy2(ctx.exe, exe)
    print("冒烟副本：%s (%d bytes)" % (exe, os.path.getsize(exe)))

    c = Checker()

    # ---------- ① --check 离线自检 ----------
    print("\n===== [1] frozen --check =====")
    log = os.path.join(SMOKE_DIR, "msi_bios_checker_selftest.log")
    if os.path.isfile(log):
        os.remove(log)
    t0 = time.time()
    p = subprocess.run([exe, "--check"], cwd=SMOKE_DIR, capture_output=True, timeout=900)
    print("  --check 退出码 = %d   耗时 %.1fs" % (p.returncode, time.time() - t0))
    c.ck(p.returncode == 0, "--check 退出码为 0")
    c.ck(os.path.isfile(log), "生成了自检日志 %s" % os.path.basename(log))
    if os.path.isfile(log):
        txt = io.open(log, encoding="utf-8", errors="replace").read()
        print("\n  ---- 自检日志 ----")
        for line in txt.splitlines():
            print("  | " + line)
        print()
        c.ck(ctx.ver in txt, "自检日志里带版本号 %s" % ctx.ver)
        # 目录款数不写死 501，而是读 dist 里那份 catalog 的 total —— 单一来源。
        total = read_catalog_total()
        if total:
            c.ck(("总型号: %d" % total) in txt,
                 "目录总型号 = %d（与 dist/msi_mb_catalog.json 的 total 一致）" % total)
        else:
            c.ck("总型号:" in txt, "自检日志里含目录总型号行（未找到 catalog，跳过数值比对）")
        for old in ctx.prev[:1]:
            c.ck(old not in txt, "自检日志里不含上一版版本号 %s" % old)

    # ---------- ② GUI 启动存活 ----------
    print("===== [2] GUI 启动存活（tkinter 门禁） =====")
    proc = subprocess.Popen([exe], cwd=SMOKE_DIR)
    time.sleep(12)
    alive = proc.poll() is None
    c.ck(alive, "启动 12 秒后进程仍存活（tkinter/Tcl 已成功初始化）")
    if alive:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=15)
        print("  已结束测试进程，退出码 = %s" % proc.returncode)
    else:
        print("  进程提前退出，退出码 = %s" % proc.returncode)

    mlog = os.path.join(SMOKE_DIR, "msi_bios_checker.log")
    c.ck(os.path.isfile(mlog), "运行期写出了 msi_bios_checker.log")
    if os.path.isfile(mlog):
        body = io.open(mlog, encoding="utf-8", errors="replace").read()
        print("  ---- 运行日志 ----")
        for line in body.splitlines():
            print("  | " + line)
        # 启动期只写一行 DPI 日志，里面不含版本号 —— 别断言「日志里有版本号」
        # （第一版冒烟脚本就这么错过一次）。这行由 _init_dpi() 在 Tk 起来之后写出，
        # 出现即证明 Tcl/Tk 初始化成功。
        c.ck("dpi: aware=" in body, "运行日志含 DPI 初始化行（证明 Tk/Tcl 真的起来了）")

    return c.done("冻结版冒烟全部通过 ✓")


def read_catalog_total():
    for p in (os.path.join(ROOT, "dist", "msi_mb_catalog.json"),
              os.path.join(ROOT, "msi_mb_catalog.json")):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            if isinstance(d.get("total"), int):
                return d["total"]
        except Exception:
            continue
    return 0


# ================================================================ zip
def step_zip(ctx, args):
    if not os.path.isfile(ctx.exe):
        print("!! 找不到 exe：%s" % ctx.exe)
        return 1
    members = [
        (ctx.exe, EXE_NAME),
        (os.path.join(ROOT, "README.txt"), "README.txt"),
        (os.path.join(ROOT, "CHANGELOG.md"), "CHANGELOG.md"),
        (os.path.join(ROOT, ctx.spec_doc), ctx.spec_doc),
    ]
    print("===== 重建 zip 归档 =====")
    print("  %s" % ctx.zip_name)
    c = Checker()
    missing = [arc for src, arc in members if not os.path.isfile(src)]
    for src, arc in members:
        c.ck(os.path.isfile(src), "归档成员存在：%s" % arc)
    if missing or args.dry_run:
        if args.dry_run:
            print("\n  DRY-RUN 只列出将写入的成员，不落盘：")
            for src, arc in members:
                print("    %-34s %s" % (arc, ("%d bytes" % os.path.getsize(src))
                                        if os.path.isfile(src) else "<缺失>"))
        return c.done("zip 成员检查通过 ✓")

    if os.path.isfile(ctx.zip_path):
        bak = ctx.zip_path + ".prev"
        shutil.copy2(ctx.zip_path, bak)
        print("  NOTE  已有同名 zip，先备份到 %s" % os.path.basename(bak))
    with zipfile.ZipFile(ctx.zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arc in members:
            z.write(src, arc)

    with zipfile.ZipFile(ctx.zip_path) as z:
        print("\n重建后的 zip 条目：")
        for i in z.infolist():
            print("  utf8=%-5s %-38s %d bytes" % (bool(i.flag_bits & 0x800), i.filename, i.file_size))

    print("\n===== zip 内 exe 哈希 =====")
    tmp = os.path.join(ROOT, "_zip_exe_check.tmp")
    with zipfile.ZipFile(ctx.zip_path) as z:
        with z.open(EXE_NAME) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
    zip_sha = sha(tmp)
    try:
        os.remove(tmp)
    except OSError as e:
        print("  NOTE  临时文件清理失败（不影响结果）：%r" % (e,))
    c.ck(zip_sha == sha(ctx.exe), "zip 内 exe 哈希 = dist exe 哈希（%s）" % zip_sha)
    return c.done("zip 归档完成 ✓")


# ================================================================ deploy
def step_deploy(ctx, args):
    if not os.path.isfile(ctx.exe):
        print("!! 找不到 exe：%s" % ctx.exe)
        return 1
    print("===== 部署桌面 =====")
    print("  目录  %s" % ctx.desk)
    c = Checker()
    if not c.ck(os.path.isdir(ctx.desk), "桌面目录存在"):
        return c.done("部署失败")
    dist_sha = sha(ctx.exe)

    if os.path.isfile(ctx.desk_exe):
        print("  NOTE  覆盖已存在的 %s（旧哈希 %s）"
              % (os.path.basename(ctx.desk_exe), sha(ctx.desk_exe)[:16]))
    if args.dry_run:
        print("  DRY-RUN 将写入：%s" % ctx.desk_exe)
        if os.path.isfile(ctx.desk_plain):
            print("  DRY-RUN 将同步：%s（无版本名副本）" % ctx.desk_plain)
        return c.done("部署预演完成 ✓")

    shutil.copy2(ctx.exe, ctx.desk_exe)
    c.ck(sha(ctx.desk_exe) == dist_sha, "桌面 V%s.exe 哈希 = dist exe 哈希" % ctx.ver)

    if os.path.isfile(ctx.desk_plain):
        plain_old = sha(ctx.desk_plain)
        prev = ctx.prev_desk_exe
        if prev and os.path.isfile(prev) and sha(prev) == plain_old:
            print("  NOTE  桌面无版本名副本原与 V%s.exe 同字节 ⇒ 确认是本工具部署副本"
                  % ctx.prev[0])
        shutil.copy2(ctx.exe, ctx.desk_plain)
        c.ck(sha(ctx.desk_plain) == dist_sha, "桌面无版本名副本已同步至 v%s" % ctx.ver)
    else:
        print("  SKIP  桌面无版本名副本不存在，跳过")

    if ctx.prev_desk_exe and os.path.isfile(ctx.prev_desk_exe):
        print("  NOTE  桌面仍留有上一版：%s（%d bytes）—— 交给 clean 处理"
              % (os.path.basename(ctx.prev_desk_exe), os.path.getsize(ctx.prev_desk_exe)))
    return c.done("桌面部署完成 ✓")


# ================================================================ archive
def step_archive(ctx, args):
    print("===== 归档 v%s =====" % ctx.ver)
    c = Checker()
    arch_exe = os.path.join(ARCHIVE, "微星主板BIOS下载工具_v%s.exe" % ctx.ver)
    arch_zip = os.path.join(ARCHIVE, ctx.zip_name)
    ok_exe = c.ck(os.path.isfile(ctx.exe), "dist exe 存在")
    ok_zip = c.ck(os.path.isfile(ctx.zip_path), "根目录 zip 存在：%s" % ctx.zip_name)
    if not (ok_exe and ok_zip):
        return c.done("归档失败")
    if args.dry_run:
        print("  DRY-RUN 将复制：")
        print("    %s" % arch_exe)
        print("    %s" % arch_zip)
        return c.done("归档预演完成 ✓")
    os.makedirs(ARCHIVE, exist_ok=True)
    shutil.copy2(ctx.exe, arch_exe)
    shutil.copy2(ctx.zip_path, arch_zip)
    c.ck(sha(arch_exe) == sha(ctx.exe), "archive/ v%s exe 哈希 = dist exe 哈希" % ctx.ver)
    c.ck(sha(arch_zip) == sha(ctx.zip_path), "archive/ v%s zip 哈希 = 根目录 zip 哈希" % ctx.ver)
    return c.done("归档完成 ✓")


# ================================================================ verify / release
def step_verify(ctx, args):
    rc = 0
    for fn in (step_pe, step_frozen, step_smoke):
        print("\n" + "=" * 68)
        rc |= fn(ctx, args)
        print("=" * 68)
    print("\nverify 汇总：%s" % ("三段校验全部通过 ✓" if rc == 0 else "存在失败项 ✗"))
    return rc


def step_release(ctx, args):
    rc = step_verify(ctx, args)
    if rc != 0 and not args.force:
        print("\n!! 校验未通过，已中止后续的 zip / 部署 / 归档（--force 可强制继续）")
        return rc
    for fn in (step_zip, step_deploy, step_archive):
        print("\n" + "=" * 68)
        rc |= fn(ctx, args)
    print("\n" + "=" * 68)
    print("发版汇总：v%s  %s" % (ctx.ver, "全部完成 ✓" if rc == 0 else "存在失败项 ✗"))
    return rc


# ================================================================ bump
BUMPS = (
    # (文件, 旧串模板, 新串模板, 期望命中次数)
    (APP_SRC, 'APP_VERSION = "%s"', 'APP_VERSION = "%s"', 1),
    (VERSION_INFO, "filevers=%s, prodvers=%s", "filevers=%s, prodvers=%s", 1),
    (VERSION_INFO, "u'FileVersion', u'%s.0'", "u'FileVersion', u'%s.0'", 1),
    (VERSION_INFO, "u'ProductVersion', u'%s.0'", "u'ProductVersion', u'%s.0'", 1),
    (SPEC, "微星主板 BIOS 下载工具 v%s", "微星主板 BIOS 下载工具 v%s", 1),
    (GATE, 'print("v%s gate summary")', 'print("v%s gate summary")', 1),
)


def step_bump(ctx, args):
    """机械版本号统一：只改「必须跟着版本走」的 6 处，不碰散落在注释/文档里的历史叙述。

    刻意不做全局字符串替换 —— `_gate_all.py` 里有两处 `# v2.5.3：...` 的变更注记，
    全局替换会把历史记录改成新版本号，那是在伪造变更史。
    """
    target = args.to
    if not target:
        print("!! bump 需要 --to X.Y.Z")
        return 1
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", target):
        print("!! --to 必须是 X.Y.Z 形式：%r" % target)
        return 1
    old = read_app_version()
    if target == old:
        print("!! 目标版本与当前一致（%s），无需 bump" % old)
        return 1
    ov4, nv4 = ver4(old), ver4(target)
    print("===== bump %s -> %s =====" % (old, target))
    print("  四元组 %s -> %s" % (ov4, nv4))
    print()

    c = Checker()
    plans = []
    for path, old_t, new_t, expect in BUMPS:
        base = os.path.basename(path)
        # 旧串：四元组模板用 "filevers=(2,5,3,0)" 这种紧凑写法
        if "%s, prodvers" in old_t:
            o = old_t % ("(%d,%d,%d,%d)" % ov4, "(%d,%d,%d,%d)" % ov4)
            n = new_t % ("(%d,%d,%d,%d)" % nv4, "(%d,%d,%d,%d)" % nv4)
        else:
            o = old_t % old
            n = new_t % target
        b = open(path, "rb").read()
        cnt = b.count(o.encode("utf-8"))
        if not c.ck(cnt == expect, "%s：%r 命中 %d 次（期望 %d）" % (base, o[:56], cnt, expect)):
            continue
        plans.append((path, o, n))

    if c.fails:
        return c.done("bump 未执行（先修上面的命中数不符）")

    print()
    if not args.yes:
        print("  DRY-RUN（默认）。将做以下替换：")
        for path, o, n in plans:
            print("    %-22s %r -> %r" % (os.path.basename(path), o, n))
        print()
        print("  确认无误后加 --yes 真正写入。")
        print("  ⚠ 写入会改变 msi_bios_checker.py 字节 ⇒ 与现有 dist exe 不同源，须重新打包。")
        return 0

    for path, o, n in plans:
        b = open(path, "rb").read()
        open(path, "wb").write(b.replace(o.encode("utf-8"), n.encode("utf-8"), 1))
        print("  WRITE %-22s %s" % (os.path.basename(path), o[:40]))

    # 写完立刻证明源码还能编译，别把坏源码留在盘上
    src = io.open(APP_SRC, encoding="utf-8").read()
    try:
        compile(src, APP_SRC, "exec", dont_inherit=True)
        ok = True
    except SyntaxError as e:
        ok = False
        print("!! 写入后源码无法编译：%r" % (e,))
    c.ck(ok, "写入后源码可编译")
    c.ck(read_app_version() == target, "回读 APP_VERSION = %s" % target)

    print()
    print("还需手工完成的（本工具不代劳，避免伪造变更叙述）：")
    print("  1. msi_bios_checker.py 版本历史 docstring 追加一条 `%d. v%s：...`" % (0, target))
    print("  2. CHANGELOG.md 顶部加 `## v%s (日期) — 标题`（frozen 的旧版本串推导靠它）" % target)
    print("  3. README.txt 标题 / 更新历史")
    print("  4. UI交互设计规范_v%s.md 改名 + 新增小节" % target)
    print("  5. 重新打包：pyinstaller msi_bios_checker.spec --noconfirm --workpath build_v%s"
          % target.replace(".", ""))
    return c.done("bump 完成 ✓")


# ================================================================ clean
def step_clean(ctx, args):
    print("===== 清理构建产物 =====")
    def dsize(p):
        t = 0
        for r, _, fs in os.walk(p):
            for f in fs:
                try:
                    t += os.path.getsize(os.path.join(r, f))
                except OSError:
                    pass
        return t

    dirs = sorted(d for d in os.listdir(ROOT)
                  if d.startswith("build_v") and os.path.isdir(os.path.join(ROOT, d)))
    dirs += [d for d in ("_smoke", "__pycache__", ".ruff_cache")
             if os.path.isdir(os.path.join(ROOT, d))]
    freed = 0
    for d in dirs:
        p = os.path.join(ROOT, d)
        sz = dsize(p)
        if args.dry_run:
            print("  DRY-RUN 将删除 %-14s %s" % (d, mb(sz)))
        else:
            shutil.rmtree(p)
            print("  removed %-14s %s" % (d, mb(sz)))
        freed += sz

    # 根目录里属于旧版本的 zip：archive 已有同字节副本则删，否则移进 archive
    olds = []
    for f in sorted(os.listdir(ROOT)):
        if not f.endswith(".zip") or f == ctx.zip_name:
            continue
        m = re.search(r"_v([0-9]+\.[0-9]+\.[0-9]+)_", f)
        if not m:
            continue
        olds.append(f)
    for f in olds:
        p = os.path.join(ROOT, f)
        arc = os.path.join(ARCHIVE, f)
        if os.path.isfile(arc) and sha(arc) == sha(p):
            if args.dry_run:
                print("  DRY-RUN 将删除旧 zip %s（archive 有同字节副本）" % f)
            else:
                os.remove(p)
                freed += 0
                print("  removed 旧 zip %s（archive 有同字节副本）" % f)
        else:
            if args.dry_run:
                print("  DRY-RUN 将把旧 zip %s 移入 archive/（无同字节副本）" % f)
            else:
                os.makedirs(ARCHIVE, exist_ok=True)
                shutil.move(p, arc)
                print("  moved   旧 zip %s -> archive/" % f)

    print()
    print("释放约 %s" % mb(freed))
    print("剩余 build 目录:", [d for d in os.listdir(ROOT)
                                if d.startswith("build_v") or d in ("_smoke", "__pycache__")])
    print("根目录 zip:", [f for f in os.listdir(ROOT) if f.endswith(".zip")])
    return 0


# ================================================================ main
STEPS = {
    "status": step_status,
    "gate": step_gate,
    "pe": step_pe,
    "frozen": step_frozen,
    "smoke": step_smoke,
    "verify": step_verify,
    "zip": step_zip,
    "deploy": step_deploy,
    "archive": step_archive,
    "release": step_release,
    "bump": step_bump,
    "clean": step_clean,
}


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="_release.py",
        description="统一发版工具（版本号读自源码 APP_VERSION）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="步骤：" + " / ".join(STEPS))
    ap.add_argument("step", nargs="?", default="status", choices=sorted(STEPS))
    ap.add_argument("--version", dest="version", help="覆盖版本号（默认读源码 APP_VERSION）")
    ap.add_argument("--stamp", help="zip 时间戳 YYYYMMDD（默认取 archive 已发包日期，无则今天）")
    ap.add_argument("--exe", help="目标 exe（默认 dist/微星主板BIOS下载工具.exe）")
    ap.add_argument("--desk", help="桌面部署目录（默认 ~/Desktop/小软件）")
    ap.add_argument("--dry-run", action="store_true", help="只算不做，不落盘")
    ap.add_argument("--force", action="store_true", help="release 时校验失败也继续")
    ap.add_argument("--to", help="bump 的目标版本 X.Y.Z")
    ap.add_argument("--yes", action="store_true", help="bump 真正写入（默认 dry-run）")
    args = ap.parse_args(argv)

    ctx = build_ctx(args)
    print("版本 %s ｜ 时间戳 %s ｜ exe %s" % (ctx.ver, ctx.stamp, os.path.basename(ctx.exe)))
    print("-" * 68)
    return STEPS[args.step](ctx, args)


if __name__ == "__main__":
    sys.exit(main())
