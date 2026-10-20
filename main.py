import ctypes
import math
import os
from pathlib import Path
import time

import cv2
import mediapipe as mp
import pydirectinput


WINDOW_NAME = "Uanderson - Controle Corporal eFootball"
MODEL_NAME = "pose_landmarker_lite.task"
TILT_ENTER_ANGLE = 12.0
TILT_EXIT_ANGLE = 7.0
ANGLE_SMOOTHING = 0.25
MIN_LANDMARK_VISIBILITY = 0.5
CONTROL_TOGGLE_KEY = ord("c")
EMERGENCY_STOP_KEY = ord("x")
MIN_KEY_INTERVAL_SECONDS = 0.4
KEY_MAPPING = {
    "inclinado_para_esquerda": "left",
    "inclinado_para_direita": "right",
}


class KeyboardController:
    def __init__(
        self,
        key_mapping,
        input_backend=pydirectinput,
        clock=time.monotonic,
    ):
        self.key_mapping = key_mapping
        self.input_backend = input_backend
        self.clock = clock
        self.enabled = False
        self.pressed_key = None
        self.last_activation = float("-inf")

    def toggle(self) -> None:
        self.enabled = not self.enabled
        if not self.enabled:
            self.release_pressed_key()

    def emergency_stop(self) -> None:
        self.enabled = False
        self.release_pressed_key()

    def release_pressed_key(self) -> None:
        if self.pressed_key is not None:
            released = self.input_backend.keyUp(
                self.pressed_key,
                _pause=False,
            )
            if released is False:
                raise RuntimeError(
                    f"Nao foi possivel libertar a tecla {self.pressed_key}."
                )
            self.pressed_key = None

    def update(self, gesture: str, window_is_active: bool) -> None:
        if not window_is_active:
            self.emergency_stop()
            return

        target_key = self.key_mapping.get(gesture)
        if not self.enabled or target_key is None:
            self.release_pressed_key()
            return

        if target_key == self.pressed_key:
            return

        self.release_pressed_key()
        now = self.clock()
        if now - self.last_activation < MIN_KEY_INTERVAL_SECONDS:
            return

        self.pressed_key = target_key
        pressed = self.input_backend.keyDown(target_key, _pause=False)
        if pressed is False:
            raise RuntimeError(f"Nao foi possivel pressionar a tecla {target_key}.")
        self.last_activation = now


def is_camera_window_active() -> bool:
    if os.name != "nt":
        return False

    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p)
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    window_handle = user32.FindWindowW(None, WINDOW_NAME)
    return bool(window_handle) and user32.GetForegroundWindow() == window_handle


def key_label(key: str | None) -> str:
    return key.upper() if key is not None else "nenhuma"


def draw_control_status(
    frame,
    gesture: str,
    controller: KeyboardController,
    window_is_active: bool,
) -> None:
    expected_key = controller.key_mapping.get(gesture)
    state = "ATIVO" if controller.enabled else "DESATIVADO"
    if controller.enabled and not window_is_active:
        state += " (janela sem foco)"

    cv2.putText(
        frame,
        gesture_label(gesture),
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2,
    )
    cv2.putText(
        frame,
        f"Controle: {state} [C ativa/desativa | X emergencia]",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2,
    )
    cv2.putText(
        frame,
        f"Tecla prevista: {key_label(expected_key)} | pressionada: "
        f"{key_label(controller.pressed_key)}",
        (20, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2,
    )


def calculate_trunk_tilt_angle(landmarks) -> float | None:
    pose_landmark = mp.tasks.vision.PoseLandmark
    shoulder_indices = (
        pose_landmark.LEFT_SHOULDER,
        pose_landmark.RIGHT_SHOULDER,
    )
    hip_indices = (
        pose_landmark.LEFT_HIP,
        pose_landmark.RIGHT_HIP,
    )
    torso_landmarks = [landmarks[index] for index in (*shoulder_indices, *hip_indices)]

    for landmark in torso_landmarks:
        visibility = getattr(landmark, "visibility", None)
        if visibility is None or visibility < MIN_LANDMARK_VISIBILITY:
            return None

    shoulder_center_x = sum(landmarks[index].x for index in shoulder_indices) / 2
    hip_center_x = sum(landmarks[index].x for index in hip_indices) / 2
    shoulder_center_y = sum(landmarks[index].y for index in shoulder_indices) / 2
    hip_center_y = sum(landmarks[index].y for index in hip_indices) / 2
    torso_height = hip_center_y - shoulder_center_y

    if torso_height <= 0:
        return None

    horizontal_offset = shoulder_center_x - hip_center_x
    return math.degrees(math.atan2(horizontal_offset, torso_height))


def classify_trunk_tilt(angle: float, previous_gesture: str) -> str:
    if previous_gesture == "inclinado_para_esquerda" and angle < -TILT_EXIT_ANGLE:
        return "inclinado_para_esquerda"
    if previous_gesture == "inclinado_para_direita" and angle > TILT_EXIT_ANGLE:
        return "inclinado_para_direita"
    if angle <= -TILT_ENTER_ANGLE:
        return "inclinado_para_esquerda"
    if angle >= TILT_ENTER_ANGLE:
        return "inclinado_para_direita"
    return "neutro"


def gesture_label(gesture: str) -> str:
    labels = {
        "inclinado_para_esquerda": "Inclinacao: esquerda",
        "inclinado_para_direita": "Inclinacao: direita",
        "neutro": "Inclinacao: neutra",
    }
    return labels[gesture]


def get_model_path() -> Path:
    configured_path = os.environ.get("MEDIAPIPE_POSE_MODEL")
    if configured_path:
        return Path(configured_path).expanduser()

    local_app_data = Path(
        os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
    )
    return local_app_data / "BodyMotionControl" / "models" / MODEL_NAME


def main() -> int:
    model_path = get_model_path()
    if not model_path.is_file():
        print(
            "Erro: modelo de pose nao encontrado. "
            f"Esperado em: {model_path}"
        )
        print("Defina MEDIAPIPE_POSE_MODEL para indicar outro arquivo .task.")
        return 1

    vision = mp.tasks.vision
    pose_connections = vision.PoseLandmarksConnections.POSE_LANDMARKS

    try:
        options = vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(model_path)
            ),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        pose_detector = vision.PoseLandmarker.create_from_options(options)
    except Exception as error:
        print(f"Erro ao inicializar o detector de pose: {error}")
        return 1

    camera = None
    gesture = "neutro"
    smoothed_angle = None
    controller = KeyboardController(KEY_MAPPING)
    try:
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("Erro: nao foi possivel abrir a camera (indice 0).")
            return 1

        print("Camera iniciada. Pressione ESC para sair.")
        while True:
            success, frame = camera.read()
            if not success:
                raise RuntimeError("Nao foi possivel capturar a imagem da camera.")

            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=image_rgb,
            )
            results = pose_detector.detect(image)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks[0]
                angle = calculate_trunk_tilt_angle(landmarks)
                if angle is None:
                    gesture = "neutro"
                    smoothed_angle = None
                else:
                    smoothed_angle = (
                        angle
                        if smoothed_angle is None
                        else ANGLE_SMOOTHING * angle
                        + (1 - ANGLE_SMOOTHING) * smoothed_angle
                    )
                    gesture = classify_trunk_tilt(smoothed_angle, gesture)

                vision.drawing_utils.draw_landmarks(
                    frame,
                    landmarks,
                    pose_connections,
                )
            else:
                gesture = "neutro"
                smoothed_angle = None
                cv2.putText(
                    frame,
                    "Corpo nao detectado",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )

            window_is_active = is_camera_window_active()
            draw_control_status(frame, gesture, controller, window_is_active)
            cv2.imshow(WINDOW_NAME, frame)

            pressed_key = cv2.waitKey(1) & 0xFF
            if pressed_key == 27:
                break
            window_is_active = is_camera_window_active()
            if window_is_active:
                if pressed_key == CONTROL_TOGGLE_KEY:
                    controller.toggle()
                elif pressed_key == EMERGENCY_STOP_KEY:
                    controller.emergency_stop()
            controller.update(gesture, window_is_active)
    except Exception as error:
        print(f"Erro durante a captura ou deteccao da pose: {error}")
        return 1
    finally:
        try:
            controller.emergency_stop()
        finally:
            try:
                if camera is not None:
                    camera.release()
            finally:
                pose_detector.close()
                cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
