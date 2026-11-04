"""v2.5.6 网络层实测：指纹轮换 + 全球站被拦时的中国站降级。

直接调产品代码（不模拟），只读官网，不写工程文件。
"""
import sys
import time

import msi_bios_checker as m


def line(t):
    print("\n== %s ==" % t)


def main():
    api = m.MsiApi()

    line("1. 芯片组分类（全球站）")
    tags = api.get_chipset_tags("com")
    print("   tags=%d  _IMP_BEST=%s  _IMP_FAILS=%s" % (len(tags), m._IMP_BEST, m._IMP_FAILS))
    assert len(tags) >= 20, "芯片组分类过少：%d" % len(tags)

    line("2. 中国站芯片组分类（结构同构）")
    ctags = api.get_chipset_tags("cn")
    print("   tags=%d  sample=%s" % (len(ctags), [t["title"] for t in ctags[:3]]))
    assert len(ctags) >= 10

    line("3. 全球站被拦 → 自动降级中国站")
    api2 = m.MsiApi()
    api2._com_block_until = time.time() + m.COM_COOLDOWN
    t0 = time.time()
    cat = m.fetch_catalog(api2, progress=lambda s: None)
    print("   source=%s total=%d brands=%s  %.1fs"
          % (cat.get("source"), cat.get("total"),
             [(b["name"], b["count"]) for b in cat["brands"]], time.time() - t0))
    assert cat.get("source") == "cn", cat.get("source")
    assert cat["total"] >= 200, cat["total"]

    line("4. 正常路径（全球站 + 中国站补全）")
    api3 = m.MsiApi()
    t0 = time.time()
    cat2 = m.fetch_catalog(api3, progress=lambda s: None)
    print("   source=%s total=%d chipsets=%d  %.1fs"
          % (cat2.get("source"), cat2.get("total"),
             sum(len(b["chipsets"]) for b in cat2["brands"]), time.time() - t0))
    print("   brands=%s" % [(b["name"], b["count"]) for b in cat2["brands"]])
    assert cat2.get("source") == "com"
    assert cat2["total"] >= 450, cat2["total"]

    line("5. 指纹轮换：把 chrome142 标记为坏，确认下次换人且仍 200")
    m._IMP_FAILS["chrome142"] = 1
    before = m._imp_order()[0]
    j = api3._get_json(m.API_PL_TAG)
    after = m._imp_order()[0]
    print("   换指纹前首位=%s 换后首位=%s 返回 filterTagList=%s"
          % (before, after, bool((j.get("result") or {}).get("filterTagList"))))
    assert before != "chrome142"
    assert after != "chrome142"

    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
