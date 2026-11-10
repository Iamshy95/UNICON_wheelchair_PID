# On-demand 2-D occupancy + early static A* (2026-11-10)

## Where the code lives
The personal repository contains all new PID files, but **the live geometric
perception node belongs to the TEAM repository**. This is intentionally NOT a
personal-repository-only deployment.

- PID code: `scripts/pid_safety.py`, `scripts/replan_path.py`,
  `scripts/pid_astar_planner.py`
- Shared occupied-cell geometry: `scripts/pid_occupancy_geometry.py`
- New-observation vote counter: `scripts/pid_static_window.py`
- On-demand service implementation: `scripts/pid_occupancy_snapshot.py`
- Installer that patches only the running team's existing geometric node:
  `scripts/pid_install_occupancy_hook.py`
- READY's geometric node: `src/static_livox_localization/scripts/obstacle_clusters.py`
  (actually instantiated by `hybrid_geometric_objects.py`).
- The normal perception fusion and ground filtering remain untouched.

## Deployment order (USER owns the team push)
1. AI commits only to `Iamshy95/UNICON_wheelchair_PID` main.
2. User pulls personal repository, copies changed PID scripts into local TEAM
   `src/pid/scripts/`; copy tests separately if desired.
3. In the **local team repository root**, run:

   ```bash
   python3 src/pid/scripts/pid_install_occupancy_hook.py .
   python3 -m py_compile src/static_livox_localization/scripts/obstacle_clusters.py
   bash -n src/pid/scripts/pid_drive.sh src/pid/scripts/pid_ready_bag.sh
   ```

   The installer checks exact source anchors, refuses unexpected layouts, and
   modifies only the team perception file in-place. Do this **after** incorporating
   separate ground-filter edits. The installer is idempotent. Inspect `git diff`
   before pushing. Do not replace the whole perception file with an older copy.
4. User commits/pushes their local TEAM `feature/ffpid` when satisfied.
5. Restart READY/perception to register service, confirm
   `rosservice info /perception/pid_occupancy_snapshot`.
6. Start DRIVE only for unmanned, controlled testing with manual stop available.
   DRIVE with A* enabled refuses to start if occupancy service is unavailable.

## Behaviour
- Existing perception 5 Hz; fused summaries 10 Hz; Safety 10 Hz.
- On the original route, watch profiles of objects blocking the next 5.0 m.
- Count only NEW geometric-source timestamps, not duplicate 10 Hz fusion frames.
- Initial static suspicion: >=8 distinct observations in a 2-second rolling
  window, >=50% classified static. Moving/unknown votes remain in denominator.
- Confirmed static candidate: STOP early, then physical wheel stop check before
  requesting planning. Existing 2 m static stop, near collision stop and dynamic
  policy remain active before the confirmation threshold.
- Do not let a single moving/static flip cancel planning. Revert to original
  route only after 0.6 s of consistently CLEAR original-route decisions.
- A* worker requests a fresh snapshot via ROS1 Trigger service, rather than
  continuously publishing the occupied cells.
- Snapshot contains 20 cm **occupied squares** keyed by existing cluster ID,
  transformed into map coordinates with the same synchronized map pose as the
  geometric detector. The geometric cluster cache is updated at 5 Hz.
- A* planner and Safety revalidator use the exact same snapshot collision
  implementation; the existing 0.50/0.60/0.70 m collision radii have NOT been
  augmented by a second chassis radius.
- Profile-based Safety removes synthetic AABB sample points for geometric
  detections. AABB is still retained in detection/tracking/RViz, and as
  conservative fallback for legacy/learned-only detections lacking profiles.
- Missing, stale, malformed occupancy: the A* worker refuses the plan; Safety
  keeps STOP. The original route assets remain immutable.
- Normal ROS bag now includes the A* handshake topics, not just controller
  status. The occupancy service response is mirrored in the A* candidate
  diagnostic message during a replan.

## Verification and limits
- Syntax and ROS-free tests: GitHub Actions workflow
  `Static A-Star Replan (offline)`, including one end-to-end synthetic
  cluster -> occupied cells -> detour -> Safety geometry regression.
- Historical 2026-11-09 rosbag DOES NOT contain raw LiDAR pointcloud or an
  already-running occupancy service. It cannot prove that the new service,
  online compute load, or actual wheelchair replanning succeeds.
- NO ROS1/NUC/physical motor tests have been run remotely by this AI.
- Handoff requires checking the independent floor false-detection changes in
  the local TEAM checkout before applying the hook.
- Detection beyond the current observed field of view stays uncertain; do not
  assume an unobserved future path is automatically safe.
