"""
Anti-Spoofing Detector Wrapper
Uses Silent-Face-Anti-Spoofing model to detect real vs fake/screen

This module wraps the minivision-ai Silent-Face-Anti-Spoofing library
to detect presentation attacks (screens, printed photos).

Author: Priscila PINTO ICKOWICZ
"""

import os
import sys
import cv2
import numpy as np
import torch
from typing import Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# Add Silent-Face-Anti-Spoofing to path
SFAS_PATH = Path(__file__).parent / "Silent-Face-Anti-Spoofing"
if str(SFAS_PATH) not in sys.path:
    sys.path.insert(0, str(SFAS_PATH))

# Change working directory temporarily for imports
import os
_original_cwd = os.getcwd()
os.chdir(SFAS_PATH)

try:
    from src.anti_spoof_predict import AntiSpoofPredict
    from src.generate_patches import CropImage
    from src.utility import parse_model_name
finally:
    os.chdir(_original_cwd)


@dataclass
class SpoofResult:
    """Result of anti-spoofing detection"""
    is_real: bool
    score: float
    label: str  # "Real" or "Fake"
    inference_time_ms: float


class AntiSpoofingDetector:
    """
    Wrapper for Silent-Face-Anti-Spoofing model.

    Detects if the image shows a real face/document or a screen/printed photo.

    Usage:
        detector = AntiSpoofingDetector()
        result, annotated_frame = detector.detect(frame)
        if result.is_real:
            print("Real!")
        else:
            print("Fake/Screen detected!")
    """

    def __init__(self, device_id: int = 0):
        """
        Initialize the anti-spoofing detector.

        Args:
            device_id: GPU device ID (0 for CPU if no GPU)
        """
        self.device_id = device_id
        self.model_dir = SFAS_PATH / "resources" / "anti_spoof_models"

        # Change to SFAS directory for proper path resolution
        original_cwd = os.getcwd()
        os.chdir(SFAS_PATH)

        try:
            # Initialize predictor (needs relative paths)
            self.predictor = AntiSpoofPredict(device_id)
            self.image_cropper = CropImage()
        finally:
            os.chdir(original_cwd)

        # Check models exist
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {self.model_dir}")

        self.model_files = list(self.model_dir.glob("*.pth"))
        if not self.model_files:
            raise FileNotFoundError(f"No .pth model files found in {self.model_dir}")

        print(f"[AntiSpoofingDetector] Loaded {len(self.model_files)} models from {self.model_dir}")

    def detect(self, frame: np.ndarray) -> Tuple[Optional[SpoofResult], np.ndarray]:
        """
        Detect if frame shows real face or fake (screen/photo).

        Args:
            frame: BGR image from camera

        Returns:
            (SpoofResult, annotated_frame) or (None, frame) if no face detected
        """
        import time

        if frame is None or frame.size == 0:
            return None, frame

        # Make copy for annotation
        annotated = np.ascontiguousarray(frame.copy())

        try:
            # Detect face bounding box
            bbox = self.predictor.get_bbox(frame)

            if bbox is None or bbox[2] <= 0 or bbox[3] <= 0:
                # No face detected
                cv2.putText(annotated, "No face detected", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                return None, annotated

            # Run prediction with all models
            prediction = np.zeros((1, 3))
            start_time = time.perf_counter()

            for model_path in self.model_files:
                model_name = model_path.name
                h_input, w_input, model_type, scale = parse_model_name(model_name)

                param = {
                    "org_img": frame,
                    "bbox": bbox,
                    "scale": scale,
                    "out_w": w_input,
                    "out_h": h_input,
                    "crop": True,
                }
                if scale is None:
                    param["crop"] = False

                img = self.image_cropper.crop(**param)
                prediction += self.predictor.predict(img, str(model_path))

            inference_time = (time.perf_counter() - start_time) * 1000

            # Get result
            label_idx = np.argmax(prediction)
            score = prediction[0][label_idx] / len(self.model_files)

            is_real = (label_idx == 1)
            label = "Real" if is_real else "Fake"

            result = SpoofResult(
                is_real=is_real,
                score=float(score),
                label=label,
                inference_time_ms=inference_time
            )

            # Draw on frame
            color = (0, 255, 0) if is_real else (0, 0, 255)
            status_text = f"{label}: {score:.2f}"

            cv2.rectangle(annotated,
                         (bbox[0], bbox[1]),
                         (bbox[0] + bbox[2], bbox[1] + bbox[3]),
                         color, 2)
            cv2.putText(annotated, status_text,
                       (bbox[0], bbox[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Add header
            header_color = (0, 255, 0) if is_real else (0, 0, 255)
            header_text = "REAL DOCUMENT" if is_real else "SCREEN/PHOTO DETECTED!"
            cv2.putText(annotated, header_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, header_color, 2)
            cv2.putText(annotated, f"Score: {score:.2f} | Time: {inference_time:.0f}ms", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            return result, annotated

        except Exception as e:
            cv2.putText(annotated, f"Error: {str(e)[:50]}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return None, annotated

    def detect_document(self, frame: np.ndarray,
                        consecutive_frames: int = 5) -> Tuple[bool, float, np.ndarray]:
        """
        Convenience method for document liveness detection.

        For ID documents, we check if the detected region appears real or fake.
        Since the model is trained on faces, it may also detect face regions
        in ID photos - which is useful because:
        - Real ID card face = model sees real characteristics
        - Screen showing ID = model detects screen artifacts

        Args:
            frame: BGR image
            consecutive_frames: Not used in single-frame detection

        Returns:
            (is_real, confidence, annotated_frame)
        """
        result, annotated = self.detect(frame)

        if result is None:
            return False, 0.0, annotated

        return result.is_real, result.score, annotated


def test_with_camera():
    """Test the detector with live camera"""
    print("Initializing Anti-Spoofing Detector...")
    detector = AntiSpoofingDetector()

    cap = cv2.VideoCapture(0)
    print("Press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        result, annotated = detector.detect(frame)

        cv2.imshow("Anti-Spoofing Test", annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_with_camera()
