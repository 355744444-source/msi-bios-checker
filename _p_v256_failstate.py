# -*- coding: utf-8 -*-
"""v2.5.6 门禁：目录加载失败时的界面状态（不是恒真式）。

背景（2026-11-04 用户截图）：Akamai 把 chrome124 指纹拉黑后目录请求稳定 403，
两栏占位块一直停在「正在读取主板目录…」，栏 2 底部却写着「目录加载失败」——
一个界面同时说"在读"和"读失败了"，而且没有任何出口，用户只能关掉重开。

六个判据：

  1. 无目录 + 未失败 -> 占位仍是「正在读取主板目录…」（正常加载态不被改坏）
  2. 无目录 + 首次失败 -> 栏 1 占位变成可点的「点此重试」：
       文案含「重试」、cursor=hand2、前景色 = 品牌红
     旧版这里什么都不做，占位永远停在「正在读取」。
  3. 无目录 + 失败 -> 栏 2 占位不得再声称"在读取目录"（它的语义是"还没有型号"）
  4. 点失败占位 -> 真的会触发一次重新抓取；非失败态点击不触发（不误触）
  5. **已有目录 + 刷新失败** -> 保留原有计数与列表，不得把栏 1 读数改成
     「目录加载失败」（旧版无条件覆盖，界面自相矛盾）
  6. 抓取成功 -> 失败标记清零、状态栏给出数据源（官网 / 中国站）

用法：
    CODEBUDDY_SESSION_ID= CLAUDE_SESSION_ID= PYTHONPATH=_testenv <py> _p_v256_failstate.py
输出纯 ASCII，失败行以 FAIL 开头（_gate_all.py 靠这个判据）。
"""
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
    print("  %-50s %s%s" % (name, "ok" if ok else "FAIL", ("  " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)
    return ok


# 空临时目录：没有 msi_mb_catalog.json -> App 处于"首次使用、无目录"状态
TMP = tempfile.mkdtemp(prefix="v256gate_")
os.chdir(TMP)

root = tk.Tk()
root.withdraw()
m._apply_dpi_scale(96)
app = m.App(root)
app._restored = True
for aid in root.tk.call("after", "info"):
    try:
        root.after_cancel(aid)
    except Exception:
        pass
root.geometry("1400x820+40+40")
root.deiconify()


def pump(n=6, pause=0.02):
    for _ in range(n):
        root.update_idletasks()
        root.update()
        time.sleep(pause)


def settle(n=3):
    """状态栏文案是排队的（_set_status -> q -> _poll_queue），必须显式排空；
    否则读到的是 _populate_tree 末尾那条即时的「就绪 · 请在左侧选择…」。"""
    for _ in range(n):
        app._poll_queue()
        pump(2)


pump()


def ph_text(lbl):
    return str(lbl.cget("text"))


def ph_visible(lbl):
    return bool(lbl.place_info())


ERR403 = "请求失败: HTTP 403"

# ---------------------------------------------------------------- 1 加载态
print("[1] no catalog + not failed -> loading placeholder")
app.catalog = None
app._cat_failed = False
app._populate_tree()
pump(2)
check("cat placeholder says reading",
      ph_visible(app._cat_ph) and "正在读取" in ph_text(app._cat_ph),
      repr(ph_text(app._cat_ph)))
check("cat counter says loading", "加载中" in app.v_cat.get(), repr(app.v_cat.get()))

# ---------------------------------------------------------------- 2/3 首次失败
print("[2] no catalog + first failure -> clickable retry")
app._apply_catalog(None, ERR403)
settle()
txt = ph_text(app._cat_ph)
check("cat placeholder visible", ph_visible(app._cat_ph))
check("cat placeholder offers retry", "重试" in txt, repr(txt))
check("retry uses hand cursor", str(app._cat_ph.cget("cursor")) == "hand2",
      repr(app._cat_ph.cget("cursor")))
check("retry uses brand red", str(app._cat_ph.cget("fg")).lower() == m.C_ACCENT.lower(),
      repr(app._cat_ph.cget("fg")))
check("counter says failed", app.v_cat.get() == "目录加载失败", repr(app.v_cat.get()))
check("failed flag set", app._cat_failed is True)
btxt = ph_text(app._board_ph)
check("board placeholder stops claiming reading", "读取" not in btxt, repr(btxt))
check("status explains retry path", "重试" in app.v_status.get(), repr(app.v_status.get()))
# 旧版症状：两栏都停在"正在读取主板目录…"
check("both panes not stuck on 'reading'",
      not (("正在读取" in txt) and ("正在读取" in btxt)), "%r | %r" % (txt, btxt))

# ---------------------------------------------------------------- 4 点击重试
print("[3] click retry only fires when failed")
calls = {"n": 0}
_orig_start = app._start_catalog


def _fake_start():
    calls["n"] += 1
    return True


app._start_catalog = _fake_start
app._on_cat_ph_click()
check("click while failed triggers refetch", calls["n"] == 1, "n=%d" % calls["n"])
app._cat_failed = False
app._on_cat_ph_click()
check("click while healthy is ignored", calls["n"] == 1, "n=%d" % calls["n"])
app._cat_failed = True
app._start_catalog = _orig_start

# ---------------------------------------------------------------- 5 刷新失败保留缓存
print("[4] cached catalog + refresh failure keeps the list")
fake = {"updated": "2026-10-28 09:11", "total": 2, "uncovered": [],
        "brands": [{"name": "Intel", "count": 2, "chipsets": [
            {"name": "Z890", "boards": [
                {"id": 1, "title": "MEG Z890 GODLIKE", "slug": "MEG-Z890-GODLIKE"},
                {"id": 2, "title": "MAG Z890 TOMAHAWK WIFI", "slug": "MAG-Z890-TOMAHAWK-WIFI"},
            ]}]}]}
app.catalog = fake
app.cat_updated = fake["updated"]
app._cat_failed = False
app._populate_tree()
pump(2)
before = app.v_cat.get()
check("counter shows 2 boards before refresh", "2" in before, repr(before))
app._apply_catalog(None, ERR403)
settle()
check("catalog preserved", app.catalog is fake)
check("counter not overwritten with failure", app.v_cat.get() == before,
      "%r -> %r" % (before, app.v_cat.get()))
check("failure flag stays clear", app._cat_failed is False)
check("status says keeping local catalog", "继续使用" in app.v_status.get(),
      repr(app.v_status.get()))
check("tree still has 2 boards",
      sum(len(app.iid_chip[i][1]) for i in app.iid_chip) == 2,
      "n=%d" % sum(len(app.iid_chip[i][1]) for i in app.iid_chip))

# ---------------------------------------------------------------- 6 成功态
print("[5] success clears failure and names the source")
cat = dict(fake)
cat["source"] = "com"
app._apply_catalog(cat, None)
settle()
check("failed flag cleared", app._cat_failed is False)
check("counter shows board count", "共 2 款" == app.v_cat.get(), repr(app.v_cat.get()))
check("status names global site", "官网" in app.v_status.get(), repr(app.v_status.get()))
cat_cn = dict(fake)
cat_cn["source"] = "cn"
app._apply_catalog(cat_cn, None)
settle()
check("status names china site", "中国站" in app.v_status.get(), repr(app.v_status.get()))
check("placeholder hidden when populated", not ph_visible(app._cat_ph))

# ---------------------------------------------------------------- 7 网络层判据
print("[6] block detection + fingerprint ordering")
check("403 recognised as block", m._is_block_err("请求失败: HTTP 403"))
check("429 recognised as block", m._is_block_err("请求失败: HTTP 429"))
check("500 is not a block (retry instead)",
      not m._is_block_err("请求失败: HTTP 500"))
check("cooldown message still recognised",
      m._is_block_err("请求失败: HTTP 403（全球站冷却中，改走中国站）"))
saved_fails, saved_best = dict(m._IMP_FAILS), m._IMP_BEST
try:
    m._IMP_FAILS.clear()
    m._IMP_BEST = None
    first = m._imp_order()[0]
    m._imp_mark(first, False)
    check("failed fingerprint leaves the front", m._imp_order()[0] != first,
          "%s -> %s" % (first, m._imp_order()[0]))
    second = m._imp_order()[0]
    m._imp_mark(second, True)
    check("working fingerprint sticks to the front", m._imp_order()[0] == second)
    check("success clears its failure count", m._IMP_FAILS.get(second, 0) == 0)
finally:
    m._IMP_FAILS.clear()
    m._IMP_FAILS.update(saved_fails)
    m._IMP_BEST = saved_best

print("")
if FAILS:
    print("FAIL %d case(s)" % len(FAILS))
    for f in FAILS:
        print("  - " + f)
    code = 1
else:
    print("PASS all")
    code = 0
try:
    root.destroy()
except Exception:
    pass
try:
    shutil.rmtree(TMP, ignore_errors=True)
except Exception:
    pass
sys.exit(code)
