"""
Sanction Node - PDF Generation

Final node in the workflow that generates the sanction letter PDF
for approved loan applications.
"""

import sys
import os
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_service import generate_sanction_letter


def sanction_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Sanction Node: Generates sanction letter PDF.
    
    This is the final node for approved applications.
    Generates a professional PDF sanction letter using ReportLab.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with PDF path and SANCTIONED status
    """
    application_id = state.get("application_id")
    customer_name = state.get("customer_name", "Customer")
    loan_amount = state.get("loan_amount", 0)
    tenure = state.get("tenure", 12)
    credit_score = state.get("credit_score", 750)
    pan = state.get("pan", "")
    income = state.get("income", 0)
    
    try:
        # Generate sanction letter PDF
        pdf_path = generate_sanction_letter(
            application_id=application_id,
            customer_name=customer_name,
            loan_amount=loan_amount,
            tenure=tenure,
            credit_score=credit_score,
            pan=pan,
            income=income
        )
        
        # URL path for frontend access
        pdf_url = f"/pdfs/{application_id}.pdf"
        
        # Build step result
        step_result = {
            "node": "sanction",
            "result": "SUCCESS",
            "data": {
                "pdf_generated": True,
                "pdf_path": pdf_path,
                "pdf_url": pdf_url
            },
            "message": "Sanction letter generated successfully"
        }
        
        # Return state updates
        current_steps = state.get("steps", [])
        
        return {
            "status": "SANCTIONED",
            "sanction_pdf_url": pdf_url,
            "steps": current_steps + [step_result],
            "error_message": None
        }
        
    except Exception as e:
        # Handle PDF generation errors
        step_result = {
            "node": "sanction",
            "result": "FAIL",
            "data": {"error": str(e)},
            "message": f"Failed to generate sanction letter: {str(e)}"
        }
        
        current_steps = state.get("steps", [])
        
        return {
            "status": "FAIL",
            "sanction_pdf_url": None,
            "steps": current_steps + [step_result],
            "error_message": f"PDF generation failed: {str(e)}"
        }
