# Agentic Loan Processing System

An intelligent loan application processing system built with **LangGraph**, **FastAPI**, and **PostgreSQL**. This system implements a multi-step agent workflow that automates the entire loan processing pipeline from application to sanction letter generation.

## 🏗️ Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js 16)                         │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Login   │  │  User    │  │ Employee │  │  Apply   │  │ Chatbot  │   │
│  │  Signup  │  │Dashboard │  │Dashboard │  │  Loan    │  │Interface │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                          Zustand Store                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                     │
│   │  AuthStore  │  │  LoanStore  │  │  ChatStore  │                     │
│   └─────────────┘  └─────────────┘  └─────────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ REST API + WebSocket
┌─────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (FastAPI)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  Auth Routes │  │ Application  │  │  Chat Routes │                   │
│  │  /api/auth/* │  │  Routes      │  │  /api/chat/* │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
├─────────────────────────────────────────────────────────────────────────┤
│                        LANGGRAPH AGENT WORKFLOW                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │   QueryCleaner → Master → Sales → Verification → Underwriting    │   │
│  │        ↓            ↓        ↓          ↓             ↓          │   │
│  │   ResponseFormatter ← ← ← ← ← ← ← Sanction ← ← ← ← ← ←           │   │
│  │                                                                  │   │
│  │   🔥 6 Decision Agents + 2 Utility Agents                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                          DATABASE (PostgreSQL)                          │
│   ┌──────┐  ┌──────────────┐  ┌────────────────┐  ┌──────────────┐      │
│   │Users │  │Applications  │  │AgentEvaluations│  │ChatSessions  │      │
│   └──────┘  └──────────────┘  └────────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 🖥️ Dashboards

The system features two distinct web interfaces tailored for different user roles:

#### 👤 Customer Dashboard
- **Loan Application**: Intuitive multi-step form for new loan requests.
- **Status Tracking**: Real-time progress tracking of active applications.
- **Chat Interface**: AI-powered assistant for queries and application support.
- **Document Management**: Upload and view submitted documents.
- **History**: View past applications and sanction letters.

#### 👔 Employee Dashboard (Admin)
- **Application Review**: Comprehensive view of all incoming loan applications.
- **Workflow Monitoring**: Visual status of the agentic workflow for each application.
- **Manual Override**: Ability to intervene or review flagged applications.
- **Analytics**: Statistics on loan processing times, approval rates, and volumes.
- **User Management**: Manage customer accounts and system settings.

### Project Structure

```
agents/
├── .env                          # Environment variables (DATABASE_URL)
├── .venv/                        # Python virtual environment
├── backend/
│   ├── main.py                   # FastAPI application entry point
│   ├── requirements.txt          # Python dependencies
│   ├── agents/                   # LangGraph agent nodes
│   │   ├── __init__.py
│   │   ├── sales_node.py         # Step 1: Input validation
│   │   ├── verification_node.py  # Step 2: KYC verification
│   │   ├── underwriting_node.py  # Step 3: Credit assessment
│   │   └── sanction_node.py      # Step 4: PDF generation
│   ├── graph/
│   │   ├── __init__.py
│   │   └── loan_graph.py         # LangGraph workflow definition
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py             # FastAPI REST endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic & SQLAlchemy models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py           # PostgreSQL connection (SQLAlchemy)
│   │   ├── mock_api.py           # Deterministic KYC/credit APIs
│   │   └── pdf_service.py        # ReportLab PDF generation
│   └── static/
│       └── pdfs/                 # Generated sanction letter PDFs
└── ppt/
    └── Instructions.md           # Original project requirements
```

## 🔄 LangGraph Workflow

The system processes loan applications through a **sequential multi-agent workflow** orchestrated by LangGraph:

```
START → Agent Alpha → Agent Beta → Agent Gamma → Agent Delta → Agent Epsilon → Agent Zeta → END
           (Sales)      (KYC)      (Credit)     (Income)      (Fraud)     (Sanction)
              ↓           ↓           ↓            ↓             ↓             ↓
           [FAIL]      [FAIL]      [FAIL]       [FAIL]        [FAIL]        [FAIL]
```

### 🤖 Agent System Details

The system employs 6 specialized decision agents and 2 utility agents to process applications:

#### Decision Agents (Sequential Processing)

| Agent | Name | Role | Responsibilities |
|-------|------|------|------------------|
| **Agent Alpha** | Sales Validator | Input Validation | • Validates application completeness<br>• Checks loan-to-income ratio (max 5x)<br>• Validates tenure (6-360 months) |
| **Agent Beta** | KYC Verifier | Identity Verification | • Validates PAN format (ABCDE1234F)<br>• Validates Aadhaar (12 digits)<br>• Cross-references identity documents |
| **Agent Gamma** | Credit Analyst | Risk Assessment | • Analyzes credit score (min 650)<br>• Calculates EMI-to-Income ratio (max 50%)<br>• Evaluates repayment capacity |
| **Agent Delta** | Income Analyzer | Financial Analysis | • Verifies income stability<br>• Checks minimum income requirements (min ₹15k)<br>• Analyzes employment type |
| **Agent Epsilon** | Fraud Detector | Security | • Checks for suspicious patterns<br>• Validates document authenticity<br>• Cross-references fraud databases |
| **Agent Zeta** | Sanction Authority | Final Decision | • Compiles all agent results<br>• Makes final approval/rejection decision<br>• Generates official sanction letter PDF |

#### Utility Agents (Chat & Processing)

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **QueryCleaner** | Pre-processing | • Cleans user input<br>• Normalizes data formats<br>• Validates required fields |
| **ResponseFormatter** | Post-processing | • Formats agent outputs for users<br>• Humanizes technical responses<br>• Adds context to decisions |

### State Schema (LoanState)

```python
class LoanState(TypedDict):
    application_id: int
    customer_name: str
    mobile: str
    pan: str
    aadhaar: str
    loan_amount: int
    tenure: int
    income: int
    status: str              # SUCCESS | FAIL | SANCTIONED
    credit_score: int        # Fixed at 750 for demo
    steps: list[dict]        # Audit trail of each node
    sanction_pdf_url: str    # Path to generated PDF
    error_message: str       # Error details if failed
```

## 🗄️ Database Schema

**PostgreSQL Table: `applications`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-increment application ID |
| `customer_name` | VARCHAR(100) | Applicant's full name |
| `mobile` | VARCHAR(10) | 10-digit mobile number |
| `pan` | VARCHAR(10) | PAN number (ABCDE1234F) |
| `aadhaar` | VARCHAR(12) | 12-digit Aadhaar number |
| `loan_amount` | INTEGER | Requested loan amount |
| `tenure` | INTEGER | Loan tenure in months |
| `income` | INTEGER | Monthly income |
| `status` | VARCHAR(20) | CREATED/PROCESSING/SANCTIONED/FAIL |
| `sanction_pdf_path` | VARCHAR(255) | URL to sanction letter PDF |
| `workflow_steps` | JSON | Complete audit trail |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

## 🌐 API Endpoints

### 🔐 Authentication (`/api/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/signup` | Register new user account |
| `POST` | `/login` | Authenticate user & get tokens |
| `POST` | `/refresh` | Refresh access token |
| `GET` | `/me` | Get current user profile |
| `POST` | `/logout` | Logout user |

### 🏦 Loan Processing (`/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/apply` | Create new loan application |
| `POST` | `/process/{id}` | Run agent workflow on application |
| `GET` | `/application/{id}` | Get application details |
| `GET` | `/health` | System health check |
| `GET` | `/pdfs/{id}.pdf` | Download sanction letter PDF |

### 💬 Chat System (`/api/chat`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/start` | Start new chat session |
| `POST` | `/message` | Send message to AI agent |
| `POST` | `/process` | Process application via chat |
| `GET` | `/session/{id}` | Get session status |
| `GET` | `/history/{id}` | Get conversation history |
| `DELETE` | `/session/{id}` | End chat session |

### 👥 Employee/Admin (`/api/admin`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/applications` | List all applications (with filters) |
| `GET` | `/applications/{id}` | Get detailed application info |

### 📡 Streaming (`/api/agents`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stream/{id}` | Real-time SSE agent updates |

### Example: Create & Process Application

**1. Create Application**
```bash
POST /apply
Content-Type: application/json

{
  "customer_name": "Naman",
  "mobile": "9876543210",
  "pan": "ABCDE1234F",
  "aadhaar": "123412341234",
  "loan_amount": 150000,
  "tenure": 24,
  "income": 30000
}

Response: { "application_id": 1, "status": "CREATED" }
```

**2. Process Application**
```bash
POST /process/1

Response:
{
  "status": "SANCTIONED",
  "sanction_pdf_url": "/pdfs/1.pdf",
  "steps": [
    { "node": "sales", "result": "SUCCESS", "message": "All validations passed" },
    { "node": "verification", "result": "SUCCESS", "message": "KYC verification completed" },
    { "node": "underwriting", "result": "SUCCESS", "data": { "credit_score": 750, "emi_calculated": 7054.79 } },
    { "node": "sanction", "result": "SUCCESS", "message": "Sanction letter generated" }
  ]
}
```

## 🔧 Mock Services (Deterministic)

For demo stability, all external APIs are mocked with **deterministic behavior**:

| Service | Behavior |
|---------|----------|
| `verify_pan(pan)` | Returns VERIFIED if format matches `^[A-Z]{5}[0-9]{4}[A-Z]{1}$` |
| `verify_aadhaar(aadhaar)` | Returns VERIFIED if exactly 12 digits |
| `get_credit_score(pan)` | Always returns **750** (EXCELLENT rating) |

## 📄 PDF Generation

Sanction letters are generated using **ReportLab** with:
- Professional NBFC letterhead
- Loan details table (amount, tenure, EMI, credit score)
- Terms and conditions
- Authorized signatory section
- System-generated footer with timestamp

**Output**: `backend/static/pdfs/{application_id}.pdf`

## 🚀 Running the Backend

```bash
# 1. Navigate to project
cd agents

# 2. Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 3. Set up PostgreSQL database
# Create database 'loan_db' and update .env with connection string

# 4. Install dependencies
uv pip install -r backend/requirements.txt

# 5. Run server
cd backend
python main.py

# Server runs at http://127.0.0.1:8000
# Swagger UI: http://127.0.0.1:8000/docs
```

## 📦 Dependencies

```
fastapi>=0.109.0          # Web framework
uvicorn[standard]>=0.27.0 # ASGI server
sqlalchemy>=2.0.0         # ORM
psycopg2-binary>=2.9.9    # PostgreSQL driver
langgraph>=0.2.0          # Agent workflow framework
langchain>=0.3.0          # LLM framework (used by LangGraph)
reportlab>=4.0.0          # PDF generation
pydantic>=2.5.0           # Data validation
python-dotenv>=1.0.0      # Environment variables
```

## 🔜 Next Steps

- [ ] Build Next.js frontend (in parent `EY/` folder)
- [ ] Add real KYC API integration
- [ ] Implement user authentication
- [ ] Add loan disbursement tracking
- [ ] Email notifications for status updates