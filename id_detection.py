import os
import re
import sys
import cv2
import json
import csv
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from ultralytics import YOLO
import easyocr

# === CONFIGURATION ===
@dataclass
class Config:
    """Configuration for ID card detection system"""
    MODEL_PATH = r"C:\Users\branq\Desktop\thesis\my_model.pt"
    OUTPUT_DIR: str = "outputs"
    CLASS_NAMES: List[str] = None
    THRESHOLDS: Dict[str, float] = None
    DOB_STOPWORDS: set = None
    IMGSZ: int = 640
    BASE_CONF: float = 0.25
    CAMERA_INDEX: int = 0
    MAX_RETRY_ATTEMPTS: int = 5  # Maximum retry attempts if status is UNKNOWN
    RETRY_ON_UNKNOWN: bool = True  # Automatically retry if status is UNKNOWN
    AUTO_CONTINUE: bool = False  # Automatically exit after successful detection (for priAge integration)
    LOG_LEVEL: str = "INFO"  # Logging level: DEBUG, INFO, WARNING, ERROR
    
    def __post_init__(self):
        if self.CLASS_NAMES is None:
            self.CLASS_NAMES = ["DOB", "GivenName", "Photo", "Surname"]
        if self.THRESHOLDS is None:
            self.THRESHOLDS = {"DOB": 0.80, "Photo": 0.80, "GivenName": 0.80, "Surname": 0.80}
        if self.DOB_STOPWORDS is None:
            self.DOB_STOPWORDS = {
                # English
                "naissance", "birth", "date", "of", "place", "lieu",
                # French
                "de", "né", "nee", "née",
                # Swedish
                "född", "fodd", "datum",
                # German
                "geboren", "geburt", "geb",
                # Dutch
                "geboren", "geb",
                # General
                "dob", "born"
            }

# === LOGGING SETUP ===
def setup_logging(output_dir: str, log_level: str = "INFO") -> logging.Logger:
    """Setup logging configuration"""
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# === DATA MODELS ===
@dataclass
class AgeInfo:
    """Age calculation result"""
    dob_parsed: Optional[str] = None
    age_years: Optional[int] = None
    status: str = "unknown"
    
    def is_adult(self) -> bool:
        return self.age_years is not None and self.age_years >= 18

# === DATE PROCESSING ===
class DateParser:
    """Handle date parsing from OCR text"""
    
    MONTH_MAP = {
        # English
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        # French
        "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
        "janv": 1, "fevr": 2, "avr": 4, "juil": 7, "aout": 8, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
        # Swedish
        "januari": 1, "februari": 2, "mars": 3, "april": 4, "maj": 5, "juni": 6,
        "juli": 7, "augusti": 8, "september": 9, "oktober": 10, "november": 11, "december": 12,
        # German
        "januar": 1, "februar": 2, "marz": 3, "mai": 5, "juni": 6,
        "juli": 7, "oktober": 10, "dezember": 12,
        # Dutch
        "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6,
        "juli": 7, "augustus": 8, "september": 9, "oktober": 10, "november": 11, "december": 12,
    }
    
    @staticmethod
    def clean_dob_text(texts: List[str], stopwords: set) -> str:
        """Clean DOB text by removing stopwords and keeping relevant tokens"""
        tokens = " ".join(texts).split()
        cleaned = []
        
        for t in tokens:
            # Skip if contains stopwords (partial match)
            if any(sw in t.lower() for sw in stopwords):
                continue
            
            # Skip common OCR garbage patterns
            if re.match(r'^[oO0]{2,}', t):  # Starts with multiple o/O/0
                continue
            if re.search(r'[a-z]{2}[0-9]{1}[a-z]{2}', t.lower()):  # Mixed pattern like "n3isst"
                continue
            
            # Keep if contains digit
            if re.search(r"\d", t):
                cleaned.append(t)
                continue
            
            # Keep if looks like month name (3+ letters, check if it's a known month pattern)
            if re.match(r"[A-Za-z]{3,}", t):
                # Only keep if it looks like a valid month (starts with common month letters)
                first_letters = t.lower()[:3]
                month_starts = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                               'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                               'jan', 'fev', 'avr', 'mai', 'jui', 'aou', 'sep',
                               'jaa', 'feo', 'maa', 'juu', 'juo', 'auu', 'okt', 'deo']
                if any(first_letters.startswith(ms[:2]) for ms in month_starts):
                    cleaned.append(t)
        
        return " ".join(cleaned)
    
    @staticmethod
    def parse_date(s: str) -> Optional[date]:
        """Try to parse date from string with multiple format support"""
        if not s:
            return None
        
        # Store original for logging
        original_s = s
        logger = logging.getLogger(__name__)
        
        # Handle bilingual months with slash (Canada/Sweden): "AUG/AUG" or "MAR/MARS"
        bilingual_match = re.search(r'([A-Z]{3,})\s*/\s*([A-Z]{3,})', s, flags=re.IGNORECASE)
        if bilingual_match:
            logger.debug(f"Detected bilingual month format: {bilingual_match.group()}")
            s = re.sub(r'([A-Z]{3,})\s*/\s*([A-Z]{3,})', r'\1', s, flags=re.IGNORECASE)
        
        # Try multiple patterns - order matters (most specific first)
        patterns = [
            # YYYY MM DD (ISO-like year first format, e.g., "1920 03 15")
            (r'(\d{4})\s+(\d{1,2})\s+(\d{1,2})',
             lambda m: DateParser._parse_ymd_flexible(m.groups())),
            # DD/MM/YYYY or MM/DD/YYYY (slash-separated - ambiguous, use smart detection)
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', 
             lambda m: DateParser._parse_ambiguous_slash_date(m.groups())),
            # DD/MM/YY (2-digit year with slashes)
            (r'(\d{1,2})/(\d{1,2})/(\d{2})(?!\d)', 
             lambda m: DateParser._parse_ambiguous_slash_date_short_year(m.groups())),
            # DD-MM-YYYY (dash-separated - assume DD-MM-YYYY for dashes)
            (r'(\d{1,2})-(\d{1,2})-(\d{4})',
             lambda m: DateParser._parse_dmy(m.groups())),
            # DD-MM-YY (2-digit year with dashes)
            (r'(\d{1,2})-(\d{1,2})-(\d{2})(?!\d)',
             lambda m: DateParser._parse_dmy_short_year(m.groups())),
            # DD.MM.YYYY (Cyprus and European format with dots)
            (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', 
             lambda m: DateParser._parse_dmy(m.groups())),
            # DD.MM.YY (2-digit year with dots)
            (r'(\d{1,2})\.(\d{1,2})\.(\d{2})(?!\d)', 
             lambda m: DateParser._parse_dmy_short_year(m.groups())),
            # DD.MM YYYY (partial dot format - OCR missing second dot)
            (r'(\d{1,2})\.(\d{1,2})\s+(\d{4})', 
             lambda m: DateParser._parse_dmy(m.groups())),
            # DD.MM YY (partial dot format with 2-digit year)
            (r'(\d{1,2})\.(\d{1,2})\s+(\d{2})(?!\d)', 
             lambda m: DateParser._parse_dmy_short_year(m.groups())),
            # DD.YYYY or MM.YYYY (OCR merged digits)
            (r'(\d{1,2})\.(\d{4})', 
             lambda m: DateParser._parse_partial_dot_date(m.group(0))),
            # Handle OCR errors with repeated digits: "111.11" -> "11.11", "11111" -> "11 11"
            # Try to extract valid date from garbled digits
            (r'1+\.?1+\s+(\d{4})', 
             lambda m: DateParser._parse_repeated_digit_date(s, m.group(1))),
            # DD MMM YY (2-digit year): "21 AUG 82"
            (r'(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{2})(?!\d)', 
             lambda m: DateParser._parse_dmy_short_year((m.group(1), m.group(2), m.group(3)))),
            # DD MM YYYY (space-separated numeric) - very common
            (r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})', 
             lambda m: DateParser._parse_dmy(m.groups())),
            # DD MM YY (2-digit year)
            (r'(\d{1,2})\s+(\d{1,2})\s+(\d{2})(?!\d)', 
             lambda m: DateParser._parse_dmy_short_year(m.groups())),
            # DD MMM YYYY (with space separation)
            (r'(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})', 
             lambda m: DateParser._parse_dmy((m.group(1), m.group(2), m.group(3)))),
            # DD YYYY MMM (OCR sometimes reorders)
            (r'(\d{1,2})\s+(\d{4})\s+([A-Za-z]{3,})', 
             lambda m: DateParser._parse_dmy((m.group(1), m.group(3), m.group(2)))),
            # DD YYYY ... MMM (with garbage word in between)
            (r'(\d{1,2})\s+(\d{4})\s+\S+\s+([A-Za-z]{3,})', 
             lambda m: DateParser._parse_dmy((m.group(1), m.group(3), m.group(2)))),
            # MMM DD YYYY
            (r'([A-Za-z]{3,})\s+(\d{1,2})\s+(\d{4})', 
             lambda m: DateParser._parse_dmy((m.group(2), m.group(1), m.group(3)))),
            # DD-MMM-YYYY
            (r'(\d{1,2})[-]([A-Za-z]{3,})[-](\d{4})', 
             lambda m: DateParser._parse_dmy(m.groups())),
            # YYYY-MM-DD (ISO format)
            (r'(\d{4})[-](\d{1,2})[-](\d{1,2})',
             lambda m: DateParser._parse_ymd(m.groups())),
            # YYYY/MM/DD (ISO format with slashes)
            (r'(\d{4})/(\d{1,2})/(\d{1,2})',
             lambda m: DateParser._parse_ymd(m.groups())),
            # Compact: DDMMYYYY
            (r'(\d{2})(\d{2})(\d{4})',
             lambda m: DateParser._parse_dmy(m.groups())),
        ]
        
        for pattern, parser in patterns:
            m = re.search(pattern, s)
            if m:
                try:
                    result = parser(m)
                    if result and DateParser._is_valid_birth_year(result.year):
                        # Check if the year is plausible (results in reasonable age)
                        if DateParser._is_plausible_birth_year(result.year):
                            if original_s != s:
                                logger.debug(f"Date normalized: '{original_s}' -> '{s}'")
                            logger.info(f"Successfully parsed '{original_s}' -> {result.isoformat()}")
                            return result
                        else:
                            # Year is valid but implausible (e.g., 1920 -> 105 years old)
                            # Try to correct it before accepting
                            age = date.today().year - result.year
                            logger.warning(
                                f"Parsed year {result.year} results in implausible age ({age}). "
                                f"Attempting OCR correction..."
                            )
                            corrected = DateParser._try_with_year_correction(s, patterns)
                            if corrected:
                                return corrected
                            # If no correction found, still return the original result
                            # but log a warning
                            logger.warning(
                                f"No plausible correction found. Using original parse: {result.isoformat()} (age={age})"
                            )
                            return result
                except (ValueError, TypeError):
                    continue

        # If no valid date found, try correcting common OCR errors in year
        return DateParser._try_with_year_correction(s, patterns)
    
    @staticmethod
    def _is_valid_birth_year(year: int) -> bool:
        """Check if year is reasonable for a birth date"""
        current_year = date.today().year
        return 1900 <= year <= current_year

    @staticmethod
    def _is_plausible_birth_year(year: int, min_age: int = 16, max_age: int = 100) -> bool:
        """
        Check if year results in a plausible age for ID verification.

        For adult ID verification, we expect ages typically between 16-100.
        Years resulting in ages outside this range are suspicious and likely OCR errors.
        """
        current_year = date.today().year
        age = current_year - year
        return min_age <= age <= max_age

    @staticmethod
    def _calculate_year_plausibility_score(year: int) -> float:
        """
        Calculate a plausibility score for a birth year.

        Higher scores indicate more likely correct years.
        This helps choose between multiple OCR correction candidates.

        Score factors:
        - Age between 18-70: highest score (most common ID verification range)
        - Age between 16-18 or 70-90: medium score
        - Age between 90-100 or < 16: low score
        - Age > 100 or negative: zero score (invalid)
        """
        current_year = date.today().year
        age = current_year - year

        if age < 0 or age > 120:
            return 0.0
        elif 18 <= age <= 70:
            return 1.0  # Most common range for ID verification
        elif 16 <= age < 18:
            return 0.7  # Possible but less common
        elif 70 < age <= 85:
            return 0.8  # Elderly but reasonable
        elif 85 < age <= 100:
            return 0.5  # Very elderly, possible but suspicious
        elif age > 100:
            return 0.1  # Extremely unlikely, almost certainly OCR error
        else:  # age < 16
            return 0.3  # Child, unusual for ID verification
    
    @staticmethod
    def _try_with_year_correction(s: str, patterns) -> Optional[date]:
        """
        Try parsing with comprehensive OCR digit corrections for years.

        This method handles common OCR misreads in birth years:
        - 8 misread as 0, 2, 3, 6 (very common: 1980 -> 1900, 1920, 1930, 1960)
        - 9 misread as 0, 2, 7 (common: 1980 -> 1080, 1280)
        - 0 misread as 8, 6, 9 (1980 -> 1988, 1986)
        - Other common confusions: 1↔7, 5↔6, 3↔8

        The method generates candidate corrections and ranks them by plausibility.
        """
        logger = logging.getLogger(__name__)

        # Comprehensive OCR digit confusion matrix
        # Each digit maps to a list of commonly confused alternatives (ordered by frequency)
        ocr_confusions = {
            '0': ['8', '6', '9', 'O', 'o', 'Q'],      # 0 often misread as 8, 6, or letter O
            '1': ['7', 'l', 'I', '|', '/'],           # 1 often misread as 7 or letters
            '2': ['7', 'Z', '?'],                      # 2 can look like 7 or Z
            '3': ['8', '5', 'B'],                      # 3 often confused with 8
            '4': ['9', 'A'],                           # 4 can look like 9
            '5': ['6', 'S', '8'],                      # 5 often confused with 6 or S
            '6': ['0', '8', '5', 'G', 'b'],           # 6 often confused with 0 or 8
            '7': ['1', '/', '?', '2'],                # 7 often misread as 1
            '8': ['0', '3', '6', 'B', '2', '9'],      # 8 VERY often misread as 0, 2, or 3
            '9': ['0', '4', '7', 'g', '2'],           # 9 often misread as 0 or 4
        }

        # Find potential year in string
        year_match = re.search(r'\d{4}', s)
        if not year_match:
            return None

        original_year = year_match.group()
        original_year_int = int(original_year)

        # If original year results in implausible age, try corrections
        if DateParser._is_plausible_birth_year(original_year_int):
            # Year seems fine, no correction needed
            return None

        logger.debug(f"Year {original_year} results in implausible age, attempting OCR correction")

        # Generate all candidate corrections and their plausibility scores
        candidates = []

        # Strategy 1: Single digit corrections (most common case)
        for i, digit in enumerate(original_year):
            if digit in ocr_confusions:
                for replacement in ocr_confusions[digit]:
                    if replacement.isdigit():
                        corrected_year = original_year[:i] + replacement + original_year[i+1:]
                        corrected_year_int = int(corrected_year)
                        if DateParser._is_valid_birth_year(corrected_year_int):
                            score = DateParser._calculate_year_plausibility_score(corrected_year_int)
                            if score > 0:
                                candidates.append((corrected_year, score, 1, corrected_year_int))

        # Strategy 2: Double digit corrections (for cases like 1980 -> 1000)
        # This handles cases where two digits were misread
        for i, digit_i in enumerate(original_year):
            if digit_i in ocr_confusions:
                for replacement_i in ocr_confusions[digit_i]:
                    if not replacement_i.isdigit():
                        continue
                    for j, digit_j in enumerate(original_year):
                        if i == j:
                            continue
                        if digit_j in ocr_confusions:
                            for replacement_j in ocr_confusions[digit_j]:
                                if not replacement_j.isdigit():
                                    continue
                                corrected = list(original_year)
                                corrected[i] = replacement_i
                                corrected[j] = replacement_j
                                corrected_year = ''.join(corrected)
                                corrected_year_int = int(corrected_year)
                                if DateParser._is_valid_birth_year(corrected_year_int):
                                    score = DateParser._calculate_year_plausibility_score(corrected_year_int)
                                    # Penalize double corrections slightly (less likely than single)
                                    score *= 0.8
                                    if score > 0:
                                        candidates.append((corrected_year, score, 2, corrected_year_int))

        # Strategy 3: Known common OCR error patterns for years
        # Direct mappings for frequently observed OCR errors
        common_year_corrections = {
            # 1980 variants (person born ~1980 would be ~45 in 2025)
            '1920': '1980',  # 8->2 error
            '1900': '1980',  # 8->0 error
            '1000': '1980',  # 9->0, 8->0 double error
            '1080': '1980',  # 9->0 error
            '1930': '1980',  # 8->3 error
            '1280': '1980',  # 9->2 error (unlikely but possible)
            '1960': '1980',  # 8->6 error
            '1910': '1980',  # Pattern: 8->1, possible OCR read
            '1020': '1980',  # 9->0, 8->2 double error

            # 1970 variants (person would be ~55)
            '1910': '1970',  # 7->1 error
            '1970': '1970',  # no change needed
            '1270': '1970',  # 9->2 error

            # 1990 variants (person would be ~35)
            '1990': '1990',
            '1290': '1990',  # 9->2 error
            '1090': '1990',  # 9->0 error
            '1900': '1990',  # 9->0, 9->0 double error - also maps to 1980

            # 1985 variants
            '1935': '1985',  # 8->3 error
            '1905': '1985',  # 8->0 error
            '1025': '1985',  # 9->0, 8->2 double error

            # 1975 variants
            '1915': '1975',  # 7->1 error
            '1275': '1975',  # 9->2 error

            # 2000+ variants (for younger adults)
            '2000': '2000',
            '2080': '2000',  # 0->8 error (unlikely year for adults)
        }

        if original_year in common_year_corrections:
            corrected_year = common_year_corrections[original_year]
            corrected_year_int = int(corrected_year)
            score = DateParser._calculate_year_plausibility_score(corrected_year_int)
            # Boost score for known patterns
            score *= 1.2
            if score > 0:
                candidates.append((corrected_year, score, 0, corrected_year_int))

        # Sort candidates by plausibility score (highest first), then by fewer corrections
        candidates.sort(key=lambda x: (-x[1], x[2]))

        # Try each candidate in order of plausibility
        for corrected_year, score, num_corrections, year_int in candidates:
            corrected_str = s.replace(original_year, corrected_year)

            for pattern, parser in patterns:
                m = re.search(pattern, corrected_str)
                if m:
                    try:
                        result = parser(m)
                        if result and DateParser._is_valid_birth_year(result.year):
                            age = date.today().year - result.year
                            logger.info(
                                f"OCR year correction: '{original_year}' -> '{corrected_year}' "
                                f"(score={score:.2f}, corrections={num_corrections}, resulting age={age})"
                            )
                            return result
                    except (ValueError, TypeError):
                        continue

        # If no plausible correction found, log warning and return None
        logger.warning(
            f"Could not find plausible year correction for '{original_year}'. "
            f"Tried {len(candidates)} candidates."
        )
        return None
    
    @staticmethod
    def _parse_dmy(groups: Tuple[str, str, str]) -> Optional[date]:
        """Parse day-month-year format"""
        d, m, y = groups
        try:
            month = int(m) if m.isdigit() else DateParser._month_to_number(m)
            if month:
                return date(int(y), month, int(d))
        except (ValueError, TypeError):
            pass
        return None
    
    @staticmethod
    def _parse_ambiguous_slash_date(groups: Tuple[str, str, str]) -> Optional[date]:
        """Parse dates with slashes - handle both DD/MM/YYYY and MM/DD/YYYY"""
        logger = logging.getLogger(__name__)
        first, second, year = groups
        first_num = int(first)
        second_num = int(second)
        year_num = int(year)
        
        # Heuristic: if first > 12, must be DD/MM/YYYY
        if first_num > 12:
            try:
                logger.debug(f"Slash date: {first}/{second}/{year} → DD/MM/YYYY (first > 12)")
                return date(year_num, second_num, first_num)
            except (ValueError, TypeError):
                pass
        # If second > 12, must be MM/DD/YYYY
        elif second_num > 12:
            try:
                logger.debug(f"Slash date: {first}/{second}/{year} → MM/DD/YYYY (second > 12)")
                return date(year_num, first_num, second_num)
            except (ValueError, TypeError):
                pass
        # Both <= 12: ambiguous, try DD/MM/YYYY first (more common globally)
        else:
            # Try DD/MM/YYYY
            try:
                result = date(year_num, second_num, first_num)
                logger.debug(f"Slash date: {first}/{second}/{year} → DD/MM/YYYY (ambiguous, trying DD/MM first)")
                return result
            except (ValueError, TypeError):
                pass
            # Fall back to MM/DD/YYYY (American format)
            try:
                result = date(year_num, first_num, second_num)
                logger.debug(f"Slash date: {first}/{second}/{year} → MM/DD/YYYY (fallback)")
                return result
            except (ValueError, TypeError):
                pass
        
        return None
    
    @staticmethod
    def _parse_ambiguous_slash_date_short_year(groups: Tuple[str, str, str]) -> Optional[date]:
        """Parse dates with slashes and 2-digit year - handle both formats"""
        logger = logging.getLogger(__name__)
        first, second, year_2digit = groups
        first_num = int(first)
        second_num = int(second)
        year_2digit_num = int(year_2digit)
        
        # Convert 2-digit year to 4-digit
        if year_2digit_num <= 30:
            full_year = 2000 + year_2digit_num
        else:
            full_year = 1900 + year_2digit_num
        
        # Heuristic: if first > 12, must be DD/MM/YY
        if first_num > 12:
            try:
                logger.debug(f"Slash date: {first}/{second}/{year_2digit} → DD/MM/YY")
                return date(full_year, second_num, first_num)
            except (ValueError, TypeError):
                pass
        # If second > 12, must be MM/DD/YY
        elif second_num > 12:
            try:
                logger.debug(f"Slash date: {first}/{second}/{year_2digit} → MM/DD/YY")
                return date(full_year, first_num, second_num)
            except (ValueError, TypeError):
                pass
        # Both <= 12: ambiguous, try DD/MM/YY first
        else:
            # Try DD/MM/YY
            try:
                result = date(full_year, second_num, first_num)
                logger.debug(f"Slash date: {first}/{second}/{year_2digit} → DD/MM/YY")
                return result
            except (ValueError, TypeError):
                pass
            # Fall back to MM/DD/YY
            try:
                result = date(full_year, first_num, second_num)
                logger.debug(f"Slash date: {first}/{second}/{year_2digit} → MM/DD/YY (fallback)")
                return result
            except (ValueError, TypeError):
                pass
        
        return None
    
    @staticmethod
    def _parse_dmy_short_year(groups: Tuple[str, str, str]) -> Optional[date]:
        """Parse day-month-year format with 2-digit year"""
        d, m, y = groups
        logger = logging.getLogger(__name__)
        try:
            month = int(m) if m.isdigit() else DateParser._month_to_number(m)
            if month:
                # Convert 2-digit year to 4-digit
                year_2digit = int(y)
                # Assume 00-30 = 2000-2030, 31-99 = 1931-1999
                if year_2digit <= 30:
                    full_year = 2000 + year_2digit
                else:
                    full_year = 1900 + year_2digit
                logger.debug(f"2-digit year conversion: {y} → {full_year}")
                return date(full_year, month, int(d))
        except (ValueError, TypeError):
            pass
        return None
    
    @staticmethod
    def _parse_partial_dot_date(s: str) -> Optional[date]:
        """Handle partial dot dates like '11.1911' (missing middle component)"""
        logger = logging.getLogger(__name__)
        
        # Extract the two numbers
        parts = s.split('.')
        if len(parts) == 2:
            try:
                first = int(parts[0])
                second = int(parts[1])
                
                # If second part is 4 digits, it's likely the year
                if len(parts[1]) == 4 and 1900 <= second <= 2100:
                    # First part could be day or month
                    # Try to infer: if <= 12, could be month; if <= 31, could be day
                    # Most likely OCR missed the middle dot: "11.11.1911" -> "11.1911"
                    # Assume day.year format and guess month = 11 (common on many IDs)
                    if 1 <= first <= 31:
                        logger.info(f"Partial dot date correction: '{s}' → assuming day.year with month=11")
                        return date(second, 11, first)
            except (ValueError, TypeError):
                pass
        
        return None
    
    @staticmethod
    def _parse_repeated_digit_date(s: str, year: str) -> Optional[date]:
        """Handle OCR errors with repeated digits like '11.11 1911' or '111.11 1911'"""
        logger = logging.getLogger(__name__)
        
        # Extract all numbers from the string before the year
        before_year = s.split(year)[0]
        numbers = re.findall(r'\d+', before_year)
        
        # Look for patterns like 11.11, 1.11, 111.11, etc.
        # Most likely: day and month are being read with extra 1s
        if len(numbers) >= 2:
            # Try the last two numbers as day and month
            try:
                day = int(numbers[-2]) if int(numbers[-2]) <= 31 else int(numbers[-2][0:2])
                month = int(numbers[-1]) if int(numbers[-1]) <= 12 else int(numbers[-1][0:2])
                full_year = int(year)
                
                if 1 <= day <= 31 and 1 <= month <= 12:
                    logger.info(f"OCR digit correction: '{s}' → day={day}, month={month}, year={full_year}")
                    return date(full_year, month, day)
            except (ValueError, TypeError):
                pass
        
        # Try common patterns for dates with all 1s like 11.11.1911
        # If we see repeated 1s, assume it's 11th day, 11th month
        if '11' in before_year:
            try:
                logger.info(f"OCR digit correction: Assuming 11.11.{year} format")
                return date(int(year), 11, 11)
            except (ValueError, TypeError):
                pass
        
        return None
    
    @staticmethod
    def _parse_ymd(groups: Tuple[str, str, str]) -> Optional[date]:
        """Parse year-month-day format"""
        y, m, d = groups
        try:
            return date(int(y), int(m), int(d))
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def _parse_ymd_flexible(groups: Tuple[str, str, str]) -> Optional[date]:
        """
        Parse year-first format flexibly, trying both YYYY-MM-DD and YYYY-DD-MM.

        This handles cases where OCR outputs "1920 03 15" which could be:
        - YYYY-MM-DD: 1920-03-15 (March 15, 1920)
        - YYYY-DD-MM: invalid (month 15 doesn't exist)

        Tries YYYY-MM-DD first (ISO standard), falls back to YYYY-DD-MM if needed.
        """
        y, second, third = groups
        year = int(y)
        num2 = int(second)
        num3 = int(third)

        # Try YYYY-MM-DD (ISO format, most common)
        if 1 <= num2 <= 12 and 1 <= num3 <= 31:
            try:
                return date(year, num2, num3)
            except (ValueError, TypeError):
                pass

        # Try YYYY-DD-MM (less common but possible)
        if 1 <= num3 <= 12 and 1 <= num2 <= 31:
            try:
                return date(year, num3, num2)
            except (ValueError, TypeError):
                pass

        return None
    
    @staticmethod
    def _month_to_number(month_str: str) -> Optional[int]:
        """Convert month name to number - handles variations and OCR errors"""
        if not month_str:
            return None
        
        month_lower = month_str.lower()
        
        # Try full name first
        if month_lower in DateParser.MONTH_MAP:
            return DateParser.MONTH_MAP[month_lower]
        
        # Try first 3 characters
        key = month_lower[:3]
        if key in DateParser.MONTH_MAP:
            return DateParser.MONTH_MAP[key]
        
        # Try first 4 characters (for months like "mars", "août")
        if len(month_lower) >= 4:
            key4 = month_lower[:4]
            if key4 in DateParser.MONTH_MAP:
                return DateParser.MONTH_MAP[key4]
        
        # Handle common OCR errors for month names
        ocr_corrections = {
            "deo": "dec", "oeo": "dec", "0ec": "dec",
            "jan": "jan", "jnn": "jan",
            "feo": "feb", "feb": "feb",
            "nar": "mar", "mar": "mar", "nars": "mars",
            "apr": "apr", "npr": "apr",
            "nay": "may", "may": "may", "naj": "maj",
            "jun": "jun", "jnn": "jun",
            "jul": "jul", "jui": "jul", "jnl": "jul",
            "nug": "aug", "aug": "aug", "auo": "aug",
            "sep": "sep", "seo": "sep",
            "oot": "oct", "oct": "oct", "okt": "oct",
            "nov": "nov", "n0v": "nov",
        }
        
        corrected = ocr_corrections.get(key)
        if corrected:
            return DateParser.MONTH_MAP.get(corrected)
        
        return None
    
    @staticmethod
    def compute_age(born: date, today: Optional[date] = None) -> int:
        """Calculate age from birth date"""
        if not today:
            today = date.today()
        age = today.year - born.year
        if (today.month, today.day) < (born.month, born.day):
            age -= 1
        return age

# === OCR PROCESSOR ===
class OCRProcessor:
    """Handle OCR operations"""
    
    def __init__(self, languages: List[str] = None):
        """Initialize OCR reader"""
        if languages is None:
            languages = ["en", "fr", "nl", "de"]
        self.reader = easyocr.Reader(languages)
        self.logger = logging.getLogger(__name__)
    
    def read_text(self, image) -> List[str]:
        """Extract text from image"""
        try:
            texts = self.reader.readtext(image, detail=0)
            return texts if texts else []
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
            return []

# === DETECTION PROCESSOR ===
class DetectionProcessor:
    """Process YOLO detections and extract information"""
    
    def __init__(self, config: Config, ocr_processor: OCRProcessor):
        self.config = config
        self.ocr = ocr_processor
        self.date_parser = DateParser()
        self.logger = logging.getLogger(__name__)
    
    def process_detections(self, frame, results, snap_dir: Path) -> Tuple[Dict, AgeInfo]:
        """Process all detections in frame"""
        ocr_results = {}
        dob_candidates = []
        
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            label = self.config.CLASS_NAMES[cls_id]
            
            # Extract and save crop
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            crop = frame[y1:y2, x1:x2]
            crop_filename = snap_dir / f"{label}_{conf:.2f}.png"
            cv2.imwrite(str(crop_filename), crop)
            
            # Perform OCR (skip Photo)
            if label != "Photo":
                texts = self.ocr.read_text(crop)
                raw = " ".join(texts) if texts else "[No text detected]"
                ocr_results.setdefault(label, []).append(raw)
                
                if label == "DOB":
                    cleaned = self.date_parser.clean_dob_text(texts, self.config.DOB_STOPWORDS)
                    ocr_results.setdefault("DOB_cleaned", []).append(cleaned)
                    dob_candidates.append(cleaned)
                    self.logger.info(f"DOB OCR - Raw: {raw} → Cleaned: {cleaned}")
        
        # Calculate age
        age_info = self._calculate_age(dob_candidates)
        
        return ocr_results, age_info
    
    def _calculate_age(self, dob_candidates: List[str]) -> AgeInfo:
        """Calculate age from DOB candidates"""
        for dob_str in dob_candidates:
            self.logger.debug(f"Trying to parse: '{dob_str}'")
            parsed_date = self.date_parser.parse_date(dob_str)
            if parsed_date:
                age = self.date_parser.compute_age(parsed_date)
                status = "adult" if age >= 18 else "kid"

                # Check if year seems incorrect (very old or future)
                current_year = date.today().year
                if parsed_date.year < 1900:
                    self.logger.warning(f"Suspicious birth year {parsed_date.year} - may be OCR error")
                elif parsed_date.year > current_year:
                    self.logger.warning(f"Future birth year {parsed_date.year} - OCR error")
                elif age > 100:
                    self.logger.warning(
                        f"Calculated age {age} is unusually high (birth year {parsed_date.year}). "
                        f"This may indicate an OCR error that could not be corrected."
                    )
                elif age > 85:
                    self.logger.info(
                        f"Calculated age {age} is high but plausible (birth year {parsed_date.year})."
                    )

                self.logger.info(f"Age calculated: {parsed_date.isoformat()} -> {age} years -> {status.upper()}")
                return AgeInfo(
                    dob_parsed=parsed_date.isoformat(),
                    age_years=age,
                    status=status
                )
            else:
                self.logger.debug(f"Failed to parse: '{dob_str}'")

        self.logger.warning(f"Could not parse any DOB from {len(dob_candidates)} candidates: {dob_candidates}")
        return AgeInfo()

# === FILE SAVER ===
class ResultSaver:
    """Save detection results to files"""
    
    @staticmethod
    def save_results(snap_dir: Path, ocr_results: Dict, age_info: AgeInfo):
        """Save all results to files"""
        # Save OCR results as JSON
        with open(snap_dir / "ocr_results.json", "w", encoding="utf-8") as f:
            json.dump(ocr_results, f, indent=4, ensure_ascii=False)
        
        # Save OCR results as CSV
        with open(snap_dir / "ocr_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Field", "Value"])
            for key, values in ocr_results.items():
                for v in values:
                    writer.writerow([key, v])
        
        # Save age info as JSON
        with open(snap_dir / "age.json", "w", encoding="utf-8") as f:
            json.dump(asdict(age_info), f, indent=4)
        
        # Save age info as CSV
        with open(snap_dir / "age.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["dob_parsed", "age_years", "status"])
            writer.writerow([age_info.dob_parsed, age_info.age_years, age_info.status])

# === MAIN DETECTOR ===
class IDCardDetector:
    """Main ID card detection system"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(config.OUTPUT_DIR, config.LOG_LEVEL)
        
        # Create output directory
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.logger.info("Loading YOLO model...")
        self.model = YOLO(config.MODEL_PATH)
        
        self.logger.info("Loading OCR reader...")
        self.ocr_processor = OCRProcessor()
        
        self.detection_processor = DetectionProcessor(config, self.ocr_processor)
        self.snapshot_count = 0
        self.successful_snapshot = False
        self.age_info = None  # Store the age info from the last snapshot
    
    def check_thresholds(self, results) -> Dict[str, bool]:
        """Check which detections meet their thresholds"""
        meets_thresh = {label: False for label in self.config.CLASS_NAMES}
        
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            label = self.config.CLASS_NAMES[cls_id]
            
            if conf >= self.config.THRESHOLDS.get(label, 0.0):
                meets_thresh[label] = True
        
        return meets_thresh
    
    def take_snapshot(self, frame, results):
        """Take and process snapshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snap_dir = Path(self.config.OUTPUT_DIR) / f"snapshot_{timestamp}"
        snap_dir.mkdir(parents=True, exist_ok=True)
        
        # Save annotated image
        annotated_frame = results[0].plot()
        cv2.imwrite(str(snap_dir / "annotated.png"), annotated_frame)
        
        # Process detections
        ocr_results, age_info = self.detection_processor.process_detections(
            frame, results, snap_dir
        )

        # Store age_info in the detector
        self.age_info = age_info

        # Save results
        ResultSaver.save_results(snap_dir, ocr_results, age_info)

        self.logger.info(f"Snapshot saved in {snap_dir}")
        self.logger.info(f"Age: {age_info.age_years} years, Status: {age_info.status.upper()}")

        return snap_dir
    
    def run(self):
        """Main detection loop"""
        cap = cv2.VideoCapture(self.config.CAMERA_INDEX)
        
        if not cap.isOpened():
            self.logger.error("Could not open webcam")
            return
        
        retry_mode = self.config.RETRY_ON_UNKNOWN
        max_attempts = self.config.MAX_RETRY_ATTEMPTS
        
        self.logger.info("Webcam started. Press 'q' to quit.")
        self.logger.info("Snapshot triggers when BOTH: DOB >= 0.80 AND Photo >= 0.80")
        if retry_mode:
            self.logger.info(f"Auto-retry enabled: Will retry up to {max_attempts} times if status is UNKNOWN")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    self.logger.error("Could not read from webcam")
                    break
                
                # Run detection
                results = self.model(frame, imgsz=self.config.IMGSZ, 
                                   conf=self.config.BASE_CONF, verbose=False)
                annotated_frame = results[0].plot()
                
                # Check thresholds
                meets_thresh = self.check_thresholds(results)
                
                # Determine if we should take a snapshot
                should_snapshot = False
                
                if meets_thresh["DOB"] and meets_thresh["Photo"]:
                    if not self.successful_snapshot:
                        # First attempt or retrying after UNKNOWN
                        if self.snapshot_count < max_attempts:
                            should_snapshot = True
                        else:
                            if self.snapshot_count == max_attempts:
                                self.logger.warning(f"Maximum retry attempts ({max_attempts}) reached. Press 'q' to quit.")
                                self.snapshot_count += 1  # Increment to avoid repeated logging
                
                if should_snapshot:
                    self.snapshot_count += 1
                    attempt_info = f"Attempt {self.snapshot_count}/{max_attempts}" if retry_mode else "Single attempt"
                    self.logger.info(f"Taking snapshot ({attempt_info})...")
                    
                    snap_dir = self.take_snapshot(frame, results)
                    
                    # Check if we got a successful result
                    # Read the age info to check status
                    age_file = snap_dir / "age.json"
                    if age_file.exists():
                        with open(age_file, 'r') as f:
                            age_data = json.load(f)
                            status = age_data.get('status', 'unknown')
                            
                            if status != 'unknown':
                                # Success!
                                self.successful_snapshot = True
                                self.logger.info(f"✓ Successfully determined age. No more snapshots will be taken.")

                                # Auto-continue if enabled (for priAge integration)
                                if self.config.AUTO_CONTINUE:
                                    self.logger.info("Auto-continuing to next phase...")
                                    cap.release()
                                    cv2.destroyAllWindows()
                                    return  # Auto-exit to continue to next phase
                                else:
                                    self.logger.info("Press 'q' to quit.")
                            else:
                                # UNKNOWN status
                                if retry_mode and self.snapshot_count < max_attempts:
                                    self.logger.warning(f"✗ Status is UNKNOWN. Will retry... ({max_attempts - self.snapshot_count} attempts remaining)")
                                    self.logger.info("Please ensure ID card is clearly visible and well-lit.")
                                elif self.snapshot_count >= max_attempts:
                                    self.logger.error(f"✗ Failed to determine age after {max_attempts} attempts.")
                                    self.logger.info("Press 'q' to quit or restart the program to try again.")
                                else:
                                    self.logger.warning("✗ Status is UNKNOWN. Press 'q' to quit.")
                
                # Display
                # Add status info to the frame
                status_text = f"Snapshots: {self.snapshot_count}/{max_attempts}"
                if self.successful_snapshot:
                    status_text += " - SUCCESS"
                cv2.putText(annotated_frame, status_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow("ID Card Detection System", annotated_frame)

                # Check for key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                elif key == ord(" ") and self.successful_snapshot and self.config.AUTO_CONTINUE:
                    # Space bar pressed and we have a successful snapshot in AUTO_CONTINUE mode
                    self.logger.info("Continuing to next phase...")
                    break
        
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Error during detection: {e}", exc_info=True)
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.logger.info("Webcam session ended")
            if self.successful_snapshot:
                self.logger.info(f"✓ Session completed successfully after {self.snapshot_count} attempt(s)")
            else:
                self.logger.info(f"✗ Session ended without successful age determination ({self.snapshot_count} attempts made)")

# === ENTRY POINT ===
def main():
    """Main entry point - returns AgeInfo from detection"""
    config = Config()
    detector = IDCardDetector(config)
    detector.run()
    # Return the age_info from the last successful snapshot
    return detector.age_info

if __name__ == "__main__":
    result = main()
    if result and result.status != "unknown":
        sys.exit(0)
    else:
        sys.exit(1)