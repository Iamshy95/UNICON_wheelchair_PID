# UNICON Wheelchair — FF–PD + Safety 터미널 운용 매뉴얼

ROS1 Noetic 기반 전동휠체어의 **READY(센서·정합 준비) → DRIVE(자율주행) → DRIVE STOP(주행 종료) → READY STOP(전체 종료)** 운용 가이드입니다.
이 README의 실행 명령은 **NUC 터미널 기준**입니다. 현장에서는 노트북에서 NUC에 SSH로 접속한 뒤 동일하게 실행할 수 있습니다. Android 앱·Bluetooth 세부 사용법은 앱 저장소에서 별도로 관리합니다.

> **중요 — NUC 배포:** 개인 저장소의 `scripts/`는 팀 저장소 `src/pid/scripts/`로 동기화된 뒤 NUC에 전체 배포됩니다. 개인 GitHub `main`의 변경만으로 NUC 실행 코드가 갱신되지는 않습니다. 아래 명령은 **2026-11-09 실제 배포 확인된 고정 링크** `~/wheelchair_deploys/ffpid`를 사용합니다. 링크 대상의 변경은 READY·DRIVE 종료 및 새 배포본 검증 후에만 수행하세요.

## 0. 가장 먼저 보는 명령어 (Quick Start)

**2026-11-09 NUC 배포 확인값**

| 항목 | 실제 설정 |
|---|---|
| 주행 코드 원본 | 팀 `Dannythechampion/UNICON_wheelchair_v2`의 `feature/ffpid`, 커밋 `78cbef8` |
| 고정 운용 경로 | `/home/mprp3/wheelchair_deploys/ffpid` (심볼릭 링크) |
| 현재 링크 대상 | `/home/mprp3/wheelchair_deploys/ffpid-78cbef8-20261109` |
| 주행 스크립트 | `~/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/` |
| 6개 경로 JSON | `~/wheelchair_deploys/ffpid/source-linux/routes/route2_manual_20261031/` |
| ROS 작업 공간 | `~/wheelchair_deploys/ffpid/ws/` |
| 별도 Bluetooth 브릿지 | `~/ffpid_bt_bridge/start.sh` · `unicon-ffpid-bt.service` |
| 배포 검증 | ROS 빌드 성공, 테스트 **803 통과·4 실패·1 스킵** → `MANUAL_TEST_EXCEPTION` 수동 예외 기록. 자동 테스트 전체 통과 아님 |

이하의 모든 실행 명령은 **고정 경로 `ffpid`**를 사용합니다. 다음 버전을 배포해도 각 명령의 날짜/커밋/경로를 고칠 필요는 없습니다. 단, 링크 대상은 운영자가 검증 후 수동 전환해야 합니다.

**노트북에서 NUC로 접속**

```bash
# 노트북 터미널에서 실행: NUC와 네트워크 접속이 가능한 상태여야 함
ssh mprp3@<NUC_IP>

# NUC 호스트명 'mprp3'가 실제로 해석되는 환경이라면
# ssh mprp3@mprp3
```

SSH 로그인 후에는 아래 READY·DRIVE 명령을 **NUC 셸 안에서** 실행하세요. 노트북의 `~/ws/wheelchair_ws` 경로를 사용하지 않습니다. 주행 중에는 SSH/DRIVE 세션을 유지하고, 실제 정지는 별도 터미널의 STOP과 물리적 정지 수단으로 관리하세요. SSH 연결은 비상정지 장치가 아닙니다.

**현재 NUC의 고정 경로와 브릿지 상태 확인(조회 전용)**

```bash
readlink -f "$HOME/wheelchair_deploys/ffpid"
git -C "$HOME/wheelchair_deploys/ffpid/source-linux" log -1 --oneline
systemctl is-enabled unicon-ffpid-bt.service
systemctl is-active unicon-ffpid-bt.service
```

**기본 운용 순서**

```bash
# ① READY: 센서·GICP 정합·인지·구동부 준비
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" start

# ② DRIVE: 선택 경로 주행 (READY 이후)
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_drive.sh" A_to_D5

# ③ DRIVE STOP: 별도 터미널에서 실행 (READY는 계속 유지)
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_stop.sh"

# ④ READY STOP: 주행 종료 후 전체 센서·정합·녹화 종료
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" stop
```

**상태 모니터링 — 필요한 터미널에서 각각 실행**

```bash
# ⑤ READY: 최초 상태와 장애·복구·모드 변화만 출력
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" watch

# ⑥ Safety: CLEAR / SLOW / STOP 또는 reason이 바뀔 때만 출력
source /opt/ros/noetic/setup.bash
python3 -u "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_safety_watch.py"
```

- `READY watch`는 상태 확인용입니다. READY를 **새로 실행하지 않습니다**.
- Safety 모니터는 `pid_drive.sh`가 Safety 노드를 시작한 뒤 상태를 수신합니다. 주행하지 않을 때는 `NO_STATUS`가 정상일 수 있습니다.
- 각 모니터의 `Ctrl+C`는 **화면 표시만 종료**합니다. 자율주행을 종료하는 명령은 `pid_stop.sh`입니다.
- `pid_drive.sh`는 시작에 성공한 뒤 **주행 상태를 계속 감시하므로 종료되지 않습니다**. DRIVE STOP은 다른 터미널에서 실행하세요.
- `pid_ready.sh start`는 준비 후 반환하며 READY 노드들은 계속 실행됩니다.

**상태를 한 번만 확인할 때**

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" status
source /opt/ros/noetic/setup.bash
rostopic echo -n1 /pid_safety/status
```

위 Safety 1회 조회는 선택 사항입니다. **지속적인 이벤트 모니터링은 `pid_safety_watch.py`**를 사용합니다.

### 운용 전 확인

- 최초 READY 정합은 A 지점 기준으로 구성되어 있습니다. 실제 지도와 휠체어의 위치·방향이 올바른지는 현장에서 별도로 확인해야 합니다.
- 출발 전에는 **MANUAL 및 정차 상태**여야 합니다. 선택 경로와의 거리 **1.0m 이하**, 경로 진행 방향과의 오차 **30° 이하**를 확인합니다. 시작점이 아니라 **선택 경로 전체 중 가장 가까운 지점**을 기준으로 하므로 경로 중간에서도 재출발할 수 있습니다.
- 출발 거부 시 회전 안내를 먼저, 경로 접근 안내를 다음에 출력합니다. 실제 이동은 운용자가 MANUAL로 수행하고, 위치 조정 후 DRIVE를 다시 실행합니다. 수치 1.0m·30°는 실차 안전성이 검증된 허용값이 아닙니다.
- 물리적 조이스틱·긴급 정지 수단을 확보해야 합니다. `pid_stop.sh`는 안전 인증된 비상정지 장치가 아닙니다.
- **`--test-clear`는 실제 Safety 판단을 우회합니다. 탑승 주행에서 사용하지 마세요.**

---

## 1. 시스템과 실행 흐름

```text
[READY] pid_ready.sh start
    ├─ ROS Master
    ├─ Livox MID-360 LiDAR / IMU
    ├─ FAST-LIO → GICP 지도 정합 (TRACKING)
    ├─ 기하학 기반 장애물 인식·객체 융합
    ├─ 동적 객체 GICP 제외 처리
    ├─ Wheel / UART / 정지 Watchdog
    └─ ROS bag 녹화 (가능한 경우)
            │
            ▼
[DRIVE] pid_drive.sh <route>
    ├─ READY 상태·MANUAL 정차·중복 /cmd_vel 확인
    ├─ 경로 거리 ≤ 1.0m / 방향 오차 ≤ 30° 검사
    ├─ ff_pid_node.py + pid_safety.py 시작
    ├─ Safety 최신 CLEAR/SLOW 정책 확인
    ├─ MANUAL → AUTO → /ff_pid/start 서비스
    └─ 주행 상태 감시 (스크립트 유지)
            │
            ▼
[DRIVE STOP] pid_stop.sh
    ├─ FF–PD 정지 요청 / MANUAL 전환
    ├─ wheel_status의 정차·MANUAL 응답 확인
    └─ FF–PD·Safety 노드 종료
            │
            └── READY 센서·GICP·ROS bag 유지
            │
            ▼
[READY STOP] pid_ready.sh stop
    ├─ 필요한 경우 주행 정지 요청
    ├─ ROS bag 정상 종료 시도
    └─ READY가 시작한 ROS 프로세스 정리
```

### READY의 역할

`pid_ready.sh start`는 전체 ROS 환경을 준비하고 GICP의 초기 정합을 검사합니다.
초기 정합에 사용되는 Route2 기준 경로는 A에서 시작하는 `A_to_D5`이며, **이후 DRIVE에서 어떤 경로를 선택할지는 별개**입니다.
READY 성공은 자율주행 명령을 의미하지 않고, 지도상 절대위치가 실제와 정확히 일치한다는 보장도 아닙니다.

`pid_ready.sh status`는 한 번의 상태 조회, `pid_ready.sh watch`는 **약 2초마다 내부 상태를 확인하되 실제 장애·회복·모드 변화가 있을 때만 출력**합니다.
LiDAR, IMU, GICP, Perception, UART, Watchdog, rosbag 등과 장애물 인식·소멸을 확인할 수 있습니다. 장애물 인식 이벤트와 Safety의 감속·정지 판단은 서로 다른 정보입니다.

### DRIVE의 역할

`pid_drive.sh`는 한 경로를 선택해 사전 조건을 확인한 후 FF–PD와 Safety를 기동합니다.
Safety 노드와 FF–PD의 제어 정책이 정상적으로 준비된 뒤에만 AUTO 전환 및 START 서비스 요청을 진행합니다.
성공 시 DRIVE 스크립트는 종료되지 않고 주행 상태 전환과 약 **30초마다 진행률**을 표시합니다.

### DRIVE STOP과 READY STOP의 차이

`pid_stop.sh`는 FF–PD와 Safety만 정리하고 **READY 센서, GICP, ROS bag을 유지**합니다. 이 상태에서 다른 경로로 다시 DRIVE를 시작할 수 있습니다.
`pid_ready.sh stop`은 그 READY 세션의 프로세스와 녹화를 종료하므로 **실험 전체를 마칠 때** 사용합니다.
MANUAL 명령이 전달되었다는 사실과 실제 물리적 정차 확인은 다릅니다. 정차 검증 실패 경고가 발생하면 물리 상태를 확인해야 합니다.

## 2. 경로 선택 및 출발 조건

### 지원 경로: A / D4 / D5 간 6개

```text
A_to_D4    A_to_D5
D4_to_A    D4_to_D5
D5_to_A    D5_to_D4
```

```bash
# 경로 이름 직접 지정
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_drive.sh" D4_to_D5

# 인자 없이 실행하면 터미널에서 경로 번호 1~6 선택
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_drive.sh"
```

터미널 인자 없이 경로를 선택하려면 대화형 터미널이 필요합니다.

### 출발 실패 시 위치 조정 안내

`pid_drive_check.py`의 `pose-on-route` 검사에는 다음이 적용됩니다.

| 항목 | 조건 | 기준 |
|---|---|---|
| GICP Pose | `map` 프레임, 최근 데이터 | 유효 데이터 필요 |
| 비교 위치 | 센서 기준점을 휠체어 중심으로 보정 | 경로의 `chair_centre`와 일치 |
| 경로 거리 | **1.0m 이하** | 선택 경로 전체에서 가장 가까운 지점 |
| 방향 오차 | **30° 이하** | 가장 가까운 경로 접선의 진행 방향 |
| 구동 모드 | MANUAL + 정차 확인 | 출발 전 필수 |

출발 조건을 만족하지 못하면 제어 노드를 실행하지 않고 MANUAL 상태를 유지합니다.
예를 들어 방향이 왼쪽으로 45° 어긋나고 경로에서 1.4m 떨어져 있다면 다음 순서로 안내합니다.

```text
[GUIDE 1/2] 먼저 MANUAL로 왼쪽 약 45.0도 회전해 경로 진행 방향을 맞추세요.
[GUIDE 2/2] 다음으로 MANUAL로 경로 쪽에 접근하세요.
             경로까지 1.40m, 허용 범위까지 최소 0.40m 더 가까워져야 합니다.
```

**45°와 0.40m는 예시값**이며 매번 최신 위치로 재계산합니다. 경로 좌우 정보는 **경로 진행 방향 기준**이고, 회전 방향은 **현재 휠체어 방향 기준**입니다. 0.40m는 경로까지 줄여야 할 최소 직선거리이지 휠체어의 실제 이동거리를 의미하지 않습니다.

출발 검사 결과는 향후 Bluetooth 브릿지에서도 읽을 수 있도록 `drive_preflight` JSON으로 출력하며, START 서비스 승인 후에는 `drive_event: STARTED`를 출력합니다. 성공 이벤트는 서비스 승인 의미이지 실제 이동이 측정되었다는 뜻이 아닙니다.

직접 위치만 조회할 때는 다음 명령을 사용합니다(주행하지 않음).

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_drive.sh" position
```

## 3. 이벤트 기반 모니터링

### READY 이벤트

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" watch
```

정상 상태에서는 반복 메시지가 없고, 장치 이상·복구, GICP TRACKING 변화, MANUAL/AUTO 전환, ROS bag 중단·재개, 객체 인식·소멸 등에 대해 이벤트를 출력합니다. `Ctrl+C`로 종료해도 READY는 계속 실행됩니다.

### Safety 이벤트 — 주행 중 권장

```bash
source /opt/ros/noetic/setup.bash
python3 -u "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_safety_watch.py"
```

`pid_safety.py`가 발행하는 `/pid_safety/status`를 구독하지만, 10Hz 메시지를 전부 출력하지 않고 **최초 상태 및 `(state, reason, route)` 변화 시에만** 출력합니다. 수신이 약 1.5초 동안 끊기면 `NO_STATUS`를 한 번 표시하고, 복구 후 다시 최초 상태를 표시합니다.

출력 예시(실측이 아닌 형식 예시):

```text
12:00:00 [SAFETY] CLEAR | reason=NO_RESTRICTION | limit=0.80 m/s | route=A_to_D5
12:00:08 [SAFETY] SLOW  | reason=CURVATURE_LIMIT | limit=0.60 m/s | route=A_to_D5
12:00:13 [SAFETY] STOP  | reason=PATH_OBSTACLE  | limit=0.00 m/s | route=A_to_D5
12:00:18 [SAFETY] CLEAR | reason=NO_RESTRICTION | limit=0.80 m/s | route=A_to_D5
```

Safety 모니터는 **읽기 전용**입니다. 감속 및 정지 제어는 `pid_safety.py`와 `ff_pid_node.py`가 수행합니다.
Safety `STOP`은 장애물·인지 오류 등으로 인한 **일시적인 주행 정지**입니다. 이를 DRIVE 종료 명령으로 취급하지 않습니다. 원인이 해소되면 기존 정책에 따라 주행이 재개될 수 있습니다.

Safety 판단의 주요 이유:

| Safety | 대표 이유 | 의미 |
|---|---|---|
| CLEAR | `NO_RESTRICTION` | 추가 속도 제한 없음 |
| SLOW | `PATH_OBSTACLE` | 전방 경로 장애물 접근 |
| SLOW | `CURVATURE_LIMIT` | 전방 경로 곡률로 감속 |
| SLOW | `CTE_LIMIT` | 경로 횡방향 오차로 감속 |
| SLOW | `GOAL_APPROACH` | 목적지까지 남은 경로 거리 3.0m 이내에서 속도 상한을 선형 감속(0.4m/s까지) |
| STOP | `PATH_OBSTACLE` | 경로 전방 정지 거리 내 장애물 |
| STOP | `VERY_CLOSE_OBJECT` | 휠체어와 너무 가까운 물체 |
| STOP | `MASK_BOUNDARY` | 주행 가능 영역 경계 검사 실패 |
| STOP | `PERCEPTION_STALE`, `POSE_MISSING` 등 | 인지·위치 데이터 이상 |
| STOP | `RELEASE_CONFIRM` | STOP 해제 전 짧은 안정 확인 |

출력은 **이벤트마다 발생**하지만, Safety의 속도 상한 숫자만 같은 이유 안에서 변하는 경우에는 별도 이벤트로 출력하지 않습니다. 상세한 연속 수치를 확인해야 할 때만 `rostopic echo /pid_safety/status`를 사용합니다(이 명령은 메시지마다 계속 출력함).

### FF–PD 주행 상태 (선택)

별도 모니터 없이도 `pid_drive.sh` 터미널에 FF–PD 상태 변경과 약 30초 간격 진행률이 출력됩니다.
추가로 전체 상태가 필요하면 다음을 사용할 수 있습니다.

```bash
source /opt/ros/noetic/setup.bash
rostopic echo /ff_pid/status
```

위 명령은 상태 메시지를 모두 출력하는 디버깅용입니다. 평소에는 READY 이벤트와 Safety 이벤트를 우선 확인하면 됩니다.

## 4. FF–PD + Safety 구성

### FF–PD 제어기

`ff_pid_core.py`는 경로를 재샘플링하지 않고 저장된 Waypoint·곡률을 사용합니다.

- 곡률 기반 **Feedforward**: 전방 경로 곡률의 조향 성분
- 예측 **CTE 기반 PD**: 횡방향 위치 오차와 변화율 보정
- 예측 **Heading Error**: 주행 방향 정렬을 위한 Yaw 보정
- 좌우 바퀴 속도 제약 및 정상 RUNNING 명령의 가속·각속도 변화 제한
- `ff_pid_node.py`에서 50Hz로 제어, 조건 미충족 시 HOLD/정지 처리

주요 시작 파라미터(실차 최종 튜닝값이 아님):

| 변수 | 값 | 역할 |
|---|---:|---|
| `KP` | 1.00 | CTE P 게인 |
| `KD` | 0.50 | CTE D 게인 |
| `KI` | 0.00 | I항 미사용 |
| `FF_GAIN` | 1.00 | FF 배율 |
| `YAW_GAIN` | 0.50 | Heading 보정 |
| `MAX_V_MPS` | 0.80 m/s | 목표 최고 전진 속도 |
| `MAX_W_RAD_S` | 0.60 rad/s | 목표 최고 각속도 |
| `WHEEL_TRACK_M` | 0.46 m | 구동 변환용 유효 바퀴 간격 |
| `PREDICTION_HORIZON_S` | 0.50 s | 예측 시간 |

### Safety 제어기

`pid_safety.py`는 FF–PD와 별도 노드로 실행되며, `/cmd_vel`을 직접 발행하지 않습니다. 현재·예측 위치, Drivable Mask, 객체 정보, 경로 진행도/CTE/곡률 및 데이터 최신성을 바탕으로 다음을 산출합니다.

- `CLEAR`: 기본 속도 상한 허용
- `SLOW`: 곡률·CTE·장애물·목적지 접근 조건별 속도 상한 중 **최솟값 하나** 적용(감속 효과 곱셈·합산 없음)
- `STOP`: 장애물 근접·영역 경계·입력 오류 등으로 속도 0 요청

`/ff_pid/motion_policy`의 `state`·`speed_limit_mps`를 FF–PD 노드가 반영하고, 진단용 `/pid_safety/status`에는 같은 정책과 `reason`을 포함합니다. Safety 정책이 최신·유효하지 않으면 제어기가 진행을 허용하지 않습니다.

주요 기준은 `scripts/pid_safety.py` 상단에 있습니다(전방 장애물 `STOP 1.0m`, `SLOW 2.0m`, 정책 주기 0.1초, 인지 타임아웃 1.0초 등). 이는 제어 정책의 초기 설정이며 물리적 안전 인증이나 실차 검증 결과를 의미하지 않습니다.

목적지 접근 시에는 Safety가 `GOAL_APPROACH`로 **SLOW 속도 상한만 조절**하고, 최종 0속도 명령·정차 확인·`GOAL_REACHED` 처리는 `ff_pid_node.py`가 담당합니다. Mask 경계 검사에서는 현재 위치와 예측 위치를 모두 확인합니다. 실차 감속거리·정지거리 검증은 별개입니다.

### 주요 ROS 인터페이스

| 토픽·서비스 | 역할 |
|---|---|
| `/fast_lio_icp/pose` | 지도 기준 위치·방향 |
| `/fast_lio_icp/localization_diagnostics` | GICP 상태 |
| `/wheel_status` | 구동 모드·바퀴 피드백 |
| `/ff_pid/start` | FF–PD START / PAUSE 요청 서비스 |
| `/ff_pid/status` | 제어기 상태·경로 진행도 |
| `/ff_pid/motion_policy` | Safety가 발행하는 주행 정책 |
| `/pid_safety/status` | Safety 상태·이유·속도 상한 |
| `/perception/objects_summary` | 인식/융합 객체 정보 |
| `/cmd_vel` | FF–PD의 구동 속도 명령 |
| `/mode_cmd` | AUTO(65) / MANUAL(77) 요청 |

## 5. 기록·실험 보조 명령

READY는 가능하면 ROS bag 녹화를 자동으로 시작합니다. 녹화 실패가 READY 자체를 항상 막지는 않으므로 확인이 필요합니다. 파일은 READY 실행 디렉터리(`~/pid_ready_logs/<실행시각>/`)에 보관하며 **512MB 또는 15분** 단위로 분할합니다.

```bash
# 녹화 상태와 저장 파일 확인
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready_bag.sh" status

# 수동 마커 기록 — 실험 중 원하는 시점
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready_bag.sh" mark START_A
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready_bag.sh" mark BUMP_ENTRY
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready_bag.sh" mark BUMP_EXIT

# READY는 유지하고 녹화만 종료하려면
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready_bag.sh" stop
```

녹화에는 `/fast_lio_icp/pose`, `/Odometry`, `/wheel_status`, `/cmd_vel`, `/ff_pid/status`, **`/ff_pid/motion_policy`, `/pid_safety/status`**, `/perception/objects_summary`, `/manual_mark` 등이 포함됩니다.

파라미터를 변경할 때는 **NUC에서 실제 실행하는 배포본**의 `ff_pid_core.py` 또는 `pid_safety.py`를 수정합니다. 실행 중인 Python 프로세스에는 즉시 적용되지 않으므로 DRIVE STOP 후 다시 DRIVE를 시작합니다. Python 소스 값보다 ROS private 파라미터가 우선하도록 구현된 항목도 있습니다. C++/메시지 정의가 아니라 Python 코드만 수정했다면 일반적으로 `catkin_make`가 필요하지 않습니다.

## 6. 주요 파일과 배포 위치

| 파일 (PID 패키지 `scripts/`) | 기능 |
|---|---|
| `pid_ready.sh` | READY 시작·상태·이벤트·전체 종료 |
| `pid_ready_monitor.py` | READY 상태 판정과 이벤트 출력 |
| `pid_ready_shutdown.sh` | READY 프로세스·녹화 정리 |
| `pid_ready_bag.sh` | ROS bag 시작·상태·마커·종료 |
| `pid_drive.sh` | 경로 선택, 사전 검사, FF–PD·Safety 시작 |
| `pid_drive_check.py` | MANUAL 정차 확인, 1.0m/30° 경로 정렬, JSON 및 주행 상태 감시 |
| `pid_safety_watch.py` | Safety 상태·사유 변경만 표시하는 읽기 전용 터미널 감시 |
| `ff_pid_core.py` | FF–PD 제어 계산·파라미터 |
| `ff_pid_node.py` | FF–PD ROS 노드, `/cmd_vel` 및 `/ff_pid/start` |
| `pid_safety.py` | CLEAR/SLOW/STOP 정책, 이유·속도 상한 |
| `pid_stop.sh` | 자율주행 종료, MANUAL 복귀 확인, READY 유지 |

**개인 저장소**에는 `scripts/`, `waypoints/`가 있습니다. **NUC 팀 전체 배포**에서는 보통 `source-linux/src/pid/scripts/`에서 PID 스크립트를 사용하며, 지도·경로의 실제 자산은 전체 배포 구조에 의존합니다.

**현재 운영 경로:** NUC의 `~/wheelchair_deploys/ffpid`는 `ffpid-78cbef8-20261109`를 가리키며, 해당 전체 팀 배포의 `source-linux/src/pid/scripts/`에는 개인 PID `main`의 `fd84eee` 변경 사항(목적지 감속·현재/예측 마스크 검사)이 반영되어 있습니다. 향후 GitHub 변경은 NUC에 자동 배포되지 않습니다. 배포 변경 시에는 새 폴더를 빌드·점검하고 `ffpid` 링크를 바꾸고, 브릿지 `sudo systemctl restart unicon-ffpid-bt.service`로 새 경로를 다시 인식시켜야 합니다. 기존 DWA `current` 배포 경로는 변경하지 않습니다.

**Bluetooth 운영:** 개인 브릿지는 `/home/mprp3/ffpid_bt_bridge/pid_bt_bridge.py`를 별도 `unicon-ffpid-bt.service`로 자동 실행하며, `--pid-scripts`와 `--routes-dir`는 위 `ffpid` 고정 경로를 참조합니다. 기존 DWA의 `ros1_bluetooth_bridge.py`는 변경하지 않습니다. READY 시작 전 `ROS not yet online` 로그는 ROS Master 미실행으로 예상될 수 있습니다. 앱↔NUC 실기 Bluetooth 연동은 아직 확인되지 않았습니다.

## 7. 문제 발생 시

| 상황 | 확인 사항 |
|---|---|
| READY 미준비 | `pid_ready.sh status`, `watch`, READY 실행 로그 |
| GICP TRACKING 실패 | 실제 위치·지도·정합 초기화 및 진단 |
| 출발 시 위치 조정 요청 | MANUAL에서 방향·경로 거리 조정 후 DRIVE 재실행 |
| `/cmd_vel` 중복 발행 | 다른 제어 노드 중지 후 단일 발행자 확인 |
| START 거절 | 터미널의 `drive_preflight`, `drive_event`, Safety 상태 및 FF–PD 로그 |
| Safety STOP | `pid_safety_watch.py`의 `reason` 확인. STOP은 주행 종료가 아님 |
| STOP 후 물리 정차 미확인 | 즉시 실제 구동 상태·물리 정지 수단 확인 |
| Safety 상태 `NO_STATUS` | 주행 전이면 미실행일 수 있음. 주행 중이면 Safety 노드·ROS 통신 점검 |
| NUC가 최신 기능을 모름 | 사용 중인 배포 디렉터리가 최신 GitHub PID 코드와 동기화됐는지 확인 |

**검증 범위:** READY 장치 초기화 및 일부 통합 검사는 이전 NUC 배포에서 수행했지만, 이후 변경된 FF–PD + Safety + 출발 위치 검사 전체에 대한 **실차 통합 검증은 완료되지 않았습니다**. 소프트웨어 감시·정지 기능은 실제 휠체어의 물리적 정지 수단을 대체하지 않습니다.

## 실험 기능: 정적 장애물 A* 우회 (feature/static-obstacle-astar-replan)

> **개발 브랜치 전용, 실차 검증 전. 기본값 OFF.** 개인 저장소 브랜치의 코드를 수정해도 팀 배포나 NUC에는 반영되지 않습니다. 장애물 팽창 반경·곡선 추종 가능성·응답 시간은 실차로 검증되지 않았으며, 탑승자 없이 감독 하에만 시험해야 합니다. 원본 6개 JSON은 수정하지 않습니다.

- 초기 설정: `PID_ENABLE_ASTAR=false` (기본값). 실험 시에만 **DRIVE를 시작하는 동일한 셸에서** `export PID_ENABLE_ASTAR=true`로 설정합니다. `_test_clear:=true`로 실행하면 자동 우회는 무조건 비활성화됩니다.
- DRIVE는 우회 기능을 명시적으로 켠 경우에만 기존 FF–PD 및 Safety 외에 `pid_astar_planner.py`를 실행합니다. STOP은 3개 노드를 함께 종료하며 READY 센서/로컬라이제이션은 유지합니다.
- **정적 장애물**은 경로 앞쪽 **2.0m 이내**에서 `PATH_OBSTACLE`로 STOP합니다. 물리적 바퀴 정지와 `static` 판정을 확인하면 별도 고정 대기 없이 A* 요청을 시작합니다.
- **동적 장애물**이 실제로 **휠체어로부터 지속적으로 멀어짐**을 최소 0.6초 이상 확인한 경우에만 1~2m 구간의 장애물 감속을 무시합니다. 1m 이하에서는 저속 제한(현재 0.4m/s)을 적용하며, 아주 가까운 물체(기존 `NEAR_STOP_GAP_M`)는 무조건 STOP합니다. 멀어짐을 확인하지 못한 `moving`, `unknown` 객체에는 기존 Safety 정지·감속을 그대로 적용합니다.
- `moving`과 `unknown`은 A* 장애물 지도에서 제외하지만 **Safety의 지속적인 충돌 감시 대상**입니다. `/perception/objects_summary` 객체 ID/위치 이력을 사용한 상대거리 변화 판정은 보수적 초기 설정이며 실주행 노이즈 검증이 필요합니다.
- 플래너는 원래 10cm 마스크에 정적 AABB 장애물을 팽창(현재 **임시 설정** 0.70 → 0.80 → 0.90m)해 8방향 A*를 실행하고, Line-of-Sight 꺾임 제거 → 5차 B-Spline 시도 → 10cm Waypoint 및 Yaw 재생성 → 기존 경로 후방 합류를 수행합니다.
- Safety는 최종 경로 전체의 마스크 여유와 정적 장애물 충돌을 재검증합니다. 실패하거나 시간 초과라면 `STOP`을 유지합니다.
- `/ff_pid/replan/request` → `/ff_pid/replan/candidate` → `/ff_pid/replan/stage` → `/ff_pid/replan/ack`(PREPARED) → `/ff_pid/replan/commit` → ACK(APPLIED) 순서입니다. ACK 전까지 `REPLAN_HOLD` 정책으로 정지합니다.
- Safety와 FF–PD가 동일한 `route_version`을 사용해야만 CLEAR/SLOW 주행이 허용됩니다. 성공한 경로는 **메모리에서만 교체**합니다. 새 경로 좌표는 `/ff_pid/active_route`에 `type: route` 형태로 발행하지만, **개인 Android Bluetooth 브릿지의 자동 전달은 아직 구현하지 않았습니다.**
- 탐색/준비 중 기존 경로의 장애물이 해소되면 후보를 폐기하고 기존 경로를 재개합니다. 이미 COMMIT 단계에 진입했으면 두 경로 버전이 엇갈리지 않도록 적용 절차를 마칩니다.
- 첫 우회 후 추가 우회는 이번 MVP에서 지원하지 않습니다. 새 경로에 또 장애물이 생기면 기존 Safety가 STOP을 명령합니다. 시작 방향·곡률 가용성에 대한 추가 경로 검증도 MVP에 없습니다. **부드러운 수학적 곡선이 물리적으로 추종 가능한 경로라는 의미는 아닙니다.**

오프라인 테스트: `python -m unittest discover -s tests -p 'test_replan_path.py' -v` (numpy 및 scipy 필요). 실차를 움직이는 통합 시험은 수행하지 않았습니다.

