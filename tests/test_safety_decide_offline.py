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


if __name__ == "__main__":
    unittest.main()
