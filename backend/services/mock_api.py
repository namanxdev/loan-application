"""
Mock External APIs for KYC Verification and Credit Scoring

DETERMINISTIC IMPLEMENTATION:
- All verifications return VERIFIED if format is valid
- Credit score is fixed at 750 for demo consistency
- No randomness - every run produces the same result
"""

import re


def verify_pan(pan: str) -> dict:
    """
    Mock PAN verification.
    Returns VERIFIED if PAN format is valid (ABCDE1234F).
    
    Args:
        pan: PAN number to verify
        
    Returns:
        dict with status and details
    """
    # Validate PAN format: 5 letters + 4 digits + 1 letter
    is_valid = bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan.upper()))
    
    return {
        "status": "VERIFIED" if is_valid else "FAILED",
        "pan": pan.upper(),
        "name_on_record": "DEMO USER" if is_valid else None,
        "message": "PAN verified successfully" if is_valid else "Invalid PAN format"
    }


def verify_aadhaar(aadhaar: str) -> dict:
    """
    Mock Aadhaar verification.
    Returns VERIFIED if Aadhaar is exactly 12 digits.
    
    Args:
        aadhaar: Aadhaar number to verify
        
    Returns:
        dict with status and details
    """
    # Validate Aadhaar: must be exactly 12 digits
    is_valid = aadhaar.isdigit() and len(aadhaar) == 12
    
    return {
        "status": "VERIFIED" if is_valid else "FAILED",
        "aadhaar_masked": f"XXXX-XXXX-{aadhaar[-4:]}" if is_valid else None,
        "message": "Aadhaar verified successfully" if is_valid else "Invalid Aadhaar format"
    }


def get_credit_score(pan: str) -> dict:
    """
    Mock credit score retrieval.
    Returns fixed score of 750 for demo consistency.
    
    Args:
        pan: PAN number to lookup credit score
        
    Returns:
        dict with credit score and rating
    """
    # Fixed credit score for deterministic demo
    FIXED_SCORE = 750
    
    # Determine rating based on score
    if FIXED_SCORE >= 750:
        rating = "EXCELLENT"
    elif FIXED_SCORE >= 700:
        rating = "GOOD"
    elif FIXED_SCORE >= 650:
        rating = "FAIR"
    elif FIXED_SCORE >= 600:
        rating = "POOR"
    else:
        rating = "VERY_POOR"
    
    return {
        "pan": pan.upper(),
        "credit_score": FIXED_SCORE,
        "rating": rating,
        "message": f"Credit score: {FIXED_SCORE} ({rating})"
    }


def verify_mobile(mobile: str) -> dict:
    """
    Mock mobile number verification.
    Returns VERIFIED if mobile is exactly 10 digits.
    
    Args:
        mobile: Mobile number to verify
        
    Returns:
        dict with status and details
    """
    is_valid = mobile.isdigit() and len(mobile) == 10
    
    return {
        "status": "VERIFIED" if is_valid else "FAILED",
        "mobile_masked": f"XXXXXX{mobile[-4:]}" if is_valid else None,
        "message": "Mobile verified successfully" if is_valid else "Invalid mobile format"
    }
