# PriAge - Privacy-Preserving Age Verification System

**Master's Thesis Project**
**Université Libre de Bruxelles (ULB) - Faculty of Science**
**Specialized Master in Data Science, Big Data**

**Author:** Priscila PINTO ICKOWICZ
**Supervisor:** Prof. Dimitris SACHARIDIS
**Co-Supervisor:** Prof. Jan Tobias MÜHLBERG
**Academic Year:** 2025-2026

**Repository:** [github.com/PPICKO/PriAge](https://github.com/PPICKO/PriAge)
**License:** MIT

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GDPR](https://img.shields.io/badge/GDPR-Compliant-success.svg)](GDPR_COMPLIANCE_README.md)
[![Status](https://img.shields.io/badge/Status-Research-orange.svg)](https://github.com/PPICKO/PriAge)

---

## Overview

**Thesis Title:** *Privacy-Preserving Age Verification under GDPR: AI-Based Identity Extraction and Encrypted Token Exchange*

PriAge is a **GDPR-compliant age verification system** that determines if an individual is 18+ **without storing personal data**. The system processes government-issued ID cards through a 5-phase AI pipeline and outputs a single boolean: `is_adult: true/false`.

This project is the result of research conducted at the **Université Libre de Bruxelles (ULB)** as part of the Specialized Master in Data Science, Big Data program.

### Key Features

1. **Privacy-First Architecture** - Stores only `is_adult` boolean, no personal identifiable information (PII)
2. **Multi-Layer Verification** - Hologram detection, OCR extraction, facial recognition, and liveness detection
3. **GDPR Compliant** - DoD 5220.22-M secure deletion ensures irreversible data erasure
4. **Strong Encryption** - AES-256-GCM with PBKDF2-SHA256 key derivation (100,000 iterations)
5. **Anti-Spoofing Protection** - Detects printed photos, screen replays, and 3D masks
6. **Dual Interface** - Command-line (CLI) and graphical user interface (GUI) support
7. **Multi-Language OCR** - English, French, Dutch, and German date-of-birth extraction

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PriAge Verification Pipeline                   │
└─────────────────────────────────────────────────────────────────────┘

  User Presents ID Card
         │
         ▼
  ┌─────────────────┐
  │   Phase 1:      │  YOLOv8 Hologram Detection
  │   Authenticity  │  → Validates physical ID card
  │   Check         │  → Rejects screen/photo displays
  └────────┬────────┘  Confidence threshold: 80%
           │           Duration: ~10s
           ▼
  ┌─────────────────┐
  │   Phase 2:      │  YOLO + EasyOCR Extraction
  │   Age           │  → Detects date-of-birth field
  │   Extraction    │  → OCR with error correction
  └────────┬────────┘  → Calculates age
           │           Duration: ~33s
           ▼
  ┌─────────────────┐
  │   Phase 3:      │  FaceNet + MTCNN Verification
  │   Facial        │  → Extracts face from ID
  │   Recognition   │  → Matches with live camera
  └────────┬────────┘  → Liveness detection (anti-spoofing)
           │           Distance threshold: 1.35
           │           Liveness threshold: 50%
           │           Duration: ~9s
           ▼
  ┌─────────────────┐
  │   Phase 4:      │  AES-256-GCM Token Generation
  │   Token         │  → Encrypts {is_adult: true/false}
  │   Generation    │  → QR code + 6-digit PIN
  └────────┬────────┘  → 24-hour expiration
           │           Duration: ~0.4s
           ▼
  ┌─────────────────┐
  │   Phase 5:      │  DoD 5220.22-M Secure Deletion
  │   Data          │  → 3-pass overwrite (0x00, 0xFF, random)
  │   Deletion      │  → Deletes all personal data
  └────────┬────────┘  → Only encrypted token remains
           │           Duration: Immediate (optional)
           ▼
  Verification Token
  (QR Code + PIN)

  Total End-to-End Time: ~52 seconds
```

---

## Installation

### Prerequisites

- **Python:** 3.8 - 3.11 (3.12+ not supported due to PyTorch dependencies)
- **Hardware:** Webcam, 4GB RAM minimum (8GB recommended)
- **Disk Space:** 500MB for dependencies + 56MB for models
- **Operating Systems:** Windows 10/11, Linux (Ubuntu 20.04+), macOS 10.15+

### Step 1: Clone Repository

```bash
git clone https://github.com/PPICKO/PriAge.git
cd PriAge
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** Installation may take 5-10 minutes due to PyTorch and deep learning libraries.

### Step 4: Download Model Files

**Important:** Model files (56MB total) are not included in the repository due to GitHub size limits.

**Required models:**
- `my_model.pt` (50MB) - YOLOv8 ID card detection model
- `holog_best.pt` (6MB) - YOLOv8 hologram detection model

**Options:**
1. Contact repository owner for direct access
2. Download from project releases
3. Train your own models using YOLOv8

Place model files in the project root directory.

### Step 5: Verify Installation

```bash
# Test GUI application
python priAge_gui.py

# Test CLI help
python main_priAge.py --help
```

---

## Usage

### GUI Application (Recommended)

```bash
# Launch graphical interface
python priAge_gui.py

# Or use launch scripts
# Windows:
run_priAge.bat

# Linux/Mac:
chmod +x run_priAge.sh
./run_priAge.sh
```

**Workflow:**
1. Click "Start Verification"
2. Present ID card to camera for hologram detection (wait for 80%+ confidence)
3. Hold ID steady for age extraction
4. Look at camera for facial recognition
5. Receive encrypted QR token + PIN

### CLI Application

```bash
# Full verification pipeline
python main_priAge.py

# Phase-specific operations
python id_hologram_detection.py       # Test hologram detection
python id_detection.py                 # Test OCR extraction
python id_facial_recognition.py        # Test face matching
```

### Token Decryption

```bash
# Decrypt and verify age token
python decrypt_qr_token.py

# Interactive prompts:
# 1. Select QR code input method (camera/file/manual)
# 2. Enter 6-digit PIN
# 3. View decrypted result: {"is_adult": true/false, "timestamp": "..."}
```

### GDPR Data Cleanup

```bash
# Preview what will be deleted (dry-run mode)
python gdpr_data_cleanup.py --dry-run --all

# Execute secure deletion
python gdpr_data_cleanup.py --all --verify

# Delete data older than 1 day
python gdpr_data_cleanup.py --all --older-than 1

# Generate compliance report
python gdpr_data_cleanup.py --all --verify --report
```

---

## Project Structure

```
PriAge/
│
├── priAge_gui.py                    # Main GUI application (CustomTkinter)
├── main_priAge.py                   # CLI verification pipeline
├── id_hologram_detection.py         # Phase 1: Hologram detection
├── id_detection.py                  # Phase 2: OCR + age extraction
├── id_facial_recognition.py         # Phase 3: Face matching
├── verification_token_gdpr.py       # Phase 4: Token generation
├── secure_deletion.py               # Phase 5: Data deletion
├── gdpr_data_cleanup.py             # GDPR cleanup utility
├── decrypt_qr_token.py              # Token decryption tool
├── anti_spoofing_detector.py        # Liveness detection wrapper
│
├── Silent-Face-Anti-Spoofing/       # Anti-spoofing ML models
│   └── src/                         # Detection algorithms
│
├── keys/                            # Encryption keys (AES-256)
├── outputs/                         # Temporary processing data
│   ├── snapshot_*.png               # ID card captures
│   ├── hologram_*.png               # Hologram crops
│   ├── facial_recognition/          # Face comparison images
│   ├── tokens/                      # Generated QR codes
│   └── logs/                        # Verification logs
│
├── my_model.pt                      # YOLO ID detection model (50MB)
├── holog_best.pt                    # YOLO hologram model (6MB)
│
├── requirements.txt                 # Python dependencies
├── INSTALL.txt                      # Detailed installation guide
├── README.md                        # This file
├── GDPR_COMPLIANCE_README.md        # GDPR documentation
├── CONTRIBUTING.md                  # Contribution guidelines
├── LICENSE                          # MIT License
└── .gitignore                       # Git exclusions
```

---

## Performance Benchmarks

### End-to-End Latency

Measured on test system (Intel Core i7, 16GB RAM, integrated GPU):

| Phase | Operation | Duration | Percentage |
|-------|-----------|----------|------------|
| Phase 1 | Hologram Detection | 9.96s | 19.2% |
| Phase 2 | Age Extraction (OCR) | 32.66s | 62.8% |
| Phase 3 | Facial Recognition | 8.88s | 17.1% |
| Phase 4 | Token Generation | 0.44s | 0.9% |
| **Total** | **End-to-End** | **51.95s** | **100%** |

**Notes:**
- Phase 2 dominates processing time due to EasyOCR initialization and inference
- First run includes model loading overhead (~5-10s)
- Subsequent verifications are faster due to cached models
- GPU acceleration can reduce total time to ~30-35 seconds

### Detection Accuracy Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| Hologram Confidence | 81.6% | Average confidence on physical ID cards |
| Hologram Threshold | 80% | Minimum required for Phase 1 pass |
| Liveness Score | 99.88% | Anti-spoofing detection confidence |
| Face Match Threshold | 1.35 | Euclidean distance (FaceNet embeddings) |
| OCR Accuracy | ~95% | Date-of-birth extraction (with error correction) |

**Test Conditions:**
- ID cards: Belgian national ID cards (with hologram)
- Lighting: Indoor office lighting (500-1000 lux)
- Camera: Standard 1080p webcam (30 FPS)
- Sample size: 10 verification sessions

---

## Model Performance

### YOLOv8 Hologram Detection

| Metric | Value |
|--------|-------|
| Model | YOLOv8n (nano) |
| Input Size | 640x640 |
| Parameters | ~3.2M |
| Confidence Threshold | 0.80 (80%) |
| Inference Time | ~50-100ms per frame |
| Target FPS | 10-20 FPS (real-time detection) |

**Training Details:**
- Framework: Ultralytics YOLOv8
- Classes: `hologram` (security holographic features)
- Dataset: Custom-labeled ID card images
- Augmentation: Rotation, brightness, blur, perspective transform

### YOLOv8 ID Field Detection

| Metric | Value |
|--------|-------|
| Model | YOLOv8n (nano) |
| Input Size | 640x640 |
| Classes | `date_of_birth`, `photo` |
| Confidence Threshold | Variable (label-specific) |
| Inference Time | ~50-100ms per frame |

### FaceNet Facial Recognition

| Metric | Value |
|--------|-------|
| Model | FaceNet (Inception ResNet V1) |
| Embedding Size | 512 dimensions |
| Distance Metric | Euclidean distance |
| Match Threshold | ≤ 1.35 |
| Face Detection | MTCNN (multi-task cascaded CNN) |
| False Accept Rate | < 1% (at threshold 1.35) |

---

## Security Features

### Attack Resistance Matrix

| Attack Vector | Detection Method | Protection Level |
|---------------|------------------|------------------|
| **Printed Photo Attack** | Hologram detection (Phase 1) | High |
| **Screen Replay Attack** | Hologram detection + liveness | High |
| **3D Mask Attack** | Silent-Face-Anti-Spoofing | Medium-High |
| **Deep Fake Video** | Liveness detection | Medium |
| **Stolen Token** | PIN required (2-factor) | High |
| **Token Replay** | Single-use enforcement | High |
| **Brute Force PIN** | 6-digit PIN (1M combinations) | Medium |
| **Data Recovery** | DoD 5220.22-M deletion | High |

### Encryption Specifications

**Token Encryption:**
```python
Algorithm: AES-256-GCM (Galois/Counter Mode)
Key Derivation: PBKDF2-SHA256
Iterations: 100,000
Salt: 32 bytes (cryptographically random)
Nonce: 16 bytes (unique per token)
Authentication Tag: 16 bytes (tamper detection)
```

**Token Structure:**
```json
{
  "is_adult": true,
  "timestamp": "2026-03-22T14:35:21",
  "token_id": "uuid4-random",
  "expires": "2026-03-23T14:35:21"
}
```

**Secure Deletion:**
- Standard: DoD 5220.22-M (3-pass overwrite)
- Pass 1: Write 0x00 (zeros)
- Pass 2: Write 0xFF (ones)
- Pass 3: Write random data
- Verification: Cryptographic hash comparison
- Result: Data forensically unrecoverable

---

## GDPR Compliance

### Compliance Matrix

| GDPR Article | Requirement | PriAge Implementation |
|--------------|-------------|-----------------------|
| **Article 5(1)(c)** | Data Minimization | Only `is_adult` boolean stored in token |
| **Article 5(1)(e)** | Storage Limitation | Automatic deletion (DoD 5220.22-M standard) |
| **Article 6** | Lawful Basis | Explicit consent before verification |
| **Article 9** | Biometric Data | Immediate deletion after facial recognition |
| **Article 17** | Right to Erasure | Manual cleanup tool (`gdpr_data_cleanup.py`) |
| **Article 25** | Data Protection by Design | Privacy-first architecture from ground up |
| **Article 32** | Security of Processing | AES-256-GCM encryption + secure deletion |
| **Article 35** | DPIA Recommendation | Full impact assessment documentation provided |

### Data Processing Flow

```
Personal Data Collected → Used Only for Verification → Immediately Deleted
         ↓                           ↓                          ↓
ID hologram image          Verify authenticity         Delete image
Date of birth text         Calculate is_adult          Delete DOB
ID photo crop             Match with live face         Delete photos
Live face capture         Liveness detection           Delete capture
         ↓                           ↓                          ↓
                    Output: {is_adult: true/false}
                           (encrypted token)
```

**Personal Data Retention:** 0 seconds (immediate deletion after token generation)

**Token Retention:** 24 hours (auto-expiration)

See [GDPR_COMPLIANCE_README.md](GDPR_COMPLIANCE_README.md) for complete documentation.

---

## Configuration

### Key Parameters

```python
# Phase 1: Hologram Detection
HOLOGRAM_CONFIDENCE_THRESHOLD = 0.80  # Require 80% confidence
SNAPSHOT_TRIGGER_THRESHOLD = 0.80     # Auto-capture at 80%

# Phase 2: OCR Extraction
OCR_LANGUAGES = ['en', 'fr', 'nl', 'de']  # Multi-language support
DATE_FORMAT_REGEX = r'\d{2}[./]\d{2}[./]\d{4}'  # DD/MM/YYYY

# Phase 3: Facial Recognition
FACE_MATCH_DISTANCE_THRESHOLD = 1.35   # FaceNet Euclidean distance
LIVENESS_THRESHOLD = 0.5               # Anti-spoofing confidence
MTCNN_DETECTION_THRESHOLDS = [0.6, 0.7, 0.7]  # MTCNN stages

# Phase 4: Token Generation
TOKEN_EXPIRATION_HOURS = 24            # 24-hour validity
PIN_LENGTH = 6                         # 6-digit PIN
PBKDF2_ITERATIONS = 100000             # Key derivation iterations

# Phase 5: Secure Deletion
DELETION_PASSES = 3                    # DoD 5220.22-M (3-pass)
VERIFY_DELETION = True                 # Cryptographic verification
```

---

## Technology Stack

### Core AI/ML Frameworks

- **YOLOv8** (Ultralytics) - Real-time object detection for hologram and ID fields
- **EasyOCR** - Multi-language optical character recognition
- **FaceNet** (Inception ResNet V1) - Facial recognition embeddings
- **MTCNN** - Multi-task cascaded convolutional networks for face detection
- **Silent-Face-Anti-Spoofing** - Deep learning liveness detection

### Cryptography & Security

- **PyCryptodome** - AES-256-GCM encryption
- **PBKDF2** - Key derivation function (OWASP recommended)
- **QR Code** - Token encoding (supports offline verification)
- **DoD 5220.22-M** - Military-grade secure deletion

### Application Frameworks

- **CustomTkinter** - Modern GUI with dark/light themes
- **OpenCV** - Video capture and image processing
- **PyTorch** - Deep learning inference engine
- **NumPy** - Numerical computations

---

## Requirements

### Python Dependencies

```
torch>=2.0.0                # Deep learning framework
ultralytics>=8.0.0          # YOLOv8 object detection
opencv-python>=4.8.0        # Computer vision
easyocr>=1.7.0              # Optical character recognition
facenet-pytorch>=2.5.0      # Facial recognition
customtkinter>=5.0.0        # Modern GUI toolkit
Pillow>=10.0.0              # Image processing
pycryptodome>=3.18.0        # Cryptography
qrcode>=7.4.2               # QR code generation
pyzbar>=0.1.9               # QR code decoding
numpy>=1.24.0               # Numerical arrays
scipy>=1.10.0               # Scientific computing
```

Full dependency list: [requirements.txt](requirements.txt)

---

## Known Limitations

1. **Processing Time:** 52-second end-to-end latency may be too slow for high-volume scenarios
2. **GPU Requirement:** CPU-only inference is significantly slower (~2-3x)
3. **Lighting Sensitivity:** Requires adequate lighting for hologram detection (500+ lux)
4. **ID Card Types:** Currently optimized for Belgian ID cards with holographic security features
5. **Language Support:** OCR limited to Latin alphabet languages (EN, FR, NL, DE)
6. **Camera Quality:** Minimum 720p webcam required for reliable facial recognition
7. **Research Status:** Not certified for production use without additional security audits

---

## Future Improvements

- **Performance Optimization:** Target <10 seconds total time (GPU optimization, model quantization)
- **Multi-Document Support:** Expand to passports, driver's licenses, residence permits
- **Mobile Support:** Android/iOS application with camera integration
- **Cloud Deployment:** Containerized deployment (Docker/Kubernetes)
- **Blockchain Integration:** Decentralized token verification
- **Biometric Template Protection:** Cancelable biometrics for enhanced privacy

---

## Documentation

- **[GDPR_COMPLIANCE_README.md](GDPR_COMPLIANCE_README.md)** - Complete GDPR compliance guide
- **[INSTALL.txt](INSTALL.txt)** - Detailed installation instructions
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to the project
- **[GITHUB_SETUP.md](GITHUB_SETUP.md)** - GitHub repository setup guide

---

## Citation

If you use PriAge in academic research, please cite:

```bibtex
@mastersthesis{pintoickowicz2026priage,
  author = {PINTO ICKOWICZ, Priscila},
  title = {Privacy-Preserving Age Verification under GDPR: AI-Based Identity Extraction and Encrypted Token Exchange},
  school = {Université Libre de Bruxelles, Faculty of Science},
  year = {2026},
  type = {Master's Thesis},
  address = {Brussels, Belgium},
  url = {https://github.com/PPICKO/PriAge},
  note = {Specialized Master in Data Science, Big Data}
}
```

---

## Important Notice

**This is a research/academic project.**

Before production deployment:
- Conduct comprehensive security audits
- Consult GDPR legal experts for compliance verification
- Test with diverse ID card types and demographics
- Implement rate limiting and abuse prevention
- Add logging and monitoring infrastructure
- Obtain necessary certifications (ISO 27001, etc.)

---

## License

MIT License - see [LICENSE](LICENSE) file.

Copyright (c) 2026 Priscila PINTO ICKOWICZ

---

## Contact & Support

**Author:** Priscila PINTO ICKOWICZ
**Institution:** Université Libre de Bruxelles (ULB)
**Program:** Specialized Master in Data Science, Big Data
**Supervisors:** Prof. Dimitris Sacharidis, Prof. Jan Tobias Mühlberg

**GitHub:** [@PPICKO](https://github.com/PPICKO)
**Repository Issues:** [github.com/PPICKO/PriAge/issues](https://github.com/PPICKO/PriAge/issues)

For model files access or collaboration inquiries, please open a GitHub issue.

---

**Built for Privacy and Security**
