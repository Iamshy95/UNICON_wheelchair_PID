# FF–PID QUICKSTART

NUC에 **SSH로 접속한 터미널**에서 실행합니다. 실행 경로는 NUC의 `~/wheelchair_deploys/ffpid` 기준입니다. 해당 경로가 실제 운용 배포본인지 확인하고 사용하세요.

## 1. 평소 주행: 이것만 하면 됩니다

### ① READY 시작

센서·위치추정·구동부 등을 준비합니다. READY가 이미 정상 실행 중이면 다시 시작할 필요가 없습니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" start
```

### ② 주행 시작

아래 `A_to_D5`를 원하는 경로로 바꿉니다. 출발 시에는 휠체어가 **수동 모드에서 정차**해 있어야 합니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_drive.sh" A_to_D5
```

지원 경로:

| 경로 | 이동 구간 |
| --- | --- |
| `A_to_D4` | 애지문 → 정몽구센터 |
| `A_to_D5` | 애지문 → 2공학관 |
| `D4_to_A` | 정몽구센터 → 애지문 |
| `D4_to_D5` | 정몽구센터 → 2공학관 |
| `D5_to_A` | 2공학관 → 애지문 |
| `D5_to_D4` | 2공학관 → 정몽구센터 |

### ③ 평소 주행 종료: `Ctrl+C`

**주행 시작 명령을 실행한 터미널에서 `Ctrl+C`를 누르면 됩니다.**

`pid_drive.sh`는 종료 시 자동으로 주행 정지 스크립트를 호출하여 MANUAL 전환과 정차 확인을 시도합니다. **종료 메시지에서 정차 확인 성공 여부를 확인하세요.** 단순히 터미널이 닫혔다고 실제 정차가 증명되는 것은 아닙니다.

주행 종료 후에도 **READY는 유지**됩니다. 다시 출발할 때는 READY를 재실행하지 않고 새로운 경로로 **주행 시작** 명령만 실행하면 됩니다.

---

## 2. 필요할 때만 사용하는 명령어

### 주행을 별도로 종료해야 할 때 — `pid_stop.sh`

다른 터미널에서 주행을 종료해야 하거나, `Ctrl+C` 처리가 안 되거나, 종료·정차 확인 경고가 나타나는 경우에 사용합니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_stop.sh"
```

**이 명령도 실제 정차가 확인됐는지 결과를 봐야 합니다.** 확인 실패 시 물리적 정지 수단으로 안전을 확보한 뒤 상태를 점검하세요. `Ctrl+C`와 `pid_stop.sh` 모두 물리적인 비상정지를 대체하지 않습니다.

### READY 상태만 확인하고 싶을 때 — `status`

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" status
```

### READY 상태 변화를 계속 보고 싶을 때 — `watch`

별도 터미널에서 실행하는 **선택적 모니터링**입니다. `Ctrl+C`로 모니터만 종료하며 READY 자체는 종료되지 않습니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" watch
```

### 주행 중 Safety 상태를 보고 싶을 때

주행 중 `CLEAR / SLOW / STOP` 및 감속·정지 이유를 확인하는 **선택적 모니터링**입니다. 별도 터미널에서 아래 두 줄을 순서대로 실행합니다.

```bash
source /opt/ros/noetic/setup.bash
python3 -u "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_safety_watch.py"
```

이 모니터의 `Ctrl+C`는 **모니터만 종료**합니다. 휠체어 주행을 종료하는 기능은 아닙니다.

### 모든 실험이 끝났을 때 — READY 종료

현재 주행이 끝나고 실제로 정차한 것을 확인한 후 READY 시스템까지 종료하려면 실행합니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" stop
```

**정리하면:** 평소에는 **READY 시작 → 주행 시작 → 주행 터미널에서 `Ctrl+C`**가 기본입니다. `pid_stop.sh`는 별도 종료·오류 상황에서, `status`·`watch`·Safety 모니터링은 확인이 필요할 때만 사용합니다.
