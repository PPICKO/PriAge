"""
QR Code Token Decryption Tool
Decrypt and verify GDPR-compliant verification tokens.

Usage:
1. Scan QR code with camera OR load from file
2. Enter 6-digit PIN
3. System decrypts and displays token contents
"""

import cv2
import json
import logging
import sys
from pathlib import Path
from pyzbar import pyzbar

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from verification_token_gdpr import GDPRCompliantTokenGenerator


class QRTokenDecryptor:
    """Decrypt and verify QR code tokens."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.generator = GDPRCompliantTokenGenerator()

    def scan_qr_from_camera(self) -> str:
        """
        Scan QR code using camera.

        Returns:
            QR code data as string
        """
        print("\n" + "=" * 70)
        print("QR CODE SCANNER")
        print("=" * 70)
        print("Position QR code in front of camera...")
        print("Press 'q' to cancel")
        print()

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Failed to open camera!")
            return None

        qr_data = None

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Detect QR codes
                decoded_objects = pyzbar.decode(frame)

                for obj in decoded_objects:
                    # Draw rectangle around QR code
                    points = obj.polygon
                    if len(points) == 4:
                        pts = [(point.x, point.y) for point in points]
                        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 255, 0), 3)

                    # Extract data
                    qr_data = obj.data.decode('utf-8')
                    cv2.putText(frame, "QR CODE DETECTED!", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    print("QR code detected!")
                    break

                # Display instructions
                cv2.putText(frame, "Position QR code in frame", (10, frame.shape[0] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                cv2.putText(frame, "Press 'q' to cancel", (10, frame.shape[0] - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

                cv2.imshow("QR Code Scanner", frame)

                if qr_data:
                    break

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("Cancelled by user")
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        return qr_data

    def load_qr_from_file(self, file_path: Path) -> str:
        """
        Load and decode QR code from image file.

        Args:
            file_path: Path to QR code image

        Returns:
            QR code data as string
        """
        print(f"\nLoading QR code from: {file_path}")

        img = cv2.imread(str(file_path))
        if img is None:
            print(f" Failed to load image: {file_path}")
            return None

        # Decode QR code
        decoded_objects = pyzbar.decode(img)

        if not decoded_objects:
            print(" No QR code found in image")
            return None

        qr_data = decoded_objects[0].data.decode('utf-8')
        print(" QR code loaded successfully")

        return qr_data

    def decrypt_token(self, qr_data: str, pin: str) -> dict:
        """
        Decrypt token using PIN.

        Args:
            qr_data: QR code JSON data
            pin: 6-digit PIN

        Returns:
            Decrypted token data or None
        """
        try:
            # Parse QR code JSON
            token_data = json.loads(qr_data)

            print("\n" + "=" * 70)
            print("TOKEN INFORMATION")
            print("=" * 70)
            print(f"Token Type: {token_data.get('type', 'unknown')}")
            print(f"Version: {token_data.get('version', 'unknown')}")
            print(f"Session ID: {token_data.get('session_id', 'unknown')}")
            print(f"Timestamp: {token_data.get('timestamp', 'unknown')}")
            print(f"Expires At: {token_data.get('expires_at', 'unknown')}")
            print()

            # Decrypt with PIN
            print("Decrypting token with PIN...")
            decrypted_data = self.generator.verify(token_data, pin)

            return decrypted_data

        except json.JSONDecodeError:
            print(" Invalid QR code format (not JSON)")
            return None
        except Exception as e:
            print(f" Decryption failed: {e}")
            return None

    def display_decrypted_data(self, data: dict):
        """
        Display decrypted token contents.

        Args:
            data: Decrypted token data
        """
        print("\n" + "=" * 70)
        print(" DECRYPTION SUCCESSFUL!")
        print("=" * 70)
        print()
        print("VERIFICATION RESULT:")
        print("-" * 70)

        # Display key information
        is_adult = data.get('is_adult', False)
        print(f"  Age Verified: {data.get('age_verified', 'N/A')}")
        print(f"  Is Adult (18+): {is_adult}")

        if is_adult:
            print("  → User is 18 or older ✓")
        else:
            print("  → User is under 18 ✗")

        print()
        print("METADATA:")
        print("-" * 70)
        print(f"  Session ID: {data.get('session_id', 'N/A')}")
        print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
        print(f"  Expires At: {data.get('expires_at', 'N/A')}")
        print(f"  Single Use: {data.get('single_use', 'N/A')}")
        print(f"  Version: {data.get('version', 'N/A')}")

        print()
        print("GDPR COMPLIANCE CHECK:")
        print("-" * 70)

        # Check for data minimization
        prohibited_fields = ['age', 'date_of_birth', 'name', 'address', 'photo']
        violations = [field for field in prohibited_fields if field in data]

        if not violations:
            print("  Data minimized: ONLY is_adult boolean")
            print("  NO age, DOB, name, or biometric data")
            print("  GDPR Article 5(1)(c) compliant")
        else:
            print(f"  WARNING: Found prohibited fields: {violations}")
            print("   Not GDPR compliant!")

        print()
        print("=" * 70)


def main():
    """Main decryption tool."""
    print("\n" + "=" * 70)
    print("GDPR-COMPLIANT TOKEN DECRYPTION TOOL")
    print("=" * 70)
    print()
    print("This tool decrypts and verifies age verification tokens.")
    print()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    decryptor = QRTokenDecryptor()

    # Choose input method
    print("How do you want to provide the QR code?")
    print("  1. Scan with camera")
    print("  2. Load from file")
    print()
    choice = input("Enter choice (1 or 2): ").strip()

    qr_data = None

    if choice == "1":
        # Scan with camera
        qr_data = decryptor.scan_qr_from_camera()
    elif choice == "2":
        # Load from file
        print()
        print("Recent tokens:")
        tokens_dir = Path("outputs/tokens")
        if tokens_dir.exists():
            token_files = sorted(tokens_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
            for i, token_file in enumerate(token_files[:5], 1):
                print(f"  {i}. {token_file.name}")

        print()
        file_path = input("Enter QR code file path (or number from list): ").strip()

        # Check if user entered a number
        if file_path.isdigit():
            idx = int(file_path) - 1
            if 0 <= idx < len(token_files):
                file_path = token_files[idx]
            else:
                print(" Invalid number")
                return 1

        qr_data = decryptor.load_qr_from_file(Path(file_path))
    else:
        print(" Invalid choice")
        return 1

    if not qr_data:
        print(" Failed to get QR code data")
        return 1

    # Get PIN from user
    print()
    print("=" * 70)
    pin = input("Enter 6-digit PIN: ").strip()

    if len(pin) != 6 or not pin.isdigit():
        print(" Invalid PIN format (must be 6 digits)")
        return 1

    # Decrypt token
    decrypted_data = decryptor.decrypt_token(qr_data, pin)

    if decrypted_data:
        # Display results
        decryptor.display_decrypted_data(decrypted_data)
        return 0
    else:
        print("\n" + "=" * 70)
        print(" DECRYPTION FAILED")
        print("=" * 70)
        print()
        print("Possible reasons:")
        print("  1. Incorrect PIN")
        print("  2. Token expired")
        print("  3. Token already used (single-use)")
        print("  4. Corrupted QR code")
        print()
        print("Please verify:")
        print("  - PIN is correct (6 digits)")
        print("  - Token has not expired (24 hours)")
        print("  - Token has not been used before")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    import numpy as np
    sys.exit(main())
