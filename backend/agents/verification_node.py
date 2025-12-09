"""
Verification Node - KYC Verification

Performs KYC verification using mock APIs:
- PAN verification
- Aadhaar verification
- Mobile verification (optional)

All verifications are deterministic for demo purposes.
"""

import sys
import os
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mock_api import verify_pan, verify_aadhaar, verify_mobile


def verification_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Verification Node: Performs KYC verification.
    
    Checks:
    - PAN verification via mock API
    - Aadhaar verification via mock API
    - Mobile verification via mock API
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with verification results
    """
    pan = state.get("pan", "")
    aadhaar = state.get("aadhaar", "")
    mobile = state.get("mobile", "")
    
    # Call mock verification APIs
    pan_result = verify_pan(pan)
    aadhaar_result = verify_aadhaar(aadhaar)
    mobile_result = verify_mobile(mobile)
    
    # Check verification status
    pan_verified = pan_result["status"] == "VERIFIED"
    aadhaar_verified = aadhaar_result["status"] == "VERIFIED"
    mobile_verified = mobile_result["status"] == "VERIFIED"
    
    # All verifications must pass
    all_verified = pan_verified and aadhaar_verified and mobile_verified
    
    # Collect error messages
    errors = []
    if not pan_verified:
        errors.append(pan_result["message"])
    if not aadhaar_verified:
        errors.append(aadhaar_result["message"])
    if not mobile_verified:
        errors.append(mobile_result["message"])
    
    # Build step result
    step_result = {
        "node": "verification",
        "result": "SUCCESS" if all_verified else "FAIL",
        "data": {
            "pan_verified": pan_verified,
            "pan_name": pan_result.get("name_on_record"),
            "aadhaar_verified": aadhaar_verified,
            "aadhaar_masked": aadhaar_result.get("aadhaar_masked"),
            "mobile_verified": mobile_verified,
            "mobile_masked": mobile_result.get("mobile_masked")
        },
        "message": "KYC verification completed successfully" if all_verified else "; ".join(errors)
    }
    
    # Return state updates
    current_steps = state.get("steps", [])
    
    return {
        "status": "SUCCESS" if all_verified else "FAIL",
        "steps": current_steps + [step_result],
        "error_message": "; ".join(errors) if errors else None
    }
