# -*- coding: utf-8 -*-
"""
Admin/Employee Routes
- Application management for employees
- Status override functionality
- Dashboard statistics
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from services.database import get_db
from services.auth_service import require_employee, get_current_user
from models.user_schemas import User
from models.schemas import (
    Application, AgentEvaluation, StatusHistory,
    ApplicationDetail, AgentResultResponse, StatusOverrideRequest
)


admin_router = APIRouter(prefix="/api/admin", tags=["Employee Dashboard"])


@admin_router.get("/applications")
async def list_all_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db)
):
    """
    List all applications with pagination and filters.
    
    **Employee/Admin only**
    
    - **skip**: Offset for pagination
    - **limit**: Max results (1-100)
    - **status_filter**: Filter by status (CREATED, PROCESSING, SANCTIONED, etc.)
    - **search**: Search by customer name or application ID
    """
    query = db.query(Application)
    
    # Apply status filter
    if status_filter:
        query = query.filter(Application.status == status_filter)
    
    # Apply search
    if search:
        if search.isdigit():
            query = query.filter(Application.id == int(search))
        else:
            query = query.filter(Application.customer_name.ilike(f"%{search}%"))
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    applications = query.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "applications": [
            {
                "id": app.id,
                "customer_name": app.customer_name,
                "phone": app.mobile,
                "loan_amount": app.loan_amount,
                "tenure": app.tenure,
                "status": app.status,
                "current_agent": app.current_agent,
                "assigned_employee_id": app.assigned_employee_id,
                "human_override": app.human_override,
                "created_at": app.created_at.isoformat(),
                "updated_at": app.updated_at.isoformat()
            }
            for app in applications
        ]
    }


@admin_router.get("/applications/{application_id}", response_model=ApplicationDetail)
async def get_application_details(
    application_id: int,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db)
):
    """
    Get detailed application info including agent evaluations.
    
    **Employee/Admin only**
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    return ApplicationDetail.model_validate(app)


@admin_router.get("/applications/{application_id}/agents")
async def get_agent_evaluations(
    application_id: int,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db)
):
    """
    Get all agent evaluations for an application.
    
    **Employee/Admin only**
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    evaluations = db.query(AgentEvaluation).filter(
        AgentEvaluation.application_id == application_id
    ).order_by(AgentEvaluation.processed_at).all()
    
    return {
        "application_id": application_id,
        "total_agents": len(evaluations),
        "evaluations": [
            AgentResultResponse.model_validate(eval) for eval in evaluations
        ]
    }


@admin_router.put("/applications/{application_id}/status")
async def override_status(
    application_id: int,
    request: StatusOverrideRequest,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db)
):
    """
    Manual status override for an application.
    
    **Employee/Admin only**
    
    Allows employees to manually change application status with a reason.
    All changes are logged in status_history.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    # Validate new status
    valid_statuses = ["CREATED", "PROCESSING", "SUCCESS", "FAIL", "SANCTIONED", "REJECTED", "MANUAL_REVIEW"]
    if request.new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    old_status = app.status
    
    # Log the change
    history = StatusHistory(
        application_id=application_id,
        old_status=old_status,
        new_status=request.new_status,
        changed_by_id=current_user.id,
        reason=request.reason
    )
    db.add(history)
    
    # Update application
    app.status = request.new_status
    app.human_override = True
    app.override_reason = request.reason
    app.assigned_employee_id = current_user.id
    app.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(app)
    
    return {
        "message": f"Status updated from {old_status} to {request.new_status}",
        "application_id": application_id,
        "old_status": old_status,
        "new_status": request.new_status,
        "changed_by": current_user.email,
        "reason": request.reason,
        "timestamp": datetime.utcnow().isoformat()
    }


@admin_router.put("/applications/{application_id}/assign")
async def assign_application(
    application_id: int,
    employee_id: Optional[int] = None,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db)
):
    """
    Assign or reassign an application to an employee.
    
    **Employee/Admin only**
    
    If employee_id is not provided, assigns to the current user.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    target_id = employee_id or current_user.id
    
    # Verify employee exists
    employee = db.query(User).filter(User.id == target_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {target_id} not found"
        )
    
    old_assignee = app.assigned_employee_id
    app.assigned_employee_id = target_id
    app.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Application assigned to {employee.email}",
        "application_id": application_id,
        "old_assignee_id": old_assignee,
        "new_assignee_id": target_id,
        "new_assignee_email": employee.email
    }


@admin_router.get("/applications/{application_id}/history")
async def get_status_history(
    application_id: int,
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db)
):
    """
    Get status change history for an application.
    
    **Employee/Admin only**
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    history = db.query(StatusHistory).filter(
        StatusHistory.application_id == application_id
    ).order_by(StatusHistory.changed_at.desc()).all()
    
    return {
        "application_id": application_id,
        "history": [
            {
                "id": h.id,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "changed_by_id": h.changed_by_id,
                "reason": h.reason,
                "changed_at": h.changed_at.isoformat()
            }
            for h in history
        ]
    }


@admin_router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_employee),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics.
    
    **Employee/Admin only**
    
    Returns counts and metrics for the dashboard.
    """
    # Total applications
    total = db.query(Application).count()
    
    # Count by status
    status_counts = db.query(
        Application.status,
        func.count(Application.id)
    ).group_by(Application.status).all()
    
    status_dict = {s: c for s, c in status_counts}
    
    # Total loan amount sanctioned
    sanctioned_amount = db.query(func.sum(Application.loan_amount)).filter(
        Application.status == "SANCTIONED"
    ).scalar() or 0
    
    # Applications pending review
    pending_review = db.query(Application).filter(
        Application.status == "MANUAL_REVIEW"
    ).count()
    
    # My assigned applications
    my_assigned = db.query(Application).filter(
        Application.assigned_employee_id == current_user.id
    ).count()
    
    # Recent activity (last 7 days)
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_count = db.query(Application).filter(
        Application.created_at >= week_ago
    ).count()
    
    return {
        "total_applications": total,
        "by_status": {
            "created": status_dict.get("CREATED", 0),
            "processing": status_dict.get("PROCESSING", 0),
            "sanctioned": status_dict.get("SANCTIONED", 0),
            "rejected": status_dict.get("REJECTED", 0) + status_dict.get("FAIL", 0),
            "manual_review": status_dict.get("MANUAL_REVIEW", 0),
        },
        "total_sanctioned_amount": sanctioned_amount,
        "pending_review": pending_review,
        "my_assigned": my_assigned,
        "recent_7_days": recent_count,
    }

