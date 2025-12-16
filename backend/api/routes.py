# -*- coding: utf-8 -*-
"""
FastAPI Routes

API endpoints for loan processing:
- POST /apply - Create new loan application
- POST /process/{application_id} - Run workflow on application
- GET /application/{application_id} - Get application details
- GET /health - Health check endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import get_db
from models.schemas import (
    Application,
    ApplicationCreate,
    ApplicationResponse,
    ProcessResponse,
    ApplicationDetail,
    StepResult
)
from graph.loan_graph import run_loan_workflow


router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "loan-processing-api"}


@router.post("/apply", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(app_data: ApplicationCreate, db: Session = Depends(get_db)):
    """
    Create a new loan application.
    
    Request body:
    - customer_name: Full name of applicant
    - mobile: 10-digit mobile number
    - pan: PAN number (format: ABCDE1234F)
    - aadhaar: 12-digit Aadhaar number
    - loan_amount: Requested loan amount (minimum Rs.10,000)
    - tenure: Loan tenure in months (6-360)
    - income: Monthly income
    
    Returns:
    - application_id: Unique application ID
    - status: "CREATED"
    """
    # Create new application record
    db_app = Application(
        customer_name=app_data.customer_name,
        mobile=app_data.mobile,
        pan=app_data.pan.upper(),
        aadhaar=app_data.aadhaar,
        loan_amount=app_data.loan_amount,
        tenure=app_data.tenure,
        income=app_data.income,
        status="CREATED"
    )
    
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    
    return ApplicationResponse(
        application_id=db_app.id,
        status="CREATED"
    )


@router.post("/process/{application_id}", response_model=ProcessResponse)
def process_application(application_id: int, db: Session = Depends(get_db)):
    """
    Process a loan application through the workflow.
    
    Runs the application through:
    1. Sales Node - Validation
    2. Verification Node - KYC checks
    3. Underwriting Node - Credit assessment
    4. Sanction Node - PDF generation
    
    Returns:
    - status: Final status (SANCTIONED/FAIL)
    - sanction_pdf_url: URL to download PDF (if approved)
    - steps: Detailed results from each node
    - error_message: Error details (if failed)
    """
    # Fetch application from database
    db_app = db.query(Application).filter(Application.id == application_id).first()
    
    if not db_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found"
        )
    
    # Check if already processed
    if db_app.status == "SANCTIONED":
        return ProcessResponse(
            status="SANCTIONED",
            sanction_pdf_url=db_app.sanction_pdf_path,
            steps=[StepResult(**step) for step in db_app.workflow_steps] if db_app.workflow_steps else [],
            error_message=None
        )
    
    # Build application data for workflow
    application_data = {
        "application_id": db_app.id,
        "customer_name": db_app.customer_name,
        "mobile": db_app.mobile,
        "pan": db_app.pan,
        "aadhaar": db_app.aadhaar,
        "loan_amount": db_app.loan_amount,
        "tenure": db_app.tenure,
        "income": db_app.income
    }
    
    # Run the LangGraph workflow
    result = run_loan_workflow(application_data)
    
    # Update database with results
    db_app.status = result.get("status", "FAIL")
    db_app.workflow_steps = result.get("steps", [])
    
    if result.get("sanction_pdf_url"):
        db_app.sanction_pdf_path = result["sanction_pdf_url"]
    
    db.commit()
    db.refresh(db_app)
    
    # Build response
    return ProcessResponse(
        status=result.get("status", "FAIL"),
        sanction_pdf_url=result.get("sanction_pdf_url"),
        steps=[StepResult(**step) for step in result.get("steps", [])],
        error_message=result.get("error_message")
    )


@router.get("/application/{application_id}", response_model=ApplicationDetail)
def get_application(application_id: int, db: Session = Depends(get_db)):
    """
    Get details of a loan application.
    
    Returns full application details including:
    - Application data
    - Current status
    - Workflow steps (if processed)
    - Sanction PDF path (if approved)
    """
    db_app = db.query(Application).filter(Application.id == application_id).first()
    
    if not db_app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found"
        )
    
    return ApplicationDetail.model_validate(db_app)


@router.get("/applications")
def list_applications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    List all loan applications with pagination.
    
    Query params:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum records to return (default: 100)
    """
    applications = db.query(Application).offset(skip).limit(limit).all()
    
    return {
        "total": db.query(Application).count(),
        "skip": skip,
        "limit": limit,
        "applications": [
            {
                "id": app.id,
                "customer_name": app.customer_name,
                "loan_amount": app.loan_amount,
                "status": app.status,
                "created_at": app.created_at
            }
            for app in applications
        ]
    }
