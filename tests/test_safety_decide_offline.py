"""Exercise the real Safety.decide method without ROS or a running wheelchair.

Mock only external ROS packages and mask resource loading. This makes the
test exercise the same obstacle aggregation code that emits STOP/SLOW/CLEAR.
"""
import importlib
import os
import sys
import types
import unittest

import numpy as np

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)


def install_ros_import_stubs():
    rospy = types.ModuleType("rospy")
    rospy.ROSInitException = RuntimeError
    sys.modules["rospy"] = rospy
    rospkg = types.ModuleType("rospkg")
    rospkg.RosPack = lambda: types.SimpleNamespace(get_path=lambda pkg: os.path.dirname(SCRIPTS))
    sys.modules["rospkg"] = rospkg

    tf = types.ModuleType("tf")
    tf.__path__ = []
    trans = types.ModuleType("tf.transformations")
    tf.transformations = trans
    sys.modules["tf"], sys.modules["tf.transformations"] = tf, trans

    for modname, classnames in (
        ("geometry_msgs.msg", ["PoseWithCovarianceStamped"]),
        ("nav_msgs.msg", ["Odometry"]),
        ("std_msgs.msg", ["String", "Int16MultiArray"]),
    ):
        pkg, _ = modname.split(".")
        module = types.ModuleType(modname)
        for name in classnames:
            setattr(module, name, type(name, (), {}))
        root = types.ModuleType(pkg)
        root.__path__ = []
        root.msg = module
        sys.modules[pkg], sys.modules[modname] = root, module

    body = types.ModuleType("body_frame")
    body.pose_correction = lambda *args: np.eye(4)
    body.reference_correction = lambda *args: np.eye(4)
    body.route_chair_centre = lambda *args: (0., 0., 0.)
    body.REFERENCE_CHAIR_CENTRE = "chair_centre"
    sys.modules["body_frame"] = body

    assets = types.ModuleType("route_assets")
    assets.mask_image_path = lambda p: p
    assets.route_content_sha256 = lambda meta: "unused"
    assets.sha256 = lambda path: "unused"
    sys.modules["route_assets"] = assets

    route_mask = types.ModuleType("route_mask")
    route_mask.RouteMask = lambda p: None
    sys.modules["route_mask"] = route_mask


install_ros_import_stubs()
from ff_pid_core import Route
from pid_static_window import StaticVoteWindow
Safety = importlib.import_module("pid_safety").Safety


class ConstantClearanceMask:
    def clearance_at(self, point):
        return 2.0


class Receding:
    def __init__(self, value):
        self.value = value

    def receding(self, object_id, stamp, now=None):
        return self.value


def straight_route():
    x = np.linspace(0, 10, 101)
    return Route({"frame": "map", "count": len(x),
                  "waypoints": [{"x": float(q), "y": 0., "yaw_deg": 0.}
                                for q in x]})


def obj(object_id, x, motion):
    return {"id": object_id, "x": x, "y": 0., "size": [.2, .2],
            "profile": {"bin_m": .2, "y0": -.1, "min_x": [x-.1]},
            "motion": motion, "band_relation": "inside"}


def decide(items, astar=False, receding=False, moving_away=False):
    safety = Safety.__new__(Safety)
    safety.route = straight_route()
    safety.station = None
    safety.mask = ConstantClearanceMask()
    safety.enable_replan = astar
    safety.enable_receding = receding
    safety.receding_tracks = Receding(moving_away)
    safety.static_votes = StaticVoteWindow()
    safety.bump_stations = []  # No mapped speed bumps in the synthetic straight route.
    summary = {"stamp": 100.0, "status": "OK", "frame": "chair_centre",
               "objects": items}
    return safety.decide(100.0, (0., 0., 0.), None, None, summary, 100.0)


class ActualSafetyAggregation(unittest.TestCase):
    def test_static_two_metre_stop_with_astar_enabled(self):
        state, cap, reason, info = decide([obj(7, 2.5, "static")], astar=True)
        self.assertEqual((state, cap, reason), ("STOP", 0., "PATH_OBSTACLE"))
        self.assertEqual(info["obstacle_id"], 7)

    def test_original_slow_when_astar_off(self):
        state, cap, _, _ = decide([obj(7, 2.5, "static")], astar=False)
        self.assertEqual(state, "SLOW")
        self.assertGreater(cap, 0.)

    def test_receding_moving_skips_slow_in_one_to_two_metre_band(self):
        state, cap, _, info = decide([obj(7, 2.5, "moving")],
                                     receding=True, moving_away=True)
        self.assertEqual((state, cap), ("CLEAR", 0.8))
        self.assertEqual(info["receding_ignored_ids"], [7])

    def test_receding_moving_slow_inside_one_metre(self):
        state, cap, _, _ = decide([obj(7, 1.5, "moving")],
                                  receding=True, moving_away=True)
        self.assertEqual((state, cap), ("SLOW", 0.4))

    def test_close_object_always_stops(self):
        state, cap, reason, _ = decide([obj(7, .8, "moving")],
                                        receding=True, moving_away=True)
        self.assertEqual((state, cap, reason), ("STOP", 0., "VERY_CLOSE_OBJECT"))

    def test_approaching_object_overrides_receding_one(self):
        state, cap, reason, info = decide([
            obj(7, 2.4, "moving"), obj(8, 1.55, "moving")
        ], receding=True, moving_away=False)
        self.assertEqual((state, cap, reason), ("STOP", 0., "PATH_OBSTACLE"))
        self.assertEqual(info["obstacle_id"], 8)

    def test_static_stop_overrides_receding_clear(self):
        state, cap, reason, info = decide([
            obj(7, 2.5, "moving"), obj(8, 2.6, "static")
        ], astar=True, receding=True, moving_away=True)
        self.assertEqual((state, cap, reason), ("STOP", 0., "PATH_OBSTACLE"))
        self.assertEqual(info["obstacle_id"], 8)

    def test_aabb_does_not_trigger_false_very_close_stop(self):
        item = obj(7, 2.5, "moving")
        # Fake a huge cluster bounding box covering the wheelchair;
        # its actual profile remains 2.5m ahead.
        item["x"] = .3
        item["size"] = [10., 9.]
        state, cap, reason, _ = decide([item])
        self.assertNotEqual(reason, "VERY_CLOSE_OBJECT")
        self.assertNotEqual(state, "STOP")

    def test_missing_profile_fails_closed_without_aabb_fallback(self):
        item = obj(7, 2.5, "moving")
        item.pop("profile")
        state, cap, reason, _ = decide([item])
        self.assertEqual((state, cap, reason),
                         ("STOP", 0., "BAD_OBJECT_PROFILE"))

    def test_unknown_never_exempted(self):
        state, cap, _, _ = decide([obj(7, 1.5, "unknown")],
                                  receding=True, moving_away=True)
        self.assertEqual((state, cap), ("STOP", 0.))


class ReplanFailureRecovery(unittest.TestCase):
    """A* failure must not latch STOP after the original path is obstacle-free."""

    @staticmethod
    def failed_safety():
        safety = Safety.__new__(Safety)
        safety.enable_replan = True
        safety.route_version = "original"
        safety.replan_mode = "FAILED"
        safety.replan_id = "failed-detour"
        safety.replan_error = "NO_PATH"
        safety.replan_clear_since = None
        safety.replan_candidate = None
        safety.replan_obstacle_id = 7
        safety.replan_started = None
        safety.replan_stage_sent_at = None
        safety.replan_pose = (0., 0., 0.)
        safety.replan_occupancy = None
        safety.station = 0.
        safety.static_votes = StaticVoteWindow()
        return safety

    @staticmethod
    def fresh(now):
        return {"status": "OK", "frame": "chair_centre",
                "stamp": now, "objects": []}

    def step(self, safety, now, state, obstacle_distance=None, objects=None):
        safety.update_replan(
            now, state, "CURVATURE_LIMIT" if state == "SLOW" else "NO_RESTRICTION",
            (0., 0., 0.), {"obstacle_distance_m": obstacle_distance},
            self.fresh(now) if objects is None else objects)

    def test_failed_astar_recovers_after_continuous_obstacle_free_slow(self):
        safety = self.failed_safety()
        self.step(safety, 10., "SLOW")
        self.step(safety, 10.5, "SLOW")
        self.assertEqual(safety.replan_mode, "FAILED")
        self.step(safety, 10.61, "SLOW")
        self.assertEqual(safety.replan_mode, "IDLE")
        self.assertIsNone(safety.replan_error)

    def test_obstacle_presence_and_stop_reset_recovery_timer(self):
        safety = self.failed_safety()
        self.step(safety, 10., "SLOW")
        self.step(safety, 10.3, "SLOW", obstacle_distance=2.)
        self.assertIsNone(safety.replan_clear_since)
        self.step(safety, 10.7, "SLOW")
        self.step(safety, 11., "STOP")
        self.assertEqual(safety.replan_mode, "FAILED")
        self.assertIsNone(safety.replan_clear_since)
        self.step(safety, 11.1, "SLOW")
        self.step(safety, 11.6, "SLOW")
        self.assertEqual(safety.replan_mode, "FAILED")
        self.step(safety, 11.71, "SLOW")
        self.assertEqual(safety.replan_mode, "IDLE")

    def test_stale_perception_cannot_clear_failed_astar(self):
        safety = self.failed_safety()
        self.step(safety, 10., "SLOW")
        stale = {"status": "OK", "frame": "chair_centre",
                 "stamp": 10., "objects": []}
        self.step(safety, 11.1, "SLOW", objects=stale)
        self.assertEqual(safety.replan_mode, "FAILED")
        self.assertIsNone(safety.replan_clear_since)

    def test_nonblocking_slow_is_not_a_stop_condition(self):
        safety = self.failed_safety()
        self.step(safety, 5., "SLOW")
        self.step(safety, 5.61, "SLOW")
        self.assertEqual(safety.replan_mode, "IDLE")


if __name__ == "__main__":
    unittest.main()
