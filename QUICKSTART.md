# FF–PID QUICKSTART

모든 명령어는 **NUC에 접속한 터미널**에서 실행합니다. **새 터미널을 열었다면 그 터미널에서도 NUC에 SSH로 접속**한 뒤 명령어를 입력합니다.

## READY 시작

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" start
```

## READY 상태 확인

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" status
```

## READY 종료

모든 주행을 마쳤을 때 실행합니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" stop
```

## 주행 시작

아래 **`A_to_D5`를 원하는 경로 이름으로 바꿔서** 실행합니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_drive.sh" A_to_D5
```

사용 가능한 경로:
- `A_to_D4` : 애지문 → 정몽구센터
- `A_to_D5` : 애지문 → 제2공학관
- `D4_to_A` : 정몽구센터 → 애지문
- `D4_to_D5` : 정몽구센터 → 제2공학관
- `D5_to_A` : 제2공학관 → 애지문
- `D5_to_D4` : 제2공학관 → 정몽구센터

**주행 시작 명령을 실행한 터미널은 주행 중 계속 사용됩니다. 닫지 마세요.**

## 주행 종료

**새 터미널을 열어 NUC에 접속한 뒤** 아래 명령어를 실행합니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_stop.sh"
```

## 주행 중 터미널 모니터링

### READY 상태 모니터링

**새 터미널을 열어 NUC에 접속한 뒤** 실행합니다.

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" watch
```

### Safety 상태 모니터링

**별도의 새 터미널을 열어 NUC에 접속한 뒤**, 아래 **두 명령어를 같은 터미널에 순서대로** 실행합니다.

```bash
source /opt/ros/noetic/setup.bash
```

```bash
python3 -u "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_safety_watch.py"
```
