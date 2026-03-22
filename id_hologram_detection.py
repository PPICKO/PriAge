# """
# Hologram Detection Module for ID Card Verification
# ===================================================
# Detects holograms on ID cards using YOLOv8 to verify document authenticity.
# Follows the same patterns as id_detection.py for seamless integration.

# Usage:
#     Standalone: python hologram_detection.py [image_path]
#     Integrated: from hologram_detection import HologramDetector, HologramConfig
# """

# import os
# import sys
# import cv2
# import json
# import csv
# import logging
# from datetime import datetime
# from typing import Dict, List, Optional, Tuple
# from dataclasses import dataclass, asdict, field
# from pathlib import Path
# from ultralytics import YOLO


# # === CONFIGURATION ===
# @dataclass
# class HologramConfig:
#     """Configuration for hologram detection system"""
#     MODEL_PATH: str = r"C:\Users\branq\Desktop\thesis\test_09_12\holog_best.pt"
#     OUTPUT_DIR: str = "outputs"
#     CLASS_NAMES: List[str] = None
#     CONFIDENCE_THRESHOLD: float = 0.50  # Minimum confidence for hologram detection
#     IMGSZ: int = 640
#     SAVE_ANNOTATED: bool = True
#     SAVE_CROPS: bool = True
#     LOG_LEVEL: str = "INFO"
    
#     # Integration settings
#     REQUIRE_HOLOGRAM: bool = True  # Whether hologram detection is required for verification
#     MIN_HOLOGRAMS: int = 1  # Minimum number of holograms required
    
#     def __post_init__(self):
#         if self.CLASS_NAMES is None:
#             self.CLASS_NAMES = ["Hologram"]


# # === LOGGING SETUP ===
# def setup_hologram_logging(output_dir: str, log_level: str = "INFO") -> logging.Logger:
#     """Setup logging configuration for hologram detection"""
#     log_dir = Path(output_dir) / "logs"
#     log_dir.mkdir(parents=True, exist_ok=True)
    
#     log_file = log_dir / f"hologram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
#     # Convert string to logging level
#     numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
#     # Create a separate logger for hologram detection
#     logger = logging.getLogger("hologram_detection")
#     logger.setLevel(numeric_level)
    
#     # Clear existing handlers
#     logger.handlers.clear()
    
#     # Add handlers
#     file_handler = logging.FileHandler(log_file, encoding='utf-8')
#     file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
#     logger.addHandler(file_handler)
    
#     stream_handler = logging.StreamHandler()
#     stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
#     logger.addHandler(stream_handler)
    
#     return logger


# # === DATA MODELS ===
# @dataclass
# class HologramDetection:
#     """Single hologram detection result"""
#     confidence: float
#     bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
#     area: int = 0
    
#     def __post_init__(self):
#         x1, y1, x2, y2 = self.bbox
#         self.area = (x2 - x1) * (y2 - y1)


# @dataclass
# class HologramResult:
#     """Hologram detection result for an image"""
#     detected: bool = False
#     count: int = 0
#     detections: List[HologramDetection] = field(default_factory=list)
#     max_confidence: float = 0.0
#     avg_confidence: float = 0.0
#     status: str = "no_hologram"  # "hologram_found", "no_hologram", "error"
#     message: str = ""
    
#     def is_authentic(self, min_holograms: int = 1) -> bool:
#         """Check if document appears authentic based on hologram detection"""
#         return self.detected and self.count >= min_holograms


# # === HOLOGRAM DETECTOR ===
# class HologramDetector:
#     """Hologram detection system using YOLOv8"""
    
#     def __init__(self, config: HologramConfig = None, logger: logging.Logger = None):
#         """
#         Initialize hologram detector
        
#         Args:
#             config: HologramConfig instance (uses defaults if None)
#             logger: Logger instance (creates new one if None)
#         """
#         self.config = config or HologramConfig()
        
#         # Setup logging
#         if logger:
#             self.logger = logger
#         else:
#             self.logger = setup_hologram_logging(self.config.OUTPUT_DIR, self.config.LOG_LEVEL)
        
#         # Create output directory
#         Path(self.config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
#         # Load model
#         self.model = None
#         self._load_model()
    
#     def _load_model(self):
#         """Load YOLOv8 model"""
#         try:
#             self.logger.info(f"Loading hologram detection model from {self.config.MODEL_PATH}")
#             self.model = YOLO(self.config.MODEL_PATH)
#             self.logger.info("Hologram detection model loaded successfully")
#         except Exception as e:
#             self.logger.error(f"Failed to load hologram model: {e}")
#             raise
    
#     def detect(self, image, save_dir: Path = None) -> HologramResult:
#         """
#         Detect holograms in an image
        
#         Args:
#             image: OpenCV image (BGR format) or path to image file
#             save_dir: Directory to save detection results (optional)
            
#         Returns:
#             HologramResult with detection information
#         """
#         # Load image if path provided
#         if isinstance(image, (str, Path)):
#             image_path = Path(image)
#             if not image_path.exists():
#                 return HologramResult(
#                     status="error",
#                     message=f"Image file not found: {image_path}"
#                 )
#             image = cv2.imread(str(image_path))
#             if image is None:
#                 return HologramResult(
#                     status="error", 
#                     message=f"Failed to load image: {image_path}"
#                 )
        
#         try:
#             # Run detection
#             results = self.model(
#                 image, 
#                 imgsz=self.config.IMGSZ, 
#                 conf=self.config.CONFIDENCE_THRESHOLD,
#                 verbose=False
#             )
            
#             # Process detections
#             detections = []
#             for box in results[0].boxes:
#                 cls_id = int(box.cls[0].item())
#                 conf = float(box.conf[0].item())
#                 x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
#                 # Only process hologram class
#                 if cls_id < len(self.config.CLASS_NAMES):
#                     label = self.config.CLASS_NAMES[cls_id]
#                     if label == "Hologram":
#                         detection = HologramDetection(
#                             confidence=conf,
#                             bbox=(x1, y1, x2, y2)
#                         )
#                         detections.append(detection)
#                         self.logger.info(f"Hologram detected: {conf:.1%} confidence, area: {detection.area}px²")
            
#             # Calculate statistics
#             count = len(detections)
#             detected = count > 0
#             max_conf = max((d.confidence for d in detections), default=0.0)
#             avg_conf = sum(d.confidence for d in detections) / count if count > 0 else 0.0
            
#             # Determine status
#             if detected:
#                 status = "hologram_found"
#                 message = f"Detected {count} hologram(s) with max confidence {max_conf:.1%}"
#             else:
#                 status = "no_hologram"
#                 message = "No hologram detected on document"
            
#             result = HologramResult(
#                 detected=detected,
#                 count=count,
#                 detections=detections,
#                 max_confidence=max_conf,
#                 avg_confidence=avg_conf,
#                 status=status,
#                 message=message
#             )
            
#             # Save results if directory provided
#             if save_dir:
#                 self._save_results(image, results, result, save_dir)
            
#             return result
            
#         except Exception as e:
#             self.logger.error(f"Error during hologram detection: {e}")
#             return HologramResult(
#                 status="error",
#                 message=str(e)
#             )
    
#     def detect_from_file(self, image_path: str, output_subdir: str = None) -> HologramResult:
#         """
#         Detect holograms from an image file
        
#         Args:
#             image_path: Path to image file
#             output_subdir: Subdirectory name for outputs (auto-generated if None)
            
#         Returns:
#             HologramResult with detection information
#         """
#         image_path = Path(image_path)
        
#         # Create output directory
#         if output_subdir:
#             save_dir = Path(self.config.OUTPUT_DIR) / output_subdir
#         else:
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             save_dir = Path(self.config.OUTPUT_DIR) / f"hologram_{timestamp}"
        
#         save_dir.mkdir(parents=True, exist_ok=True)
        
#         # Load and detect
#         image = cv2.imread(str(image_path))
#         if image is None:
#             self.logger.error(f"Failed to load image: {image_path}")
#             return HologramResult(status="error", message=f"Failed to load: {image_path}")
        
#         return self.detect(image, save_dir)
    
#     def _save_results(self, image, yolo_results, result: HologramResult, save_dir: Path):
#         """Save detection results to files"""
#         save_dir = Path(save_dir)
#         save_dir.mkdir(parents=True, exist_ok=True)
        
#         # Save annotated image
#         if self.config.SAVE_ANNOTATED:
#             annotated = yolo_results[0].plot()
#             cv2.imwrite(str(save_dir / "hologram_annotated.png"), annotated)
#             self.logger.debug(f"Saved annotated image to {save_dir / 'hologram_annotated.png'}")
        
#         # Save hologram crops
#         if self.config.SAVE_CROPS:
#             for i, detection in enumerate(result.detections):
#                 x1, y1, x2, y2 = detection.bbox
#                 crop = image[y1:y2, x1:x2]
#                 crop_path = save_dir / f"hologram_{i+1}_{detection.confidence:.2f}.png"
#                 cv2.imwrite(str(crop_path), crop)
#                 self.logger.debug(f"Saved hologram crop to {crop_path}")
        
#         # Save results as JSON
#         result_dict = {
#             "detected": result.detected,
#             "count": result.count,
#             "max_confidence": result.max_confidence,
#             "avg_confidence": result.avg_confidence,
#             "status": result.status,
#             "message": result.message,
#             "detections": [
#                 {
#                     "confidence": d.confidence,
#                     "bbox": d.bbox,
#                     "area": d.area
#                 }
#                 for d in result.detections
#             ]
#         }
        
#         with open(save_dir / "hologram_result.json", "w", encoding="utf-8") as f:
#             json.dump(result_dict, f, indent=4)
        
#         # Save results as CSV
#         with open(save_dir / "hologram_result.csv", "w", newline="", encoding="utf-8") as f:
#             writer = csv.writer(f)
#             writer.writerow(["detected", "count", "max_confidence", "avg_confidence", "status"])
#             writer.writerow([
#                 result.detected, 
#                 result.count, 
#                 f"{result.max_confidence:.4f}",
#                 f"{result.avg_confidence:.4f}",
#                 result.status
#             ])
        
#         self.logger.info(f"Hologram detection results saved to {save_dir}")
    
#     def annotate_frame(self, frame, result: HologramResult) -> any:
#         """
#         Annotate a frame with hologram detection results
        
#         Args:
#             frame: OpenCV image to annotate
#             result: HologramResult from detection
            
#         Returns:
#             Annotated frame
#         """
#         annotated = frame.copy()
        
#         for detection in result.detections:
#             x1, y1, x2, y2 = detection.bbox
#             conf = detection.confidence
            
#             # Draw bounding box (green for hologram)
#             color = (0, 255, 0)  # Green
#             cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
#             # Draw label
#             label = f"Hologram {conf:.0%}"
#             (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
#             cv2.rectangle(annotated, (x1, y1 - 25), (x1 + w, y1), color, -1)
#             cv2.putText(annotated, label, (x1, y1 - 5), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
#         # Add status text
#         status_color = (0, 255, 0) if result.detected else (0, 0, 255)
#         status_text = f"Hologram: {'YES' if result.detected else 'NO'}"
#         if result.detected:
#             status_text += f" ({result.max_confidence:.0%})"
        
#         cv2.putText(annotated, status_text, (10, 60), 
#                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
#         return annotated


# # === INTEGRATION HELPER ===
# class HologramVerifier:
#     """
#     High-level verifier for integration with id_detection.py
#     Provides simple pass/fail hologram verification
#     """
    
#     def __init__(self, config: HologramConfig = None):
#         self.config = config or HologramConfig()
#         self.detector = HologramDetector(self.config)
#         self.logger = self.detector.logger
    
#     def verify(self, image, save_dir: Path = None) -> Tuple[bool, HologramResult]:
#         """
#         Verify if document has required holograms
        
#         Args:
#             image: OpenCV image or path to image file
#             save_dir: Directory to save results (optional)
            
#         Returns:
#             Tuple of (is_authentic: bool, result: HologramResult)
#         """
#         result = self.detector.detect(image, save_dir)
#         is_authentic = result.is_authentic(self.config.MIN_HOLOGRAMS)
        
#         if is_authentic:
#             self.logger.info(f"✓ Document hologram verification PASSED: {result.message}")
#         else:
#             self.logger.warning(f"✗ Document hologram verification FAILED: {result.message}")
        
#         return is_authentic, result
    
#     def verify_frame(self, frame) -> Tuple[bool, HologramResult, any]:
#         """
#         Verify hologram and return annotated frame (for live video)
        
#         Args:
#             frame: OpenCV frame from video capture
            
#         Returns:
#             Tuple of (is_authentic, result, annotated_frame)
#         """
#         result = self.detector.detect(frame)
#         is_authentic = result.is_authentic(self.config.MIN_HOLOGRAMS)
#         annotated = self.detector.annotate_frame(frame, result)
        
#         return is_authentic, result, annotated


# # === STANDALONE CLI ===
# def main():
#     """Main entry point - runs webcam hologram detection"""
#     config = HologramConfig()
#     detector = HologramDetector(config)
    
#     print("Starting webcam... Press 'q' to quit, 's' to save snapshot")
#     cap = cv2.VideoCapture(0)
    
#     if not cap.isOpened():
#         print("Error: Could not open webcam")
#         return None
    
#     last_result = None
    
#     try:
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 break
            
#             # Detect holograms
#             result = detector.detect(frame)
#             last_result = result
            
#             # Annotate frame
#             annotated = detector.annotate_frame(frame, result)
            
#             cv2.imshow("Hologram Detection", annotated)
            
#             key = cv2.waitKey(1) & 0xFF
#             if key == ord('q'):
#                 break
#             elif key == ord('s'):
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 save_dir = Path(config.OUTPUT_DIR) / f"snapshot_{timestamp}"
#                 save_dir.mkdir(parents=True, exist_ok=True)
#                 cv2.imwrite(str(save_dir / "captured.png"), frame)
#                 detector._save_results(frame, detector.model(frame, imgsz=config.IMGSZ, conf=config.CONFIDENCE_THRESHOLD, verbose=False), result, save_dir)
#                 print(f"Snapshot saved to {save_dir}")
#     finally:
#         cap.release()
#         cv2.destroyAllWindows()
    
#     return last_result


# if __name__ == "__main__":
#     main()
"""
Hologram Detection Module for ID Card Verification
===================================================
Detects holograms on ID cards using YOLOv8 to verify document authenticity.
Follows the same patterns as id_detection.py for seamless integration.

Usage:
    Standalone: python hologram_detection.py [image_path]
    Integrated: from hologram_detection import HologramDetector, HologramConfig
"""

import os
import sys
import cv2
import json
import csv
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from ultralytics import YOLO


# === CONFIGURATION ===
@dataclass
class HologramConfig:
    """Configuration for hologram detection system"""
    MODEL_PATH: str = r"C:\Users\branq\Desktop\thesis\test_09_12\holog_best.pt"
    OUTPUT_DIR: str = "outputs"
    CLASS_NAMES: List[str] = None
    CONFIDENCE_THRESHOLD: float = 0.50  # Minimum confidence for hologram detection
    IMGSZ: int = 640
    SAVE_ANNOTATED: bool = True
    SAVE_CROPS: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Area filter to reject false positives (faces, large objects)
    MIN_HOLOGRAM_AREA: int = 3000      # Minimum area in pixels² (too small = noise)
    MAX_HOLOGRAM_AREA: int = 25000     # Maximum area in pixels² (too big = fingers/false positive)
    
    # Integration settings
    REQUIRE_HOLOGRAM: bool = True  # Whether hologram detection is required for verification
    MIN_HOLOGRAMS: int = 1  # Minimum number of holograms required
    
    def __post_init__(self):
        if self.CLASS_NAMES is None:
            self.CLASS_NAMES = ["Hologram"]


# === LOGGING SETUP ===
def setup_hologram_logging(output_dir: str, log_level: str = "INFO") -> logging.Logger:
    """Setup logging configuration for hologram detection"""
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"hologram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create a separate logger for hologram detection
    logger = logging.getLogger("hologram_detection")
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Add handlers
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)
    
    return logger


# === DATA MODELS ===
@dataclass
class HologramDetection:
    """Single hologram detection result"""
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    area: int = 0
    
    def __post_init__(self):
        x1, y1, x2, y2 = self.bbox
        self.area = (x2 - x1) * (y2 - y1)


@dataclass
class HologramResult:
    """Hologram detection result for an image"""
    detected: bool = False
    count: int = 0
    detections: List[HologramDetection] = field(default_factory=list)
    max_confidence: float = 0.0
    avg_confidence: float = 0.0
    status: str = "no_hologram"  # "hologram_found", "no_hologram", "error"
    message: str = ""
    
    def is_authentic(self, min_holograms: int = 1) -> bool:
        """Check if document appears authentic based on hologram detection"""
        return self.detected and self.count >= min_holograms


# === HOLOGRAM DETECTOR ===
class HologramDetector:
    """Hologram detection system using YOLOv8"""
    
    def __init__(self, config: HologramConfig = None, logger: logging.Logger = None):
        """
        Initialize hologram detector
        
        Args:
            config: HologramConfig instance (uses defaults if None)
            logger: Logger instance (creates new one if None)
        """
        self.config = config or HologramConfig()
        
        # Setup logging
        if logger:
            self.logger = logger
        else:
            self.logger = setup_hologram_logging(self.config.OUTPUT_DIR, self.config.LOG_LEVEL)
        
        # Create output directory
        Path(self.config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        # Load model
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLOv8 model"""
        try:
            self.logger.info(f"Loading hologram detection model from {self.config.MODEL_PATH}")
            self.model = YOLO(self.config.MODEL_PATH)
            self.logger.info("Hologram detection model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load hologram model: {e}")
            raise
    
    def detect(self, image, save_dir: Path = None) -> HologramResult:
        """
        Detect holograms in an image
        
        Args:
            image: OpenCV image (BGR format) or path to image file
            save_dir: Directory to save detection results (optional)
            
        Returns:
            HologramResult with detection information
        """
        # Load image if path provided
        if isinstance(image, (str, Path)):
            image_path = Path(image)
            if not image_path.exists():
                return HologramResult(
                    status="error",
                    message=f"Image file not found: {image_path}"
                )
            image = cv2.imread(str(image_path))
            if image is None:
                return HologramResult(
                    status="error", 
                    message=f"Failed to load image: {image_path}"
                )
        
        try:
            # Run detection
            results = self.model(
                image, 
                imgsz=self.config.IMGSZ, 
                conf=self.config.CONFIDENCE_THRESHOLD,
                verbose=False
            )
            
            # Process detections
            detections = []
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                # Only process hologram class
                if cls_id < len(self.config.CLASS_NAMES):
                    label = self.config.CLASS_NAMES[cls_id]
                    if label == "Hologram":
                        detection = HologramDetection(
                            confidence=conf,
                            bbox=(x1, y1, x2, y2)
                        )
                        # Filter by area to reject false positives
                        if self.config.MIN_HOLOGRAM_AREA <= detection.area <= self.config.MAX_HOLOGRAM_AREA:
                            detections.append(detection)
                        else:
                            self.logger.debug(f"Rejected detection: area {detection.area}px² outside valid range [{self.config.MIN_HOLOGRAM_AREA}-{self.config.MAX_HOLOGRAM_AREA}]")
            
            # Calculate statistics
            count = len(detections)
            detected = count > 0
            max_conf = max((d.confidence for d in detections), default=0.0)
            avg_conf = sum(d.confidence for d in detections) / count if count > 0 else 0.0
            
            # Determine status
            if detected:
                status = "hologram_found"
                message = f"Detected {count} hologram(s) with max confidence {max_conf:.1%}"
            else:
                status = "no_hologram"
                message = "No hologram detected on document"
            
            result = HologramResult(
                detected=detected,
                count=count,
                detections=detections,
                max_confidence=max_conf,
                avg_confidence=avg_conf,
                status=status,
                message=message
            )
            
            # Save results if directory provided
            if save_dir:
                self._save_results(image, results, result, save_dir)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during hologram detection: {e}")
            return HologramResult(
                status="error",
                message=str(e)
            )
    
    def detect_from_file(self, image_path: str, output_subdir: str = None) -> HologramResult:
        """
        Detect holograms from an image file
        
        Args:
            image_path: Path to image file
            output_subdir: Subdirectory name for outputs (auto-generated if None)
            
        Returns:
            HologramResult with detection information
        """
        image_path = Path(image_path)
        
        # Create output directory
        if output_subdir:
            save_dir = Path(self.config.OUTPUT_DIR) / output_subdir
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_dir = Path(self.config.OUTPUT_DIR) / f"hologram_{timestamp}"
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Load and detect
        image = cv2.imread(str(image_path))
        if image is None:
            self.logger.error(f"Failed to load image: {image_path}")
            return HologramResult(status="error", message=f"Failed to load: {image_path}")
        
        return self.detect(image, save_dir)
    
    def _save_results(self, image, yolo_results, result: HologramResult, save_dir: Path):
        """Save detection results to files"""
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save annotated image
        if self.config.SAVE_ANNOTATED:
            annotated = yolo_results[0].plot()
            cv2.imwrite(str(save_dir / "hologram_annotated.png"), annotated)
            self.logger.debug(f"Saved annotated image to {save_dir / 'hologram_annotated.png'}")
        
        # Save hologram crops
        if self.config.SAVE_CROPS:
            for i, detection in enumerate(result.detections):
                x1, y1, x2, y2 = detection.bbox
                crop = image[y1:y2, x1:x2]
                crop_path = save_dir / f"hologram_{i+1}_{detection.confidence:.2f}.png"
                cv2.imwrite(str(crop_path), crop)
                self.logger.debug(f"Saved hologram crop to {crop_path}")
        
        # Save results as JSON
        result_dict = {
            "detected": result.detected,
            "count": result.count,
            "max_confidence": result.max_confidence,
            "avg_confidence": result.avg_confidence,
            "status": result.status,
            "message": result.message,
            "detections": [
                {
                    "confidence": d.confidence,
                    "bbox": d.bbox,
                    "area": d.area
                }
                for d in result.detections
            ]
        }
        
        with open(save_dir / "hologram_result.json", "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=4)
        
        # Save results as CSV
        with open(save_dir / "hologram_result.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["detected", "count", "max_confidence", "avg_confidence", "status"])
            writer.writerow([
                result.detected, 
                result.count, 
                f"{result.max_confidence:.4f}",
                f"{result.avg_confidence:.4f}",
                result.status
            ])
        
        self.logger.info(f"Hologram detection results saved to {save_dir}")
    
    def annotate_frame(self, frame, result: HologramResult) -> any:
        """
        Annotate a frame with hologram detection results
        
        Args:
            frame: OpenCV image to annotate
            result: HologramResult from detection
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        
        for detection in result.detections:
            x1, y1, x2, y2 = detection.bbox
            conf = detection.confidence
            
            # Draw bounding box (green for hologram)
            color = (0, 255, 0)  # Green
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"Hologram {conf:.0%}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - 25), (x1 + w, y1), color, -1)
            cv2.putText(annotated, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        # Add status text
        status_color = (0, 255, 0) if result.detected else (0, 0, 255)
        status_text = f"Hologram: {'YES' if result.detected else 'NO'}"
        if result.detected:
            status_text += f" ({result.max_confidence:.0%})"
        
        cv2.putText(annotated, status_text, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        return annotated


# === INTEGRATION HELPER ===
class HologramVerifier:
    """
    High-level verifier for integration with id_detection.py
    Provides simple pass/fail hologram verification
    """
    
    def __init__(self, config: HologramConfig = None):
        self.config = config or HologramConfig()
        self.detector = HologramDetector(self.config)
        self.logger = self.detector.logger
    
    def verify(self, image, save_dir: Path = None) -> Tuple[bool, HologramResult]:
        """
        Verify if document has required holograms
        
        Args:
            image: OpenCV image or path to image file
            save_dir: Directory to save results (optional)
            
        Returns:
            Tuple of (is_authentic: bool, result: HologramResult)
        """
        result = self.detector.detect(image, save_dir)
        is_authentic = result.is_authentic(self.config.MIN_HOLOGRAMS)
        
        if is_authentic:
            self.logger.info(f"✓ Document hologram verification PASSED: {result.message}")
        else:
            self.logger.warning(f"✗ Document hologram verification FAILED: {result.message}")
        
        return is_authentic, result
    
    def verify_frame(self, frame) -> Tuple[bool, HologramResult, any]:
        """
        Verify hologram and return annotated frame (for live video)
        
        Args:
            frame: OpenCV frame from video capture
            
        Returns:
            Tuple of (is_authentic, result, annotated_frame)
        """
        result = self.detector.detect(frame)
        is_authentic = result.is_authentic(self.config.MIN_HOLOGRAMS)
        annotated = self.detector.annotate_frame(frame, result)
        
        return is_authentic, result, annotated


# === STANDALONE CLI ===
def main():
    """Main entry point - runs webcam hologram detection with auto-snapshot"""
    config = HologramConfig()
    config.CONFIDENCE_THRESHOLD = 0.25  # Low threshold for display, high for snapshot
    
    detector = HologramDetector(config)
    logger = detector.logger
    
    SNAPSHOT_THRESHOLD = 0.80  # Auto-snapshot when confidence >= 80%
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        logger.error("Could not open webcam")
        return None
    
    logger.info("Webcam started. Press 'q' to quit.")
    logger.info(f"Snapshot triggers when Hologram confidence >= {SNAPSHOT_THRESHOLD:.0%}")
    
    snapshot_taken = False
    last_result = None
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Could not read from webcam")
                break
            
            # Only run detection if snapshot not yet taken
            if not snapshot_taken:
                # Detect holograms
                result = detector.detect(frame)
                last_result = result
                
                # Check if we should take snapshot (hologram >= 80%)
                if result.detected and result.max_confidence >= SNAPSHOT_THRESHOLD:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_dir = Path(config.OUTPUT_DIR) / f"hologram_{timestamp}"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save captured frame
                    cv2.imwrite(str(save_dir / "captured.png"), frame)
                    
                    # Save detection results
                    yolo_results = detector.model(frame, imgsz=config.IMGSZ, conf=config.CONFIDENCE_THRESHOLD, verbose=False)
                    detector._save_results(frame, yolo_results, result, save_dir)
                    
                    snapshot_taken = True
                    logger.info(f"✓ Snapshot saved to {save_dir}")
                    logger.info(f"✓ Hologram detected: {result.max_confidence:.1%} confidence")
                    logger.info("Press 'q' to quit.")
                
                # Annotate frame with detection
                annotated = detector.annotate_frame(frame, result)
                
                # Add status overlay
                if result.detected:
                    conf_color = (0, 255, 0) if result.max_confidence >= SNAPSHOT_THRESHOLD else (0, 255, 255)
                    status_text = f"Hologram: {result.max_confidence:.0%}"
                else:
                    conf_color = (0, 0, 255)
                    status_text = "Hologram: NOT DETECTED"
                
                cv2.putText(annotated, status_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, conf_color, 2)
                cv2.putText(annotated, f"Waiting for >= {SNAPSHOT_THRESHOLD:.0%} confidence...", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                # Snapshot already taken - just show frame with success message
                annotated = frame.copy()
                cv2.putText(annotated, "SNAPSHOT SAVED", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(annotated, f"Hologram: {last_result.max_confidence:.0%} confidence", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(annotated, "Press 'q' to quit", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow("Hologram Detection", annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        logger.info("Webcam session ended")
        if snapshot_taken:
            logger.info("✓ Session completed successfully")
        else:
            logger.info("✗ Session ended without hologram detection")
    
    return last_result


if __name__ == "__main__":
    main()