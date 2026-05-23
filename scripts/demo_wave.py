#!/usr/bin/env python3
"""SO-101 팔로워 웨이브 데모.

캘리브레이션 기준의 안전한 범위 내에서 부드럽게 움직이는 데모.
가동범위 50% 사용.
"""

import math
import os
import time
from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig

PORT = os.getenv("FOLLOWER_PORT", "/dev/ttyACM0")
ROBOT_ID = os.getenv("FOLLOWER_ID", "my_follower_arm")
DURATION = 15.0     # 총 재생 시간 (초)
FPS = 30
RANGE_USE = 0.5     # 가동범위의 50%만 사용

# 안정적인 쉬는 자세 (teleop_keyboard.py의 HOME_POS와 동일)
HOME_POS = {
    "shoulder_pan": 0.3,
    "shoulder_lift": -36.0,
    "elbow_flex": 36.2,
    "wrist_flex": -41.7,
    "wrist_roll": -0.1,
    "gripper": 2.7,
}


def compute_amplitudes(robot):
    """각 관절의 캘리브레이션 중심과 amplitude 계산."""
    MAX_RES = 4095
    amps = {}
    for name, cal in robot.bus.calibration.items():
        mid = (cal.range_min + cal.range_max) / 2
        if name == "gripper":
            lo, hi = 0.0, 100.0
        else:
            lo = (cal.range_min - mid) * 360 / MAX_RES
            hi = (cal.range_max - mid) * 360 / MAX_RES
        center = (lo + hi) / 2
        amp = (hi - lo) / 2 * RANGE_USE
        amps[name] = (center, amp)
    return amps


def approach(robot, target, duration=3.0, steps=90):
    """현재 위치에서 target까지 부드럽게 이동."""
    obs = robot.get_observation()
    start = {k: v for k, v in obs.items() if k.endswith(".pos")}
    for i in range(1, steps + 1):
        a = i / steps
        inter = {k: start[k] + (target[k] - start[k]) * a for k in start}
        robot.send_action(inter)
        time.sleep(duration / steps)


def main():
    config = SOFollowerRobotConfig(port=PORT, id=ROBOT_ID, use_degrees=True)
    robot = SOFollower(config)
    robot.connect()

    amps = compute_amplitudes(robot)
    print("각 관절 동작:")
    for name, (c, a) in amps.items():
        print(f"  {name}: center={c:+.1f}, amplitude=±{a:.1f}")

    # 중앙 자세로 부드럽게 이동
    center_pose = {f"{n}.pos": c for n, (c, _) in amps.items()}
    print("\n[중앙 자세로 이동 3초]")
    approach(robot, center_pose, duration=3.0)
    time.sleep(1.0)

    # 웨이브: 각 관절마다 다른 위상으로 사인파 움직임
    phases = {
        "shoulder_pan":  0.0,
        "shoulder_lift": 1.0,
        "elbow_flex":    2.0,
        "wrist_flex":    3.0,
        "wrist_roll":    4.0,
        "gripper":       5.0,
    }
    freq = 0.3  # Hz

    print(f"\n[웨이브 {DURATION}초] Ctrl+C로 중단")
    FADE = 2.0  # 시작/끝 페이드 시간 (초)
    t0 = time.perf_counter()
    dt = 1.0 / FPS
    try:
        while True:
            t = time.perf_counter() - t0
            if t >= DURATION:
                break
            # amplitude envelope: 0 -> 1 -> 0 (fade in/out)
            if t < FADE:
                env = t / FADE
            elif t > DURATION - FADE:
                env = (DURATION - t) / FADE
            else:
                env = 1.0
            action = {}
            for name, (center, amp) in amps.items():
                val = center + env * amp * math.sin(2 * math.pi * freq * t + phases[name])
                action[f"{name}.pos"] = val
            robot.send_action(action)
            time.sleep(dt)
    finally:
        print("\n[쉬는 자세로 복귀]")
        home_pose = {f"{n}.pos": HOME_POS[n] for n in HOME_POS}
        approach(robot, home_pose, duration=3.0)
        time.sleep(0.5)  # 토크 꺼지기 전 안정화
        robot.disconnect()
        print("[완료]")


if __name__ == "__main__":
    main()
