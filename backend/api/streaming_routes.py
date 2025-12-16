# -*- coding: utf-8 -*-
"""
Streaming Routes - Server-Sent Events for Agent Updates

Provides real-time streaming of agent processing updates to the frontend.
"""

import asyncio
import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from services.database import get_db
from services.auth_service import get_current_user, get_current_user_optional
from models.user_schemas import User
from models.schemas import Application, AgentEvaluation
from graph.agent_orchestrator import run_agent_workflow_async
from services.pdf_service import generate_sanction_letter


streaming_router = APIRouter(prefix="/api/agents", tags=["Agent Streaming"])


@streaming_router.get("/stream/{application_id}")
async def stream_agent_processing(
    application_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events endpoint for streaming agent updates.
    
    Connect to this endpoint after creating an application to receive
    real-time updates as each agent processes the application.
    
    Events:
    - agent_start: Agent begins processing
    - agent_complete: Agent finished with result
    - complete: All agents done, final result
    - error: An error occurred
    """
    # Fetch application from database
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    # Check if already processed
    if app.status in ["SANCTIONED", "REJECTED"]:
        async def already_processed():
            yield {
                "event": "complete",
                "data": json.dumps({
                    "status": app.status,
                    "message": "Application already processed",
                    "sanction_pdf_url": app.sanction_pdf_path
                })
            }
        return EventSourceResponse(already_processed())
    
    async def event_generator():
        try:
            # Update application status
            app.status = "PROCESSING"
            db.commit()
            
            # Build application data for workflow
            application_data = {
                "application_id": app.id,
                "customer_name": app.customer_name,
                "mobile": app.mobile,
                "pan": app.pan,
                "aadhaar": app.aadhaar,
                "loan_amount": app.loan_amount,
                "tenure": app.tenure,
                "income": app.income
            }
            
            # Define agents for progress tracking
            agents = [
                ("AgentAlpha", "Sales Validator"),
                ("AgentBeta", "KYC Verifier"),
                ("AgentGamma", "Credit Analyst"),
                ("AgentDelta", "Income Analyzer"),
                ("AgentEpsilon", "Fraud Detector"),
                ("AgentZeta", "Sanction Authority"),
            ]
            
            current_idx = 0
            final_status = "FAIL"
            final_decision = None
            
            # Stream workflow execution
            async for update in run_agent_workflow_async(application_data):
                if update.get("type") == "complete":
                    final_status = update.get("status", "FAIL")
                    final_decision = update.get("final_decision")
                    continue
                
                agent_name = update.get("agent")
                
                # Send agent start event for next agent
                if current_idx < len(agents):
                    yield {
                        "event": "agent_start",
                        "data": json.dumps({
                            "agent": agents[current_idx][0],
                            "display_name": agents[current_idx][1],
                            "status": "processing",
                            "progress": current_idx / len(agents) * 100
                        })
                    }
                
                # Small delay for visual effect
                await asyncio.sleep(0.3)
                
                # Send agent complete event
                yield {
                    "event": "agent_complete",
                    "data": json.dumps(update)
                }
                
                # Store agent evaluation in database
                if update.get("result"):
                    result = update["result"]
                    evaluation = AgentEvaluation(
                        application_id=application_id,
                        agent_name=result.get("agent_name", agent_name),
                        agent_type=result.get("agent_type", "unknown"),
                        score=result.get("score", 0),
                        decision=result.get("decision", "review"),
                        confidence=result.get("confidence", 50),
                        explanation_summary=result.get("explanation", ""),
                        detailed_analysis=result.get("details", {}),
                        processing_time_ms=result.get("processing_time_ms", 0)
                    )
                    db.add(evaluation)
                    db.commit()
                
                # Update current agent in application
                app.current_agent = agent_name
                db.commit()
                
                current_idx += 1
                
                # Check for early exit
                if update.get("result", {}).get("decision") == "reject":
                    final_status = "REJECTED"
                    break
                
                await asyncio.sleep(0.2)
            
            # Generate sanction PDF if approved
            sanction_pdf_url = None
            if final_status == "SANCTIONED":
                try:
                    sanction_pdf_url = generate_sanction_letter(
                        application_id=application_data["application_id"],
                        customer_name=application_data["customer_name"],
                        loan_amount=application_data["loan_amount"],
                        tenure=application_data["tenure"],
                        credit_score=750,  # Default score for sanctioned applications
                        pan=application_data.get("pan", ""),
                        income=application_data.get("income", 0)
                    )
                    app.sanction_pdf_path = sanction_pdf_url
                except Exception as e:
                    print(f"PDF generation error: {e}")
            
            # Update final application status
            app.status = final_status
            app.final_decision = final_decision
            app.current_agent = None
            app.processed_at = datetime.utcnow()
            db.commit()
            
            # Send final complete event
            yield {
                "event": "complete",
                "data": json.dumps({
                    "status": final_status,
                    "final_decision": final_decision,
                    "sanction_pdf_url": sanction_pdf_url,
                    "application_id": application_id
                })
            }
            
        except Exception as e:
            # Send error event
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "application_id": application_id
                })
            }
            
            # Update application status
            app.status = "FAIL"
            app.current_agent = None
            db.commit()
    
    return EventSourceResponse(event_generator())


@streaming_router.get("/results/{application_id}")
async def get_agent_results(
    application_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get all agent evaluation results for an application.
    
    Non-streaming alternative to SSE endpoint.
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
        "status": app.status,
        "total_agents": len(evaluations),
        "results": [
            {
                "agent_name": e.agent_name,
                "agent_type": e.agent_type,
                "score": e.score,
                "decision": e.decision,
                "confidence": e.confidence,
                "explanation": e.explanation_summary,
                "details": e.detailed_analysis,
                "processing_time_ms": e.processing_time_ms,
                "processed_at": e.processed_at.isoformat()
            }
            for e in evaluations
        ],
        "sanction_pdf_url": app.sanction_pdf_path
    }


@streaming_router.post("/process/{application_id}")
async def trigger_processing(
    application_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Trigger agent processing for an application.
    
    Returns immediately with stream URL for SSE connection.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    if app.status in ["SANCTIONED", "REJECTED"]:
        return {
            "message": "Application already processed",
            "status": app.status,
            "sanction_pdf_url": app.sanction_pdf_path
        }
    
    return {
        "message": "Connect to SSE stream for updates",
        "application_id": application_id,
        "stream_url": f"/api/agents/stream/{application_id}",
        "current_status": app.status
    }

