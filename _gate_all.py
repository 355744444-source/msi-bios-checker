# -*- coding: utf-8 -*-
"""v2.4.0 视觉焕新 —— 全量门禁跑一遍（纯 ASCII 输出，避免控制台编码干扰）。

用法：
    CODEBUDDY_SESSION_ID= CLAUDE_SESSION_ID= \
    PYTHONPATH=_testenv \
    <py> _gate_all.py

结果落 _gatelog/<name>.log，同时在 stdout 打一行汇总。
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
LOGDIR = os.path.join(HERE, "_gatelog")

# 顺序：先物理/几何，再数据，再行为
CASES = [
    "_p_v230_spring",
    "_p_v230_prow",
    "_p_v230_pbsync",
    # v2.5.0：_p_v231_split 断言的是「两栏之间的那一条分隔条」，三栏化后
    # 已不适用（现在有两条，且栏宽口径从"左栏"变成"导航栏"）。
    # 该探针的覆盖由 _p_v250_3col 接替（三栏几何 + 两条分隔条 + 工具条 + 详情面板）。
    # 旧文件保留在项目根以便回溯，但不再进门禁。
    "_p_v250_3col",
    # v2.5.2：底部工具条按钮几何 + 信息不重复（带断言）。
    # 负向对照已验：换回 v2.5.1 源码时它报 6 项 FAIL（含精确复现的重叠 91px），
    # 换回 v2.5.2 则全绿 —— 不是恒真式。
    "_p_v252_btngap",
    # v2.5.3：栏 2 省略号口径统一后的行为验证。断言显示串不溢出 / 不过度截短 /
    # 省略串是全名前缀，并统计新旧实现的实际差异条数（实测 0，属纯去重）。
    "_p_v253_ellipsis",
    # v2.5.4：_build_ui 拆成 16 段 _ui_* 后的**结构等价**证明。逐控件比对
    # 类 / 布局参数 / 实测几何 / 文本（基线 _fixtures/ui_tree_baseline.json），
    # 外加两条运行时契约：关窗协议必须真的改绑到 _on_close。
    # 负向对照已验：把 dot_status 的 pack 方向左→右，它报 3 条差异（1 布局 + 2 几何）。
    "_p_v254_uistruct",
    "_p_v240_contrast",
    "_p_v240_tagprio",
    "_p_v240_latestbg",
    "_opt_unit",
    "_opt_dl",
    "_opt_gui",
    "_opt_boot_flow",
]


def main():
    if not os.path.isdir(LOGDIR):
        os.makedirs(LOGDIR)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(HERE, "_testenv")
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("CODEBUDDY_SESSION_ID", None)
    env.pop("CLAUDE_SESSION_ID", None)
    env["CODEBUDDY_SAFE_DELETE_SANDBOX"] = ""

    results = []
    for name in CASES:
        src = os.path.join(HERE, name + ".py")
        if not os.path.isfile(src):
            results.append((name, None, "MISSING"))
            continue
        t0 = time.time()
        p = subprocess.run(
            [PY, src],
            cwd=HERE,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        dt = time.time() - t0
        out = p.stdout.decode("utf-8", "replace")
        with open(os.path.join(LOGDIR, name + ".log"), "w", encoding="utf-8") as f:
            f.write(out)
        # 判据：rc==0 且输出里没有以 FAIL / ✗ / 不符 开头的失败行。
        # 不用「必须出现某句成功文案」—— 各探针的收尾措辞不统一（有的写「全部通过」，
        # 有的写「结论：…一致」），用成功文案当判据会误报（_p_v230_pbsync 就踩过）。
        # v2.5.3：前缀补上 ✗ / 不符。此前注释里写着这两条、代码里却只查 FAIL 三兄弟
        # —— 注释与代码脱节（v2.5.1 的 btn_cancel 就是同一类问题）。补之前已核对
        # _gatelog/ 下 13 份日志，无任何一行以 ✗ / 不符 开头，故不会引入误报。
        bad_lines = [
            ln for ln in out.splitlines()
            if ln.strip().startswith(("FAIL", "FAILED", "[FAIL]", "✗", "不符"))
        ]
        ok = (p.returncode == 0) and not bad_lines
        results.append((name, p.returncode, "OK" if ok else "FAIL", dt))

    print("=" * 62)
    print("v2.5.4 gate summary")
    print("=" * 62)
    bad = 0
    for row in results:
        if len(row) == 3:
            print("  %-22s %s" % (row[0], row[2]))
            bad += 1
            continue
        name, rc, verdict, dt = row
        print("  %-22s rc=%s  %-4s  %.1fs" % (name, rc, verdict, dt))
        if verdict != "OK":
            bad += 1
    print("-" * 62)
    print("TOTAL=%d  BAD=%d" % (len(CASES), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
