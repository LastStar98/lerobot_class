#!/usr/bin/env python3
"""안전한 리더-팔로워 텔레옵.

시작할 때 팔로워가 리더 위치로 급발진하지 않도록:
1. 시작 시 리더/팔로워 현재 위치 확인
2. 큰 차이가 있으면 사용자 확인
3. 팔로워를 리더 위치로 '천천히' 이동 (수 초에 걸쳐)
4. 그 다음 1:1 실시간 추종 시작
5. Ctrl+C로 언제든 중단 (토크 해제)
"""

import time
import os
import signal
import sys

from lerobot.teleoperators.so_leader import SOLeader
from lerobot.teleoperators.so_leader.config_so_leader import SOLeaderTeleopConfig
from lerobot.robots.so_follower import SOFollower, SOFollowerRobotConfig

LEADER_PORT = os.getenv("LEADER_PORT", "/dev/ttyACM1")
LEADER_ID = os.getenv("LEADER_ID", "my_leader_arm")
FOLLOWER_PORT = os.getenv("FOLLOWER_PORT", "/dev/ttyACM0")
FOLLOWER_ID = os.getenv("FOLLOWER_ID", "my_follower_arm")

APPROACH_SECS = 5.0   # 초기 접근 시간 (길수록 안전)
APPROACH_HZ = 50      # 접근 중 제어 주기
TRACK_HZ = 50         # 추종 중 제어 주기
MAX_STEP_DEG = 3.0    # 한 틱에 팔로워가 움직일 수 있는 최대 각도 (안전 속도 제한)
BIG_DIFF_THRESHOLD = 20.0  # 시작 시 경고할 관절 차이 (degrees)


def get_pos(robot):
    obs = robot.get_observation()
    return {k: v for k, v in obs.items() if k.endswith(".pos")}


def clamp_delta(current, target, max_step):
    """팔로워 급발진 방지: 한 틱당 최대 변화량 제한."""
    out = {}
    for k, t in target.items():
        c = current[k]
        diff = t - c
        if abs(diff) > max_step:
            out[k] = c + max_step * (1 if diff > 0 else -1)
        else:
            out[k] = t
    return out


def main():
    print("[연결 중...]")
    leader = SOLeader(SOLeaderTeleopConfig(port=LEADER_PORT, id=LEADER_ID))
    follower = SOFollower(SOFollowerRobotConfig(port=FOLLOWER_PORT, id=FOLLOWER_ID, use_degrees=True))
    leader.bus.connect()
    follower.connect()
    print("[연결 완료]")

    # Ctrl+C 시 안전 종료
    stopped = {"flag": False}
    def stop_handler(*_):
        stopped["flag"] = True
    signal.signal(signal.SIGINT, stop_handler)

    try:
        # 시작 시 위치 비교
        def get_leader_degrees():
            return {f"{n}.pos": leader.bus.read("Present_Position", n, normalize=True)
                    for n in leader.bus.motors}

        leader_pos = get_leader_degrees()
        follower_pos = get_pos(follower)

        print("\n[초기 위치 비교]")
        big_diffs = []
        for k in leader_pos:
            l, f = leader_pos[k], follower_pos[k]
            diff = abs(l - f)
            mark = "  <-- BIG!" if diff > BIG_DIFF_THRESHOLD else ""
            print(f"  {k}: leader={l:+7.1f}, follower={f:+7.1f}, diff={diff:5.1f}{mark}")
            if diff > BIG_DIFF_THRESHOLD:
                big_diffs.append(k)

        if big_diffs:
            print(f"\n[주의] 큰 차이 있는 관절: {big_diffs}")
            print(f"팔로워가 {APPROACH_SECS}초간 천천히 리더 위치로 이동합니다.")
            print("계속하려면 Enter, 중단은 Ctrl+C")
            input()
        else:
            print("\n차이 작음. 2초 후 텔레옵 시작.")
            time.sleep(2)

        # 단계 1: 팔로워를 리더 위치로 천천히 접근
        print(f"\n[접근 단계 {APPROACH_SECS}초]")
        steps = int(APPROACH_SECS * APPROACH_HZ)
        start = dict(follower_pos)
        for i in range(1, steps + 1):
            if stopped["flag"]:
                break
            leader_now = get_leader_degrees()
            alpha = i / steps
            intermediate = {k: start[k] + (leader_now[k] - start[k]) * alpha
                            for k in start}
            follower.send_action(intermediate)
            time.sleep(1.0 / APPROACH_HZ)

        if stopped["flag"]:
            raise KeyboardInterrupt

        # 단계 2: 실시간 추종. 매 틱마다 최대 변화량을 제한해 급격한 목표 이동을 막는다.
        print("\n[실시간 추종 시작 — Ctrl+C로 중단]")
        dt = 1.0 / TRACK_HZ
        while not stopped["flag"]:
            t0 = time.perf_counter()
            leader_now = get_leader_degrees()
            follower_now = get_pos(follower)
            safe_goal = clamp_delta(follower_now, leader_now, MAX_STEP_DEG)
            follower.send_action(safe_goal)
            elapsed = time.perf_counter() - t0
            if elapsed < dt:
                time.sleep(dt - elapsed)

    except KeyboardInterrupt:
        pass
    finally:
        print("\n[종료 중 — 토크 해제]")
        leader.bus.disconnect(disable_torque=False)
        follower.disconnect()
        print("[완료]")


if __name__ == "__main__":
    main()
