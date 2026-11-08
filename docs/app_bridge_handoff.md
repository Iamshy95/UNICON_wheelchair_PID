# FF–PID app bridge handoff (pre-bridge interface)

This branch provides **script-level output only**. It does not implement Bluetooth transport or Android UI.

## Command-line operations (NUC)

- READY start: `bash scripts/pid_ready.sh start`
- READY shutdown: `bash scripts/pid_ready.sh stop`
- DRIVE start: `bash scripts/pid_drive.sh A_to_D5` (one of six route IDs)
- DRIVE stop: `bash scripts/pid_stop.sh`

Paths above are relative to the PID package's `scripts/` directory; in the ROS workspace they are normally `src/pid/scripts/...`. `pid_ready.sh` brings up sensors and localization only; `pid_stop.sh` leaves READY running.

Never expose `--test-clear` in an occupied-driving app. It bypasses real obstacle protection.

## Start/position contract (JSON-lines on stdout)

The DRIVE script writes ordinary operator log lines **and** machine-readable JSON lines. The future bridge must decode lines that parse as JSON objects and switch on `type`, ignoring ordinary logs. Standard error contains human-readable diagnostics.

At preflight time, the script checks a fresh GICP pose against **any station along the selected route**, using the same chair-center correction as FF–PID. Current provisional acceptance limits: distance <= 1.0 m, heading error <= 30 degrees. This check runs once per START request, not continuously.

Examples (illustrative values):

```json
{"type":"drive_preflight","route":"A_to_D5","ok":false,"reason":"POSE_NOT_ALIGNED","message":"출발 위치를 조정해주세요.","distance_m":1.4,"cte_m":-1.4,"heading_error_deg":45.0,"distance_limit_m":1.0,"heading_limit_deg":30.0,"station_m":12.0,"route_length_m":40.0,"distance_ok":false,"heading_ok":false,"turn_direction":"LEFT","turn_deg":45.0,"route_side":"LEFT","approach_m":0.4,"guidance":["먼저 MANUAL로 왼쪽 약 45.0도 회전해 경로 진행 방향을 맞추세요.","다음으로 MANUAL로 경로 쪽에 접근하세요. 경로는 진행 방향 기준 왼쪽에 있습니다. 경로까지 1.40m, 허용 범위까지 최소 0.40m 더 가까워져야 합니다."]}
```

```json
{"type":"drive_event","status":"REJECTED","reason":"SCRIPT_CHECK_FAILED","route":"A_to_D5","message":"출발 위치 점검 실패. MANUAL로 조정한 뒤 주행 시작을 다시 누르세요."}
```

- `drive_preflight.ok=false` describes the *specific* position failure and its adjustment advice; the following generic `drive_event:REJECTED` confirms that the DRIVE request did not proceed.
- `POSE_UNAVAILABLE` / `POSE_INVALID` / `CHECK_ERROR` produce a `drive_preflight` JSON result without fabricated distances or turn guidance.
- `drive_preflight.ok=true` **is not a success indication for the whole DRIVE start**. Safety, wheel feedback and START service must still pass.
- Other script-level refusals use `drive_event:REJECTED` with an explanation.

Once the FF–PID START service responds `success: true`, `pid_drive.sh` emits:

```json
{"type":"drive_event","status":"STARTED","reason":"START_CONFIRMED","route":"A_to_D5","message":"FF-PD START 서비스가 주행을 승인했습니다."}
```

**STARTED means the START service accepted the request**, not that physical movement was measured. The future bridge must also monitor `/ff_pid/status` and report live controller status separately.

After STARTED, `pid_drive.sh` remains running and watches the controller. The bridge must not wait for process exit before reporting STARTED. A separate STOP command must be able to launch `pid_stop.sh` immediately, independently of this long-running process.

## Runtime status (future bridge subscriptions)

- `/ff_pid/status` — controller `RUNNING`, `PAUSED`, `GOAL_STOPPING`, `GOAL_REACHED`, etc.
- `/pid_safety/status` — current `CLEAR` / `SLOW` / `STOP`, `reason`, `speed_limit_mps`, `route`, `stamp`.
- `/wheel_status` — actual wheel mode and feedback.
- `/fast_lio_icp/pose` — localization pose (convert to chair-center coordinates for display where appropriate).

Safety `STOP` due to an obstacle is a **temporary driving hold**, not a command to shut down READY or end the run. Manual drive stop is a separate action. Reject stale telemetry in the bridge/UI.

## UI contract

The rider screen has an always-tappable START when connected and no start request is already in progress. If the request fails, display the preflight's `guidance` (turn **first**, approach **second**) under START. If a START is accepted, replace that area with live Safety state and its reason, and show a separate DRIVE END button. The administrator screen offers READY START / READY END. The position-adjustment text is operator guidance only, not a collision-free motion instruction.

This document describes the available script interface. Bluetooth forwarding, command handling and screen changes are **not implemented** in this branch.
