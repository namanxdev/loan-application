# -*- coding: utf-8 -*-
"""
Chat Routes - API endpoints for conversational loan application

Endpoints:
- POST /chat/start - Start a new chat session
- POST /chat/message - Send a message in the conversation
- POST /chat/process - Process the complete application
- GET /chat/session/{session_id} - Get session status
- GET /chat/history/{session_id} - Get conversation history
- DELETE /chat/session/{session_id} - End a chat session
"""

import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.chat_schemas import (
    StartChatRequest,
    StartChatResponse,
    ChatRequest,
    ChatResponse,
    ProcessApplicationRequest,
    ApplicationProcessResponse,
    ProcessingStep,
    SessionStatus,
    ConversationHistory,
    ChatMessage,
    MessageRole
)
from services.conversation_service import conversation_manager, RAGContextBuilder
from services.database import get_db
from models.schemas import Application
from agents.master_agent import master_agent
from graph.chat_graph import run_chat_workflow


# ============== Validation Helpers ==============

def validate_application_data(data: Dict) -> Tuple[Dict, List[str]]:
    """
    Validate and sanitize application data with user-friendly error messages.
    
    Args:
        data: Dictionary containing application fields
        
    Returns:
        Tuple of (sanitized_data, error_messages)
        - sanitized_data: Cleaned and normalized data
        - error_messages: List of user-friendly validation errors (empty if valid)
    """
    errors = []
    sanitized = {}
    
    # Validate and sanitize customer name
    customer_name = str(data.get("customer_name", "")).strip()
    if len(customer_name) < 2:
        errors.append("Please enter your full name (at least 2 characters)")
    elif len(customer_name) > 100:
        errors.append("Name is too long. Please use a shorter name (max 100 characters)")
    else:
        sanitized["customer_name"] = customer_name
    
    # Validate and sanitize mobile number
    mobile = str(data.get("mobile", "")).strip().replace(" ", "").replace("-", "")
    if not mobile.isdigit():
        errors.append("Please enter a valid mobile number using digits only")
    elif len(mobile) != 10:
        errors.append("Please enter a valid 10-digit mobile number")
    else:
        sanitized["mobile"] = mobile
    
    # Validate and sanitize PAN
    pan = str(data.get("pan", "")).strip().upper().replace(" ", "")
    pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    if not re.match(pan_pattern, pan):
        errors.append("Please enter a valid PAN number (format: ABCDE1234F)")
    else:
        sanitized["pan"] = pan
    
    # Validate and sanitize Aadhaar
    aadhaar = str(data.get("aadhaar", "")).strip().replace(" ", "").replace("-", "")
    if not aadhaar.isdigit():
        errors.append("Aadhaar should contain only digits")
    elif len(aadhaar) != 12:
        errors.append("Please enter a valid 12-digit Aadhaar number")
    else:
        sanitized["aadhaar"] = aadhaar
    
    # Validate loan amount
    try:
        loan_amount = int(data.get("loan_amount", 0))
        if loan_amount < 10000:
            errors.append("Minimum loan amount is Rs.10,000. Please enter a higher amount")
        elif loan_amount > 50000000:
            errors.append("Maximum loan amount is Rs.5 Crore. Please enter a lower amount")
        else:
            sanitized["loan_amount"] = loan_amount
    except (ValueError, TypeError):
        errors.append("Please enter a valid loan amount in numbers")
    
    # Validate tenure
    try:
        tenure = int(data.get("tenure", 0))
        if tenure < 6:
            errors.append("Minimum tenure is 6 months. Please choose a longer tenure")
        elif tenure > 360:
            errors.append("Maximum tenure is 360 months (30 years). Please choose a shorter tenure")
        else:
            sanitized["tenure"] = tenure
    except (ValueError, TypeError):
        errors.append("Please enter a valid tenure in months")
    
    # Validate income
    try:
        income = int(data.get("income", 0))
        if income <= 0:
            errors.append("Please enter your valid monthly income")
        elif income < 10000:
            errors.append("Minimum monthly income required is Rs.10,000")
        else:
            sanitized["income"] = income
    except (ValueError, TypeError):
        errors.append("Please enter a valid income amount in numbers")
    
    return sanitized, errors


chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.post("/start", response_model=StartChatResponse)
async def start_chat(request: StartChatRequest = None):
    """
    Start a new chat session.
    
    Creates a new conversation session and returns an initial greeting
    from the Master Agent.
    
    Returns:
    - session_id: Unique session identifier
    - greeting: Welcome message from the assistant
    - stage: Current conversation stage
    """
    session_id = request.session_id if request else None
    
    # Create new session
    session = conversation_manager.create_session(session_id)
    
    # Generate greeting from Master Agent
    greeting = master_agent.get_greeting()
    
    # Add greeting to conversation history
    session.add_message("assistant", greeting)
    session.set_stage("greeting")
    
    return StartChatResponse(
        session_id=session.session_id,
        greeting=greeting,
        stage=session.stage,
        timestamp=datetime.utcnow()
    )


@chat_router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message in an existing chat session.
    
    The Master Agent will:
    1. Extract any application information from the message
    2. Update the collected data
    3. Generate an appropriate response
    4. Indicate if ready to process the application
    
    Returns:
    - response: Assistant's reply
    - stage: Current conversation stage
    - collected_data: All information collected so far
    - missing_fields: Fields still needed
    - ready_to_process: Whether application can be submitted
    """
    # Get session
    session = conversation_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found. Please start a new chat."
        )
    
    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session has ended. Please start a new chat."
        )
    
    # Add user message to history
    session.add_message("user", request.message)
    
    # Get conversation history as LangChain messages
    from langchain_core.messages import HumanMessage, AIMessage
    history = []
    for msg in session.get_context_window():
        if msg["role"] == "user":
            history.append(HumanMessage(content=msg["content"]))
        else:
            history.append(AIMessage(content=msg["content"]))
    
    # Build thinking/reasoning trace
    thinking_steps = []
    
    # Step 1: Extract information from message
    thinking_steps.append({
        "agent_name": "master_agent",
        "action": "extracting_info",
        "reasoning": f"Analyzing message for loan application data..."
    })
    
    extracted, validation_errors = master_agent.extract_info(request.message, session.collected_data)
    
    thinking_steps.append({
        "agent_name": "master_agent",
        "action": "extraction_complete",
        "reasoning": f"Extracted {len(extracted)} field(s)" if extracted else "No new data extracted",
        "extracted_data": extracted if extracted else None,
        "validation_errors": validation_errors if validation_errors else None
    })
    
    # Update session with extracted data
    if extracted:
        session.update_data(extracted)
    
    # Get missing fields
    missing_fields = master_agent.get_missing_fields(session.collected_data)
    
    # Determine stage and active agent
    if not session.collected_data:
        stage = "greeting"
        active_agent = "master_agent"
    elif missing_fields:
        stage = "collecting_info"
        active_agent = "master_agent"
    else:
        stage = "confirming"
        active_agent = "master_agent"
    
    thinking_steps.append({
        "agent_name": active_agent,
        "action": "determining_next_step",
        "reasoning": f"Stage: {stage}, Missing fields: {missing_fields if missing_fields else 'None - ready to process!'}"
    })
    
    # Generate response using Master Agent (pass extracted data and validation errors for feedback)
    response = master_agent.generate_response(
        message=request.message,
        history=history,
        current_data=session.collected_data,
        stage=stage,
        just_extracted=extracted,
        validation_errors=validation_errors
    )
    
    thinking_steps.append({
        "agent_name": active_agent,
        "action": "response_generated",
        "reasoning": "Generated conversational response"
    })
    
    # Update stage
    session.set_stage(stage)
    
    # Add assistant response to history
    session.add_message("assistant", response)
    
    # Check if ready to process
    ready_to_process = len(missing_fields) == 0
    
    # Convert thinking steps to AgentThinking models
    from models.chat_schemas import AgentThinking
    thinking = [AgentThinking(**step) for step in thinking_steps]
    
    return ChatResponse(
        session_id=session.session_id,
        response=response,
        stage=stage,
        collected_data=session.collected_data,
        missing_fields=missing_fields,
        ready_to_process=ready_to_process,
        timestamp=datetime.utcnow(),
        active_agent=active_agent,
        thinking=thinking,
        metadata={
            "extracted_info": extracted
        }
    )


@chat_router.post("/process", response_model=ApplicationProcessResponse)
async def process_application(
    request: ProcessApplicationRequest,
    db: Session = Depends(get_db)
):
    """
    Process the complete loan application.
    
    Runs the application through all agents:
    1. Sales Agent - Validates data
    2. Verification Agent - KYC checks
    3. Underwriting Agent - Credit assessment
    4. Sanction Agent - Generates approval letter
    
    Returns:
    - status: SANCTIONED or REJECTED
    - message: Final result message
    - steps: Details from each processing step
    - sanction_pdf_url: PDF download link (if approved)
    """
    # Get session
    session = conversation_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found."
        )
    
    # Check if all required fields are present
    required_fields = ["customer_name", "mobile", "pan", "aadhaar", "loan_amount", "tenure", "income"]
    missing = [f for f in required_fields if f not in session.collected_data or not session.collected_data[f]]
    
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {', '.join(missing)}. Please provide all information before processing."
        )
    
    # Validate and sanitize application data with user-friendly messages
    sanitized_data, validation_errors = validate_application_data(session.collected_data)
    
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="\n".join(validation_errors)
        )
    
    # Create application in database using sanitized data
    db_app = Application(
        customer_name=sanitized_data["customer_name"],
        mobile=sanitized_data["mobile"],
        pan=sanitized_data["pan"],
        aadhaar=sanitized_data["aadhaar"],
        loan_amount=sanitized_data["loan_amount"],
        tenure=sanitized_data["tenure"],
        income=sanitized_data["income"],
        status="PROCESSING"
    )
    
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    
    # Update session with application ID
    session.set_application_id(db_app.id)
    
    # Prepare data for workflow using sanitized data
    workflow_data = {
        "application_id": db_app.id,
        "customer_name": sanitized_data["customer_name"],
        "mobile": sanitized_data["mobile"],
        "pan": sanitized_data["pan"],
        "aadhaar": sanitized_data["aadhaar"],
        "loan_amount": sanitized_data["loan_amount"],
        "tenure": sanitized_data["tenure"],
        "income": sanitized_data["income"],
        "conversation_history": session.messages
    }
    
    # Run the chat-based workflow
    result = run_chat_workflow(workflow_data)
    
    # Update database with results
    db_app.status = result.get("status", "FAIL")
    db_app.workflow_steps = result.get("steps", [])
    if result.get("sanction_pdf_url"):
        db_app.sanction_pdf_path = result["sanction_pdf_url"]
    
    db.commit()
    db.refresh(db_app)
    
    # Store processing result in session
    session.set_processing_result(result)
    session.set_stage("completed" if result.get("status") == "SANCTIONED" else "rejected")
    
    # Add final response to conversation
    final_response = result.get("final_response", "")
    session.add_message("assistant", final_response)
    
    # Build response steps
    processing_steps = []
    for step in result.get("steps", []):
        processing_steps.append(ProcessingStep(
            agent=step.get("node", "unknown"),
            status=step.get("result", "UNKNOWN"),
            message=step.get("message", ""),
            details=step.get("data")
        ))
    
    # Add agent messages as steps
    agent_messages = result.get("agent_messages", [])
    
    return ApplicationProcessResponse(
        session_id=session.session_id,
        status=result.get("status", "FAIL"),
        message=final_response,
        steps=processing_steps,
        sanction_pdf_url=result.get("sanction_pdf_url"),
        application_id=db_app.id,
        timestamp=datetime.utcnow()
    )


@chat_router.get("/session/{session_id}", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """
    Get the current status of a chat session.
    
    Returns:
    - Session stage
    - Collected data
    - Missing fields
    - Whether ready to process
    """
    session = conversation_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found."
        )
    
    # Calculate missing fields
    required_fields = ["customer_name", "mobile", "pan", "aadhaar", "loan_amount", "tenure", "income"]
    missing = [f for f in required_fields if f not in session.collected_data or not session.collected_data[f]]
    
    return SessionStatus(
        session_id=session.session_id,
        stage=session.stage,
        collected_data=session.collected_data,
        missing_fields=missing,
        ready_to_process=len(missing) == 0,
        application_id=session.application_id,
        is_active=session.is_active
    )


@chat_router.get("/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(session_id: str):
    """
    Get the full conversation history for a session.
    """
    session = conversation_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found."
        )
    
    messages = [
        ChatMessage(
            role=MessageRole(msg["role"]),
            content=msg["content"],
            timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else None,
            metadata=msg.get("metadata")
        )
        for msg in session.messages
    ]
    
    return ConversationHistory(
        session_id=session.session_id,
        messages=messages,
        current_stage=session.stage,
        collected_data=session.collected_data,
        application_id=session.application_id,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@chat_router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """
    End a chat session.
    """
    session = conversation_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found."
        )
    
    session.deactivate()
    
    return {
        "message": f"Session {session_id} has been ended.",
        "application_id": session.application_id
    }


@chat_router.get("/sessions")
async def list_sessions():
    """
    List all active chat sessions (admin endpoint).
    """
    active_sessions = conversation_manager.list_active_sessions()
    
    return {
        "total_sessions": conversation_manager.get_session_count(),
        "active_sessions": len(active_sessions),
        "session_ids": active_sessions
    }


@chat_router.post("/cleanup")
async def cleanup_sessions(max_age_hours: int = 24):
    """
    Clean up old sessions (admin endpoint).
    """
    deleted = conversation_manager.cleanup_old_sessions(max_age_hours)
    
    return {
        "message": f"Cleaned up {deleted} old sessions.",
        "remaining_sessions": conversation_manager.get_session_count()
    }
