"""Offline tests for the static detour planner; no ROS or motor required."""
import math
import os
import sys
import unittest

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ff_pid_core import Route
from replan_path import (astar, checked_path, footprint_free, replan,
                         static_boxes)


class SyntheticMask:
    def __init__(self):
        self.resolution = 0.1
        self.origin = np.array((-3.0, -10.0))
        self.free = np.ones((201, 301), dtype=bool)
        self.clearance = ndimage.distance_transform_edt(self.free) * self.resolution

    def _cells(self, pts):
        pts = np.asarray(pts, dtype=float).reshape(-1, 2)
        c = np.rint((pts[:, 0] - self.origin[0]) / self.resolution).astype(int)
        r = np.rint(self.free.shape[0] - 1 -
                    (pts[:, 1] - self.origin[1]) / self.resolution).astype(int)
        valid = ((r >= 0) & (r < self.free.shape[0]) &
                 (c >= 0) & (c < self.free.shape[1]))
        return r, c, valid

    def clearance_many(self, pts):
        r, c, valid = self._cells(pts)
        value = np.zeros(len(r))
        value[valid] = self.clearance[r[valid], c[valid]]
        return value

    def segment_is_contained(self, a, b):
        a, b = np.asarray(a), np.asarray(b)
        n = max(2, int(np.linalg.norm(b-a) / .02) + 2)
        return bool((self.clearance_many(np.linspace(a, b, n)) > 0).all())

    def paths_are_contained(self, paths):
        return np.asarray([all(self.segment_is_contained(a, b)
                               for a, b in zip(path[:-1], path[1:]))
                           for path in paths])


class TestReplan(unittest.TestCase):
    def test_astar_rejects_corner_cutting(self):
        free = np.asarray([[True, False], [False, True]])
        with self.assertRaises(ValueError):
            astar(free, (0, 0), (1, 1))

    def test_astar_detours_around_wall(self):
        free = np.ones((8, 10), dtype=bool)
        free[2:6, 4] = False
        cells = astar(free, (4, 1), (4, 8))
        self.assertFalse(any(not free[cell] for cell in cells))
        self.assertTrue(any(row != 4 for row, col in cells))

    def test_only_static_boxes(self):
        data = [
            {"motion": "static", "x": 1.4, "y": 0., "size": [.5, .5]},
            {"motion": "moving", "x": 2., "y": 0., "size": [.5, .5]},
            {"motion": "unknown", "x": 3., "y": 0., "size": [.5, .5]},
        ]
        self.assertEqual(len(static_boxes(data)), 1)

    def test_continuous_obstacle_inflation(self):
        boxes = [(1.5, 0., .5, .5)]
        xy = np.asarray([[1.5, .8], [1.5, 1.2]])
        result = footprint_free(xy, (0., 0., 0.), boxes, .7)
        self.assertFalse(result[0])
        self.assertTrue(result[1])

    def test_collision_validation_fails_blocked_curve(self):
        mask = SyntheticMask()
        boxes = [(1.5, 0., .5, .5)]
        blocked = np.asarray([[0., 0.], [1.5, 0.], [3., 0.]])
        self.assertFalse(checked_path(mask, blocked, (0., 0., 0.), boxes, .7))

    def test_does_not_write_original_waypoints(self):
        mask = SyntheticMask()
        xy = np.column_stack([np.linspace(0., 20., 201), np.zeros(201)])
        original = Route({
            "frame": "map", "route_key": "A_to_D5", "count": len(xy),
            "reference_point": "chair_centre", "body_frame_profile": "builtin",
            "chair_centre_in_body_xyz": [-.5, -.2, 0.],
            "waypoints": [{"x": float(x), "y": float(y), "yaw_deg": 0.}
                          for x, y in xy]
        })
        saved = np.copy(original.xy)
        obstacle = [{"id": 9, "motion": "static", "band_relation": "inside",
                     "x": 1.5, "y": 0., "size": [.5, .5]}]
        planned = replan(original, mask, (1.7, 0., 0.), 1.7, obstacle)
        self.assertEqual(planned["route_key"], "A_to_D5")
        self.assertEqual(planned["count"], len(planned["waypoints"]))
        self.assertEqual(planned["source"], "runtime_static_astar")
        self.assertTrue(np.array_equal(saved, original.xy))
        self.assertAlmostEqual(planned["waypoints"][-1]["x"], 20., places=2)
        path = np.asarray([[p["x"], p["y"]] for p in planned["waypoints"]])
        self.assertTrue(checked_path(mask, path, (1.7, 0., 0.),
                                     static_boxes(obstacle), .7))


if __name__ == "__main__":
    unittest.main()
