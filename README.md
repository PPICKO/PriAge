# PriAge - Privacy-Preserving Age Verification

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GDPR](https://img.shields.io/badge/GDPR-Compliant-success.svg)](GDPR_COMPLIANCE_README.md)
[![Status](https://img.shields.io/badge/Status-Research-orange.svg)](https://github.com/PPICKO/PriAge)

A GDPR-compliant age verification system using AI-based identity document processing and encrypted token exchange. Preserving age verification system that verifies if someone is 18+ **without storing personal data**, using a GDPR-compliant 5-phase AI pipeline.

Master's Thesis Project - Université Libre de Bruxelles
Author: Priscila PINTO ICKOWICZ

---

## Features

- **Privacy-First**: No personal data stored, only `is_adult` boolean
- **GDPR Compliant**: Full compliance with EU data protection regulations
- **Secure**: AES-256-GCM encryption + DoD 5220.22-M secure deletion
- **Accurate**: Multi-model AI pipeline with anti-spoofing
- **Fast**: ~50 seconds total verification time
- **User-Friendly**: Both CLI and GUI interfaces

---

## How It Works

PriAge uses a **5-phase verification pipeline**:

### Phase 1: ID Authenticity Check
- YOLOv8 detects holographic security features
- Verifies physical ID card (not screen/photo)

### Phase 2: Age Extraction
- YOLO + EasyOCR extract date of birth
- Multi-language support (EN, FR, NL, DE)
- Automatic OCR error correction

### Phase 3: Facial Recognition
- FaceNet matches ID photo to live face
- MTCNN face detection
- Anti-spoofing liveness detection

### Phase 4: Token Generation
- Generates encrypted QR code
- Contains **ONLY** `is_adult: true/false`
- AES-256-GCM + PBKDF2-SHA256
- Single-use, 24-hour validity

### Phase 5: Data Deletion
- **DoD 5220.22-M** secure deletion
- All personal data permanently erased
- Only encrypted token remains

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/PPICKO/PriAge.git
cd PriAge

# Install dependencies
pip install -r requirements.txt

# Run GUI application
python priAge_gui.py
```

**Note:** YOLO model files (56MB total) must be downloaded separately. See [Installation](#installation).

---

## Installation

### Prerequisites

- Python 3.8 - 3.11
- Webcam (for ID card and face capture)
- 4GB RAM minimum (8GB recommended)
- 500MB disk space

### Step 1: Clone Repository

```bash
git clone https://github.com/PPICKO/PriAge.git
cd PriAge
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

###Step 3: Download Models

**Important:** Model files are not included in the repository due to size.

Contact repository owner for access to:
- `my_model.pt` (50MB) - YOLO ID detection model
- `holog_best.pt` (6MB) - YOLO hologram detection model

Place these files in the root directory.

### Step 4: Run Application

```bash
# Windows
run_priAge.bat

# Linux/Mac
./run_priAge.sh

# Or manually
python priAge_gui.py
```

---

## GDPR Compliance

| GDPR Article | Requirement | Implementation |
|--------------|-------------|----------------|
| Article 5(1)(c) | Data Minimization | Only `is_adult` boolean stored |
| Article 5(1)(e) | Storage Limitation | Automatic deletion (DoD 5220.22-M) |
| Article 9 | Biometric Data | Immediate deletion after processing |
| Article 17 | Right to Erasure | Secure deletion tool included |
| Article 25 | Data Protection by Design | Privacy-first architecture |
| Article 32 | Security | AES-256-GCM encryption |

See [GDPR_COMPLIANCE_README.md](GDPR_COMPLIANCE_README.md) for complete documentation.

---

## Usage Examples

### GUI Application

```bash
python priAge_gui.py
```

Follow on-screen instructions through 5 phases.

### GDPR Data Cleanup

```bash
# Dry run
python gdpr_data_cleanup.py --dry-run --all

# Actual deletion
python gdpr_data_cleanup.py --all --verify

# Delete data older than 1 day
python gdpr_data_cleanup.py --all --older-than 1
```

### Token Decryption

```bash
python decrypt_qr_token.py
```

---

## Technology Stack

- **YOLOv8** - Object detection
- **EasyOCR** - Text extraction
- **FaceNet** - Facial recognition
- **MTCNN** - Face detection
- **Silent-Face-Anti-Spoofing** - Liveness detection
- **AES-256-GCM** - Encryption
- **CustomTkinter** - GUI framework
- **PyTorch** - Deep learning

---

## Documentation

- [GDPR_COMPLIANCE_README.md](GDPR_COMPLIANCE_README.md) - Complete GDPR guide
- [INSTALL.txt](INSTALL.txt) - Installation instructions
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

---

## Important

This is a **research/academic project**. Before production deployment:
- Consult GDPR legal experts
- Conduct security audits
- Test in your environment

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Contact

**Author:** Priscila PINTO ICKOWICZ

**GitHub:** [@PPICKO](https://github.com/PPICKO)

---

**Built for Privacy and Security** 
