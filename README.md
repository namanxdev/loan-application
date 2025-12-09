# Agentic Loan Processing System

An intelligent loan application processing system built with **LangGraph**, **FastAPI**, and **PostgreSQL**. This system implements a multi-step agent workflow that automates the entire loan processing pipeline from application to sanction letter generation.

## 🏗️ Architecture Overview

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

The system processes loan applications through a **deterministic multi-step agent workflow**:

```
START → Sales Node → Verification Node → Underwriting Node → Sanction Node → END
              ↓              ↓                  ↓
           [FAIL]         [FAIL]             [FAIL]
              ↓              ↓                  ↓
             END            END               END
```

### Node Details

| Node | Purpose | Success Criteria |
|------|---------|------------------|
| **Sales Node** | Validates input data | Valid PAN (ABCDE1234F), Aadhaar (12 digits), loan ≥ ₹10,000, tenure 6-360 months |
| **Verification Node** | KYC verification | PAN & Aadhaar format validation (mock API - always passes if format valid) |
| **Underwriting Node** | Credit assessment | Credit score ≥ 600, EMI ≤ 50% income, loan ≤ 50x income |
| **Sanction Node** | Generate PDF | Creates professional sanction letter using ReportLab |

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info and available endpoints |
| `GET` | `/health` | Health check |
| `POST` | `/apply` | Create new loan application |
| `POST` | `/process/{id}` | Run LangGraph workflow on application |
| `GET` | `/application/{id}` | Get application details |
| `GET` | `/applications` | List all applications (paginated) |
| `GET` | `/pdfs/{id}.pdf` | Download sanction letter PDF |

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