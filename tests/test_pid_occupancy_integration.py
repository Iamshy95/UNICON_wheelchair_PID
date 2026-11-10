"""Offline integrated regression: scan cells -> 2D A* -> Safety collision check,
plus 5 Hz static vote gating, repeated 10 Hz fusion stamps and disappearance.
No ROS, motor, or hardware required.
"""
import os
import sys
import unittest
import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ff_pid_core import Route
from pid_static_window import StaticVoteWindow
from pid_occupancy_geometry import OccupiedCells
from pid_occupancy_snapshot import snapshot_from_clusters
from replan_path import replan, checked_path, OBSTACLE_RADIUS_M


class OpenMask:
    resolution = .1
    origin = np.array((-5., -12.))
    def __init__(self):
        self.free = np.ones((241, 351), dtype=bool)
        self.clearance = ndimage.distance_transform_edt(self.free) * self.resolution
    def _cells(self, pts):
        pts = np.asarray(pts, dtype=float).reshape(-1, 2)
        c = np.rint((pts[:, 0] - self.origin[0]) / self.resolution).astype(int)
        r = np.rint(self.free.shape[0] - 1 - (pts[:, 1] - self.origin[1]) / self.resolution).astype(int)
        valid = ((r >= 0) & (r < self.free.shape[0]) & (c >= 0) & (c < self.free.shape[1]))
        return r, c, valid
    def clearance_many(self, pts):
        r, c, v = self._cells(pts)
        result = np.zeros(len(r), dtype=float)
        result[v] = self.clearance[r[v], c[v]]
        return result
    def paths_are_contained(self, paths):
        return np.asarray([np.all(self.clearance_many(p) > .01) for p in paths])


class IntegratedAstar(unittest.TestCase):
    def test_5hz_votes_not_double_counted_by_10hz_fusion(self):
        votes = StaticVoteWindow()
        for i in range(7):
            stamp = 100.0 + i*.2
            self.assertTrue(votes.add(stamp, [(611, "static" if i%2==0 else "moving", 3.0)]))
            self.assertFalse(votes.add(stamp, [(611, "static", 3.0)]))
        self.assertIsNone(votes.confirmed())
        votes.add(101.4, [(611, "static", 3.)])
        self.assertEqual(votes.confirmed(), 611)
        for i in range(12):
            votes.add(101.6 + i*.2, [])
        self.assertIsNone(votes.confirmed())

    def test_only_profile_5m_and_distinct_stamps(self):
        v = StaticVoteWindow()
        for i in range(10):
            v.add(200+i*.2, [(123, "static", 5.1)])
        self.assertIsNone(v.confirmed())
        for i in range(10):
            v.add(202+i*.2, [(123, "static", 4.8)])
        self.assertEqual(v.confirmed(), 123)

    def test_on_demand_snapshot_cells_and_astar_same_geometry(self):
        # Synthetic LiDAR cluster points mapped by identity transform.
        xyz = np.asarray([[3.5, -.2, .8], [3.7, 0., .8], [3.7, .2, .8],
                          [3.9, -.2, .8], [3.9, 0., .8], [3.9, .2, .8]])
        scan = snapshot_from_clusters(100., np.eye(4), [(611, xyz)])
        self.assertEqual(scan["frame"], "map")
        occupied = OccupiedCells(scan)
        self.assertTrue(occupied.has_id(611))
        self.assertFalse(occupied.free(np.asarray([[3.8, 0.]]), .5)[0])
        self.assertTrue(occupied.free(np.asarray([[3.8, 1.5]]), .5)[0])
        xs = np.linspace(0., 20., 201)
        route = Route({"frame": "map", "route_key": "A_to_D5", "count": len(xs),
                       "reference_point": "chair_centre",
                       "body_frame_profile": "builtin",
                       "chair_centre_in_body_xyz": [-.5, -.2, 0.],
                       "waypoints": [{"x": float(x), "y": 0., "yaw_deg": 0.}
                                     for x in xs]})
        meta = replan(route, OpenMask(), (0., 0., 0.), 0.,
                      [{"id": 611, "motion": "moving"}],
                      occupancy=scan, blocking_id=611)
        self.assertEqual(meta["source"], "runtime_static_astar")
        pts = np.asarray([[p["x"], p["y"]] for p in meta["waypoints"]])
        self.assertTrue(checked_path(OpenMask(), pts, (0., 0., 0.),
                                     occupied, OBSTACLE_RADIUS_M[0]))
        self.assertTrue(np.any(np.abs(pts[:, 1]) > 0.65))
        with self.assertRaisesRegex(ValueError, "blocker absent"):
            replan(route, OpenMask(), (0., 0., 0.), 0., [],
                   occupancy=scan, blocking_id=999)

    def test_no_snapshot_does_not_mean_free(self):
        with self.assertRaisesRegex(ValueError, "empty occupancy"):
            OccupiedCells({"status":"OK","frame":"map","stamp":100.,
                           "cell_m":.2,"objects":[]}).free(np.asarray([[0.,0.]]), .5)


if __name__ == "__main__":
    unittest.main()
