# SO-101 LeRobot 실습 가이드

이 문서는 SO-101 리더암과 팔로워암을 처음 연결하는 과정을 순서대로 정리한 실습 가이드입니다. WSL2 설치부터 LeRobot 환경 구성, USB 연결, 모터 ID 설정, 캘리브레이션까지 한 번에 확인할 수 있습니다.

## 환경
- OS: Windows 10 Pro (WSL2 Ubuntu 22.04 사용)
- 로봇: SO-101 (팔로워암 + 리더암)
- 참고 문서:
  - https://huggingface.co/docs/lerobot/so101
  - https://huggingface.co/docs/lerobot/index

---

## 설치 순서

### 1단계: WSL2 설치

PowerShell (관리자):
```powershell
wsl --install
```
재부팅 후 Ubuntu 설치를 완료합니다.

---

### 2단계: Miniforge (conda) 설치

WSL Ubuntu 터미널에서:
```bash
cd ~
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
bash Miniforge3-Linux-x86_64.sh
source ~/.bashrc
```

설치 중 선택:
- 라이선스 → `yes`
- 설치 경로 → Enter (기본값)
- conda init → `yes`

> **주의**: `/mnt/c/` 같은 Windows 경로에서 wget을 실행하면 Permission denied가 발생할 수 있습니다. 반드시 `cd ~`로 이동한 뒤 실행하세요.

---

### 3단계: conda 환경 생성

```bash
conda create -y -n lerobot python=3.12
conda activate lerobot
```

---

### 4단계: LeRobot 클론 및 설치

WSL Ubuntu 터미널에서 작업합니다. Windows 경로(`/mnt/c/...`)보다 WSL 홈 디렉터리(`~`) 안에서 clone하는 편이 권한과 속도 문제가 적습니다.

```bash
cd ~
git clone https://github.com/huggingface/lerobot.git
```

설치 순서:
```bash
cd ~/lerobot
conda activate lerobot
conda install evdev -c conda-forge          # WSL 입력 장치 의존성
conda install ffmpeg -c conda-forge
pip install -e ".[core_scripts,feetech]"
```

> **evdev 빌드 실패가 나는 경우**: WSL 커널 헤더 문제로 pip에서 evdev 빌드가 실패할 수 있습니다.
> `conda install evdev -c conda-forge`로 먼저 설치하면 pip 설치 단계에서 evdev 빌드를 건너뜁니다.
> 이 과정을 놓치면 `lerobot-find-port`, `lerobot-setup-motors` 등 CLI 명령이 등록되지 않을 수 있습니다.

---

### 5단계: USB 연결 (usbipd)

#### 5-1: usbipd 설치 (Windows PowerShell 관리자)
```powershell
winget install --interactive --exact dorssel.usbipd-win
```

#### 5-2: 로봇팔 USB 꽂기
- 팔로워암과 리더암 USB를 PC에 연결
- Windows 장치관리자에서 USB 시리얼 장치가 정상 인식되는지 확인
- 드라이버 자동 설치 팝업이 뜨면 완료될 때까지 대기

#### 5-3: WSL로 USB 넘기기

PowerShell에서 실행합니다. `bind`는 관리자 권한이 필요합니다.
```powershell
usbipd list                                  # BUSID 확인
usbipd bind --busid <robot-busid>           # 최초 1회만
usbipd attach --wsl --busid <robot-busid>   # WSL에 연결
```

> **주의**: USB를 뺐다 꽂을 때마다 `usbipd attach` 다시 실행 필요!

#### 5-4: WSL에서 포트 확인
```bash
conda activate lerobot
ls /dev/ttyACM*
sudo chmod 666 /dev/ttyACM*
lerobot-find-port
```

`lerobot-find-port` 실행 시:
1. 포트 목록 표시됨
2. "USB 케이블을 빼고 Enter" → 물리적으로 빼기
3. 어떤 포트가 사라졌는지 비교 → 해당 포트가 로봇팔

팔로워암과 리더암을 각각 확인해서 아래처럼 기록합니다.

| 장치 | BUSID | WSL 포트 | ID |
|------|-------|----------|----|
| 팔로워암 | `<follower-busid>` | `/dev/ttyACM0` | `my_follower_arm` |
| 리더암 | `<leader-busid>` | `/dev/ttyACM1` | `my_leader_arm` |

현재 터미널 세션에서 스크립트가 같은 포트를 쓰도록 환경변수를 설정합니다.

```bash
export FOLLOWER_PORT=/dev/ttyACM0
export LEADER_PORT=/dev/ttyACM1
export FOLLOWER_ID=my_follower_arm
export LEADER_ID=my_leader_arm
```

권한 오류가 나면 즉시 아래 명령으로 권한을 열 수 있습니다. USB를 다시 연결하면 권한이 초기화될 수 있으니 포트가 바뀔 때마다 다시 확인하세요.

```bash
sudo chmod 666 "$FOLLOWER_PORT" "$LEADER_PORT"
```

반복 실습 환경에서는 `dialout` 그룹 등록을 한 번 해두는 것도 좋습니다. 등록 후에는 WSL을 다시 시작해야 적용됩니다.

```bash
sudo usermod -aG dialout "$USER"
```

---

### 6단계: 모터 ID 설정

모터 ID 설정 전 확인:

- 컨트롤러 보드에 USB와 전원이 모두 연결되어 있어야 합니다.
- Waveshare 컨트롤러 보드는 점퍼가 B 채널(USB)에 있어야 합니다.
- 새 모터는 기본 ID가 모두 `1`일 수 있으므로 반드시 한 개씩만 연결합니다.

#### 모터 구조 (팔로워암)
| ID | 이름 | 위치 |
|----|------|------|
| 1 | shoulder_pan | 베이스 회전 (맨 아래) |
| 2 | shoulder_lift | 어깨 위아래 |
| 3 | elbow_flex | 팔꿈치 |
| 4 | wrist_flex | 손목 굽힘 |
| 5 | wrist_roll | 손목 회전 |
| 6 | gripper | 집게 (맨 끝) |

#### 공식 방법 (모터 물리적 분리 필요)
팔로워암:

```bash
lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port="$FOLLOWER_PORT"
```

리더암:

```bash
lerobot-setup-motors \
    --teleop.type=so101_leader \
    --teleop.port="$LEADER_PORT"
```

- 모터를 **한 개씩만** 3핀 케이블로 보드에 연결
- 스크립트가 gripper → wrist_roll → ... → shoulder_pan 순서로 안내
- 새 모터는 전부 ID=1이라 동시 연결 시 충돌

> **참고**: 조립 완료 상태에서는 3핀 케이블이 프레임 관절 사이에 들어 있어 분리가 어려울 수 있습니다.
> 필요하면 브로드캐스트 방식으로 Python 코드를 통해 ID를 변경하는 대체 방법을 사용할 수 있습니다.

---

### 7단계: 캘리브레이션 (모터 ID 설정 후)

팔로워암:
```bash
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port="$FOLLOWER_PORT" \
    --robot.id="$FOLLOWER_ID"
```

리더암:
```bash
lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port="$LEADER_PORT" \
    --teleop.id="$LEADER_ID"
```

> **중요**: 여기에서 사용한 ID와 스크립트 실행 시 사용하는 `FOLLOWER_ID`, `LEADER_ID`가 같아야 같은 캘리브레이션 파일을 읽습니다.

---

### 8단계: 첫 동작 확인

처음에는 팔로워암 단독 연결과 현재 위치 읽기부터 확인합니다.

```bash
python scripts/test_follower.py
```

리더암과 팔로워암을 모두 연결한 뒤에는 안전 제한이 들어간 텔레옵부터 실행합니다.

```bash
python scripts/safe_teleop.py
```

이상이 없을 때만 키보드 제어와 웨이브 데모를 실행합니다.

```bash
python scripts/teleop_keyboard.py
python scripts/demo_wave.py
```

---

## 자주 발생하는 문제

### 문제 1: conda not found
```
Command 'conda' not found
```
- **상황**: WSL Ubuntu에서 `conda activate lerobot` 실행
- **원인**: WSL에 conda 자체가 없음 (Windows Anaconda와 별개)
- **해결**: Miniforge 설치 (2단계)

---

### 문제 2: wget Permission denied
```
Miniforge3-Linux-x86_64.sh: Permission denied
Cannot write to 'Miniforge3-Linux-x86_64.sh' (Success).
```
- **상황**: Windows 마운트 경로(`/mnt/c/...`)에서 wget 실행
- **원인**: Windows 마운트 경로에서 권한 또는 실행 위치 문제 발생
- **해결**: `cd ~` 후 다시 실행

---

### 문제 3: git clone Permission denied
```
fatal: could not create work tree dir 'lerobot': Permission denied
```
- **상황**: WSL 또는 Windows에서 쓰기 권한이 불안정한 위치에 clone 시도
- **원인**: 시스템 보호 경로 또는 작업용으로 적절하지 않은 경로에서 clone 시도
- **해결**: 사용자 계정 기준의 쓰기 가능한 작업 폴더에서 clone

---

### 문제 4: evdev 빌드 실패
```
The 'linux/input.h' and 'linux/input-event-codes.h' include files are missing.
ERROR: Failed building wheel for evdev
```
- **상황**: `pip install -e ".[core_scripts,feetech]"` 실행 시
- **원인**: WSL 커널 헤더 미설치 + WSL 커널은 특수해서 일반 헤더도 안 맞음
- `sudo apt-get install linux-headers-$(uname -r)` 또는 `linux-headers-generic` 설치로 해결되지 않을 수 있습니다.
- `pip install evdev-binary`를 설치해도 pip이 evdev를 다시 빌드하려고 할 수 있습니다.
- 해결: `conda install evdev -c conda-forge` 후 `pip install -e ".[core_scripts,feetech]"`를 다시 실행합니다.

---

### 문제 5: lerobot-find-port / lerobot CLI 명령 not found
```
lerobot-find-port: command not found
```
- **상황**: 포트 확인을 위해 실행
- **원인**: evdev 빌드 실패로 pip install이 중간에 실패 → lerobot CLI 미등록
- **해결**: evdev conda 설치 후 pip install 재실행

---

### 문제 6: No module named 'lerobot'
```
ModuleNotFoundError: No module named 'lerobot'
```
- **상황**: Python에서 lerobot import 시도
- **원인**: 실패 5와 동일. pip install 중간 실패로 editable 모드 미등록
- **해결**: evdev conda 설치 후 pip install 재실행

---

### 문제 7: Motor not found
```
RuntimeError: Motor 'gripper' (model 'sts3215') was not found. Make sure it is connected.
```
- **상황**: `lerobot-setup-motors` 실행 후 Enter
- **원인**: 모터 6개가 전부 ID=1 (공장 기본값)로 데이지체인 연결 → ID 충돌
- **해결 방법 A**: 모터를 한 개씩 물리적으로 분리해서 보드에 직접 연결 후 ID 설정
- **해결 방법 B**: Python 코드로 브로드캐스트 방식 ID 변경
- **참고**: 조립 완료 상태에서는 3핀 케이블이 관절 프레임 사이에 있어 분리하기 어렵습니다.

---

## 주의사항과 팁

- WSL에서 `/mnt/c/` 경로는 Windows 파일시스템 → 권한 문제 빈번, 속도도 느림
- USB 장치는 WSL에서 기본적으로 안 보임 → `usbipd`로 넘겨야 함
- USB를 뺐다 꽂을 때마다 `usbipd attach --wsl --busid <BUSID>` 다시 실행
- `evdev` 설치는 반드시 `conda install evdev -c conda-forge`로 (pip 아님!)
- Waveshare 컨트롤러 보드: 점퍼를 B 채널 (USB)에 설정 확인
- 전원 케이블이 조작 중 빠지기 쉬우니 매 단계 확인
- 전원: 12V 어댑터 사용 (7.4V도 있지만 12V 권장)
- 모터 ID 설정 시 반드시 한 개씩만 연결 (새 모터 기본 ID가 전부 1)
- **조립 전에 모터 ID부터 설정할 것!** (조립 후에는 3핀 분리가 어려움)
- 수업 중 포트가 바뀌면 `FOLLOWER_PORT`, `LEADER_PORT` 환경변수를 다시 설정

---

## 실습 체크리스트

- WSL2 설치
- Miniforge (conda) 설치
- conda 환경 생성 (`lerobot`, Python 3.12)
- LeRobot clone 및 `pip install -e ".[core_scripts,feetech]"`
- `usbipd` 설치 및 USB 포트 WSL 연결
- `lerobot-find-port`로 팔로워/리더 포트 확인
- `FOLLOWER_PORT`, `LEADER_PORT`, `FOLLOWER_ID`, `LEADER_ID` 설정
- 팔로워암/리더암 모터 ID 설정
- 팔로워암/리더암 캘리브레이션
- 팔로워암 코드 제어 테스트
- 안전 텔레옵 테스트
