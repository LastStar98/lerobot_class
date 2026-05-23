#!/usr/bin/env python3
"""리더와 팔로워 좌표 정렬.

사용법:
1. 두 팔을 손으로 **같은 물리적 자세**로 맞춤
   (예: 둘 다 홈 자세 — 팔꿈치 접고 자연스럽게 놓은 모습)
2. 이 스크립트 실행
3. 리더의 각 관절 homing_offset이 자동 조정됨

결과: 두 팔 동일 자세 → 동일 degrees → 텔레옵 시 좌표 일치
"""

import json
import os
from pathlib import Path

from lerobot.teleoperators.so_leader import SOLeader
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig
from lerobot.motors import MotorCalibration

LEADER_PORT = os.getenv("LEADER_PORT", "/dev/ttyACM1")
LEADER_ID = os.getenv("LEADER_ID", "my_leader_arm")
FOLLOWER_PORT = os.getenv("FOLLOWER_PORT", "/dev/ttyACM0")
FOLLOWER_ID = os.getenv("FOLLOWER_ID", "my_follower_arm")


def main():
    print("=" * 60)
    print("리더 ↔ 팔로워 좌표 정렬")
    print("=" * 60)
    print("\n두 팔을 손으로 같은 자세로 잡으세요 (예: 둘 다 홈 자세).")
    print("정확히 같은 각도일수록 결과가 정확합니다.")
    input("\n준비되면 Enter... ")

    leader = SOLeader(SOLeaderTeleopConfig(port=LEADER_PORT, id=LEADER_ID))
    leader.bus.connect()
    follower = SOFollower(SOFollowerRobotConfig(port=FOLLOWER_PORT, id=FOLLOWER_ID, use_degrees=True))
    follower.bus.connect()

    # 현재 위치 읽기 (raw, 이미 homing_offset 적용됨)
    l_pos = {n: leader.bus.read("Present_Position", n, normalize=False) for n in leader.bus.motors}
    f_pos = {n: follower.bus.read("Present_Position", n, normalize=False) for n in follower.bus.motors}

    # 리더 캘리브 로드
    lp = Path.home() / f".cache/huggingface/lerobot/calibration/teleoperators/so_leader/{LEADER_ID}.json"
    # 백업
    (lp.parent / f"{LEADER_ID}.json.pre_align.bak").write_text(lp.read_text())
    lc = json.loads(lp.read_text())

    print("\n[정렬 결과]")
    print(f"{'관절':<15} {'리더':>7} {'팔로워':>7} {'delta':>7} {'old_ho':>7} {'new_ho':>7}")
    for name in l_pos:
        delta = l_pos[name] - f_pos[name]
        old_ho = lc[name]["homing_offset"]
        new_ho = old_ho + delta
        # Homing_Offset 범위는 ±2047 (sign-magnitude 12bit)
        if abs(new_ho) > 2047:
            print(f"{name:<15} {l_pos[name]:>7} {f_pos[name]:>7} {delta:>+7} "
                  f"{old_ho:>7} {new_ho:>7}  [!] 범위 초과, 유지")
            continue
        lc[name]["homing_offset"] = new_ho
        print(f"{name:<15} {l_pos[name]:>7} {f_pos[name]:>7} {delta:>+7} {old_ho:>7} {new_ho:>7}")

    # 저장 + 모터 동기화
    lp.write_text(json.dumps(lc, indent=4))
    cal = {n: MotorCalibration(**d) for n, d in lc.items()}
    leader.bus.write_calibration(cal)

    # 검증
    print("\n[검증 — 동일 자세에서 degrees 비교]")
    print(f"{'관절':<15} {'leader_deg':>10} {'follower_deg':>12} {'diff':>7}")
    for name in l_pos:
        ldeg = leader.bus.read("Present_Position", name, normalize=True)
        fdeg = follower.bus.read("Present_Position", name, normalize=True)
        print(f"{name:<15} {ldeg:>10.1f} {fdeg:>12.1f} {ldeg-fdeg:>+7.1f}")

    leader.bus.disconnect(disable_torque=False)
    follower.bus.disconnect(disable_torque=False)
    print("\n완료. 이제 python safe_teleop.py 실행해봐.")


if __name__ == "__main__":
    main()
