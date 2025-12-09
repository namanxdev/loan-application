"""
Loan Processing API - Main Application

FastAPI backend for agentic loan processing using LangGraph.
Implements a multi-step workflow: Sales → Verification → Underwriting → Sanction

Run with: uvicorn main:app --reload
"""

import os
import sys

# Add backend directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from api.routes import router
from services.database import engine, Base
from models.schemas import Application  # noqa: F401 - Required for table creation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Creates database tables on startup.
    """
    # Startup: Create database tables
    print("🚀 Starting Loan Processing API...")
    print("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready!")
    
    # Ensure static PDF directory exists
    pdf_dir = os.path.join(os.path.dirname(__file__), "static", "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    print(f"📁 PDF directory: {pdf_dir}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Loan Processing API...")


# Create FastAPI application
app = FastAPI(
    title="Loan Processing API",
    description="""
    Agentic Loan Processing System using LangGraph.
    
    ## Workflow
    The API processes loan applications through a multi-step agent workflow:
    1. **Sales Node**: Validates application data
    2. **Verification Node**: KYC verification (PAN, Aadhaar)
    3. **Underwriting Node**: Credit assessment and eligibility
    4. **Sanction Node**: Generates sanction letter PDF
    
    ## Endpoints
    - `POST /apply`: Create a new loan application
    - `POST /process/{id}`: Process application through workflow
    - `GET /application/{id}`: Get application details
    - `GET /applications`: List all applications
    - `GET /pdfs/{id}.pdf`: Download sanction letter
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for PDF serving
static_dir = os.path.join(os.path.dirname(__file__), "static", "pdfs")
os.makedirs(static_dir, exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=static_dir), name="pdfs")

# Include API routes
app.include_router(router)

# Include Chat routes for conversational loan application
from api.chat_routes import chat_router
app.include_router(chat_router)


@app.get("/")
def root():
    """Root endpoint with API info"""
    return {
        "service": "Loan Processing API",
        "version": "2.0.0",
        "description": "Agentic Loan Processing with Conversational AI",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "# Traditional API": {
                "create_application": "POST /apply",
                "process_application": "POST /process/{application_id}",
                "get_application": "GET /application/{application_id}",
                "list_applications": "GET /applications",
                "download_pdf": "GET /pdfs/{application_id}.pdf"
            },
            "# Chat API (Conversational)": {
                "start_chat": "POST /chat/start",
                "send_message": "POST /chat/message",
                "process_application": "POST /chat/process",
                "get_session": "GET /chat/session/{session_id}",
                "get_history": "GET /chat/history/{session_id}",
                "end_session": "DELETE /chat/session/{session_id}"
            }
        },
        "workflow": [
            "1. Customer lands on chatbot → Master Agent",
            "2. Discusses loan amount & terms → Sales Agent",
            "3. Performs KYC verification → Verification Agent",
            "4. Checks credit score, salary, eligibility → Underwriting Agent",
            "5. Generates sanction letter → Sanction Agent",
            "6. Customer receives instant approval/rejection → Master Agent"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
