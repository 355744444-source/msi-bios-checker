"""v2.5.6 视觉核对：
  A. 冻结版 exe 在空目录首启（无缓存）—— 目录要真的加载出来（403 已修）
  B. 源码 + 模拟 403 失败 —— 失败占位要变成可点的「点此重试」

截图落 _smoke/，不写工程目录。
"""
import ctypes
import ctypes.wintypes as wt
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk

from PIL import ImageGrab

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_smoke")
os.makedirs(OUT, exist_ok=True)
TITLE = "微星主板 BIOS 下载工具"
u32 = ctypes.windll.user32


def find_window(title_part, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
        def cb(hwnd, _lp):
            if not u32.IsWindowVisible(hwnd):
                return True
            n = u32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                u32.GetWindowTextW(hwnd, buf, n + 1)
                if title_part in buf.value:
                    found.append(hwnd)
            return True

        u32.EnumWindows(cb, 0)
        if found:
            return found[0]
        time.sleep(0.5)
    return None


def rect_of(hwnd):
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def shot(hwnd, path):
    l, t, r, b = rect_of(hwnd)
    img = ImageGrab.grab()
    img.crop((l, t, r, b)).save(path)
    print("saved", path, (r - l, b - t))


def case_a():
    print("[A] frozen exe, empty dir, cold start")
    tmp = tempfile.mkdtemp(prefix="v256shotA_")
    exe = os.path.join(HERE, "dist", "微星主板BIOS下载工具.exe")
    # 让 exe 把 cache/log 落在临时目录：复制一份 exe 过去
    local = os.path.join(tmp, os.path.basename(exe))
    shutil.copy2(exe, local)
    t0 = time.time()
    p = subprocess.Popen([local], cwd=tmp)
    hwnd = find_window(TITLE, 60)
    if not hwnd:
        print("FAIL window not found")
        p.terminate()
        return False
    # 等目录真的落盘（catalog 写盘 = 抓取完成）
    cache = os.path.join(tmp, "msi_mb_catalog.json")
    end = time.time() + 120
    while time.time() < end and not os.path.isfile(cache):
        time.sleep(1)
    print("   catalog after %.1fs -> %s" % (time.time() - t0, os.path.isfile(cache)))
    time.sleep(2.5)
    shot(hwnd, os.path.join(OUT, "v256_a_cold_start.png"))
    try:
        u32.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.5)
    shot(hwnd, os.path.join(OUT, "v256_a_cold_start.png"))
    log = os.path.join(tmp, "msi_bios_checker.log")
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            txt = f.read()
        print("   log tail:", txt.strip().splitlines()[-3:])
    if os.path.isfile(cache):
        import json
        with open(cache, encoding="utf-8") as f:
            cat = json.load(f)
        print("   total=%s source=%s" % (cat.get("total"), cat.get("source")))
    p.terminate()
    try:
        p.wait(10)
    except Exception:
        p.kill()
    return os.path.isfile(cache)


def case_b():
    print("[B] source + simulated 403 failure")
    tmp = tempfile.mkdtemp(prefix="v256shotB_")
    os.chdir(tmp)
    spec = importlib.util.spec_from_file_location(
        "mb", os.path.join(HERE, "msi_bios_checker.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["mb"] = m
    spec.loader.exec_module(m)

    root = tk.Tk()
    m._apply_dpi_scale(96)
    app = m.App(root)
    app._restored = True
    for aid in root.tk.call("after", "info"):
        try:
            root.after_cancel(aid)
        except Exception:
            pass
    root.geometry("1400x840+60+60")
    root.deiconify()
    for _ in range(8):
        root.update_idletasks()
        root.update()
        time.sleep(0.03)
    app._apply_catalog(None, "请求失败: HTTP 403")
    for _ in range(4):
        app._poll_queue()
        root.update_idletasks()
        root.update()
        time.sleep(0.05)
    # 置于最前再抓：桌面此时有其他窗口，SetForegroundWindow 会被系统拒绝，
    # 结果抓到的是叠在上面的别的程序（第一版就抓错了）。
    try:
        root.attributes("-topmost", True)
        root.lift()
        root.focus_force()
    except Exception:
        pass
    for _ in range(10):
        root.update_idletasks()
        root.update()
        time.sleep(0.05)
    time.sleep(0.8)
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    img = ImageGrab.grab()
    img.crop((x, y, x + w, y + h)).save(os.path.join(OUT, "v256_b_failure.png"))
    print("saved b", (x, y, w, h))
    print("   v_cat=%r ph=%r board=%r" % (app.v_cat.get(),
                                          app._cat_ph.cget("text"),
                                          app._board_ph.cget("text")))
    root.destroy()
    return True


if __name__ == "__main__":
    ok_a = case_a()
    ok_b = case_b()
    print("\nRESULT A=%s B=%s" % (ok_a, ok_b))
    sys.exit(0 if (ok_a and ok_b) else 1)
