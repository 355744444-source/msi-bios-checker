# -*- coding: utf-8 -*-
"""v2.2.0 验证（一）：纯函数 / 缓存 / 配置持久化。无需 GUI、无需网络。"""
import importlib.util
import io
import os
import sys
import tempfile

spec = importlib.util.spec_from_file_location("mb", "msi_bios_checker.py")
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

fails = []


def ck(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


print("=== [1] LRU 有界容器 ===")
l = m.LRU(3)
for i in range(5):
    l.put("k%d" % i, i)
ck(len(l) == 3, "上限生效（放 5 个留 3 个）")
ck(l.get("k0") is None and l.get("k1") is None, "淘汰最久未用的 k0/k1")
ck(l.get("k4") == 4, "最近写入的 k4 在")
l.get("k2")                    # 命中 → 变为最近使用
l.put("k9", 9)                 # 应淘汰 k3（此时最久未用）
ck(l.get("k3") is None, "命中过的 k2 被保护，k3 被淘汰")
ck(l.get("k2") == 2 and l.get("k9") == 9, "k2/k9 仍在")
ck("k9" in l and len(l) == 3, "__contains__ / __len__")
l.clear()
ck(len(l) == 0, "clear")

print("\n=== [2] 文本省略 _ellipsize ===")
mm = lambda s: len(s) * 10            # 注入测量：每字符 10px
ck(m._ellipsize("ABC", 100, None, None, measure=mm) == "ABC", "宽度足够时不改动")
ck(m._ellipsize("ABCDEFGHIJ", 55, None, None, measure=mm) == "ABCD…", "二分裁剪 + 省略号")
ck(m._ellipsize("ABCDEFGHIJ", 5, None, None, measure=mm) == "…", "极窄时只留省略号")
ck(all(mm(m._ellipsize("A" * 40, w, None, None, measure=mm)) <= w
       for w in (20, 35, 55, 95, 155)), "任意宽度下结果都不超过预算")

print("\n=== [3] DoH 健康记忆 ===")
m._DOH_FAILS.clear()
ck(m._doh_order() == m.DOH_URLS, "初始顺序 = 配置顺序")
for _ in range(m._DOH_DEMOTE_AT):
    m._doh_mark(m.DOH_URLS[0], False)
ck(m._doh_order()[0] == m.DOH_URLS[1], "连续失败 3 次 → 降到队尾")
m._doh_mark(m.DOH_URLS[0], True)
ck(m._doh_order() == m.DOH_URLS, "一次成功 → 计数清零、恢复原位")
m._DOH_FAILS.clear()

print("\n=== [4] 退避抖动 ===")
ds = [m._backoff_delay(i) for i in range(30)]
ck(max(ds) <= m.NET_BACKOFF_MAX + 1e-9, "不超过上限 %.1fs（实测最大 %.2f）" % (m.NET_BACKOFF_MAX, max(ds)))
ck(min(ds) > 0, "不为 0")
ck(len({round(m._backoff_delay(3), 6) for _ in range(10)}) > 1, "带随机抖动")
ck(m._backoff_delay(0) < m._backoff_delay(5), "随重试次数增长")

print("\n=== [5] 原子写 ===")
tmpdir = tempfile.mkdtemp()
p = os.path.join(tmpdir, "a.json")
ck(m._atomic_write(p, '{"x":1}'), "返回成功")
ck(io.open(p, encoding="utf-8").read() == '{"x":1}', "内容正确")
ck(not os.path.exists(p + ".tmp"), "无残留 .tmp")

print("\n=== [6] 配置持久化（新状态字段）===")
cwd = os.getcwd()
os.chdir(tmpdir)
try:
    ok = m.save_cfg({"refresh_days": 3, "win": [1200, 780, 10, 20],
                     "last_slug": "MPG-Z790-EDGE", "last_title": "MPG Z790 EDGE",
                     "last_dir": "D:\\bios", "expanded": ["Z890", "B760"]})
    c = m.load_cfg()
    ck(ok and c["win"] == [1200, 780, 10, 20], "win 往返")
    ck(c["last_slug"] == "MPG-Z790-EDGE" and c["last_dir"] == "D:\\bios", "slug / 目录 往返")
    ck(c["expanded"] == ["Z890", "B760"], "展开记录往返")
    ck(c["refresh_days"] == 3, "旧字段不受影响")
    ck(sorted(c.keys()) == sorted(m.DEFAULT_CFG.keys()), "字段集合 = DEFAULT_CFG")

    io.open(m._cfg_path(), "w", encoding="utf-8").write(
        '{"refresh_days":"bad","win":[1,2,3],"last_slug":5,"expanded":"x","last_dir":null}')
    c = m.load_cfg()
    ck(c["win"] is None, "win 长度不对 → 回退 None")
    ck(c["last_slug"] == "" and c["last_dir"] == "", "类型不对 → 回退空串")
    ck(c["expanded"] == [], "expanded 类型不对 → 空列表")
    ck(c["refresh_days"] == m.DEFAULT_REFRESH_DAYS, "refresh_days 非法 → 回退默认")

    io.open(m._cfg_path(), "w", encoding="utf-8").write("{ 这不是 json")
    c = m.load_cfg()
    ck(c["refresh_days"] == m.DEFAULT_REFRESH_DAYS, "整文件损坏 → 全默认（不抛异常）")
finally:
    os.chdir(cwd)

print("\n=== [7] 窗口几何恢复 ===")


class _Fake(object):
    pass


f = _Fake()
f.cfg = {}
w, h, geo = m.App._restore_geometry(f)
ck(geo == "%dx%d" % (w, h), "无记录 → 默认尺寸、不定位（由系统居中）")
f.cfg = {"win": [1000, 700, 50, 60]}
w, h, geo = m.App._restore_geometry(f)
ck(geo == "%dx%d+50+60" % (w, h), "记录有效 → 原样恢复位置")
f.cfg = {"win": [1000, 700, -99999, 99999]}
w, h, geo = m.App._restore_geometry(f)
ck("+" not in geo, "位置越界 → 丢弃位置只保留尺寸")
f.cfg = {"win": [99999, 99999, 10, 10]}
w, h, geo = m.App._restore_geometry(f)
aw, ah = m._work_area()
ck(w <= aw and h <= ah, "超大尺寸被夹紧到工作区 %dx%d" % (aw, ah))
f.cfg = {"win": "garbage"}
ck(m.App._restore_geometry(f)[2] == "%dx%d" % m.App._restore_geometry(f)[:2], "脏数据不抛异常")

print("\n=== [8] 下载分片尺寸助手 ===")
ck(m._part_size(os.path.join(tmpdir, "不存在")) == 0, "文件不存在 → 0")
fp = os.path.join(tmpdir, "s.part")
io.open(fp, "wb").write(b"x" * 1234)
ck(m._part_size(fp) == 1234, "已存在 → 实际大小")

print("\n" + ("全部通过 ✓" if not fails else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
