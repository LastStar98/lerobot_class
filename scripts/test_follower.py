#!/usr/bin/env python3
"""SO-101 팔로워암 기본 제어 테스트.

1. 현재 위치 읽기
2. 각 관절을 조금씩 움직여보기 (안전한 범위)
3. 중립 위치로 복귀
"""

import os
import time
from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig

PORT = os.getenv("FOLLOWER_PORT", "/dev/ttyACM0")
ROBOT_ID = os.getenv("FOLLOWER_ID", "my_follower_arm")


def main():
    config = SOFollowerRobotConfig(port=PORT, id=ROBOT_ID, use_degrees=True)
    robot = SOFollower(config)

    print("[연결 중...]")
    robot.connect()
    print("[연결 완료]\n")

    # 1. 현재 위치 읽기
    obs = robot.get_observation()
    current = {k: v for k, v in obs.items() if k.endswith(".pos")}
    print("현재 위치 (degrees):")
    for name, pos in current.items():
        print(f"  {name}: {pos:+.1f}")

    # 2. 안전: 현재 위치로 action 전송 (움직임 없음, 토크만 활성화)
    print("\n[중립 위치 유지 3초]")
    robot.send_action(current)
    time.sleep(3)

    # 3. shoulder_pan만 작게 흔들어보기 (±10도)
    print("\n[shoulder_pan ±10도 흔들기]")
    base_pan = current["shoulder_pan.pos"]
    for delta in [10, -10, 10, -10, 0]:
        target = dict(current)
        target["shoulder_pan.pos"] = base_pan + delta
        print(f"  shoulder_pan -> {base_pan + delta:+.1f}")
        robot.send_action(target)
        time.sleep(1.2)

    # 4. gripper 열고 닫기 (0~100%)
    print("\n[gripper 열고 닫기]")
    for grip in [0, 50, 100, 50, current["gripper.pos"]]:
        target = dict(current)
        target["gripper.pos"] = grip
        print(f"  gripper -> {grip}")
        robot.send_action(target)
        time.sleep(1.0)

    print("\n[종료]")
    robot.disconnect()


if __name__ == "__main__":
    main()
