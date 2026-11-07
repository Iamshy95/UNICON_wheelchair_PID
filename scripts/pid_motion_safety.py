#!/usr/bin/env python3
"""Independent FF-PID route/heading safety policy; does not compute steering.

The thresholds are the existing 0.70 m and 1.50 rad limits.
Once tripped, manual DRIVE restart is required.
"""
import json
import math
import rospy
from std_msgs.msg import Bool, String

MAX_PATH_DISTANCE_M = 0.70
MAX_HEADING_ERROR_RAD = 1.50

class RouteSafety:
    def __init__(self):
        rospy.init_node('pid_motion_safety')
        self.pub = rospy.Publisher('/ff_pid/stop_request', Bool, queue_size=2, latch=True)
        self.status = rospy.Publisher('/ff_pid/safety_status', String, queue_size=2, latch=True)
        self.latched = False
        rospy.Subscriber('/ff_pid/status', String, self.on_state, queue_size=10)

    def on_state(self, msg):
        if self.latched:
            return
        try:
            state = json.loads(msg.data)
            if state.get('state') != 'RUNNING':
                return
            if 'distance' not in state or 'heading_error' not in state:
                return
            distance = float(state['distance'])
            heading = abs(float(state['heading_error']))
            predicted = float(state.get('predicted_distance', 0.0))
            if not all(map(math.isfinite, (distance, heading, predicted))):
                reason = 'INVALID_GEOMETRY'
            elif state.get('predicted_in_mask') is False:
                reason = 'PREDICTED_MASK_EXIT'
            elif distance > MAX_PATH_DISTANCE_M:
                reason = 'PATH_DISTANCE'
            elif predicted > MAX_PATH_DISTANCE_M:
                reason = 'PREDICTED_PATH_DISTANCE'
            elif heading > MAX_HEADING_ERROR_RAD:
                reason = 'HEADING_ERROR'
            else:
                return
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            reason = 'INVALID_STATUS'
        self.latched = True
        rospy.logerr('PID independent safety stop: %s', reason)
        self.pub.publish(Bool(data=True))
        self.status.publish(String(data=json.dumps({'state': 'STOP', 'reason': reason})))

if __name__ == '__main__':
    RouteSafety()
    rospy.spin()
