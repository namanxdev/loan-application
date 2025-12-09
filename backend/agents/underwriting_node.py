"""
Underwriting Node - Credit Assessment and Eligibility

Applies underwriting rules:
1. Credit Score Check: Score >= 600 required
2. DTI Ratio: EMI <= 50% of monthly income
3. Loan Amount Cap: Max loan = income * 50

Uses deterministic credit score of 750 for demo.
"""

import sys
import os
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mock_api import get_credit_score


def calculate_emi(principal: int, tenure_months: int, annual_rate: float = 12.0) -> float:
    """
    Calculate EMI using reducing balance method.
    
    Args:
        principal: Loan amount
        tenure_months: Loan tenure in months
        annual_rate: Annual interest rate (default 12%)
        
    Returns:
        Monthly EMI amount
    """
    monthly_rate = annual_rate / 12 / 100  # Convert to monthly decimal
    
    if monthly_rate == 0:
        return principal / tenure_months
    
    emi = (principal * monthly_rate * (1 + monthly_rate)**tenure_months) / \
          ((1 + monthly_rate)**tenure_months - 1)
    
    return emi


def underwriting_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Underwriting Node: Applies credit assessment rules.
    
    Rules:
    1. Credit Score >= 600 (fixed at 750 for demo)
    2. EMI <= 50% of monthly income (DTI rule)
    3. Loan amount <= income * 50 (max loan cap)
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with underwriting decision
    """
    try:
        pan = state.get("pan", "")
        loan_amount = state.get("loan_amount", 0)
        tenure = state.get("tenure", 12)
        income = state.get("income", 0)
        
        errors = []
        
        # Get credit score (deterministic: always 750)
        credit_result = get_credit_score(pan)
        credit_score = credit_result["credit_score"]
        credit_rating = credit_result["rating"]
        
        # Rule 1: Credit Score Check
        min_credit_score = 600
        if credit_score < min_credit_score:
            errors.append(f"Your credit score of {credit_score} is below our minimum requirement of {min_credit_score}")
        
        # Calculate EMI
        emi = calculate_emi(loan_amount, tenure)
        
        # Rule 2: DTI Ratio (EMI <= 50% of monthly income)
        max_emi_allowed = income * 0.5
        if emi > max_emi_allowed:
            errors.append(
                f"Based on your income, your maximum affordable EMI is ₹{max_emi_allowed:,.2f}, "
                f"but the requested loan would require ₹{emi:,.2f} per month"
            )
        
        # Rule 3: Loan Amount Cap (max loan = income * 50)
        max_loan_allowed = income * 50
        if loan_amount > max_loan_allowed:
            errors.append(
                f"Based on your income, you can borrow up to ₹{max_loan_allowed:,}. "
                f"Consider reducing your loan amount or showing additional income"
            )
        
        # Calculate debt-to-income ratio
        dti_ratio = (emi / income * 100) if income > 0 else 0
        
        # Build step result
        is_approved = len(errors) == 0
        step_result = {
            "node": "underwriting",
            "result": "SUCCESS" if is_approved else "FAIL",
            "data": {
                "credit_score": credit_score,
                "credit_rating": credit_rating,
                "emi_calculated": round(emi, 2),
                "max_emi_allowed": round(max_emi_allowed, 2),
                "max_loan_allowed": max_loan_allowed,
                "dti_ratio": round(dti_ratio, 2),
                "interest_rate": "12% p.a."
            },
            "message": "Congratulations! Your credit assessment is approved" if is_approved else "; ".join(errors)
        }
        
        # Return state updates
        current_steps = state.get("steps", [])
        
        return {
            "status": "SUCCESS" if is_approved else "FAIL",
            "credit_score": credit_score,
            "steps": current_steps + [step_result],
            "error_message": "; ".join(errors) if errors else None
        }
        
    except Exception as e:
        # Handle unexpected errors gracefully
        step_result = {
            "node": "underwriting",
            "result": "FAIL",
            "data": {"error": str(e)},
            "message": "We encountered an issue during credit assessment. Please try again."
        }
        
        current_steps = state.get("steps", [])
        
        return {
            "status": "FAIL",
            "credit_score": 0,
            "steps": current_steps + [step_result],
            "error_message": f"Credit assessment error: {str(e)}"
        }
