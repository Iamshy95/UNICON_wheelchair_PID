# UNICON Wheelchair — FF–PID / Safety

ROS1 Noetic 기반 전동휠체어의 **FF–PID 경로 추종 및 Safety 제어 코드**입니다. 기존 휠체어 시스템의 센서·위치추정·구동부를 활용하고, 주행 제어 및 운용 스크립트를 FF–PID용으로 구성했습니다.

## 관련 GitHub 및 버전

- **민준님 원본 저장소:** 정확한 GitHub 주소 확인 후 추가 예정
- **팀 전체 휠체어 저장소:** https://github.com/Dannythechampion/UNICON_wheelchair_v2
- **팀에서 사용하는 FF–PID 브랜치:** https://github.com/Dannythechampion/UNICON_wheelchair_v2/tree/feature/ffpid
- **개인 FF–PID 저장소(현재 저장소):** https://github.com/Iamshy95/UNICON_wheelchair_PID
- **Android 앱 및 전용 Bluetooth 브릿지:** https://github.com/Iamshy95/UNICON_wheelchair_app

**이 저장소의 `main`은 팀 저장소 `feature/ffpid`의 PID 스크립트·경로 파일과 같은 버전으로 동기화했습니다(2026-11-20 기준).** 개인 저장소에는 PID 관련 파일만 들어 있으며, 팀 저장소의 다른 ROS 패키지와 NUC 구동부 파일까지 모두 포함된 것은 아닙니다.

**실제 NUC 배포는 팀 저장소의 `feature/ffpid` 브랜치를 기준으로 진행합니다.** 개인 저장소에 커밋하는 것만으로 NUC의 실행 코드가 자동 갱신되지는 않습니다.

## 빠른 사용법

**[QUICKSTART — READY·주행 시작·종료·상태 확인 명령어](QUICKSTART.md)**

노트북을 NUC와 같은 유선 네트워크에 연결한 다음 SSH로 접속해 사용합니다.

```bash
ssh mprp3@192.168.1.5
```

SSH 접속 후 **NUC 터미널에서** QUICKSTART 명령어를 실행하면 됩니다. 새 터미널에서 주행 종료나 상태 모니터링을 할 때도 각각 NUC에 SSH로 접속해야 합니다.

- **READY 시작:** LiDAR·IMU, FAST-LIO, GICP 위치추정, 장애물 인식, 바퀴 통신을 준비합니다.
- **DRIVE 시작:** 6개 경로 중 하나를 선택해 자율주행합니다.
- **DRIVE 종료:** 현재 주행만 종료합니다. READY는 계속 유지됩니다.
- **READY 종료:** 실험이 끝나면 센서·위치추정 등 READY 시스템을 정리합니다.
- **상태 확인:** READY 진행 상태 및 Safety 감속·정지 이유를 모니터링할 수 있습니다.

> **배포 경로 확인:** QUICKSTART는 `~/wheelchair_deploys/ffpid/`를 사용합니다. NUC의 해당 링크가 **실제 운용 중인 배포본**을 가리키는지 `readlink -f ~/wheelchair_deploys/ffpid`로 먼저 확인하세요. 11월 19일 현장 확인 당시 작업 경로는 `~/wheelchair_deploys/pid-20261112-dd5bfef/source-linux/`였습니다. 경로가 다르면 운영 중인 실제 배포본의 `src/pid/scripts/`를 사용해야 합니다. 실행 중인 시스템을 업데이트하거나 링크를 바꾸지 마세요.

앱에서 운용할 경우에는 **[앱 README](https://github.com/Iamshy95/UNICON_wheelchair_app#readme)**의 버튼 설명과 문제 해결 방법을 참고하면 됩니다.

## 주요 변경 사항

기존 시스템의 **센서·위치추정·장애물 인식·바퀴 통신을 재사용**하면서, 주행 제어와 운용 방식을 다음과 같이 변경했습니다.

- **FF–PID 주행 제어:** 경로 곡률을 미리 반영하는 Feedforward와 경로 오차·진행 방향 보정을 결합했습니다.
- **Safety 분리:** 주행 제어기와 별도로 장애물, 경로 이탈, 주행 가능 영역, 센서 상태를 감시하고 감속·정지를 결정합니다.
- **상황별 감속:** 곡선·경로 오차·목적지 접근·과속방지턱에 맞춰 속도를 제한합니다.
- **장애물 정지와 재출발:** 진행 경로의 장애물을 감지하면 감속·정지하고, 안전 상태가 회복되면 기존 자동 재출발 동작을 수행합니다.
- **A* 장애물 우회:** 정적 장애물에 대한 우회 경로 생성 및 재합류 기능을 추가했습니다. **현재 실험 기능이며, 우회 경로의 안정적인 실차 추종은 해결되지 않았습니다.**
- **READY·DRIVE 운용 개선:** 시작 조건 검사, 상태 표시, 로그 기록, 주행 종료 및 재시작 절차를 스크립트로 정리했습니다.
- **LiDAR 연결 테스트:** READY 실패 시 LiDAR·IMU 수신 여부만 별도로 점검할 수 있습니다.
- **NUC 구동부 변경:** 팀 저장소에는 개인 PID에 포함되지 않은 센서·인지 연동 변경도 있습니다. 실제 NUC `base_model`에는 FF–PID 전용 Fast Stop Ramp가 적용되며, 팀 저장소의 `docs/nuc_runtime_20261118/base_model/`에는 관련 파일의 **참고용 사본**이 있습니다. 개인 PID 저장소만 복사해서 전체 시스템이 구성되는 것은 아닙니다.
- **전용 앱·브릿지:** Android 앱 및 NUC Bluetooth 브릿지는 **별도 앱 저장소**에서 관리합니다.

## 주요 노드 및 스크립트 구조

### READY: 자율주행 준비

`pid_ready.sh`가 ROS Master, LiDAR·IMU, FAST-LIO·GICP, 장애물 인식 및 구동부를 준비합니다.

| 파일 | 역할 |
| --- | --- |
| `scripts/pid_ready.sh` | READY 시작·상태 확인·모니터링·종료 |
| `scripts/pid_ready_monitor.py` | 센서·위치추정·구동 상태 확인 |
| `scripts/pid_ready_bag.sh` | 지정 토픽 ROS bag 기록 |
| `scripts/pid_ready_shutdown.sh` | READY 전체 종료·정리 |
| `scripts/pid_lidar_test.sh` | LiDAR·IMU 연결 단독 테스트 |

### DRIVE: 경로 추종·안전 제어

```text
READY 완료
  └─ pid_drive.sh : 경로·출발 조건 검사
       ├─ /ff_pid            : FF–PID 경로 추종, /cmd_vel 출력
       ├─ /pid_safety        : CLEAR / SLOW / STOP 판단
       └─ /pid_astar_planner : 정적 장애물 A* 우회 (실험 기능)
              ↓
        NUC base_model / 바퀴 구동부
```

| 파일 | 역할 |
| --- | --- |
| `scripts/pid_drive.sh` | 주행 경로 선택, 출발 검사, DRIVE 노드 시작 |
| `scripts/pid_drive_check.py` | 출발 위치·방향·바퀴 상태 검사 |
| `scripts/ff_pid_core.py` | FF–PID 제어 계산 |
| `scripts/ff_pid_node.py` | ROS 기반 주행 제어 노드 |
| `scripts/pid_safety.py` | 장애물·경로·위치추정 등에 따른 속도 제한 및 정지 |
| `scripts/pid_astar_planner.py` | 정적 장애물 A* 우회 경로 생성 |
| `scripts/pid_stop.sh` | 현재 DRIVE만 종료하고 READY 유지 |
| `scripts/pid_safety_watch.py` | Safety 상태 변화 모니터링 |

경로 파일은 `waypoints/route2_manual_20261031/`에 있으며, A(애지문)·D4(정몽구센터)·D5(2공학관) 사이의 6개 방향을 지원합니다. 실제 NUC에서는 팀 저장소에 배포된 경로 파일을 사용합니다.

## 현재 확인된 문제 및 향후 점검 항목

2026년 11월 18~19일 실차 운용 및 최근 로그 분석에서 확인되었거나 반복 관찰된 증상입니다. **원인은 아직 확정되지 않았습니다.**

1. **한쪽 바퀴가 멈추거나 예상과 다르게 동작하며 크게 회전하는 현상:** 특히 장애물 정지·재출발 부근에서 약 180° 수준의 급회전이 관찰되었습니다. Fast Stop Ramp와의 연관성은 의심 단계이며, 구동 명령과 실제 바퀴 피드백·UART 기록을 비교해야 합니다.
2. **`STOP_WATCHDOG` 경보 후 주행 재시작 실패:** 경보가 발생한 뒤 종료·재시작을 시도해도 경보가 남아 출발이 거부되는 경우가 있습니다.
3. **순간적인 `NO_TRACKING` / `POSE_STALE`:** 위치추정 정보가 잠깐 불안정해져 정지하거나 이후 복귀가 원활하지 않은 경우가 있습니다. 일시적인 끊김과 실제 위치추정 실패를 구분할 필요가 있습니다.
4. **장애물 정지 후 재출발이 되지 않거나 정지 상태가 오래 유지되는 경우:** 화면에 `OBSTACLE_STOP` 또는 `REPLAN_HOLD` 등으로 표시되더라도 실제 바퀴 상태와 제어기 상태가 일치하는지 확인이 필요합니다.
5. **주행 종료 후 다음 주행 시작 실패:** 이전 주행의 종료·정차 확인이 완료되지 않아 재시작이 거부될 때가 있습니다. 앱에는 **정지 상태 재검증** 기능이 있지만, 근본 원인 확인은 별개입니다.
6. **A* 우회 경로 추종 불안정:** 우회 경로 생성·적용은 확인했으나 실제 휠체어가 새 경로를 안정적으로 따라가지 못하는 문제가 남아 있습니다.
7. **정지·감속 거동 추가 검증 필요:** 급정지·정지 직전의 한쪽 바퀴 거동, 정지거리, 장애물 인식 시점을 비교하고 필요하면 더 부드러운 감속 및 IMU 기반 비정상 회전 감지를 검토해야 합니다.

**위 문제들이 해결·검증되기 전에는 안전이 확보된 통제 환경에서만 시험해야 합니다.** 소프트웨어의 STOP이나 앱의 주행 종료는 물리적 비상정지 수단을 대체하지 않습니다.
