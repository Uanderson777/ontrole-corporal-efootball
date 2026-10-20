import unittest
from types import SimpleNamespace

import main


def make_landmarks(shoulder_x=0.5, hip_x=0.5, shoulder_y=0.4, hip_y=0.7):
    landmarks = [SimpleNamespace(x=0.5, y=0.5, visibility=1.0) for _ in range(33)]
    pose_landmark = main.mp.tasks.vision.PoseLandmark
    points = {
        pose_landmark.LEFT_SHOULDER: (shoulder_x - 0.1, shoulder_y),
        pose_landmark.RIGHT_SHOULDER: (shoulder_x + 0.1, shoulder_y),
        pose_landmark.LEFT_HIP: (hip_x - 0.05, hip_y),
        pose_landmark.RIGHT_HIP: (hip_x + 0.05, hip_y),
    }
    for landmark, (x, y) in points.items():
        landmarks[landmark.value] = SimpleNamespace(x=x, y=y, visibility=1.0)
    return landmarks


class FakeInputBackend:
    def __init__(self):
        self.events = []

    def keyDown(self, key, _pause=False):
        self.events.append(("down", key))
        return True

    def keyUp(self, key, _pause=False):
        self.events.append(("up", key))
        return True


class TrunkTiltTests(unittest.TestCase):
    def test_calculates_neutral_torso_angle(self):
        angle = main.calculate_trunk_tilt_angle(make_landmarks())
        self.assertAlmostEqual(angle, 0.0)

    def test_calculates_left_and_right_tilt(self):
        left_angle = main.calculate_trunk_tilt_angle(
            make_landmarks(shoulder_x=0.43)
        )
        right_angle = main.calculate_trunk_tilt_angle(
            make_landmarks(shoulder_x=0.57)
        )
        self.assertLess(left_angle, 0)
        self.assertGreater(right_angle, 0)

    def test_rejects_landmarks_with_low_visibility(self):
        landmarks = make_landmarks()
        landmarks[
            main.mp.tasks.vision.PoseLandmark.LEFT_SHOULDER.value
        ].visibility = 0.1
        self.assertIsNone(main.calculate_trunk_tilt_angle(landmarks))

    def test_rejects_invalid_torso_geometry(self):
        landmarks = make_landmarks(shoulder_y=0.7, hip_y=0.4)
        self.assertIsNone(main.calculate_trunk_tilt_angle(landmarks))

    def test_applies_enter_and_exit_thresholds(self):
        self.assertEqual(
            main.classify_trunk_tilt(-12.0, "neutro"),
            "inclinado_para_esquerda",
        )
        self.assertEqual(
            main.classify_trunk_tilt(-8.0, "inclinado_para_esquerda"),
            "inclinado_para_esquerda",
        )
        self.assertEqual(
            main.classify_trunk_tilt(-7.0, "inclinado_para_esquerda"),
            "neutro",
        )


class KeyboardControllerTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeInputBackend()
        self.controller = main.KeyboardController(
            main.KEY_MAPPING,
            input_backend=self.backend,
            clock=lambda: 1.0,
        )

    def test_requires_explicit_activation(self):
        self.controller.update("inclinado_para_esquerda", True)
        self.assertEqual(self.backend.events, [])

    def test_holds_and_releases_gesture_key(self):
        self.controller.toggle()
        self.controller.update("inclinado_para_esquerda", True)
        self.controller.update("neutro", True)
        self.assertEqual(
            self.backend.events,
            [("down", "left"), ("up", "left")],
        )

    def test_emergency_stop_disables_and_releases_key(self):
        self.controller.toggle()
        self.controller.update("inclinado_para_direita", True)
        self.controller.emergency_stop()
        self.assertFalse(self.controller.enabled)
        self.assertIsNone(self.controller.pressed_key)
        self.assertEqual(
            self.backend.events,
            [("down", "right"), ("up", "right")],
        )

    def test_losing_window_focus_stops_control(self):
        self.controller.toggle()
        self.controller.update("inclinado_para_esquerda", True)
        self.controller.update("inclinado_para_esquerda", False)
        self.assertFalse(self.controller.enabled)
        self.assertEqual(
            self.backend.events,
            [("down", "left"), ("up", "left")],
        )


if __name__ == "__main__":
    unittest.main()
