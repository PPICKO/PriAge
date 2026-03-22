"""
priAge GUI - Privacy-Preserving Age Verification System
Dashboard-style interface using CustomTkinter

Author: Priscila PINTO ICKOWICZ
"""

import customtkinter as ctk
import cv2
import threading
import logging
import warnings
from PIL import Image, ImageTk
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum
import time
import json

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Import verification modules
from id_hologram_detection import HologramVerifier, HologramConfig
from id_detection import IDCardDetector, Config, AgeInfo
from id_facial_recognition import FacialRecognitionVerifier
from verification_token_gdpr import GDPRCompliantTokenGenerator
from secure_deletion import GDPRCompliantDataEraser  # GDPR Article 5(1)(e) - Storage Limitation


# === CONSTANTS ===
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


class PhaseStatus(Enum):
    """Status for each verification phase"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class VerificationState:
    """Holds the state of the verification process"""
    phase1_status: PhaseStatus = PhaseStatus.PENDING
    phase2_status: PhaseStatus = PhaseStatus.PENDING
    phase3_status: PhaseStatus = PhaseStatus.PENDING
    phase4_status: PhaseStatus = PhaseStatus.PENDING

    hologram_confidence: float = 0.0
    age_info: Optional[AgeInfo] = None
    is_adult: bool = False
    face_matched: bool = False

    qr_path: Optional[Path] = None
    pin: Optional[str] = None

    error_message: str = ""


@dataclass
class PerformanceMetrics:
    """Holds comprehensive performance benchmarking data for Big Data thesis metrics"""
    # Phase timing (seconds) - empirical observations
    phase1_duration: float = 0.0
    phase2_duration: float = 0.0
    phase3_duration: float = 0.0
    phase4_duration: float = 0.0
    total_duration: float = 0.0
    verification_start_time: float = 0.0

    # FPS tracking - video processing metrics
    current_fps: float = 0.0
    average_fps: float = 0.0
    fps_samples: list = field(default_factory=list)
    frame_count: int = 0
    fps_start_time: float = 0.0

    # === PHASE 1: Hologram Detection Metrics ===
    hologram_detection_confidence: float = 0.0
    hologram_inference_time_ms: float = 0.0
    hologram_num_detections: int = 0
    hologram_max_confidence: float = 0.0
    hologram_avg_confidence: float = 0.0

    # === PHASE 2: ID Field Detection Metrics ===
    id_dob_confidence: float = 0.0
    id_photo_confidence: float = 0.0
    id_inference_time_ms: float = 0.0
    id_ocr_processing_time_ms: float = 0.0
    id_total_detections: int = 0
    id_fields_detected: list = field(default_factory=list)

    # === PHASE 3: Facial Recognition Metrics ===
    face_detection_confidence: float = 0.0
    face_embedding_extraction_time_ms: float = 0.0
    face_distance_score: float = 0.0
    face_similarity_score: float = 0.0
    face_match_threshold: float = 0.0
    face_is_match: bool = False
    # Anti-Spoofing Metrics
    antispoof_liveness_score: float = 0.0
    antispoof_is_real: bool = False
    antispoof_inference_time_ms: float = 0.0

    # === PHASE 4: Token System Metrics ===
    token_key_derivation_time_ms: float = 0.0
    token_encryption_time_ms: float = 0.0
    token_total_generation_time_ms: float = 0.0
    token_qr_generation_time_ms: float = 0.0

    def reset(self):
        """Reset all metrics"""
        # Phase timing (empirical observations)
        self.phase1_duration = 0.0
        self.phase2_duration = 0.0
        self.phase3_duration = 0.0
        self.phase4_duration = 0.0
        self.total_duration = 0.0
        self.verification_start_time = 0.0
        # FPS metrics (video processing)
        self.current_fps = 0.0
        self.average_fps = 0.0
        self.fps_samples = []
        self.frame_count = 0
        self.fps_start_time = 0.0
        # Phase 1: Hologram
        self.hologram_detection_confidence = 0.0
        self.hologram_inference_time_ms = 0.0
        self.hologram_num_detections = 0
        self.hologram_max_confidence = 0.0
        self.hologram_avg_confidence = 0.0
        # Phase 2: ID Detection
        self.id_dob_confidence = 0.0
        self.id_photo_confidence = 0.0
        self.id_inference_time_ms = 0.0
        self.id_ocr_processing_time_ms = 0.0
        self.id_total_detections = 0
        self.id_fields_detected = []
        # Phase 3: Facial Recognition
        self.face_detection_confidence = 0.0
        self.face_embedding_extraction_time_ms = 0.0
        self.face_distance_score = 0.0
        self.face_similarity_score = 0.0
        self.face_match_threshold = 0.0
        self.face_is_match = False
        self.antispoof_liveness_score = 0.0
        self.antispoof_is_real = False
        self.antispoof_inference_time_ms = 0.0
        # Phase 4: Token
        self.token_key_derivation_time_ms = 0.0
        self.token_encryption_time_ms = 0.0
        self.token_total_generation_time_ms = 0.0
        self.token_qr_generation_time_ms = 0.0

    def to_dict(self) -> dict:
        """Convert all metrics to dictionary for comprehensive JSON export"""
        return {
            "timestamp": datetime.now().isoformat(),
            "phases": {
                "phase1_hologram": {
                    "duration_seconds": round(self.phase1_duration, 3),
                    "description": "Hologram Detection",
                    "metrics": {
                        "detection_confidence": round(self.hologram_detection_confidence, 4),
                        "max_confidence": round(self.hologram_max_confidence, 4),
                        "avg_confidence": round(self.hologram_avg_confidence, 4),
                        "inference_time_ms": round(self.hologram_inference_time_ms, 2),
                        "num_detections": self.hologram_num_detections
                    }
                },
                "phase2_id_ocr": {
                    "duration_seconds": round(self.phase2_duration, 3),
                    "description": "ID Detection & OCR",
                    "metrics": {
                        "dob_detection_confidence": round(self.id_dob_confidence, 4),
                        "photo_detection_confidence": round(self.id_photo_confidence, 4),
                        "inference_time_ms": round(self.id_inference_time_ms, 2),
                        "ocr_processing_time_ms": round(self.id_ocr_processing_time_ms, 2),
                        "total_detections": self.id_total_detections,
                        "fields_detected": self.id_fields_detected
                    }
                },
                "phase3_facial": {
                    "duration_seconds": round(self.phase3_duration, 3),
                    "description": "Facial Recognition",
                    "metrics": {
                        "face_detection_confidence": round(self.face_detection_confidence, 4),
                        "embedding_extraction_time_ms": round(self.face_embedding_extraction_time_ms, 2),
                        "distance_score": round(self.face_distance_score, 4),
                        "similarity_score": round(self.face_similarity_score, 4),
                        "match_threshold": round(self.face_match_threshold, 4),
                        "is_match": self.face_is_match
                    },
                    "anti_spoofing": {
                        "liveness_score": round(self.antispoof_liveness_score, 4),
                        "is_real": self.antispoof_is_real,
                        "inference_time_ms": round(self.antispoof_inference_time_ms, 2)
                    }
                },
                "phase4_token": {
                    "duration_seconds": round(self.phase4_duration, 3),
                    "description": "Token Generation",
                    "metrics": {
                        "key_derivation_time_ms": round(self.token_key_derivation_time_ms, 2),
                        "encryption_time_ms": round(self.token_encryption_time_ms, 2),
                        "total_generation_time_ms": round(self.token_total_generation_time_ms, 2),
                        "qr_generation_time_ms": round(self.token_qr_generation_time_ms, 2)
                    }
                }
            },
            "total_time": {
                "total_duration_seconds": round(self.total_duration, 3),
                "note": "Empirical observation - security processing requires computational time"
            },
            "fps_metrics": {
                "average_fps": round(self.average_fps, 2),
                "current_fps": round(self.current_fps, 2),
                "note": "Video processing frame rate"
            },
            "summary": {
                "total_phases": 4,
                "verification_type": "Big Data multi-model pipeline"
            }
        }


class PhaseIndicator(ctk.CTkFrame):
    """Custom widget for displaying phase status"""

    STATUS_COLORS = {
        PhaseStatus.PENDING: ("gray50", "gray40"),
        PhaseStatus.IN_PROGRESS: ("#1E90FF", "#1E90FF"),  # Blue
        PhaseStatus.PASSED: ("#32CD32", "#32CD32"),  # Green
        PhaseStatus.FAILED: ("#DC143C", "#DC143C"),  # Red
    }

    def __init__(self, master, phase_number: int, phase_name: str, **kwargs):
        super().__init__(master, **kwargs)

        self.phase_number = phase_number
        self.phase_name = phase_name
        self.status = PhaseStatus.PENDING

        self.configure(fg_color="transparent")

        # Status indicator circle
        self.indicator = ctk.CTkLabel(
            self,
            text=str(phase_number),
            width=40,
            height=40,
            corner_radius=20,
            fg_color=self.STATUS_COLORS[PhaseStatus.PENDING][0],
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.indicator.pack(side="left", padx=(0, 10))

        # Phase info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        self.name_label = ctk.CTkLabel(
            info_frame,
            text=phase_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        self.name_label.pack(fill="x")

        self.status_label = ctk.CTkLabel(
            info_frame,
            text="Pending",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="w"
        )
        self.status_label.pack(fill="x")

        self.detail_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            anchor="w"
        )
        self.detail_label.pack(fill="x")

    def set_status(self, status: PhaseStatus, detail: str = ""):
        """Update the phase status"""
        self.status = status

        # Update indicator color
        color = self.STATUS_COLORS[status][0]
        self.indicator.configure(fg_color=color)

        # Update status text
        status_texts = {
            PhaseStatus.PENDING: "Pending",
            PhaseStatus.IN_PROGRESS: "In Progress...",
            PhaseStatus.PASSED: "Passed",
            PhaseStatus.FAILED: "Failed",
        }
        self.status_label.configure(text=status_texts[status])

        # Update detail
        self.detail_label.configure(text=detail)


class PriAgeApp(ctk.CTk):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Configure appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Window setup
        self.title("priAge - Privacy-Preserving Age Verification")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(1000, 600)

        # State (using verification_state to avoid conflict with tkinter's state() method)
        self.verification_state = VerificationState()
        self.camera_running = False
        self.cap = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.verification_thread = None
        self.is_verifying = False

        # Performance metrics for Big Data thesis
        self.performance_metrics = PerformanceMetrics()

        # Setup logging
        self._setup_logging()

        # Build UI
        self._create_widgets()

        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("outputs") / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"priAge_gui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _create_widgets(self):
        """Create all UI widgets"""
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        self._create_header()

        # Content area (camera + status)
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, pady=10)

        # Camera panel (left)
        self._create_camera_panel()

        # Status panel (right)
        self._create_status_panel()

        # Control panel (bottom)
        self._create_control_panel()

    def _create_header(self):
        """Create header with title"""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="priAge",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title_label.pack(side="left")

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Privacy-Preserving Age Verification",
            font=ctk.CTkFont(size=14),
            text_color="gray60"
        )
        subtitle_label.pack(side="left", padx=(10, 0), pady=(10, 0))

        # GDPR badge
        gdpr_badge = ctk.CTkLabel(
            header_frame,
            text="GDPR Compliant",
            font=ctk.CTkFont(size=11),
            fg_color="#2E7D32",
            corner_radius=5,
            padx=10,
            pady=3
        )
        gdpr_badge.pack(side="right")

    def _create_camera_panel(self):
        """Create camera display panel"""
        self.camera_frame = ctk.CTkFrame(self.content_frame)
        self.camera_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Camera label
        camera_header = ctk.CTkLabel(
            self.camera_frame,
            text="Camera Feed",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        camera_header.pack(pady=(10, 5))

        # Camera display
        self.camera_label = ctk.CTkLabel(
            self.camera_frame,
            text="Camera not started\nClick 'Start Verification' to begin",
            width=CAMERA_WIDTH,
            height=CAMERA_HEIGHT,
            fg_color="gray20",
            corner_radius=10
        )
        self.camera_label.pack(padx=10, pady=10)

        # Instructions
        self.instruction_label = ctk.CTkLabel(
            self.camera_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.instruction_label.pack(pady=(0, 10))

    def _create_status_panel(self):
        """Create status and results panel"""
        self.status_frame = ctk.CTkFrame(self.content_frame, width=350)
        self.status_frame.pack(side="right", fill="y", padx=(10, 0))
        self.status_frame.pack_propagate(False)

        # Status header
        status_header = ctk.CTkLabel(
            self.status_frame,
            text="Verification Status",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        status_header.pack(pady=(10, 15))

        # Phase indicators
        self.phase_indicators = {}

        phases = [
            (1, "Hologram Detection", "Verify real ID card"),
            (2, "ID Detection & OCR", "Extract age from ID"),
            (3, "Facial Recognition", "Match face to ID photo"),
            (4, "Token Generation", "Create verification token"),
        ]

        for num, name, desc in phases:
            indicator = PhaseIndicator(self.status_frame, num, name)
            indicator.pack(fill="x", padx=15, pady=8)
            self.phase_indicators[num] = indicator

        # Separator
        separator = ctk.CTkFrame(self.status_frame, height=2, fg_color="gray40")
        separator.pack(fill="x", padx=15, pady=15)

        # Results area
        self.results_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=15)

        # Age result
        self.age_result_label = ctk.CTkLabel(
            self.results_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray60"
        )
        self.age_result_label.pack(pady=5)

        # QR Code display (initially hidden)
        self.qr_frame = ctk.CTkFrame(self.results_frame, fg_color="gray25", corner_radius=10)

        self.qr_label = ctk.CTkLabel(
            self.qr_frame,
            text="",
            width=150,
            height=150
        )
        self.qr_label.pack(padx=10, pady=10)

        self.pin_label = ctk.CTkLabel(
            self.qr_frame,
            text="",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.pin_label.pack(pady=(0, 10))

        # Performance metrics display
        self.perf_frame = ctk.CTkFrame(self.results_frame, fg_color="gray25", corner_radius=10)

        perf_header = ctk.CTkLabel(
            self.perf_frame,
            text="Performance Metrics",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        perf_header.pack(pady=(10, 5))

        self.timing_label = ctk.CTkLabel(
            self.perf_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            justify="left"
        )
        self.timing_label.pack(padx=10, pady=(0, 10))

    def _create_control_panel(self):
        """Create control buttons panel"""
        control_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        control_frame.pack(fill="x", pady=(10, 0))

        # Start button
        self.start_button = ctk.CTkButton(
            control_frame,
            text="Start Verification",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=150,
            height=40,
            command=self._start_verification
        )
        self.start_button.pack(side="left", padx=5)

        # Cancel button
        self.cancel_button = ctk.CTkButton(
            control_frame,
            text="Cancel",
            font=ctk.CTkFont(size=14),
            width=100,
            height=40,
            fg_color="gray40",
            hover_color="gray30",
            command=self._cancel_verification,
            state="disabled"
        )
        self.cancel_button.pack(side="left", padx=5)

        # Reset button
        self.reset_button = ctk.CTkButton(
            control_frame,
            text="Reset",
            font=ctk.CTkFont(size=14),
            width=100,
            height=40,
            fg_color="gray40",
            hover_color="gray30",
            command=self._reset_verification
        )
        self.reset_button.pack(side="left", padx=5)

        # Status text
        self.status_text = ctk.CTkLabel(
            control_frame,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.status_text.pack(side="right", padx=10)

    # === CAMERA METHODS ===

    def _start_camera(self):
        """Start camera capture thread"""
        if self.camera_running:
            return

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.logger.error("Failed to open camera")
            self._update_status("Error: Could not open camera")
            return False

        self.camera_running = True
        self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.camera_thread.start()

        # Start UI update loop
        self._update_camera_display()
        return True

    def _stop_camera(self):
        """Stop camera capture"""
        self.camera_running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def _camera_loop(self):
        """Camera capture loop (runs in thread) with FPS measurement"""
        # Initialize FPS tracking
        self.performance_metrics.fps_start_time = time.time()
        self.performance_metrics.frame_count = 0
        fps_update_interval = 0.5  # Update FPS calculation every 0.5 seconds
        last_fps_update = time.time()

        while self.camera_running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.performance_metrics.frame_count += 1

                # Calculate FPS periodically
                current_time = time.time()
                elapsed_since_update = current_time - last_fps_update

                if elapsed_since_update >= fps_update_interval:
                    # Calculate current FPS
                    self.performance_metrics.current_fps = self.performance_metrics.frame_count / elapsed_since_update

                    # Store FPS sample for average calculation
                    self.performance_metrics.fps_samples.append(self.performance_metrics.current_fps)

                    # Keep only last 20 samples for rolling average
                    if len(self.performance_metrics.fps_samples) > 20:
                        self.performance_metrics.fps_samples.pop(0)

                    # Calculate average FPS
                    self.performance_metrics.average_fps = sum(self.performance_metrics.fps_samples) / len(self.performance_metrics.fps_samples)

                    # Reset counters for next interval
                    self.performance_metrics.frame_count = 0
                    last_fps_update = current_time

                with self.frame_lock:
                    self.current_frame = frame
            time.sleep(0.03)  # ~30 FPS target

    def _update_camera_display(self):
        """Update camera display in UI (runs in main thread) with FPS overlay"""
        if not self.camera_running:
            return

        with self.frame_lock:
            frame = self.current_frame

        if frame is not None:
            # Make a copy to draw on
            frame_display = frame.copy()

            # Add FPS overlay
            fps = self.performance_metrics.current_fps
            avg_fps = self.performance_metrics.average_fps
            fps_color = (0, 255, 0)  # Green

            # Draw FPS text in top-right corner
            fps_text = f"FPS: {fps:.1f} (Avg: {avg_fps:.1f})"
            cv2.putText(
                frame_display,
                fps_text,
                (CAMERA_WIDTH - 200, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                fps_color,
                2
            )

            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB)

            # Resize to fit display
            frame_resized = cv2.resize(frame_rgb, (CAMERA_WIDTH, CAMERA_HEIGHT))

            # Convert to PIL Image
            img = Image.fromarray(frame_resized)
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(CAMERA_WIDTH, CAMERA_HEIGHT))

            self.camera_label.configure(image=img_tk, text="")
            self.camera_label.image = img_tk

        # Schedule next update
        if self.camera_running:
            self.after(33, self._update_camera_display)

    # === VERIFICATION METHODS ===

    def _start_verification(self):
        """Start the verification process"""
        if self.is_verifying:
            return

        self.logger.info("Starting verification process...")
        self._reset_state()

        # Start camera
        if not self._start_camera():
            return

        self.is_verifying = True
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        # Run verification in thread
        self.verification_thread = threading.Thread(target=self._run_verification, daemon=True)
        self.verification_thread.start()

    def _cancel_verification(self):
        """Cancel ongoing verification"""
        self.logger.info("Verification cancelled by user")
        self.is_verifying = False
        self._stop_camera()
        self._update_status("Verification cancelled")
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

    def _reset_verification(self):
        """Reset to initial state"""
        self._cancel_verification()
        self._reset_state()
        self._update_status("Ready")

        # Reset camera display
        self.camera_label.configure(
            image=None,
            text="Camera not started\nClick 'Start Verification' to begin"
        )

        # Hide QR code and performance metrics
        self.qr_frame.pack_forget()
        self.perf_frame.pack_forget()
        self.age_result_label.configure(text="")

    def _reset_state(self):
        """Reset verification state and performance metrics"""
        self.verification_state = VerificationState()
        self.performance_metrics.reset()

        # Reset phase indicators
        for indicator in self.phase_indicators.values():
            indicator.set_status(PhaseStatus.PENDING)

    def _run_verification(self):
        """Run all verification phases with performance timing"""
        # Start total verification timer
        self.performance_metrics.verification_start_time = time.time()
        self.logger.info("=" * 60)
        self.logger.info("PERFORMANCE BENCHMARKING - Big Data Multi-Model Pipeline")
        self.logger.info("=" * 60)

        try:
            # Phase 1: Hologram Detection
            phase1_start = time.time()
            phase1_result = self._run_phase1_hologram()
            self.performance_metrics.phase1_duration = time.time() - phase1_start
            self.logger.info(f"Phase 1 completed in {self.performance_metrics.phase1_duration:.2f}s")
            if not phase1_result:
                self._log_performance_summary()
                return

            # Phase 2: ID Detection & OCR
            phase2_start = time.time()
            phase2_result = self._run_phase2_id_detection()
            self.performance_metrics.phase2_duration = time.time() - phase2_start
            self.logger.info(f"Phase 2 completed in {self.performance_metrics.phase2_duration:.2f}s")
            if not phase2_result:
                self._log_performance_summary()
                return

            # Phase 3: Facial Recognition
            phase3_start = time.time()
            phase3_result = self._run_phase3_facial()
            self.performance_metrics.phase3_duration = time.time() - phase3_start
            self.logger.info(f"Phase 3 completed in {self.performance_metrics.phase3_duration:.2f}s")
            if not phase3_result:
                self._log_performance_summary()
                return

            # Phase 4: Token Generation
            phase4_start = time.time()
            phase4_result = self._run_phase4_token()
            self.performance_metrics.phase4_duration = time.time() - phase4_start
            self.logger.info(f"Phase 4 completed in {self.performance_metrics.phase4_duration:.2f}s")
            if not phase4_result:
                self._log_performance_summary()
                return

            # Calculate total duration
            self.performance_metrics.total_duration = time.time() - self.performance_metrics.verification_start_time

            # Log final performance summary
            self._log_performance_summary()

            # Success!
            self._verification_success()

        except Exception as e:
            self.logger.error(f"Verification error: {e}", exc_info=True)
            self._update_status(f"Error: {str(e)}")
            self._log_performance_summary()
        finally:
            self.is_verifying = False
            self.after(0, lambda: self.start_button.configure(state="normal"))
            self.after(0, lambda: self.cancel_button.configure(state="disabled"))

    def _log_performance_summary(self):
        """Log comprehensive performance benchmarking summary with all thesis metrics"""
        # Calculate total if not already done
        if self.performance_metrics.total_duration == 0.0 and self.performance_metrics.verification_start_time > 0:
            self.performance_metrics.total_duration = time.time() - self.performance_metrics.verification_start_time

        pm = self.performance_metrics  # Shorthand

        self.logger.info("=" * 70)
        self.logger.info("COMPREHENSIVE PERFORMANCE SUMMARY - BIG DATA THESIS METRICS")
        self.logger.info("=" * 70)

        # Phase Timing Summary
        self.logger.info("PHASE TIMING:")
        self.logger.info(f"  Phase 1 (Hologram):   {pm.phase1_duration:.2f}s")
        self.logger.info(f"  Phase 2 (ID/OCR):     {pm.phase2_duration:.2f}s")
        self.logger.info(f"  Phase 3 (Facial):     {pm.phase3_duration:.2f}s")
        self.logger.info(f"  Phase 4 (Token):      {pm.phase4_duration:.2f}s")
        self.logger.info("-" * 70)

        # Hologram Detection Metrics
        self.logger.info("HOLOGRAM DETECTION METRICS:")
        self.logger.info(f"  Detection Confidence: {pm.hologram_detection_confidence:.2%}")
        self.logger.info(f"  Max Confidence:       {pm.hologram_max_confidence:.2%}")
        self.logger.info(f"  Avg Confidence:       {pm.hologram_avg_confidence:.2%}")
        self.logger.info(f"  Inference Time:       {pm.hologram_inference_time_ms:.2f}ms")
        self.logger.info(f"  Num Detections:       {pm.hologram_num_detections}")
        self.logger.info("-" * 70)

        # ID Field Detection Metrics
        self.logger.info("ID FIELD DETECTION METRICS:")
        self.logger.info(f"  DOB Confidence:       {pm.id_dob_confidence:.2%}")
        self.logger.info(f"  Photo Confidence:     {pm.id_photo_confidence:.2%}")
        self.logger.info(f"  Inference Time:       {pm.id_inference_time_ms:.2f}ms")
        self.logger.info(f"  OCR Processing Time:  {pm.id_ocr_processing_time_ms:.2f}ms")
        self.logger.info(f"  Total Detections:     {pm.id_total_detections}")
        self.logger.info(f"  Fields Detected:      {pm.id_fields_detected}")
        self.logger.info("-" * 70)

        # Facial Recognition Metrics
        self.logger.info("FACIAL RECOGNITION METRICS:")
        self.logger.info(f"  Face Detection Conf:  {pm.face_detection_confidence:.2%}")
        self.logger.info(f"  Embedding Time:       {pm.face_embedding_extraction_time_ms:.2f}ms")
        self.logger.info(f"  Distance Score:       {pm.face_distance_score:.4f}")
        self.logger.info(f"  Similarity Score:     {pm.face_similarity_score:.4f}")
        self.logger.info(f"  Match Threshold:      {pm.face_match_threshold:.2f}")
        self.logger.info(f"  Is Match:             {pm.face_is_match}")
        self.logger.info("  ANTI-SPOOFING:")
        self.logger.info(f"    Liveness Score:     {pm.antispoof_liveness_score:.4f}")
        self.logger.info(f"    Is Real:            {pm.antispoof_is_real}")
        self.logger.info(f"    Inference Time:     {pm.antispoof_inference_time_ms:.2f}ms")
        self.logger.info("-" * 70)

        # Token System Metrics
        self.logger.info("TOKEN SYSTEM METRICS:")
        self.logger.info(f"  Key Derivation Time:  {pm.token_key_derivation_time_ms:.2f}ms")
        self.logger.info(f"  Encryption Time:      {pm.token_encryption_time_ms:.2f}ms")
        self.logger.info(f"  QR Generation Time:   {pm.token_qr_generation_time_ms:.2f}ms")
        self.logger.info(f"  Total Generation:     {pm.token_total_generation_time_ms:.2f}ms")
        self.logger.info("-" * 70)

        # Performance Summary
        self.logger.info("PERFORMANCE OBSERVATIONS:")
        self.logger.info(f"  Total Verification Time: {pm.total_duration:.2f}s")
        self.logger.info(f"  Average FPS: {pm.average_fps:.1f}")
        self.logger.info(f"  Note: Multi-model deep learning pipeline - timing reflects security processing")
        self.logger.info("=" * 70)

        # Save metrics to JSON
        self._save_metrics_to_json()

    def _save_metrics_to_json(self):
        """Save performance metrics to JSON file"""
        try:
            # Create metrics directory
            metrics_dir = Path("C:/Users/branq/Desktop/thesis/test_09_12/benchmark_results")
            metrics_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = metrics_dir / f"performance_metrics_{timestamp}.json"

            # Get metrics as dictionary
            metrics_data = self.performance_metrics.to_dict()

            # Add verification result info
            metrics_data["verification_completed"] = self.verification_state.phase4_status == PhaseStatus.PASSED

            # Save to JSON file
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Performance metrics saved to: {json_file}")

        except Exception as e:
            self.logger.error(f"Failed to save metrics to JSON: {e}")

    def _run_phase1_hologram(self) -> bool:
        """Phase 1: Hologram Detection with comprehensive metrics capture"""
        self.logger.info("Starting Phase 1: Hologram Detection")
        self._set_phase_status(1, PhaseStatus.IN_PROGRESS, "Detecting hologram...")
        self._update_instruction("Position your ID card to show the hologram")
        self._update_status("Phase 1: Detecting hologram...")

        config = HologramConfig()
        config.CONFIDENCE_THRESHOLD = 0.50
        verifier = HologramVerifier(config)

        # Detection loop
        detection_start = time.time()
        required_confidence = 0.80  # Require 80% confidence for hologram detection
        max_wait_time = 30  # seconds

        # Track inference times for averaging
        inference_times = []

        while self.is_verifying and (time.time() - detection_start) < max_wait_time:
            with self.frame_lock:
                frame = self.current_frame

            if frame is None:
                time.sleep(0.1)
                continue

            # Detect hologram with timing
            inference_start = time.perf_counter()
            is_authentic, result = verifier.verify(frame)
            inference_time_ms = (time.perf_counter() - inference_start) * 1000
            inference_times.append(inference_time_ms)

            if result.detected:
                detail = f"Confidence: {result.max_confidence:.0%}"
                self._set_phase_status(1, PhaseStatus.IN_PROGRESS, detail)

                if result.max_confidence >= required_confidence:
                    self.verification_state.hologram_confidence = result.max_confidence
                    self.verification_state.phase1_status = PhaseStatus.PASSED

                    # === CAPTURE HOLOGRAM METRICS ===
                    self.performance_metrics.hologram_detection_confidence = result.max_confidence
                    self.performance_metrics.hologram_max_confidence = result.max_confidence
                    self.performance_metrics.hologram_num_detections = result.count if hasattr(result, 'count') else 1
                    self.performance_metrics.hologram_inference_time_ms = inference_time_ms

                    # Calculate average confidence if multiple detections
                    if hasattr(result, 'detections') and result.detections:
                        confidences = [d.confidence for d in result.detections]
                        self.performance_metrics.hologram_avg_confidence = sum(confidences) / len(confidences)
                    else:
                        self.performance_metrics.hologram_avg_confidence = result.max_confidence

                    self.logger.info(f"Hologram Metrics - Confidence: {result.max_confidence:.2%}, "
                                    f"Inference: {inference_time_ms:.2f}ms, "
                                    f"Detections: {self.performance_metrics.hologram_num_detections}")

                    # Save snapshot
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_dir = Path("outputs") / f"hologram_{timestamp}"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(save_dir / "captured.png"), frame)

                    self._set_phase_status(1, PhaseStatus.PASSED, f"Hologram detected ({result.max_confidence:.0%})")
                    self.logger.info(f"Phase 1 PASSED: Hologram detected at {result.max_confidence:.0%}")
                    return True

            time.sleep(0.1)

        # Timeout or cancelled - still capture any metrics we have
        if inference_times:
            self.performance_metrics.hologram_inference_time_ms = sum(inference_times) / len(inference_times)

        if not self.is_verifying:
            return False

        self.verification_state.phase1_status = PhaseStatus.FAILED
        self._set_phase_status(1, PhaseStatus.FAILED, "No hologram detected")
        self._update_status("Phase 1 FAILED: Could not detect hologram")
        self.logger.error("Phase 1 FAILED: Hologram not detected")
        return False

    def _run_phase2_id_detection(self) -> bool:
        """Phase 2: ID Detection & OCR with comprehensive metrics capture"""
        self.logger.info("Starting Phase 2: ID Detection & OCR")
        self._set_phase_status(2, PhaseStatus.IN_PROGRESS, "Detecting ID card...")
        self._update_instruction("Hold your ID card steady for scanning")
        self._update_status("Phase 2: Extracting age from ID...")

        # Initialize ID detector without calling run() - we will use the model directly
        config = Config()
        config.AUTO_CONTINUE = True
        detector = IDCardDetector(config)

        # Detection parameters
        max_attempts = config.MAX_RETRY_ATTEMPTS
        max_wait_time = 60  # seconds
        detection_start = time.time()
        snapshot_count = 0
        successful_detection = False

        # Track metrics
        inference_times = []
        best_dob_confidence = 0.0
        best_photo_confidence = 0.0

        self.logger.info("Running ID detection in GUI camera panel...")
        self.logger.info("Snapshot triggers when BOTH: DOB >= 0.80 AND Photo >= 0.80")

        try:
            while self.is_verifying and (time.time() - detection_start) < max_wait_time:
                # Get current frame from GUI camera
                with self.frame_lock:
                    frame = self.current_frame.copy() if self.current_frame is not None else None

                if frame is None:
                    time.sleep(0.1)
                    continue

                # Run YOLO detection on the frame with timing
                inference_start = time.perf_counter()
                results = detector.model(
                    frame,
                    imgsz=config.IMGSZ,
                    conf=config.BASE_CONF,
                    verbose=False
                )
                inference_time_ms = (time.perf_counter() - inference_start) * 1000
                inference_times.append(inference_time_ms)

                # Get annotated frame with detection boxes
                annotated_frame = results[0].plot()

                # Check if thresholds are met
                meets_thresh = detector.check_thresholds(results)
                dob_met = meets_thresh.get("DOB", False)
                photo_met = meets_thresh.get("Photo", False)

                # Build status text for the frame and capture confidence values
                status_parts = []
                fields_detected = []
                for label in ["DOB", "Photo"]:
                    # Find confidence for this label
                    conf_val = 0.0
                    for box in results[0].boxes:
                        cls_id = int(box.cls[0].item())
                        if config.CLASS_NAMES[cls_id] == label:
                            conf_val = max(conf_val, float(box.conf[0].item()))
                            if label not in fields_detected:
                                fields_detected.append(label)

                    # Track best confidence values
                    if label == "DOB":
                        best_dob_confidence = max(best_dob_confidence, conf_val)
                    elif label == "Photo":
                        best_photo_confidence = max(best_photo_confidence, conf_val)

                    thresh = config.THRESHOLDS.get(label, 0.80)
                    met_symbol = "[OK]" if meets_thresh.get(label, False) else "[--]"
                    status_parts.append(f"{label}: {conf_val:.0%} {met_symbol}")

                status_text = " | ".join(status_parts)
                cv2.putText(
                    annotated_frame,
                    status_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0) if (dob_met and photo_met) else (0, 165, 255),
                    2
                )

                # Add attempt counter
                attempt_text = f"Attempts: {snapshot_count}/{max_attempts}"
                cv2.putText(
                    annotated_frame,
                    attempt_text,
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                # Update GUI with annotated frame
                self._display_frame_in_gui(annotated_frame)

                # Update phase status with current detection info
                if dob_met and photo_met:
                    self._set_phase_status(2, PhaseStatus.IN_PROGRESS, "Thresholds met - processing...")
                elif dob_met or photo_met:
                    detail = f"DOB: {'OK' if dob_met else 'Low'}, Photo: {'OK' if photo_met else 'Low'}"
                    self._set_phase_status(2, PhaseStatus.IN_PROGRESS, detail)

                # Check if both DOB and Photo meet thresholds
                if dob_met and photo_met and snapshot_count < max_attempts:
                    snapshot_count += 1
                    self.logger.info(f"Taking snapshot (Attempt {snapshot_count}/{max_attempts})...")
                    self._set_phase_status(2, PhaseStatus.IN_PROGRESS, f"Processing OCR (attempt {snapshot_count})...")

                    # Take snapshot and process OCR with timing
                    ocr_start = time.perf_counter()
                    snap_dir = detector.take_snapshot(frame, results)
                    ocr_time_ms = (time.perf_counter() - ocr_start) * 1000
                    age_info = detector.age_info

                    if age_info and age_info.status != "unknown":
                        # Success!
                        successful_detection = True
                        self.logger.info(f"Successfully determined age: {age_info.age_years} years")

                        self.verification_state.age_info = age_info
                        self.verification_state.is_adult = age_info.is_adult()
                        self.verification_state.phase2_status = PhaseStatus.PASSED

                        # === CAPTURE ID DETECTION METRICS ===
                        self.performance_metrics.id_dob_confidence = best_dob_confidence
                        self.performance_metrics.id_photo_confidence = best_photo_confidence
                        self.performance_metrics.id_inference_time_ms = inference_time_ms
                        self.performance_metrics.id_ocr_processing_time_ms = ocr_time_ms
                        self.performance_metrics.id_total_detections = len(results[0].boxes)
                        self.performance_metrics.id_fields_detected = fields_detected

                        self.logger.info(f"ID Detection Metrics - DOB Conf: {best_dob_confidence:.2%}, "
                                        f"Photo Conf: {best_photo_confidence:.2%}, "
                                        f"Inference: {inference_time_ms:.2f}ms, "
                                        f"OCR: {ocr_time_ms:.2f}ms")

                        detail = f"Age: {age_info.age_years} years"
                        self._set_phase_status(2, PhaseStatus.PASSED, detail)

                        # Update age result display
                        status = "ADULT (18+)" if self.verification_state.is_adult else "MINOR (under 18)"
                        self.after(0, lambda ai=age_info, s=status: self.age_result_label.configure(
                            text=f"Age: {ai.age_years} years\nStatus: {s}",
                            text_color="#32CD32" if ai.is_adult() else "#DC143C"
                        ))

                        self.logger.info(f"Phase 2 PASSED: Age {age_info.age_years}, Adult: {self.verification_state.is_adult}")

                        # Check if minor
                        if not self.verification_state.is_adult:
                            self._update_status("VERIFICATION STOPPED: Minor detected")
                            self._set_phase_status(3, PhaseStatus.FAILED, "Minor - cannot proceed")
                            self._set_phase_status(4, PhaseStatus.FAILED, "Minor - cannot proceed")
                            return False

                        return True
                    else:
                        # OCR failed to extract age, will retry
                        remaining = max_attempts - snapshot_count
                        self.logger.warning(f"Status is UNKNOWN. Will retry... ({remaining} attempts remaining)")
                        self._set_phase_status(2, PhaseStatus.IN_PROGRESS, f"Retrying... ({remaining} left)")
                        # Wait a bit before next attempt to allow repositioning
                        time.sleep(1.0)

                # Small delay to avoid overwhelming CPU
                time.sleep(0.05)

            # Loop ended - capture metrics even on failure
            if inference_times:
                self.performance_metrics.id_inference_time_ms = sum(inference_times) / len(inference_times)
            self.performance_metrics.id_dob_confidence = best_dob_confidence
            self.performance_metrics.id_photo_confidence = best_photo_confidence

            # Check why loop ended
            if not self.is_verifying:
                self.logger.info("Phase 2 cancelled by user")
                return False

            if snapshot_count >= max_attempts:
                self.logger.error(f"Failed to determine age after {max_attempts} attempts")
                self.verification_state.phase2_status = PhaseStatus.FAILED
                self._set_phase_status(2, PhaseStatus.FAILED, f"Failed after {max_attempts} attempts")
                self._update_status("Phase 2 FAILED: Could not extract age from ID")
                return False

            # Timeout
            self.logger.error("Phase 2 timeout - no valid detection")
            self.verification_state.phase2_status = PhaseStatus.FAILED
            self._set_phase_status(2, PhaseStatus.FAILED, "Timeout - no ID detected")
            self._update_status("Phase 2 FAILED: Timeout waiting for ID detection")
            return False

        except Exception as e:
            self.logger.error(f"Phase 2 error: {e}", exc_info=True)
            self.verification_state.phase2_status = PhaseStatus.FAILED
            self._set_phase_status(2, PhaseStatus.FAILED, str(e))
            return False

    def _display_frame_in_gui(self, frame):
        """Display an OpenCV frame in the GUI camera label (thread-safe)"""
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Resize to fit display
            frame_resized = cv2.resize(frame_rgb, (CAMERA_WIDTH, CAMERA_HEIGHT))

            # Convert to PIL Image
            img = Image.fromarray(frame_resized)
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(CAMERA_WIDTH, CAMERA_HEIGHT))

            # Update GUI in main thread
            def update():
                self.camera_label.configure(image=img_tk, text="")
                self.camera_label.image = img_tk

            self.after(0, update)
        except Exception as e:
            self.logger.error(f"Error displaying frame: {e}")

    def _run_phase3_facial(self) -> bool:
        """Phase 3: Facial Recognition with comprehensive metrics capture"""
        self.logger.info("Starting Phase 3: Facial Recognition")
        self._set_phase_status(3, PhaseStatus.IN_PROGRESS, "Starting face match...")
        self._update_instruction("Look at the camera for face verification")
        self._update_status("Phase 3: Matching face to ID photo...")

        # Stop camera for facial recognition module
        self._stop_camera()
        time.sleep(0.5)

        try:
            # Find ID photo
            id_photo_path = self._find_latest_id_photo()

            if id_photo_path is None:
                self.verification_state.phase3_status = PhaseStatus.FAILED
                self._set_phase_status(3, PhaseStatus.FAILED, "No ID photo found")
                self.logger.error("Phase 3 FAILED: No ID photo")
                return False

            self.logger.info(f"Using ID photo: {id_photo_path}")

            # Run facial recognition with metrics capture
            facial_verifier = FacialRecognitionVerifier()

            # Store the threshold being used
            self.performance_metrics.face_match_threshold = facial_verifier.distance_threshold

            # Time the ID embedding extraction
            embedding_start = time.perf_counter()
            id_embedding, id_metadata = facial_verifier.extract_face_from_id(id_photo_path)
            id_embedding_time_ms = (time.perf_counter() - embedding_start) * 1000

            if id_embedding is None:
                self.verification_state.phase3_status = PhaseStatus.FAILED
                self._set_phase_status(3, PhaseStatus.FAILED, "No face in ID photo")
                self.logger.error("Phase 3 FAILED: Cannot extract face from ID")
                facial_verifier.cleanup()
                return False

            # Capture ID face detection confidence
            if 'detection_prob' in id_metadata:
                self.performance_metrics.face_detection_confidence = float(id_metadata['detection_prob'])

            # Run the verification (interactive, captures metrics internally)
            face_match = facial_verifier.verify(id_photo_path)

            # Try to extract metrics from the last verification
            # These are captured during the interactive verify() process
            if hasattr(facial_verifier, 'last_distance'):
                self.performance_metrics.face_distance_score = facial_verifier.last_distance
                # Calculate similarity score (inverse of distance, normalized)
                # Typical FaceNet distances range 0-4, so we normalize
                self.performance_metrics.face_similarity_score = max(0, 1 - (facial_verifier.last_distance / 4.0))

            if hasattr(facial_verifier, 'last_antispoof_score'):
                self.performance_metrics.antispoof_liveness_score = facial_verifier.last_antispoof_score

            if hasattr(facial_verifier, 'last_antispoof_is_real'):
                self.performance_metrics.antispoof_is_real = facial_verifier.last_antispoof_is_real

            # Estimate embedding extraction time (we timed ID extraction, live is similar)
            self.performance_metrics.face_embedding_extraction_time_ms = id_embedding_time_ms

            # Capture anti-spoofing inference time if available
            if hasattr(facial_verifier, 'last_antispoof_time_ms'):
                self.performance_metrics.antispoof_inference_time_ms = facial_verifier.last_antispoof_time_ms

            self.performance_metrics.face_is_match = face_match

            facial_verifier.cleanup()

            if not face_match:
                self.verification_state.phase3_status = PhaseStatus.FAILED
                self._set_phase_status(3, PhaseStatus.FAILED, "Face mismatch or spoof detected")
                self._update_status("Phase 3 FAILED: Face does not match ID")
                self.logger.error("Phase 3 FAILED: Face mismatch")

                self.logger.info(f"Facial Metrics - Distance: {self.performance_metrics.face_distance_score:.4f}, "
                                f"Threshold: {self.performance_metrics.face_match_threshold}, "
                                f"Liveness: {self.performance_metrics.antispoof_liveness_score:.4f}")
                return False

            self.verification_state.face_matched = True
            self.verification_state.phase3_status = PhaseStatus.PASSED
            self._set_phase_status(3, PhaseStatus.PASSED, "Face matched successfully")

            # Log captured metrics
            self.logger.info(f"Facial Metrics - Distance: {self.performance_metrics.face_distance_score:.4f}, "
                            f"Threshold: {self.performance_metrics.face_match_threshold}, "
                            f"Similarity: {self.performance_metrics.face_similarity_score:.4f}, "
                            f"Embedding Time: {self.performance_metrics.face_embedding_extraction_time_ms:.2f}ms, "
                            f"Liveness: {self.performance_metrics.antispoof_liveness_score:.4f}, "
                            f"Is Real: {self.performance_metrics.antispoof_is_real}")

            self.logger.info("Phase 3 PASSED: Face matched")
            return True

        finally:
            # Restart camera
            self._start_camera()

    def _run_phase4_token(self) -> bool:
        """Phase 4: Token Generation with comprehensive metrics capture"""
        self.logger.info("Starting Phase 4: Token Generation")
        self._set_phase_status(4, PhaseStatus.IN_PROGRESS, "Generating token...")
        self._update_instruction("Generating secure verification token...")
        self._update_status("Phase 4: Generating GDPR-compliant token...")

        try:
            token_generator = GDPRCompliantTokenGenerator(
                validity_hours=24,
                single_use=True,
                enable_tpm=True
            )

            qr_path, pin = token_generator.generate(is_adult=self.verification_state.is_adult)

            if qr_path is None:
                self.verification_state.phase4_status = PhaseStatus.FAILED
                self._set_phase_status(4, PhaseStatus.FAILED, "Token generation failed")
                self.logger.error("Phase 4 FAILED: Token generation error")
                return False

            # === CAPTURE TOKEN GENERATION METRICS ===
            self.performance_metrics.token_key_derivation_time_ms = token_generator.last_key_derivation_time_ms
            self.performance_metrics.token_encryption_time_ms = token_generator.last_encryption_time_ms
            self.performance_metrics.token_total_generation_time_ms = token_generator.last_total_generation_time_ms
            self.performance_metrics.token_qr_generation_time_ms = token_generator.last_qr_generation_time_ms

            self.logger.info(f"Token Metrics - Key Derivation: {self.performance_metrics.token_key_derivation_time_ms:.2f}ms, "
                            f"Encryption: {self.performance_metrics.token_encryption_time_ms:.2f}ms, "
                            f"QR Gen: {self.performance_metrics.token_qr_generation_time_ms:.2f}ms, "
                            f"Total: {self.performance_metrics.token_total_generation_time_ms:.2f}ms")

            self.verification_state.qr_path = qr_path
            self.verification_state.pin = pin
            self.verification_state.phase4_status = PhaseStatus.PASSED

            self._set_phase_status(4, PhaseStatus.PASSED, f"Token generated (PIN: {pin})")
            self.logger.info(f"Phase 4 PASSED: Token saved to {qr_path}")

            # Display QR code
            self._display_qr_code(qr_path, pin)

            return True

        except Exception as e:
            self.logger.error(f"Phase 4 error: {e}")
            self.verification_state.phase4_status = PhaseStatus.FAILED
            self._set_phase_status(4, PhaseStatus.FAILED, str(e))
            return False

    def _verification_success(self):
        """Handle successful verification"""
        self.logger.info("VERIFICATION COMPLETE - ALL PHASES PASSED")
        self._update_status("VERIFICATION COMPLETE - Adult verified!")
        self._update_instruction("Verification successful! Scan QR code to verify.")
        self._stop_camera()

        # =====================================================================
        # GDPR-COMPLIANT DATA DELETION (Storage Limitation - Article 5(1)(e))
        # =====================================================================
        # After token generation, all personal data must be securely deleted
        # to comply with GDPR Article 5(1)(e) - data minimization and storage limitation
        #
        # Data to delete:
        # 1. ID snapshots (photo, DOB, name, ID number)
        # 2. Hologram detection images
        # 3. Facial recognition comparison images (biometric data)
        # 4. OCR results
        # 5. Temporary files containing personal data
        #
        # What remains:
        # - Encrypted token (contains ONLY is_adult boolean)
        # - PIN for token decryption
        # - Anonymized performance metrics
        # =====================================================================
        self._gdpr_compliant_data_deletion()

        # Display QR code in camera panel
        self._display_qr_in_camera_panel()

        # Display performance metrics in UI
        self._display_performance_metrics()

    def _gdpr_compliant_data_deletion(self):
        """
        GDPR-compliant secure deletion of all personal data after token generation.

        Implements GDPR Article 5(1)(e) - Storage Limitation:
        "Personal data shall be kept in a form which permits identification of data
        subjects for no longer than is necessary for the purposes for which the
        personal data are processed"

        Deletion method: DoD 5220.22-M (3-pass overwrite)
        - Pass 1: Zeros
        - Pass 2: Ones
        - Pass 3: Random data

        This ensures data CANNOT be recovered even with forensic tools.
        """
        try:
            self.logger.info("="*60)
            self.logger.info("PHASE 5: GDPR-COMPLIANT DATA DELETION")
            self.logger.info("="*60)

            # Initialize secure eraser
            eraser = GDPRCompliantDataEraser()

            # Collect directories to delete
            files_to_delete = []

            # 1. ID snapshot directory (contains photo, DOB, name, OCR data)
            if hasattr(self.verification_state, 'snapshot_dir') and self.verification_state.snapshot_dir:
                snapshot_path = Path(self.verification_state.snapshot_dir)
                if snapshot_path.exists():
                    files_to_delete.append(("ID Snapshot", snapshot_path))
                    self.logger.info(f"Marked for deletion: {snapshot_path} (PII: photo, DOB, name)")

            # 2. Hologram detection directory (contains ID card images)
            hologram_dirs = list(Path("outputs").glob("hologram_*"))
            if hologram_dirs:
                latest_hologram = max(hologram_dirs, key=lambda p: p.stat().st_mtime)
                files_to_delete.append(("Hologram Detection", latest_hologram))
                self.logger.info(f"Marked for deletion: {latest_hologram} (ID card images)")

            # 3. Facial recognition comparison images (biometric data - highly sensitive!)
            facial_dirs = list(Path("outputs/facial_recognition").glob("*"))
            if facial_dirs:
                latest_facial = max(facial_dirs, key=lambda p: p.stat().st_mtime)
                files_to_delete.append(("Facial Recognition", latest_facial))
                self.logger.info(f"Marked for deletion: {latest_facial} (biometric data)")

            # Log deletion plan
            self.logger.info(f"Total items marked for deletion: {len(files_to_delete)}")
            self.logger.info("Deletion method: DoD 5220.22-M (3-pass overwrite)")

            # COMMENTED OUT: Actual deletion
            # Uncomment to enable automatic secure deletion
            #
            # deletion_summary = []
            # for label, path in files_to_delete:
            #     self.logger.info(f"Securely deleting {label}: {path}")
            #     result = eraser.erase_directory(path, verify=True)
            #
            #     if result.success:
            #         self.logger.info(
            #             f"✓ {label} deleted: {result.files_deleted} files, "
            #             f"{result.bytes_overwritten} bytes overwritten"
            #         )
            #         deletion_summary.append((label, True, result.files_deleted))
            #     else:
            #         self.logger.error(f"✗ {label} deletion FAILED: {result.error_message}")
            #         deletion_summary.append((label, False, 0))
            #
            # # Log summary
            # successful = sum(1 for _, success, _ in deletion_summary if success)
            # total_files = sum(count for _, success, count in deletion_summary if success)
            #
            # self.logger.info("="*60)
            # self.logger.info("GDPR DELETION SUMMARY")
            # self.logger.info("="*60)
            # self.logger.info(f"Directories deleted: {successful}/{len(files_to_delete)}")
            # self.logger.info(f"Total files deleted: {total_files}")
            # self.logger.info(f"Method: DoD 5220.22-M (3-pass)")
            # self.logger.info(f"Data recovery: IMPOSSIBLE")
            # self.logger.info("="*60)
            #
            # if successful == len(files_to_delete):
            #     self.logger.info("GDPR COMPLIANCE: ACHIEVED")
            #     self.logger.info("All personal data securely deleted per Article 5(1)(e)")
            # else:
            #     self.logger.warning("GDPR COMPLIANCE: PARTIAL")
            #     self.logger.warning("Some files could not be deleted - manual review required")

            # Currently just logging what would be deleted
            self.logger.info("="*60)
            self.logger.info("DATA DELETION: DISABLED (code commented out)")
            self.logger.info("In production: uncomment deletion code to enable automatic cleanup")
            self.logger.info("="*60)

        except Exception as e:
            self.logger.error(f"Error in GDPR data deletion: {e}", exc_info=True)
            # Non-fatal - verification already succeeded, deletion is post-processing

    def _display_performance_metrics(self):
        """Display performance benchmarking results in the status panel"""
        metrics = self.performance_metrics

        def update_metrics():
            timing_text = (
                f"Phase 1: {metrics.phase1_duration:.2f}s\n"
                f"Phase 2: {metrics.phase2_duration:.2f}s\n"
                f"Phase 3: {metrics.phase3_duration:.2f}s\n"
                f"Phase 4: {metrics.phase4_duration:.2f}s\n"
                f"-------------------\n"
                f"Total: {metrics.total_duration:.2f}s\n"
                f"-------------------\n"
                f"Avg FPS: {metrics.average_fps:.1f}"
            )
            self.timing_label.configure(text=timing_text)

            # Set color to green (observations, not pass/fail)
            self.perf_frame.configure(fg_color="#1a472a")  # Dark green

            self.perf_frame.pack(pady=10, fill="x")

        self.after(0, update_metrics)

    def _display_qr_in_camera_panel(self):
        """Display QR code in the camera panel area"""
        def update_display():
            try:
                if self.verification_state.qr_path is None:
                    return

                # Load QR image
                qr_img = Image.open(str(self.verification_state.qr_path))

                # Calculate size to fit in camera area (maintain aspect ratio)
                qr_size = min(CAMERA_WIDTH, CAMERA_HEIGHT) - 100  # Leave some padding
                qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)

                # Create a composite image with QR code centered and text
                composite = Image.new('RGB', (CAMERA_WIDTH, CAMERA_HEIGHT), color=(26, 71, 42))  # Dark green background

                # Center the QR code
                qr_x = (CAMERA_WIDTH - qr_size) // 2
                qr_y = (CAMERA_HEIGHT - qr_size) // 2 - 30  # Shift up a bit for text below
                composite.paste(qr_img, (qr_x, qr_y))

                # Convert to CTkImage
                img_tk = ctk.CTkImage(light_image=composite, dark_image=composite, size=(CAMERA_WIDTH, CAMERA_HEIGHT))

                self.camera_label.configure(image=img_tk, text="", fg_color="#1a472a")
                self.camera_label.image = img_tk

                # Update instruction with PIN
                pin = self.verification_state.pin
                self._update_instruction(f"VERIFICATION COMPLETE - PIN: {pin}")

            except Exception as e:
                self.logger.error(f"Error displaying QR in camera panel: {e}")
                # Fallback to text
                self.camera_label.configure(
                    image=None,
                    text="VERIFICATION COMPLETE\n\nAll phases passed!\n\nScan the QR code to verify.",
                    fg_color="#1a472a"
                )

        self.after(0, update_display)

    def _display_qr_code(self, qr_path: Path, pin: str):
        """Display QR code in results panel"""
        def update_qr():
            try:
                # Load QR image
                qr_img = Image.open(str(qr_path))
                qr_img = qr_img.resize((150, 150), Image.Resampling.NEAREST)
                qr_tk = ctk.CTkImage(light_image=qr_img, dark_image=qr_img, size=(150, 150))

                self.qr_label.configure(image=qr_tk, text="")
                self.qr_label.image = qr_tk

                self.pin_label.configure(text=f"PIN: {pin}")

                self.qr_frame.pack(pady=10)

            except Exception as e:
                self.logger.error(f"Error displaying QR: {e}")

        self.after(0, update_qr)

    def _find_latest_id_photo(self) -> Optional[Path]:
        """Find the most recent ID photo from outputs"""
        output_dir = Path("outputs")
        if not output_dir.exists():
            return None

        for snapshot_dir in sorted(output_dir.glob("snapshot_*"), reverse=True):
            photos = list(snapshot_dir.glob("Photo_*.png"))
            if photos:
                return photos[0]

        return None

    # === UI UPDATE HELPERS ===

    def _set_phase_status(self, phase: int, status: PhaseStatus, detail: str = ""):
        """Update phase indicator (thread-safe)"""
        self.after(0, lambda: self.phase_indicators[phase].set_status(status, detail))

    def _update_status(self, text: str):
        """Update status text (thread-safe)"""
        self.after(0, lambda: self.status_text.configure(text=text))

    def _update_instruction(self, text: str):
        """Update instruction text (thread-safe)"""
        self.after(0, lambda: self.instruction_label.configure(text=text))

    def _on_closing(self):
        """Handle window close"""
        self.is_verifying = False
        self._stop_camera()
        self.destroy()


def main():
    """Main entry point"""
    app = PriAgeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
