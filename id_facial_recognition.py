"""
Facial Recognition with Anti-Spoofing Module

Compares the photo from the ID card with a live snapshot of the user's face.
Uses FaceNet for embedding comparison and Silent-Face-Anti-Spoofing for liveness detection.

Features:
- FaceNet (InceptionResnetV1) for face embeddings
- MTCNN for face detection
- Silent-Face-Anti-Spoofing for real/fake face detection
- Rejects screen/photo attacks

Author: Priscila PINTO ICKOWICZ
"""

import cv2
import numpy as np
import logging
import torch
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from PIL import Image

# FaceNet imports
from facenet_pytorch import MTCNN, InceptionResnetV1

# Anti-spoofing import
from anti_spoofing_detector import AntiSpoofingDetector


class FacialRecognitionVerifier:
    """
    Verifies identity by comparing ID photo with live face capture.
    Includes anti-spoofing to detect screen/photo attacks.
    """

    THRESHOLD_STRICT = 1.0
    THRESHOLD_BALANCED = 1.2
    THRESHOLD_LENIENT = 1.35

    def __init__(
        self,
        camera_index: int = 0,
        similarity_threshold: float = 0.4,
        distance_threshold: float = 1.35,
        max_attempts: int = 3,
        min_face_size: int = 40,
        margin: int = 20
    ):
        """
        Initialize the facial recognition verifier with anti-spoofing.

        Args:
            camera_index: Index of the camera to use (default: 0)
            similarity_threshold: Legacy parameter for interface compatibility
            distance_threshold: Euclidean distance threshold for FaceNet
            max_attempts: Maximum number of capture attempts (default: 3)
            min_face_size: Minimum face size in pixels
            margin: Margin around detected face
        """
        self.logger = logging.getLogger(__name__)
        self.camera_index = camera_index
        self.similarity_threshold = similarity_threshold
        self.distance_threshold = distance_threshold
        self.max_attempts = max_attempts
        self.min_face_size = min_face_size
        self.margin = margin
        self.cap = None

        # Device setup
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.logger.info(f"Using device: {self.device}")

        # Initialize MTCNN
        self.logger.info("Initializing MTCNN face detector...")
        self.mtcnn = MTCNN(
            image_size=160,
            margin=margin,
            min_face_size=min_face_size,
            thresholds=[0.6, 0.7, 0.7],
            factor=0.709,
            post_process=True,
            device=self.device,
            keep_all=True  # Detect all faces to filter
        )

        # Single face detector for ID photo
        self.mtcnn_single = MTCNN(
            image_size=160,
            margin=margin,
            min_face_size=20,
            thresholds=[0.5, 0.6, 0.6],
            factor=0.709,
            post_process=True,
            device=self.device,
            keep_all=False
        )

        # Initialize FaceNet
        self.logger.info("Loading InceptionResnetV1 (VGGFace2) model...")
        self.facenet = InceptionResnetV1(
            pretrained='vggface2',
            classify=False,
            device=self.device
        ).eval()

        # Initialize Anti-Spoofing
        self.logger.info("Loading Anti-Spoofing model...")
        self.anti_spoof = AntiSpoofingDetector()

        # Output directory for snapshots
        self.output_dir = Path("outputs") / "facial_recognition"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Metrics tracking for thesis integration
        self.last_distance = 0.0
        self.last_antispoof_score = 0.0
        self.last_antispoof_is_real = False
        self.last_antispoof_time_ms = 0.0
        self.last_embedding_time_ms = 0.0

        self.logger.info("Facial recognition verifier initialized with anti-spoofing.")

    def _extract_embedding(self, image: np.ndarray, use_single: bool = False) -> Tuple[Optional[torch.Tensor], Optional[float]]:
        """Extract face embedding from an image"""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        mtcnn = self.mtcnn_single if use_single else self.mtcnn

        try:
            face_tensor, prob = mtcnn(pil_image, return_prob=True)
        except Exception as e:
            self.logger.error(f"Face detection error: {e}")
            return None, None

        if face_tensor is None:
            return None, None

        # Handle multiple faces (take highest confidence)
        if face_tensor.dim() == 4:
            face_tensor = face_tensor[0]
            prob = prob[0] if isinstance(prob, (list, np.ndarray)) else prob

        face_tensor = face_tensor.unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.facenet(face_tensor)

        return embedding, prob

    def extract_face_from_id(self, id_photo_path: Path) -> Tuple[Optional[torch.Tensor], Dict[str, Any]]:
        """Extract face embedding from ID photo"""
        metadata = {'source': 'id_photo', 'path': str(id_photo_path)}

        if not id_photo_path.exists():
            self.logger.error(f"ID photo not found: {id_photo_path}")
            return None, metadata

        id_image = cv2.imread(str(id_photo_path))
        if id_image is None:
            self.logger.error(f"Failed to load ID photo")
            return None, metadata

        embedding, prob = self._extract_embedding(id_image, use_single=True)

        if embedding is not None:
            self.logger.info(f"Face extracted from ID (confidence: {prob:.2f})")
            metadata['extraction_success'] = True
            metadata['detection_prob'] = prob
        else:
            self.logger.warning("No face detected in ID photo")
            metadata['extraction_success'] = False

        return embedding, metadata

    def verify(self, id_photo_path: Path) -> bool:
        """
        Run facial recognition with anti-spoofing.

        Process:
        1. Extract face from ID photo
        2. Open camera for live face capture
        3. Check anti-spoofing (reject screens/photos)
        4. If real face, compare with ID photo using FaceNet

        Args:
            id_photo_path: Path to the ID photo crop

        Returns:
            bool: True if live face matches ID photo AND passes anti-spoofing
        """
        # Extract embedding from ID photo
        self.logger.info(f"Loading ID photo: {id_photo_path}")
        id_embedding, id_metadata = self.extract_face_from_id(id_photo_path)

        if id_embedding is None:
            self.logger.error("Failed to extract face from ID photo")
            return False

        # Open camera
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.logger.error("Failed to open camera")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print("\n" + "="*50)
        print("FACIAL RECOGNITION + ANTI-SPOOFING")
        print("="*50)
        print("1. PUT YOUR ID CARD DOWN")
        print("2. Look at the camera with your REAL face")
        print("3. Press SPACE when ready, 'q' to cancel")
        print("="*50 + "\n")

        required_real_frames = 15
        real_face_count = 0
        match_found = False

        while True:
            ret, frame = self.cap.read()
            if not ret:
                continue

            h, w = frame.shape[:2]
            frame_area = h * w
            display = frame.copy()

            # Draw guide area
            guide_x1, guide_y1 = w // 4, 20
            guide_x2, guide_y2 = 3 * w // 4, h // 2 + 50
            cv2.rectangle(display, (guide_x1, guide_y1), (guide_x2, guide_y2), (0, 255, 0), 2)
            cv2.putText(display, "Position face here", (guide_x1, guide_y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Detect faces
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(frame_rgb)

            try:
                boxes, probs = self.mtcnn.detect(pil_frame)
            except:
                boxes, probs = None, None

            live_face_found = False
            best_box = None

            if boxes is not None and len(boxes) > 0:
                for i, box in enumerate(boxes):
                    if box is None or probs[i] < 0.9:
                        continue

                    x1, y1, x2, y2 = map(int, box)
                    face_w = x2 - x1
                    face_h = y2 - y1
                    face_area = face_w * face_h
                    face_center_y = (y1 + y2) / 2

                    # Check if it's a live face (large, upper half of frame)
                    face_ratio = face_area / frame_area
                    is_large = face_ratio > 0.08
                    is_upper = face_center_y < h * 0.65
                    is_reasonable = face_w > 100 and face_h > 100

                    if is_large and is_upper and is_reasonable:
                        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        best_box = box
                        live_face_found = True
                    else:
                        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        reason = "TOO SMALL" if not is_large else "WRONG POS"
                        cv2.putText(display, reason, (x1, y1-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            if live_face_found and best_box is not None:
                x1, y1, x2, y2 = map(int, best_box)

                # Anti-spoofing check with timing
                import time as time_module
                antispoof_start = time_module.perf_counter()
                spoof_result, _ = self.anti_spoof.detect(frame)
                self.last_antispoof_time_ms = (time_module.perf_counter() - antispoof_start) * 1000

                if spoof_result is None:
                    cv2.putText(display, "Anti-spoof: checking...", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
                elif not spoof_result.is_real:
                    # FAKE DETECTED - store metrics
                    self.last_antispoof_score = spoof_result.score
                    self.last_antispoof_is_real = False
                    real_face_count = 0  # Reset counter
                    cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.putText(display, "SCREEN/PHOTO DETECTED!", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    cv2.putText(display, f"Score: {spoof_result.score:.2f}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.putText(display, "Use your REAL face - no screens!", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                else:
                    # REAL FACE - store metrics and increment counter
                    self.last_antispoof_score = spoof_result.score
                    self.last_antispoof_is_real = True
                    real_face_count += 1
                    cv2.putText(display, f"REAL face ({real_face_count}/{required_real_frames})", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    # After enough real frames, do face matching
                    if real_face_count >= required_real_frames:
                        # Extract live face embedding with timing
                        margin = 20
                        x1_c = max(0, int(x1) - margin)
                        y1_c = max(0, int(y1) - margin)
                        x2_c = min(w, int(x2) + margin)
                        y2_c = min(h, int(y2) + margin)

                        face_crop = frame[y1_c:y2_c, x1_c:x2_c]
                        embedding_start = time_module.perf_counter()
                        live_embedding, prob = self._extract_embedding(face_crop, use_single=True)
                        self.last_embedding_time_ms = (time_module.perf_counter() - embedding_start) * 1000

                        if live_embedding is not None:
                            # Compare embeddings and store distance
                            distance = torch.dist(id_embedding, live_embedding).item()
                            self.last_distance = distance
                            is_match = distance < self.distance_threshold

                            if is_match:
                                cv2.putText(display, f"MATCH! (dist: {distance:.2f})", (10, 60),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                                cv2.putText(display, "IDENTITY VERIFIED!", (10, 90),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                                cv2.imshow("Facial Recognition", display)
                                cv2.waitKey(1000)

                                # Save snapshots
                                self._save_comparison_images(
                                    id_photo_path, frame, face_crop, display,
                                    is_match=True, distance=distance
                                )

                                match_found = True
                                break
                            else:
                                cv2.putText(display, f"NO MATCH (dist: {distance:.2f})", (10, 60),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                                real_face_count = 10  # Partial reset, try again

                                # Save failed attempt
                                self._save_comparison_images(
                                    id_photo_path, frame, face_crop, display,
                                    is_match=False, distance=distance
                                )
            else:
                cv2.putText(display, "Position your face in frame...", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)

            cv2.imshow("Facial Recognition", display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.logger.info("Cancelled by user")
                break

        self.cap.release()
        cv2.destroyAllWindows()

        if match_found:
            self.logger.info("Facial recognition PASSED with anti-spoofing")
            return True
        else:
            self.logger.warning("Facial recognition FAILED")
            return False

    def _save_comparison_images(
        self,
        id_photo_path: Path,
        live_frame: np.ndarray,
        face_crop: np.ndarray,
        display_frame: np.ndarray,
        is_match: bool,
        distance: float
    ):
        """
        Save comparison images for debugging and audit.

        Saves:
        - ID photo
        - Live frame
        - Face crop
        - Annotated display
        - Side-by-side comparison

        Args:
            id_photo_path: Path to ID photo
            live_frame: Full live camera frame
            face_crop: Cropped face from live frame
            display_frame: Annotated display frame
            is_match: Whether faces matched
            distance: Euclidean distance between embeddings
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.output_dir / timestamp
        session_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Save live frame
            live_path = session_dir / "live_frame.png"
            cv2.imwrite(str(live_path), live_frame)

            # Save face crop
            if face_crop is not None and face_crop.size > 0:
                crop_path = session_dir / "face_crop.png"
                cv2.imwrite(str(crop_path), face_crop)

            # Save annotated display
            display_path = session_dir / "display_annotated.png"
            cv2.imwrite(str(display_path), display_frame)

            # Create comparison image
            id_image = cv2.imread(str(id_photo_path))
            if id_image is not None:
                # Resize both to same height
                target_height = 300

                id_scale = target_height / id_image.shape[0]
                id_resized = cv2.resize(id_image, None, fx=id_scale, fy=id_scale)

                if face_crop is not None and face_crop.size > 0:
                    crop_scale = target_height / face_crop.shape[0]
                    crop_resized = cv2.resize(face_crop, None, fx=crop_scale, fy=crop_scale)
                else:
                    crop_resized = np.zeros((target_height, target_height, 3), dtype=np.uint8)

                # Create comparison with gap
                gap = 20
                comparison_width = id_resized.shape[1] + crop_resized.shape[1] + gap
                comparison = np.ones((target_height + 80, comparison_width, 3), dtype=np.uint8) * 255

                # Place images
                comparison[:target_height, :id_resized.shape[1]] = id_resized
                comparison[:target_height, id_resized.shape[1] + gap:id_resized.shape[1] + gap + crop_resized.shape[1]] = crop_resized

                # Add labels
                cv2.putText(comparison, "ID Photo", (10, target_height + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                cv2.putText(comparison, "Live Face", (id_resized.shape[1] + gap + 10, target_height + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                # Add result
                result_text = f"{'MATCH' if is_match else 'NO MATCH'} (dist: {distance:.2f})"
                result_color = (0, 180, 0) if is_match else (0, 0, 255)
                cv2.putText(comparison, result_text, (10, target_height + 55),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, result_color, 2)

                # Save comparison
                comparison_path = session_dir / "comparison.png"
                cv2.imwrite(str(comparison_path), comparison)

            # Save report
            report_path = session_dir / "report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("FACIAL RECOGNITION VERIFICATION REPORT\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"ID Photo: {id_photo_path}\n")
                f.write(f"Distance: {distance:.4f}\n")
                f.write(f"Threshold: {self.distance_threshold}\n")
                f.write(f"Result: {'MATCH' if is_match else 'NO MATCH'}\n\n")

                f.write("=" * 60 + "\n")

            self.logger.info(f"Comparison images saved to: {session_dir}")

        except Exception as e:
            self.logger.error(f"Failed to save comparison images: {e}")

    def cleanup(self):
        """Release resources"""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()

        if self.device.type == 'cuda':
            torch.cuda.empty_cache()


def main():
    """Test the facial recognition verifier"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     FACIAL RECOGNITION + ANTI-SPOOFING TEST               ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Find ID photo
    id_photo_path = None
    output_dir = Path("outputs")
    if output_dir.exists():
        for snapshot_dir in sorted(output_dir.glob("snapshot_*"), reverse=True):
            photos = list(snapshot_dir.glob("Photo_*.png"))
            if photos:
                id_photo_path = photos[0]
                break

    if id_photo_path is None:
        print("ERROR: No ID photo found in outputs/")
        print("Please run id_detection.py first to capture an ID photo.")
        return 1

    print(f"Using ID photo: {id_photo_path}")

    verifier = FacialRecognitionVerifier()
    is_match = verifier.verify(id_photo_path)
    verifier.cleanup()

    print("\n" + "="*50)
    if is_match:
        print("RESULT: FACE MATCHED")
        print("Identity verified with anti-spoofing protection.")
    else:
        print("RESULT: FACE NOT MATCHED OR SPOOFING DETECTED")
    print("="*50)

    return 0 if is_match else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
