"""Offline checks for ROS bag auto processing. No ROS or wheel hardware required."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / filename)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = obj
    spec.loader.exec_module(obj)
    return obj


class MockStamp:
    def __init__(self, time):
        self.time = time

    def to_sec(self):
        return self.time


class FakeBag:
    events = []

    def __init__(self, path, mode):
        assert mode == "r"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read_messages(self, topics):
        for t, state, route in self.events:
            yield "/ff_pid/status", types.SimpleNamespace(
                data=json.dumps(dict(state=state, route=route))), MockStamp(t)


class AutoBagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.organizer = load("pid_rosbag_organize.py", "pid_organizer_test")
        cls.worker = load("pid_rosbag_auto.py", "pid_rosbag_auto_test")

    def analyze(self, events):
        FakeBag.events = events
        with patch.dict(sys.modules, {"rosbag": types.SimpleNamespace(Bag=FakeBag)}):
            return self.organizer.analyze([Path("/unused/ready.bag")])

    def test_obstacle_hold_is_same_drive(self):
        drives, details = self.analyze([
            (1, "RUNNING", "A_to_D5"),
            (5, "OBSTACLE_STOP", "A_to_D5"),
            (12, "RUNNING", "A_to_D5"),
            (19, "GOAL_REACHED", "A_to_D5"),
        ])
        self.assertEqual(len(drives), 1)
        self.assertEqual(drives[0].close, "GOAL_REACHED")
        self.assertEqual(drives[0].route, "A_to_D5")

    def test_explicit_paused_then_restart_is_two_drives(self):
        drives, details = self.analyze([
            (1, "RUNNING", "A_to_D5"),
            (5, "PAUSED", "A_to_D5"),
            (12, "RUNNING", "D5_to_A"),
            (19, "GOAL_REACHED", "D5_to_A"),
        ])
        self.assertEqual(len(drives), 2)
        self.assertEqual([d.route for d in drives], ["A_to_D5", "D5_to_A"])

    def test_unclosed_drive_is_preserved_and_reported(self):
        drives, details = self.analyze([(1, "RUNNING", "A_to_D4")])
        self.assertEqual(len(drives), 1)
        self.assertEqual(drives[0].close, "UNCLOSED")
        self.assertTrue(details["uncertain"])

    def test_live_rosbag_is_not_processed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "20261111_123456_AbCd"
            path.mkdir()
            (path / "ready_topics_0.bag").write_bytes(b"mock")
            (path / "rosbag.pid").write_text("1234")
            with patch.object(self.worker, "identity_alive", return_value=True):
                self.assertTrue(self.worker.session_busy(path))
                self.assertFalse(self.worker.pending_runs(Path(td), Path(td).parent / "out"))

    def test_completed_session_is_skipped_when_verified(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "input"
            out = Path(td) / "out"
            run = root / "20261111_123456_AbCd"
            run.mkdir(parents=True)
            source = run / "ready_topics_0.bag"
            source.write_bytes(b"mock")
            target = out / "20261111" / run.name
            target.mkdir(parents=True)
            report = {"exports_verified": True, "outputs": [], "recovery": []}
            (target / "report.json").write_text(json.dumps(report))
            (target / "auto_complete.json").write_text(json.dumps({
                "source_signature": self.worker.signature([source])}))
            self.assertEqual(self.worker.pending_runs(root, out), [])

    def test_no_source_deletion_in_organizer(self):
        source = (SCRIPTS / "pid_rosbag_organize.py").read_text()
        self.assertNotIn("--delete-safe", source)
        self.assertNotIn("src.unlink()", source)
        self.assertNotIn("os.remove(", source)


if __name__ == "__main__":
    unittest.main()
