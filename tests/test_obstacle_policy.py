"""Offline safety-policy tests, no ROS hardware or motor access."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from obstacle_policy import obstacle_restriction
from receding_motion import RecedingTracks


def box(stamp, x, y=0.0, state="moving", obj_id=41):
    return {"stamp": stamp, "status": "OK", "frame": "chair_centre",
            "objects": [{"id": obj_id, "x": x, "y": y, "motion": state,
                         "size": [0.4, 0.4]}]}


class ObstaclePolicyTests(unittest.TestCase):
    def policy(self, distance, motion, receding=False):
        return obstacle_restriction(
            distance, motion, receding, 0.8, 0.4,
            static_detour_enabled=True, receding_enabled=True)

    def test_both_experimental_flags_off_preserve_legacy(self):
        original_static = obstacle_restriction(1.5, "static", False, .8, .4)
        original_receding = obstacle_restriction(1.5, "moving", True, .8, .4)
        self.assertEqual(original_static, original_receding)
        self.assertFalse(original_static[1])
        self.assertTrue(obstacle_restriction(.9, "static", False, .8, .4)[1])
        self.assertTrue(obstacle_restriction(.9, "moving", True, .8, .4)[1])

    def test_static_stops_exactly_at_two_metres(self):
        self.assertEqual(self.policy(2.0, "static"), (0.0, True, "STATIC_PATH_OBSTACLE"))
        self.assertFalse(self.policy(2.01, "static")[1])

    def test_static_stops_even_if_close(self):
        self.assertTrue(self.policy(0.8, "static")[1])

    def test_unknown_or_approaching_moving_preserves_stop(self):
        for motion in ("moving", "unknown", None):
            self.assertTrue(self.policy(0.8, motion)[1])
            self.assertLess(self.policy(1.5, motion)[0], 0.8)

    def test_receding_moving_ignores_only_one_to_two_metres(self):
        for d in (1.001, 1.5, 2.0):
            self.assertEqual(self.policy(d, "moving", True)[0], 0.8)
            self.assertFalse(self.policy(d, "moving", True)[1])

    def test_receding_moving_slows_inside_one_metre(self):
        for d in (0.4, 0.99, 1.0):
            self.assertEqual(self.policy(d, "moving", True),
                             (0.4, False, "RECEDING_NEAR_SLOW"))

    def test_not_static_receding_exempt(self):
        self.assertEqual(self.policy(1.6, "static", True)[0], 0.0)
        self.assertLess(self.policy(1.6, "unknown", True)[0], 0.8)


class RecedingMotionTests(unittest.TestCase):
    def test_qualifies_after_sustained_separation(self):
        monitor = RecedingTracks()
        for t, x in ((10.0, 1.0), (10.2, 1.08), (10.4, 1.18), (10.6, 1.27), (10.8, 1.34)):
            monitor.update(box(t, x))
        self.assertTrue(monitor.receding(41, 10.8))

    def test_one_noisy_frame_never_qualifies(self):
        monitor = RecedingTracks()
        for t, x in ((10., 1.0), (10.2, 1.4)):
            monitor.update(box(t, x))
        self.assertFalse(monitor.receding(41, 10.2))

    def test_increasing_then_closing_resets_confidence(self):
        monitor = RecedingTracks()
        for t, x in ((10., 1.), (10.2, 1.07), (10.4, 1.17),
                     (10.6, 1.27), (10.8, 1.39)):
            monitor.update(box(t, x))
        self.assertTrue(monitor.receding(41, 10.8))
        monitor.update(box(11., 1.20))
        self.assertFalse(monitor.receding(41, 11.0))

    def test_track_id_change_and_unknown_reset(self):
        monitor = RecedingTracks()
        for t, x in ((10., 1.), (10.2, 1.09), (10.4, 1.2),
                     (10.6, 1.3), (10.8, 1.4)):
            monitor.update(box(t, x))
        self.assertTrue(monitor.receding(41, 10.8))
        monitor.update(box(11.0, 1.5, obj_id=42))
        self.assertFalse(monitor.receding(41, 11.0))
        self.assertFalse(monitor.receding(42, 11.0))
        monitor.update(box(11.2, 1.6, state="unknown", obj_id=42))
        self.assertFalse(monitor.receding(42, 11.2))

    def test_static_and_stale_status_reset(self):
        monitor = RecedingTracks()
        for t, x in ((10., 1.), (10.2, 1.1), (10.4, 1.2),
                     (10.6, 1.3), (10.8, 1.4)):
            monitor.update(box(t, x))
        monitor.update(box(11.0, 1.5, state="static"))
        self.assertFalse(monitor.receding(41, 11.0))
        monitor.update({"status": "STALE", "stamp": 11.1, "frame": "chair_centre",
                        "objects": []})
        self.assertFalse(monitor.receding(41, 11.1))

    def test_stale_source_cannot_claim_receding(self):
        monitor = RecedingTracks()
        for t, x in ((10., 1.), (10.2, 1.08), (10.4, 1.18),
                     (10.6, 1.27), (10.8, 1.34)):
            monitor.update(box(t, x))
        self.assertTrue(monitor.receding(41, 10.8, now=10.8))
        self.assertFalse(monitor.receding(41, 10.8, now=11.3))

    def test_reversing_last_frames_cannot_claim_receding(self):
        monitor = RecedingTracks()
        for t, x in ((10., 1.), (10.2, 1.16), (10.4, 1.34),
                     (10.6, 1.46), (10.8, 1.43), (11.0, 1.40)):
            monitor.update(box(t, x))
        self.assertFalse(monitor.receding(41, 11.0, now=11.0))

    def test_lateral_approach_cannot_claim_receding(self):
        monitor = RecedingTracks()
        for t, x, y in ((10., 1., .5), (10.2, 1.1, .45),
                        (10.4, 1.2, .40), (10.6, 1.3, .35),
                        (10.8, 1.4, .30)):
            monitor.update(box(t, x, y=y))
        self.assertFalse(monitor.receding(41, 10.8, now=10.8))

    def test_duplicate_fusion_timestamp_is_not_extra_evidence(self):
        monitor = RecedingTracks()
        for _ in range(10):
            monitor.update(box(10.0, 1.2))
        self.assertFalse(monitor.receding(41, 10.0))


if __name__ == "__main__":
    unittest.main()
