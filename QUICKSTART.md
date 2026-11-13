# FF–PID QUICKSTART

## READY 시작

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" start
```

## READY 상태 확인

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" status
```

## READY 종료

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" stop
```

## 주행 시작

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_drive.sh" A_to_D5
```

## 주행 종료

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_stop.sh"
```

## 주행 중 터미널 모니터링

### READY 상태 모니터링

```bash
bash "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_ready.sh" watch
```

### Safety 상태 모니터링

```bash
source /opt/ros/noetic/setup.bash
```

```bash
python3 -u "$HOME/wheelchair_deploys/ffpid/source-linux/src/pid/scripts/pid_safety_watch.py"
```
