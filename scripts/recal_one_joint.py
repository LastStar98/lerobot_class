#!/usr/bin/env python3
"""한 관절만 재캘리브레이션 — range_min/range_max만 다시 기록.

homing_offset은 유지. 다른 관절 캘리브레이션도 건드리지 않음.

사용법:
  python recal_one_joint.py wrist_flex
"""

import json
import os
import sys
import time
from pathlib import Path

from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig

PORT = os.getenv("FOLLOWER_PORT", "/dev/ttyACM0")
ROBOT_ID = os.getenv("FOLLOWER_ID", "my_follower_arm")
CAL_PATH = Path.home() / f".cache/huggingface/lerobot/calibration/robots/so_follower/{ROBOT_ID}.json"


def main():
    if len(sys.argv) < 2:
        print("사용법: python recal_one_joint.py <관절이름>")
        print("  예: python recal_one_joint.py wrist_flex")
        return 1

    target = sys.argv[1]

    # 백업
    backup = CAL_PATH.with_suffix(".json.bak")
    backup.write_text(CAL_PATH.read_text())
    print(f"[백업] {backup}")

    config = SOFollowerRobotConfig(port=PORT, id=ROBOT_ID, use_degrees=True)
    robot = SOFollower(config)
    # 기존 캘리브레이션 유지하고 연결 (calibrate=False로 재캘 안함)
    robot.bus.connect()

    if target not in robot.bus.motors:
        print(f"모터 '{target}' 없음. 선택 가능: {list(robot.bus.motors)}")
        robot.bus.disconnect(disable_torque=False)
        return 1

    print(f"\n=== {target} 관절 범위 재기록 ===")
    print(f"{target} 관절을 손으로 끝에서 끝까지 천천히 움직이세요.")
    print("MIN/MAX 값이 업데이트됩니다. 다 움직였으면 Enter.\n")

    # record_ranges_of_motion을 특정 모터만 호출
    robot.bus.disable_torque()
    range_mins, range_maxes = robot.bus.record_ranges_of_motion([target])
    new_min = int(range_mins[target])
    new_max = int(range_maxes[target])

    # JSON 로드 후 해당 관절만 수정
    cal = json.loads(CAL_PATH.read_text())
    old_min = cal[target]["range_min"]
    old_max = cal[target]["range_max"]
    cal[target]["range_min"] = new_min
    cal[target]["range_max"] = new_max

    print(f"\n{target} 범위 변경:")
    print(f"  range_min: {old_min} -> {new_min}")
    print(f"  range_max: {old_max} -> {new_max}  (span: {new_max - new_min})")

    CAL_PATH.write_text(json.dumps(cal, indent=4))
    print(f"\n[저장] {CAL_PATH}")

    # 모터에도 새 범위 쓰기 (다른 관절은 기존 값으로)
    from lerobot.motors import MotorCalibration
    full_cal = {
        name: MotorCalibration(
            id=d["id"],
            drive_mode=d["drive_mode"],
            homing_offset=d["homing_offset"],
            range_min=d["range_min"],
            range_max=d["range_max"],
        )
        for name, d in cal.items()
    }
    robot.bus.write_calibration(full_cal)
    print("[모터에 새 범위 쓰기 완료]")

    robot.bus.disconnect(disable_torque=True)
    print("\n완료. teleop_keyboard.py 재실행해서 확인해봐.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
