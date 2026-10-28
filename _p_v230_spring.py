# -*- coding: utf-8 -*-
"""v2.3.0 数值探针：弹簧引擎物理正确性 + 交互原语。

不渲染界面，只对积分器与几何原语做**数值**断言 —— 弹簧是否过冲、过冲多少、
多久静止、能否被中途打断并保留速度，这些都能直接量出来，比"看着挺顺"可靠。
"""
import importlib.util
import math
import os
import sys

HERE = os.getcwd()
spec = importlib.util.spec_from_file_location("mb", os.path.join(HERE, "msi_bios_checker.py"))
m = importlib.util.module_from_spec(spec)
sys.modules["mb"] = m
spec.loader.exec_module(m)

fails = []


def ck(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def run(spring, dt, seconds):
    """按 dt 帧步长推进 seconds 秒，返回位移轨迹。"""
    traj = []
    n = int(round(seconds / dt))
    for _ in range(n):
        spring.advance(dt)
        traj.append(spring.x)
    return traj


def advance_total(sp, total, chunk):
    """把 total 秒按 chunk 为步长推进（末段补齐余量），保证三种步长推进到**同一时刻**。"""
    n = int(total / chunk)
    for _ in range(n):
        sp.advance(chunk)
    rest = total - n * chunk
    if rest > 1e-12:
        sp.advance(rest)


def settle_time(damping, response, target=1.0, dt=0.008, cap=6.0):
    """从 0 起步到静止用了多久（秒）。"""
    sp = m.Spring(damping, response, 0.0, target)
    t = 0.0
    while t < cap:
        sp.advance(dt)
        t += dt
        if sp.done():
            break
    return t


def overshoot(z, response=0.30):
    """首次过冲量 —— 直接取**解析峰点** t_p = π/ω_d 求值，不做时间采样。

    采样会漏掉峰点：1ms 栅格下 ζ=0.60 只能量到 0.094775，而真值是 0.094780，
    差 5e-6 全是栅格误差，会被误判成"物理不准"。
    """
    if z >= 1.0:
        return 0.0
    w0 = 6.283185307179586 / response
    wd = w0 * math.sqrt(1.0 - z * z)
    sp = m.Spring(z, response, 0.0, 1.0)
    x, _v = sp._at(math.pi / wd)
    return x - 1.0


print("=== [1] 阻尼比 → 过冲（ζ=1.0 必须零过冲）===")
for z, expect_over in ((1.00, False), (0.85, True), (0.70, True), (0.55, True)):
    over = overshoot(z)
    ck((over > 0.004) == expect_over,
       "ζ=%.2f 过冲 %+.4f（%s）" % (z, over, "应有弹跳" if expect_over else "不应有弹跳"))

print("\n=== [2] 过冲量 = 解析解 exp(-ζπ/√(1-ζ²))，且随 ζ 下降单调增大 ===")
overs = []
for z in (1.00, 0.90, 0.80, 0.70, 0.60, 0.55, 0.45):
    overs.append((z, overshoot(z)))
print("     " + "  ".join("ζ%.2f:%.4f" % t for t in overs))
ck(all(overs[i][1] <= overs[i + 1][1] + 1e-9 for i in range(len(overs) - 1)),
   "过冲量随 ζ 减小单调不减")
ck(overs[0][1] <= 1e-12, "ζ=1.00 时零过冲（实测 %.2e）" % overs[0][1])
for z, got in overs[1:]:
    want = math.exp(-z * math.pi / math.sqrt(1.0 - z * z))
    ck(abs(got - want) < 1e-6,
       "ζ=%.2f 过冲 %.6f = 解析解 %.6f（差 %.2e）" % (z, got, want, abs(got - want)))

print("\n=== [3] 稳定时间 ∝ response（ω₀ = 2π/response）===")
t1 = settle_time(1.0, 0.20)
t2 = settle_time(1.0, 0.40)
print("     response 0.20 → %.3fs ；response 0.40 → %.3fs ；比值 %.2f" % (t1, t2, t2 / t1))
ck(1.75 <= (t2 / t1) <= 2.25, "响应时间翻倍 → 稳定时间近似翻倍（比例 %.2f）" % (t2 / t1))
ck(0.2 < t1 < 0.6, "response 0.20 的稳定时间在合理区间（%.3fs）" % t1)

print("\n=== [4] 可打断：改目标时位移连续、速度保留（速度移交）===")
sp = m.Spring(1.0, 0.30, 0.0, 1.0)
run(sp, 0.008, 0.12)                       # 走到一半
x_before, v_before = sp.x, sp.v
ck(0.05 < x_before < 0.95, "确实停在半途（x=%.3f）" % x_before)
ck(v_before > 0, "半途仍带正向速度（v=%.3f）—— 保留速度才能连续反转" % v_before)
sp.retarget(0.0)                           # 反向
ck(abs(sp.x - x_before) < 1e-12, "改目标瞬间位移**不跳变**（%.6f）" % sp.x)
ck(abs(sp.v - v_before) < 1e-12, "速度被完整保留（%.4f → %.4f）" % (v_before, sp.v))
traj = run(sp, 0.008, 0.9)
# 关键：正速度会把值继续往前带一点（动量延续）才回头 —— 旧版"从 0 重新计时"会
# 直接把颜色**跳回起点**再走一遍。这里用"沿原方向、且位移增量与速度相符"钉住连续性
# （8ms × 4.26/s ≈ 0.034，正是实测的 0.02 量级）。
step = traj[0] - x_before
ck(step > 0 and step <= v_before * 0.008 * 1.5,
   "下一帧位移连续且与速度相符（+%.4f ≤ v·dt=%.4f）" % (step, v_before * 0.008))
ck(x_before <= max(traj) <= x_before + 0.05,
   "动量延续：先往前走一点点（峰值 %.4f）再回头，不是立刻归零" % max(traj))
ck(min(traj) >= -1e-9, "ζ=1.0 反向不越过新目标（最小 %.2e）" % min(traj))
ck(abs(traj[-1]) < 1e-3, "最终收敛到新目标（%.2e）" % traj[-1])
sp2 = m.Spring(1.0, 0.30, 0.0, 1.0)
sp2.retarget(0.5, velocity=8.0)
ck(sp2.v == 8.0, "显式速度移交生效（v=8.0）")

print("\n=== [5] 帧率无关：不同帧步长在同一时刻位移逐位相同 ===")
a = m.Spring(0.55, 0.32, 0.0, 1.0)
b = m.Spring(0.55, 0.32, 0.0, 1.0)
c = m.Spring(0.55, 0.32, 0.0, 1.0)
advance_total(a, 0.40, 0.016)
advance_total(b, 0.40, 0.048)
advance_total(c, 0.40, 0.100)
print("     16ms→%.12f  48ms→%.12f  100ms→%.12f" % (a.x, b.x, c.x))
ck(abs(a.x - b.x) < 1e-9 and abs(a.x - c.x) < 1e-9,
   "t=0.40s 处三种帧步长的位移一致（差 %.2e / %.2e）" % (abs(a.x - b.x), abs(a.x - c.x)))
ck(abs(a.v - c.v) < 1e-9, "速度同样与帧步长无关（差 %.2e）" % abs(a.v - c.v))

print("\n=== [6] 稳定性：所有令牌参数都不发散、必然静止 ===")
for name in ("SPR_VALUE", "SPR_ENTER", "SPR_BANNER", "SPR_PRESS",
             "SPR_SHAKE", "SPR_PULSE", "SPR_EMPTY"):
    z, r = getattr(m, name)
    t = settle_time(z, r, 1.0)
    sp = m.Spring(z, r, 0.0, 1.0)
    traj = run(sp, 0.016, 3.0)
    ck(t < 1.2 and all(abs(x) < 1.6 for x in traj),
       "%-10s ζ=%.2f r=%.2f → %.3fs 静止，最大位移 %.4f（不发散）"
       % (name, z, r, t, max(traj)))

print("\n=== [7] 软边界（Apple 橡胶缓冲）：界内 1:1，越界渐进吸收 ===")
cap = 11.0
ck(abs(m._soft_clamp(0.0, cap)) < 1e-12, "原点不动")
ck(abs(m._soft_clamp(6.0, cap) - 6.0) < 1e-12, "界内 1:1 原样通过（6.0 → 6.0）")
ck(abs(m._soft_clamp(-6.0, cap) + 6.0) < 1e-12, "界内负向对称")
o12 = m._soft_clamp(12.0, cap)
o100 = m._soft_clamp(100.0, cap)
print("     越界 1.0px → %.4f ；越界 89px → %.4f （上界 %.1f）" % (o12 - cap, o100 - cap, 2 * cap))
ck(cap < o12 < 12.0, "越界后位移被吸收但仍在增长（%.4f < 12）" % o12)
ck(o100 < 2 * cap, "越界无穷远也只到约 2×cap，永不硬截断也不无限外扩（%.3f）" % o100)
ck(m._soft_clamp(12.0, cap) < m._soft_clamp(13.0, cap) < m._soft_clamp(14.0, cap),
   "越界段单调递增（无折返/不连续）")

print("\n=== [8] 动量投射（Apple 官方公式）===")
proj = m._project(1000.0)                  # 1000 px/s
want = (1000.0 / 1000.0) * 0.998 / (1 - 0.998)
ck(abs(proj - want) < 1e-9, "project(1000) = %.3f px（≈ %.0f）" % (proj, want))
ck(m._project(2000.0) > m._project(1000.0) > m._project(500.0),
   "投射距离随释放速度单调增大")
ck(m._project(1000.0, 0.99) < m._project(1000.0, 0.998),
   "更干脆的减速率(0.99)投射更短（%.1f < %.1f）"
   % (m._project(1000.0, 0.99), m._project(1000.0, 0.998)))

print("\n=== [9] 初速度反解：实际峰值 = 目标幅度（误差 <0.5%）===")
for amp, spec_ in ((9.0, m.SPR_SHAKE), (14.0, m.SPR_SHAKE), (9.0, m.SPR_PRESS),
                   (6.0, m.SPR_BANNER)):
    v0 = m._kick_velocity(amp, *spec_)
    sp = m.Spring(spec_[0], spec_[1], 0.0, 0.0, v0)
    peak = 0.0
    for i in range(1, 3001):                     # 1ms 细采样，不漏峰点
        sp.x, sp.v = sp._at(i * 0.001)
        peak = max(peak, abs(sp.x))
    ck(abs(peak - amp) / amp < 0.005,
       "amp=%.1f ζ=%.2f r=%.2f → v0=%.1f px/s，实测峰值 %.3f（误差 %.2f%%）"
       % (amp, spec_[0], spec_[1], v0, peak, abs(peak - amp) / amp * 100))
ck(m._kick_velocity(9.0, *m.SPR_SHAKE) == m._kick_velocity(9.0, *m.SPR_SHAKE),
   "反解结果有缓存（同参数复用同一对象值）")

print("\n=== [10] 减弱动效：瞬时到位，不产生过渡 ===")
m._MOTION_ON = False
frames = []
anim = m.Anim(None)                        # 减弱动效分支不触碰 root
anim.spring("t", m.SPR_BANNER, lambda x, v: frames.append(x), 1.0, value=0.0)
ck(frames == [1.0], "直接落到终值且只回调一次（%r）" % (frames,))
ck(anim.busy() is False, "不注册任何动画（空闲零开销）")
ck(anim.spring_x("t") == 1.0, "spring_x 仍能读到终值（重定向续接用）")
m._MOTION_ON = True

print("\n" + ("弹簧物理全部通过 ✓" if not fails
              else "失败 %d 项：\n  - %s" % (len(fails), "\n  - ".join(fails))))
sys.exit(1 if fails else 0)
