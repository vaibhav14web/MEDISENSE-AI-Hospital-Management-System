# MEDISENSE-AI: Clinical Intelligence & Hospital Management System

**MEDISENSE-AI** is a state-of-the-art, AI-powered Hospital Management System (AI-HMS) built for clinical intelligence, predictive operational workflows, automated diagnostic explainability, and multi-role clinical assistance.

---

## 🌟 Key Capabilities

### 1. 🤖 Lumi — Clinical AI Assistant
- **Multi-Role Personalization:** Dynamic clinical personas calibrated for **Patients**, **Attending Physicians**, **Triage Nurses**, and **Hospital Administrators**.
- **Evidence-Based Knowledge Grounding:** Integrated with **16,407 peer-reviewed MedQuAD clinical articles** for reliable decision support.
- **Computer Vision Diagnostics:** Interactive chest radiograph analysis powered by deep learning with **Grad-CAM visual explainability heatmaps**.
- **PostgreSQL Persistence:** Complete session and conversation history persistence with instant new-session isolation.

### 2. 🧠 Predictive No-Show Risk Intelligence (ML)
- **Gradient Boosted Risk Modeling:** XGBoost and LightGBM models trained on clinical appointment features to predict non-attendance before consultation slots.
- **Fairness & Calibration Validation:** Algorithmic bias mitigation ensuring demographic parity and calibrated probabilistic outputs.
- **SHAP Feature Explainability:** Transparent insights into key drivers affecting patient attendance.

### 3. 🏥 Real-Time Clinical Operations & Queue Management
- **Live Consultation Queue:** Status transitions (`SCHEDULED` ➔ `CONFIRMED` ➔ `CHECKED_IN` ➔ `IN_PROGRESS` ➔ `COMPLETED`).
- **Operational KPIs:** Dynamic tracking of patient throughput, fulfillment rates, average consultation times, and physician room allocation.
- **Role-Based Access Control (RBAC):** Strict multi-tenant security isolating patient records, medical directories, and administrative dashboards.

---

## 🏗️ Architecture

```
AI_HMS / MEDISENSE-AI
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # REST API: auth, appointments, patients, ml, llm, analytics
│   │   ├── core/              # Security, JWT, RBAC, config
│   │   ├── db/                # PostgreSQL engine & session management
│   │   ├── models/            # SQLAlchemy ORM definitions
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   └── services/          # LLM service, analytics service, ML inference
│   └── tests/                 # Full unit & integration test suite (50+ tests)
├── frontend/
│   ├── src/
│   │   ├── components/        # Sidebar, Navbar, LoginModal, KPI widgets
│   │   ├── context/           # AuthContext & Multi-role persona switcher
│   │   ├── services/          # API client
│   │   └── views/             # ChatView (Lumi), AnalyticsView, AppointmentsView, MLNoShowView, etc.
│   └── vite.config.js
├── models/
│   ├── imaging/               # ResNet-18 pneumonia classifier & Grad-CAM pipeline
│   ├── no_show/               # XGBoost / LightGBM appointment risk pipelines
│   └── artifacts/             # Trained deep learning model weights
└── docker-compose.yml
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (with PyTorch and CUDA support for imaging inference)
- **Node.js 18+** & npm
- **PostgreSQL 15+**
- **Ollama** (for local clinical LLM inference)

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/vaibhav14web/MEDISENSE-AI-Hospital-Management-System.git
cd MEDISENSE-AI-Hospital-Management-System

# Create & activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp backend/.env.example backend/.env

# Run backend API server
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

### 3. Running Automated Tests
```bash
python backend/verify_all.py
```

---

## 🔒 Security & Privacy
- Zero leakage of raw patient records across tenant boundaries.
- Token-based JWT authentication with granular RBAC enforcement.
- Medical disclaimer guardrails applied across all conversational assistance threads.

---

## 📄 License
This project is licensed under the MIT License.
