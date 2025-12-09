"""
Sales Node - Initial Validation

Validates basic application details:
- Loan amount (minimum ₹10,000)
- Tenure (6-360 months)
- Income (positive value)
- PAN format (ABCDE1234F)
- Aadhaar length (12 digits)
"""

import re
from typing import Any


def sales_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Sales Node: Validates basic application details.
    
    Checks:
    - PAN format (5 letters + 4 digits + 1 letter)
    - Aadhaar (12 digits)
    - Loan amount (minimum ₹10,000)
    - Tenure (6-360 months)
    - Income (positive value)
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with validation results
    """
    try:
        errors = []
        validated_fields = []
        
        # Validate PAN format: ABCDE1234F
        pan = state.get("pan", "")
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan.upper()):
            errors.append("Your PAN number doesn't appear to be in the correct format. It should look like ABCDE1234F")
        else:
            validated_fields.append("pan")
        
        # Validate Aadhaar: 12 digits
        aadhaar = state.get("aadhaar", "")
        if not aadhaar.isdigit() or len(aadhaar) != 12:
            errors.append("Your Aadhaar number should be exactly 12 digits")
        else:
            validated_fields.append("aadhaar")
        
        # Validate loan amount: minimum ₹10,000
        loan_amount = state.get("loan_amount", 0)
        if loan_amount < 10000:
            errors.append(f"The loan amount ₹{loan_amount:,} is below our minimum of ₹10,000")
        else:
            validated_fields.append("loan_amount")
        
        # Validate tenure: 6-360 months
        tenure = state.get("tenure", 0)
        if tenure < 6 or tenure > 360:
            errors.append(f"Please choose a tenure between 6 and 360 months. You selected {tenure} months")
        else:
            validated_fields.append("tenure")
        
        # Validate income: positive value
        income = state.get("income", 0)
        if income <= 0:
            errors.append("Please provide a valid monthly income amount")
        else:
            validated_fields.append("income")
        
        # Validate mobile: 10 digits
        mobile = state.get("mobile", "")
        if not mobile.isdigit() or len(mobile) != 10:
            errors.append("Please provide a valid 10-digit mobile number")
        else:
            validated_fields.append("mobile")
        
        # Build step result
        is_success = len(errors) == 0
        step_result = {
            "node": "sales",
            "result": "SUCCESS" if is_success else "FAIL",
            "data": {
                "validated_fields": validated_fields,
                "errors": errors
            },
            "message": "All your details have been validated successfully" if is_success else "; ".join(errors)
        }
        
        # Return state updates
        current_steps = state.get("steps", [])
        
        return {
            "status": "SUCCESS" if is_success else "FAIL",
            "steps": current_steps + [step_result],
            "error_message": "; ".join(errors) if errors else None
        }
        
    except Exception as e:
        # Handle unexpected errors gracefully
        step_result = {
            "node": "sales",
            "result": "FAIL",
            "data": {"error": str(e)},
            "message": "We encountered an issue while validating your details. Please try again."
        }
        
        current_steps = state.get("steps", [])
        
        return {
            "status": "FAIL",
            "steps": current_steps + [step_result],
            "error_message": f"Validation error: {str(e)}"
        }
