# SO-101 LeRobot 실습 자료

SO-101 리더암과 팔로워암을 WSL2 환경에서 연결하고, 캘리브레이션과 기본 제어를 실습하기 위한 자료입니다. 처음 설정하는 경우에도 순서대로 따라 할 수 있도록 설치 흐름, 실행 스크립트, 자주 발생하는 문제를 함께 정리했습니다.

> LeRobot 본체 소스코드는 이 저장소에 포함되어 있지 않습니다. 먼저 LeRobot를 설치한 뒤, `lerobot` 패키지가 import되는 conda 환경에서 이 저장소의 스크립트를 실행하세요.

## 먼저 확인할 것

- Windows 10 이상과 WSL2 Ubuntu 22.04 환경을 사용합니다.
- conda 환경 이름은 예시 기준 `lerobot`입니다.
- USB 장치가 WSL에 연결되어 있어야 합니다.
- 포트는 `lerobot-find-port`로 직접 확인한 뒤 사용합니다.
- 스크립트의 기본값은 팔로워암 `/dev/ttyACM0`, 리더암 `/dev/ttyACM1`입니다.
- 로봇암은 갑자기 움직일 수 있으니 전원, 케이블, 주변 공간을 먼저 확인하세요.

## 실습 순서

1. [설치 가이드](./lerobot_class.md)를 따라 WSL2, conda, LeRobot를 준비합니다.
2. `usbipd`로 로봇암 USB 장치를 WSL에 연결합니다.
3. `lerobot-find-port`로 팔로워암과 리더암 포트를 각각 확인합니다.
4. 팔로워암과 리더암의 모터 ID 설정, 캘리브레이션을 진행합니다.
5. `scripts/test_follower.py`로 팔로워암 연결을 확인합니다.
6. `scripts/safe_teleop.py`로 리더-팔로워 동작을 먼저 확인합니다.
7. 이상이 없을 때 키보드 제어와 데모 스크립트를 실행합니다.

## 빠른 실행

PowerShell을 관리자 권한으로 열고 USB 장치를 WSL에 공유합니다. `bind`는 장치별 최초 1회만 필요하고, `attach`는 USB를 다시 꽂을 때마다 다시 실행합니다.

```powershell
usbipd list
usbipd bind --busid <follower-busid>
usbipd bind --busid <leader-busid>
usbipd attach --wsl --busid <follower-busid>
usbipd attach --wsl --busid <leader-busid>
```

WSL 터미널에서 포트를 확인하고, 확인한 값을 환경변수로 기록합니다.

```bash
conda activate lerobot
ls /dev/ttyACM*
sudo chmod 666 /dev/ttyACM*
lerobot-find-port
export FOLLOWER_PORT=/dev/ttyACM0
export LEADER_PORT=/dev/ttyACM1
export FOLLOWER_ID=my_follower_arm
export LEADER_ID=my_leader_arm
sudo chmod 666 "$FOLLOWER_PORT" "$LEADER_PORT"
cd <repository-dir>
```

처음 동작은 아래 순서로 확인합니다.

```bash
python scripts/test_follower.py
python scripts/safe_teleop.py
python scripts/teleop_keyboard.py
python scripts/demo_wave.py
```

## 파일 구성

```text
so101-class/
├── README.md
├── calibration/
│   ├── my_follower_arm.json
│   └── my_leader_arm.json
├── lerobot_class.md
└── scripts/
    ├── align_leader.py
    ├── demo_wave.py
    ├── recal_one_joint.py
    ├── safe_teleop.py
    ├── teleop_keyboard.py
    └── test_follower.py
```

## 스크립트

- `scripts/test_follower.py`: 팔로워암 연결과 기본 제어 확인
- `scripts/teleop_keyboard.py`: 키보드로 각 관절을 수동 제어
- `scripts/demo_wave.py`: 팔로워암 자동 웨이브 동작 테스트
- `scripts/safe_teleop.py`: 급격한 움직임을 줄인 리더-팔로워 텔레옵
- `scripts/align_leader.py`: 리더암과 팔로워암 좌표 정렬 보정
- `scripts/recal_one_joint.py`: 특정 관절의 range 값만 다시 기록

## 캘리브레이션 파일

`calibration/` 폴더의 JSON 파일은 캘리브레이션 형식을 확인하거나 백업할 때 참고할 수 있는 스냅샷입니다.

- 다른 SO-101 장비에 그대로 적용하지 마세요.
- 실습에 사용하는 장비는 각자 다시 캘리브레이션하는 것을 권장합니다.
- 기존 파일을 덮어쓰기 전에 원본을 백업해 두세요.
- LeRobot가 실제로 사용하는 캘리브레이션은 `~/.cache/huggingface/lerobot/calibration/` 아래에 저장됩니다.

## 안전 메모

- 처음 동작을 확인할 때는 `scripts/safe_teleop.py`를 우선 사용하세요.
- `lerobot-teleoperate` CLI는 장비 상태에 따라 급격한 움직임이 발생할 수 있어 이 자료에서는 권장하지 않습니다.
- 전원 기준:
  - 팔로워암: 12V
  - 리더암: 5V 또는 7.4V

## 상세 문서

- [SO-101 LeRobot 실습 가이드](./lerobot_class.md): 설치, USB 연결, 모터 ID 설정, 캘리브레이션, 문제 해결
