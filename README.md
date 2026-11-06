# UNICON Wheelchair — FF–PD 자율주행 시스템

ROS1 Noetic 기반 전동휠체어의 **정합 → 주행 → 정지**, 제어 파라미터 변경, 위치 기록과 ROS bag 녹화에 대한 사용 설명서입니다.

> **저장소 구분:** 이 개인 저장소는 팀 저장소 [UNICON_wheelchair_v2](https://github.com/Dannythechampion/UNICON_wheelchair_v2)의 **PID 패키지 사본**입니다. 개인 저장소에서는 코드가 `scripts/`에, 경로 파일이 `waypoints/`에 있습니다. 아래 실행 명령어는 센서·위치추정·구동부 등이 갖춰진 **NUC의 전체 팀 프로젝트**(`UNICON_wheelchair_v2`)를 기준으로 작성했습니다. 개인 저장소만 단독으로 내려받아서는 READY/DRIVE가 실행되지 않습니다.
>
> **동기화 기준:** 팀 저장소 `feature/ffpid`, 커밋 `48c7b826` (2026-11-06).

## 1. 명령어 빠른 참조

아래 명령어는 NUC 터미널에서 실행합니다.

### 프로젝트 디렉터리 이동

```bash
cd ~/ws/wheelchair_ws/UNICON_wheelchair_v2
```

### ① 정합 및 주행 준비 — ROS bag 자동 녹화 포함

```bash
bash src/pid/scripts/pid_ready.sh
```

READY는 LiDAR, FAST-LIO, GICP, 장애물 인식, 구동부 및 Watchdog을 실행하고 상태를 점검합니다. **자율주행을 시작하지는 않습니다.** 정상 준비 뒤에도 READY의 모니터는 상태 변화를 감시합니다.

### ② 경로 지정 후 주행 시작

경로 선택 메뉴를 열려면:

```bash
bash src/pid/scripts/pid_drive.sh
```

경로를 바로 지정하려면:

```bash
bash src/pid/scripts/pid_drive.sh A_to_D5
```

사용 가능한 경로는 다음 6개입니다.

```text
A_to_D4
A_to_D5
D4_to_A
D4_to_D5
D5_to_A
D5_to_D4
```

### ③ 파라미터 변경 후 주행 시작

VS Code에서 **NUC에서 실행하는 실제 파일** `src/pid/scripts/ff_pid_core.py`를 열어 `KP`, `KD`, `MAX_V_MPS` 등 원하는 값을 수정하고 저장합니다.

이미 주행 중이면 먼저 정지한 뒤 다시 시작합니다.

```bash
bash src/pid/scripts/pid_stop.sh
bash src/pid/scripts/pid_drive.sh A_to_D5
```

**Python 파라미터 수정에는 재빌드가 필요하지 않습니다.** 값은 FF–PD 노드를 새로 실행할 때 적용됩니다. 단, 해당 항목의 `/ff_pid/*` ROS private 파라미터가 설정돼 있으면 그 값이 파일의 기본값보다 우선합니다.

> 현재 `pid_drive.sh`에 제어 파라미터를 명령행 인자로 직접 전달하는 기능은 없습니다. 이 README는 VS Code에서 파일을 수정하는 사용 방식을 기준으로 합니다.

### ④ 자율주행 정지

```bash
bash src/pid/scripts/pid_stop.sh
```

FF–PD 정지와 MANUAL 복귀를 요청합니다. **READY, 위치추정 및 ROS bag 녹화는 계속 유지**되므로 주행을 다시 시작할 때 READY를 반복할 필요는 없습니다.

### ⑤ 현재 위치 확인

```bash
bash src/pid/scripts/pid_drive.sh position
```

현재 GICP Map 기준 X, Y, Yaw를 한 번 출력합니다. 주행 명령을 보내지 않습니다.

### ⑥ 특정 위치 기록 (ROS bag 마커)

```bash
# 출발·도착 지점
bash src/pid/scripts/pid_ready_bag.sh mark START_A
bash src/pid/scripts/pid_ready_bag.sh mark START_D4
bash src/pid/scripts/pid_ready_bag.sh mark START_D5

# 과속방지턱
bash src/pid/scripts/pid_ready_bag.sh mark BUMP_ENTRY
bash src/pid/scripts/pid_ready_bag.sh mark BUMP_EXIT
```

각 명령은 `/manual_mark` 토픽에 마커를 전송합니다. 해당 시각의 위치·바퀴 정보는 녹화된 bag과 대응해 분석할 수 있습니다.

### ⑦ 실험 완료 후 ROS bag 녹화 종료

```bash
bash src/pid/scripts/pid_ready_bag.sh stop
```

자율주행 정지와 별개입니다. 녹화가 계속 필요한 동안에는 이 명령어를 실행하지 않습니다.

---

## 2. 전체 시스템 구조

```text
[READY] pid_ready.sh
   ├─ ROS Master
   ├─ Livox MID-360 / IMU
   ├─ FAST-LIO → Odometry
   ├─ GICP → Map Localization / TRACKING
   ├─ Geometric Perception + Object Fusion
   ├─ Dynamic Object Exclusion
   ├─ Wheel / UART / Stop Watchdog
   └─ ROS bag 자동 녹화
           │
           ▼
[DRIVE] pid_drive.sh
   ├─ 경로 선택 및 사전 검사
   ├─ MANUAL → AUTO
   ├─ ff_pid_node.py
   └─ ff_pid_core.py
       ├─ 곡률 기반 Feedforward
       ├─ 예측 CTE 기반 PD Feedback
       ├─ 전방 곡률 기반 감속
       ├─ 좌·우 바퀴 속도 제약 검사
       └─ /cmd_vel 출력
           │
           ▼
[STOP] pid_stop.sh
   ├─ FF–PD 정지 요청
   ├─ 바퀴 정지 피드백 확인
   ├─ MANUAL 복귀
   └─ /ff_pid 노드 종료

   ※ READY 센서·정합과 ROS bag 녹화는 유지
```

### READY의 역할

`pid_ready.sh`는 전체 ROS 센서·정합·인지·구동 환경을 준비하며 최초 성공 여부와 Map 위치를 보여줍니다. 초기 정합 기준은 `A_to_D5` 경로의 A 지점이며, 이후 선택하는 주행 경로와는 별개입니다. READY는 주행 명령을 발행하지 않습니다.

### DRIVE의 역할

`pid_drive.sh`는 선택한 경로를 확인하고 주행 전 검사를 수행합니다. 주요 검사 대상은 GICP TRACKING, Map 위치와 센서 데이터의 최신성, 모터 MANUAL 및 정차 상태, 선택 경로와 위치·방향의 적합성, `/cmd_vel` 중복 발행 여부 등입니다.

출발점과 좌표가 반드시 같을 필요는 없습니다. **선택 경로의 중간에서 정지했다가 재출발할 수 있습니다.** 경로와 너무 멀거나 방향이 맞지 않으면 시작하지 않습니다.

### STOP의 역할

`pid_stop.sh`는 FF–PD에 정지를 요청한 뒤 모터 피드백으로 정차와 MANUAL 전환을 확인하고 주행 노드를 종료합니다. 정상적인 ROS 통신과 구동부 응답을 전제로 하므로 **물리적 긴급정지를 대신하지 않습니다.**

## 3. FF–PD 제어 방식

- **Feedforward:** 전방 경로 곡률을 사용해 선제적으로 각속도를 계산합니다.
- **PD Feedback:** 예측된 횡방향 경로 추종 오차(CTE)와 오차 변화율로 조향을 보정합니다.
- **커브 감속:** 현재 위치 전방 구간에서 절대 곡률 상위 20%의 평균을 구하고, 횡가속도·각속도 제한을 적용해 목표 속도를 낮춥니다.
- **제약 및 HOLD:** 바퀴 속도 제약, 경로 이탈, 위치추정 상태 오류 등 주행 조건이 맞지 않으면 정지 또는 HOLD 상태로 전환합니다.

### 현재 기본 제어 파라미터

파일: `src/pid/scripts/ff_pid_core.py` (개인 저장소에서는 `scripts/ff_pid_core.py`)

| 변수 | 기본값 | 의미 |
|---|---:|---|
| `KP` | 1.00 | P 게인 |
| `KD` | 0.50 | D 게인 |
| `KI` | 0.00 | I 게인 |
| `MAX_V_MPS` | 0.80 | 최대 전진 속도 (m/s) |
| `MAX_W_RAD_S` | 0.60 | 최대 각속도 (rad/s) |
| `WHEEL_TRACK_M` | 0.46 | 유효 바퀴 간격 (m) |
| `MIN_WHEEL_MPS` | 0.30 | 최소 바퀴 속도 (m/s) |
| `MAX_WHEEL_MPS` | 1.00 | 최대 바퀴 속도 (m/s) |
| `LATERAL_ACCEL_MPS2` | 0.15 | 곡률 감속 횡가속도 제한 (m/s²) |
| `CURVATURE_PREVIEW_M` | 2.0 | 전방 곡률 확인 거리 (m) |
| `CTE_DEADZONE_M` | 0.20 | CTE 데드존 (m) |
| `D_DEADZONE_MPS` | 0.02 | D항 입력 데드존 (m/s) |
| `D_CLAMP_RAD_S` | 0.15 | D항 기여 각속도 제한 (rad/s) |

수정된 Python 소스는 **현재 실행 중인 제어기에 즉시 반영되지 않습니다.** 정지 후 DRIVE를 다시 실행해야 하며, 별도의 `catkin_make`는 일반적으로 필요하지 않습니다. C++ 코드나 ROS 메시지 정의 등 빌드 대상이 변경되면 빌드가 필요할 수 있습니다.

## 4. 터미널 상태 출력

정상 상태를 계속 출력하기보다는 **최초 점검 및 상태 변화 중심**으로 출력합니다.

| 시점·상황 | 출력 |
|---|---|
| READY 처음 완료 | 장치·센서·정합 점검 결과와 Map 위치 |
| 정상 작동 유지 | 반복 출력 없음 |
| LiDAR / IMU / UART / GICP 이상·복구 | 변화 발생 시 |
| MANUAL ↔ AUTO 전환 | 변화 발생 시 |
| 장애물 인식·소멸 | 인식 상태 변경 시 |
| ROS bag 녹화 중단·재개 | 변화 발생 시 |
| 주행 RUNNING / HOLD / 종료 | 상태 변경 시 |
| 주행 진행률 | 주행 중 약 30초마다 |
| 현재 위치 | 사용자가 `position` 명령을 실행할 때 |
| 목표·실제 선속도, 각속도, CTE | 정상 주행 중 상시 출력하지 않음 |

장애물 **인식**과 장애물에 대한 **감속·정지 판단**은 다른 기능입니다. 현재 출력되는 장애물 메시지는 인식 이벤트만 나타냅니다.

## 5. ROS bag 데이터 기록

READY에서 별도 명령 없이 ROS bag 녹화를 시작합니다. 기본 저장 경로는 다음과 같습니다.

```text
~/pid_ready_logs/<실행시각>/
```

bag 파일은 **512MB 또는 15분**마다 분할됩니다.

기록 토픽:

```text
/fast_lio_icp/pose
/fast_lio_icp/localization_diagnostics
/Odometry
/livox/imu
/wheel_status
/wheel_cmd
/mode_cmd
/cmd_vel
/ff_pid/status
/perception/objects_summary
/uart_tx_diag
/stop_watchdog/alarm
/manual_mark
```

READY와 녹화는 자율주행을 STOP한 이후에도 유지되므로 수동주행·정지 후 재출발 상황도 기록할 수 있습니다. 녹화를 모두 마쳤을 때만 `pid_ready_bag.sh stop`을 실행합니다.

## 6. 코드 파일별 역할

| 파일 (개인 저장소의 `scripts/`) | 역할 |
|---|---|
| `pid_ready.sh` | 전체 ROS 환경과 GICP 정합 준비, bag 시작 |
| `pid_ready_monitor.py` | READY 상태 점검과 상태 변화 출력 |
| `pid_ready_bag.sh` | ROS bag 녹화·마커 기록·종료 |
| `pid_drive.sh` | 경로 선택, 사전 검사, AUTO 전환 및 주행 시작 |
| `pid_drive_check.py` | 주행 전 상태 검사, 위치 조회, 주행 상태·진행률 출력 |
| `ff_pid_node.py` | FF–PD ROS 인터페이스, `/ff_pid/start`, `/cmd_vel` |
| `ff_pid_core.py` | FF–PD 알고리즘과 제어 파라미터 |
| `pid_stop.sh` | 자율주행 정지 및 MANUAL 복귀 |

## 7. 안전 제한 및 검증 상태

현재 FF–PD는 위치추정, 경로·마스크 및 구동 상태 등을 검사하지만 **장애물 인식 결과에 따른 자동 감속·정지 판단은 아직 FF–PD와 연결되지 않았습니다.** 기존 SafetyGate/TipGuard 역시 이 FF–PD 구성에서 활성화되지 않습니다.

실제 주행 시험은 통제된 구역에서 실시하고, 작업자가 물리적 정지 수단을 확보해야 합니다. 소프트웨어 정지 스크립트는 안전 인증된 비상정지 기능이 아닙니다.

**검증 범위:** GitHub에 반영된 코드 확인. NUC 실기 구동 검증 및 장애물 정지 기능 검증은 포함되지 않습니다.
