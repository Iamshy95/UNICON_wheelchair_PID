#!/usr/bin/env bash
# Full PID READY session shutdown (ROS1 Noetic on NUC).
# NOT an emergency stop. Operate only after physical MANUAL / stopped check.
# Stops the bag cleanly, then ONLY the process groups recorded by this READY run.
# Does not switch or modify ~/wheelchair_deploys/current.
set -Eeuo pipefail

DEPLOY="${PID_READY_DEPLOY_DIR:-$HOME/wheelchair_deploys/ffpid-aadc8d1-20261106}"
S="$DEPLOY/source-linux/src/pid/scripts"
STATE="${PID_READY_STATE_DIR:-$HOME/.local/state/pid_ready}"
ROS_SETUP="${ROS_SETUP:-/opt/ros/noetic/setup.bash}"
: "${ROS_MASTER_URI:=http://localhost:11311}"
export ROS_MASTER_URI

fail() { echo "[FAIL] $*" >&2; exit 1; }
info() { echo "[INFO] $*"; }
ok() { echo "[OK] $*"; }

[[ "$#" == 0 ]] || fail "Usage: bash pid_ready_shutdown.sh"
[[ -f "$ROS_SETUP" ]] || fail "ROS setup missing: $ROS_SETUP"
[[ -s "$STATE/latest_run_dir" ]] || fail "No READY run recorded"
IFS= read -r RUN_DIR < "$STATE/latest_run_dir"
[[ -d "$RUN_DIR" && -f "$RUN_DIR/started_pids.tsv" ]] || fail "Missing PID list: $RUN_DIR"
[[ "$RUN_DIR" == "$HOME/pid_ready_logs/"* || -n "${PID_READY_LOG_DIR:-}" ]] ||
  fail "Unexpected RUN_DIR: $RUN_DIR"
for file in pid_stop.sh pid_drive_check.py pid_ready_bag.sh; do
  [[ -f "$S/$file" ]] || fail "Missing deployed helper: $S/$file"
done
command -v fuser >/dev/null 2>&1 || fail "Need fuser to verify shutdown"

set +u
# shellcheck disable=SC1090
source "$ROS_SETUP"
set -u

master_alive() { timeout 3 rosparam list >/dev/null 2>&1; }
node_alive() { timeout 3 rosnode ping -c1 "$1" >/dev/null 2>&1; }

# A software shutdown MUST NOT tear down hardware control during unverified motion.
# First use the physical joystick/E-stop to ensure MANUAL and stopped.
if master_alive; then
  if node_alive /ff_pid; then
    info "FF-PD active: requesting verified STOP first"
    bash "$S/pid_stop.sh" || fail "FF-PD stop verification failed; nothing was torn down"
  fi
  if node_alive /uart || node_alive /wheel_cmd || node_alive /odom_pub; then
    info "Checking MANUAL and stopped wheel feedback"
    python3 "$S/pid_drive_check.py" wheel --mode MANUAL --stopped --timeout 8 ||
      fail "Cannot verify MANUAL + stopped; nothing was torn down"
  fi
else
  # When there is no ROS Master, the wheel mode cannot be verified through ROS.
  # Refuse to kill a possibly still-live base process.
  while IFS=$'\t' read -r name pid; do
    [[ "$name" == base && "$pid" =~ ^[0-9]+$ ]] || continue
    if kill -0 "$pid" 2>/dev/null; then
      fail "ROS Master unreachable while recorded base PID $pid remains; verify physically and inspect before shutdown"
    fi
  done < "$RUN_DIR/started_pids.tsv"
  info "ROS Master absent and no recorded base process alive"
fi

# Finalize the recorder before stopping its ROS publishers and Master.
if bash "$S/pid_ready_bag.sh" status | grep -Fq '[OK] Recorder active:'; then
  info "Finalizing ROS bag"
  bash "$S/pid_ready_bag.sh" stop || fail "ROS bag did not finalize; stop and inspect it before restarting"
else
  info "ROS bag recorder already stopped"
fi

# READY starts all components with setsid; only kill verified group leaders,
# in reverse order, and never sweep all ROS processes on the machine.
while IFS=$'\t' read -r name pid; do
  [[ "$pid" =~ ^[0-9]+$ ]] || continue
  group="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d '[:space:]' || true)"
  [[ "$group" == "$pid" ]] || continue
  case "$name" in
    roscore) expected=roscore ;;
    livox|fastlio|localization|base) expected=roslaunch ;;
    geometry) expected=hybrid_geometric ;;
    fusion) expected=hybrid_object ;;
    exclusion) expected=localization_exclusion ;;
    stop_watchdog) expected=stop_watchdog ;;
    *) info "Skipping unknown process: $name"; continue ;;
  esac
  cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  [[ "$cmd" == *"$expected"* ]] || {
    info "Skipping PID $pid (process identity differs)"
    continue
  }
  info "Stopping $name (group $group)"
  kill -TERM -- "-$group"
  sleep 0.5
done < <(tac "$RUN_DIR/started_pids.tsv")

sleep 3
echo '=== READY startup lock holders ==='
if fuser -v "$STATE/start.lock"; then
  fail "A process still holds start.lock; do NOT remove the file or rerun READY"
fi
ok "READY processes and rosbag stopped; start.lock released"
