# -*- coding: utf-8 -*-
"""v2.2.0 验证（二）：下载层（断点续传 / 增量 SHA-256 / 取消保留分片 / 落盘）。

用本地 HTTP 服务器做真实往返：能分别模拟「支持 Range」与「不支持 Range」两种服务端。
"""
import hashlib
import http.server
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import threading
import time

spec = importlib.util.spec_from_file_location("mb", "msi_bios_checker.py")
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

fails = []


def ck(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


DATA = bytes(bytearray(((i * 7 + 13) % 251) for i in range(400000)))   # 400 KB 伪 BIOS
SHA = hashlib.sha256(DATA).hexdigest()
SEEN_RANGES = []


class Handler(http.server.BaseHTTPRequestHandler):
    support_range = True
    chunk_delay = 0.0

    def do_GET(self):
        rng = self.headers.get("Range")
        SEEN_RANGES.append(rng)
        start = 0
        if rng and self.support_range:
            mt = re.match(r"bytes=(\d+)-", rng)
            if mt:
                start = int(mt.group(1))
            body = DATA[start:]
            self.send_response(206)
            self.send_header("Content-Range",
                             "bytes %d-%d/%d" % (start, len(DATA) - 1, len(DATA)))
        else:
            body = DATA
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        step = 65536
        for i in range(0, len(body), step):
            self.wfile.write(body[i:i + step])
            if self.chunk_delay:
                time.sleep(self.chunk_delay)

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/fw.zip" % PORT
tmp = tempfile.mkdtemp()
print("本地测试服务器 127.0.0.1:%d，载荷 %d 字节" % (PORT, len(DATA)))

try:
    print("\n=== [1] 全量下载 + 增量摘要 ===")
    SEEN_RANGES.clear()
    dest = os.path.join(tmp, "full.zip")
    ok, path, err, sha = m.do_download(URL, dest,
                                       progress_cb=lambda d, t: True)
    ck(ok and err is None, "下载成功（err=%r）" % (err,))
    ck(sha == SHA, "返回的摘要 = 整文件 SHA-256（增量算，未重读）")
    ck(io.open(dest, "rb").read() == DATA, "字节完全一致")
    ck(not os.path.exists(dest + ".part"), "成功后不留 .part")
    ck(abs(os.path.getsize(dest) - len(DATA)) == 0, "文件大小一致")
    ck(SEEN_RANGES and SEEN_RANGES[0] is None, "全新下载不带 Range 头")

    print("\n=== [2] 断点续传（服务端支持 Range）===")
    SEEN_RANGES.clear()
    dest2 = os.path.join(tmp, "resume.zip")
    part = dest2 + ".part"
    io.open(part, "wb").write(DATA[:120000])          # 预置 120KB 半成品
    seen_total = []

    def cb2(done, total):
        seen_total.append((done, total))
        return True

    ok, path, err, sha = m.do_download(URL, dest2, progress_cb=cb2)
    ck(ok, "续传下载成功（err=%r）" % (err,))
    ck(SEEN_RANGES[0] == "bytes=120000-", "确实发了 Range: bytes=120000-（实测 %r）" % SEEN_RANGES[0])
    ck(sha == SHA, "续传后摘要仍等于整文件（含对已有分片的补算）")
    ck(io.open(dest2, "rb").read() == DATA, "拼接结果字节完全一致（无错位）")
    ck(seen_total and seen_total[0][0] >= 120000, "首次进度从断点处起算（%d）" % (seen_total[0][0] if seen_total else -1))
    ck(seen_total and seen_total[0][1] == len(DATA),
       "总大小按 Content-Range 解析为整文件大小（%s）" % (seen_total[0][1] if seen_total else None))
    ck(not os.path.exists(part), "完成后 .part 改名，无残留")

    print("\n=== [3] 服务端不支持 Range → 自动回退全量 ===")
    Handler.support_range = False
    SEEN_RANGES.clear()
    dest3 = os.path.join(tmp, "norange.zip")
    io.open(dest3 + ".part", "wb").write(DATA[:77777])   # 残留半成品（内容还是旧的）
    ok, path, err, sha = m.do_download(URL, dest3, progress_cb=lambda d, t: True)
    Handler.support_range = True
    ck(ok, "回退后仍下载成功（err=%r）" % (err,))
    ck(io.open(dest3, "rb").read() == DATA, "回退时丢弃旧分片、结果无拼接损坏")
    ck(sha == SHA, "摘要正确")

    print("\n=== [4] 取消 → 保留分片（续传原料）===")
    Handler.chunk_delay = 0.02            # 放慢一点，避免一次 recv 就收完
    dest4 = os.path.join(tmp, "cancel.zip")
    ev = threading.Event()
    CUT = 150000

    def cb4(done, total):
        # 按「已下字节数」确定性触发取消（不依赖墙钟，避免 400KB 秒下完导致测不到）
        if done >= CUT:
            ev.set()
        return True

    ok, path, err, sha = m.do_download(URL, dest4, progress_cb=cb4, cancel_event=ev)
    Handler.chunk_delay = 0.0
    ck((not ok) and err == "已取消", "返回已取消（%r）" % (err,))
    ck(os.path.exists(dest4 + ".part"), "取消后 **保留** .part")
    psz = m._part_size(dest4 + ".part")
    ck(CUT <= psz < len(DATA), "分片大小居中不完整（%d 字节，触发点 %d）" % (psz, CUT))
    ck(not os.path.exists(dest4), "目标文件未生成（不会留半成品）")
    # 再次下载 → 从断点续传并最终校验通过
    SEEN_RANGES.clear()
    ok, path, err, sha = m.do_download(URL, dest4, progress_cb=lambda d, t: True)
    ck(ok and sha == SHA, "取消后重下：续传完成且摘要正确")
    ck(SEEN_RANGES[0] == "bytes=%d-" % psz, "第二次带 Range: bytes=%d-" % psz)
    ck(io.open(dest4, "rb").read() == DATA, "最终文件字节一致")

    print("\n=== [5] 异常路径（连不上的主机）===")
    dest5 = os.path.join(tmp, "dead.zip")
    io.open(dest5 + ".part", "wb").write(b"partial")
    ok, path, err, sha = m.do_download("http://127.0.0.1:1/x.zip", dest5)
    ck(not ok and err, "连接失败被捕获并返回 err（不抛异常）")
    ck(os.path.exists(dest5 + ".part"), "失败也保留分片（便于重试续传）")
finally:
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + ("全部通过 ✓" if not fails else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
