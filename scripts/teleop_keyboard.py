#!/usr/bin/env python3
"""SO-101 키보드 텔레옵.

키:
  1~6 : 관절 선택
        1=shoulder_pan, 2=shoulder_lift, 3=elbow_flex,
        4=wrist_flex, 5=wrist_roll, 6=gripper
  j   : 선택된 관절 -방향 (닫기/감소)
  k   : 선택된 관절 +방향 (열기/증가)
  r   : 현재 위치 표시
  h   : 홈 자세(0도) 복귀
  q   : 종료
"""

import os
import sys
import termios
import time
import tty
from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig

PORT = os.getenv("FOLLOWER_PORT", "/dev/ttyACM0")
ROBOT_ID = os.getenv("FOLLOWER_ID", "my_follower_arm")

STEP_DEG = 3.0       # 관절 이동량 (도)
STEP_GRIP = 5.0      # gripper 이동량 (0~100 범위)
RANGE_SHRINK = 0.10  # 가동범위 축소 비율 (10% = 양 끝에서 5%씩 줄임)

JOINTS = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

HOME_POS = {
    "shoulder_pan": 0.3,
    "shoulder_lift": -36.0,
    "elbow_flex": 36.2,
    "wrist_flex": -41.7,
    "wrist_roll": -0.1,
    "gripper": 2.7,
}

# 캘리브레이션 값을 직접 덮어쓰는 수동 한계 (degrees, gripper는 0~100)
# None이면 캘리브레이션 기반 값 사용. 값을 주면 그 값이 그대로 한계가 됨.
MANUAL_LIMITS = {
    "wrist_flex": (0.0, 182.0),  # 하한 0도, 상한 182도
}


def getch():
    """키보드 한 글자 읽기 (Enter 없이)."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def print_status(selected, target):
    joint_name = JOINTS[selected]
    val = target[f"{joint_name}.pos"]
    print(f"\r[{selected+1}:{joint_name:14s}] = {val:+7.2f}   "
          f"(j=- / k=+ / 1-6=관절 선택 / h=홈 / r=현재위치 / q=종료)",
          end="", flush=True)


def compute_limits(robot):
    """캘리브레이션 값으로부터 각 관절의 degrees/정규화 범위 계산.
    양 끝에서 RANGE_SHRINK/2 만큼씩 줄임 (전체 범위의 RANGE_SHRINK 비율 축소)."""
    MAX_RES = 4095
    half_shrink = RANGE_SHRINK / 2
    limits = {}
    for name, cal in robot.bus.calibration.items():
        mid = (cal.range_min + cal.range_max) / 2
        if name == "gripper":
            lo_raw, hi_raw = 0.0, 100.0
        else:
            lo_raw = (cal.range_min - mid) * 360 / MAX_RES
            hi_raw = (cal.range_max - mid) * 360 / MAX_RES
        span = hi_raw - lo_raw
        lo = lo_raw + span * half_shrink
        hi = hi_raw - span * half_shrink
        # 수동 오버라이드 — 값을 그대로 한계로 사용 (확장/축소 모두 가능)
        if name in MANUAL_LIMITS:
            m_lo, m_hi = MANUAL_LIMITS[name]
            if m_lo is not None:
                lo = m_lo
            if m_hi is not None:
                hi = m_hi
        limits[name] = (lo, hi)
    return limits


def main():
    config = SOFollowerRobotConfig(port=PORT, id=ROBOT_ID, use_degrees=True)
    robot = SOFollower(config)

    print("[연결 중...]")
    robot.connect()
    print("[연결 완료]\n")

    limits = compute_limits(robot)
    print("관절 가동범위:")
    for name in JOINTS:
        lo, hi = limits[name]
        unit = "" if name == "gripper" else "deg"
        print(f"  {name}: {lo:+.1f} ~ {hi:+.1f} {unit}")
    print()

    # 현재 위치를 목표값으로 시작
    obs = robot.get_observation()
    target = {k: v for k, v in obs.items() if k.endswith(".pos")}

    print("현재 위치:")
    for name in JOINTS:
        print(f"  {name}: {target[name + '.pos']:+.1f}")
    print()
    print("=== 키보드 텔레옵 시작 ===")
    print("1~6: 관절 선택 | j/k: -/+ | h: 홈 | r: 현재위치 | q: 종료")
    print()

    selected = 0  # 현재 선택된 관절 인덱스
    print_status(selected, target)

    try:
        while True:
            ch = getch()

            if ch == "q" or ch == "\x03":  # q 또는 Ctrl+C
                print("\n[종료]")
                break

            elif ch in "123456":
                selected = int(ch) - 1
                print_status(selected, target)

            elif ch in ("j", "k"):
                joint_name = JOINTS[selected]
                key = f"{joint_name}.pos"
                step = STEP_GRIP if joint_name == "gripper" else STEP_DEG
                delta = -step if ch == "j" else step
                lo, hi = limits[joint_name]
                new_val = max(lo, min(hi, target[key] + delta))
                # 한계에 닿았는지 표시
                clamped = (target[key] + delta) != new_val
                target[key] = new_val
                robot.send_action(target)
                if clamped:
                    print(f"\n[한계 도달: {joint_name} {lo:+.1f}~{hi:+.1f}]")
                print_status(selected, target)

            elif ch == "h":
                # 사용자 정의 홈 자세로 천천히 이동 (선형 보간)
                print("\n[홈 자세로 천천히 이동 중...]")
                start = dict(target)
                goal = {}
                for name in JOINTS:
                    lo, hi = limits[name]
                    goal[f"{name}.pos"] = max(lo, min(hi, HOME_POS[name]))

                HOME_DURATION = 1.0  # 초 (기본 ~1초의 3배)
                HOME_STEPS = 100
                dt = HOME_DURATION / HOME_STEPS
                for i in range(1, HOME_STEPS + 1):
                    alpha = i / HOME_STEPS
                    for name in JOINTS:
                        key = f"{name}.pos"
                        target[key] = start[key] + (goal[key] - start[key]) * alpha
                    robot.send_action(target)
                    time.sleep(dt)
                print_status(selected, target)

            elif ch == "r":
                obs = robot.get_observation()
                print("\n현재 실제 위치:")
                for name in JOINTS:
                    pos = obs[f"{name}.pos"]
                    print(f"  {name}: {pos:+.1f}")
                print_status(selected, target)

    finally:
        print("\n[연결 해제 중...]")
        robot.disconnect()
        print("[완료]")


if __name__ == "__main__":
    main()
