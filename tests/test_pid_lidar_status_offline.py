"""Offline regression tests for the non-driving MID-360 connection-test status."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pid_lidar_test.sh"


class LidarStandaloneStatusTests(unittest.TestCase):
    def call(self, directory):
        env = os.environ.copy()
        env["PID_LIDAR_TEST_STATE_DIR"] = str(directory)
        env["ROS_MASTER_URI"] = "http://127.0.0.1:11311"
        return subprocess.run(["bash", str(SCRIPT), "status"], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=8)

    def test_stopped_when_no_session(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.call(Path(td))
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["state"], "STOPPED")
            self.assertIs(payload["connection_ok"], False)

    def test_fake_cached_ok_is_rejected_after_monitor_exit(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory / "active").write_text("/tmp/old_lidar_session")
            (directory / "status.json").write_text(json.dumps({
                "timestamp": 4102444800, "state": "RUNNING",
                "lidar": "OK", "imu": "OK", "master": "RUNNING",
                "driver": "RUNNING"}))
            (directory / "monitor.pid").write_text("999999999")
            result = self.call(directory)
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["state"], "FAULT")
            self.assertEqual(payload["reason"], "MONITOR_NOT_RUNNING")
            self.assertFalse(payload["connection_ok"])

    def test_orphan_pid_detected_without_active_marker(self):
        # Stale PID files alone are not proof of a running process.
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory / "driver.pid").write_text("999999999")
            result = self.call(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["state"], "STOPPED")


if __name__ == "__main__":
    unittest.main()
