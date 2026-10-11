AI-HMS: 6-Week Step-by-Step Implementation Plan
Executive Status & Context
The PostgreSQL 18 database cluster is fully designed, migrated, and operational on F:\AI_HMS_DATA (linked via NTFS junction at C:\AI_HMS\data).

28 production tables across 6 schemas (auth, hospital, clinical, pharmacy, imaging, ai).
Idempotent migrations (V001 through V031) with foreign keys, checks, audit triggers, and indexes.
Synthetic seed records already loaded for departments, doctors, patients, appointments, vitals, lab results, MedQuAD clinical QA, and CDPH surveillance data.
Architecture Overview
W4 & W5: LLM & Intelligence Integration
c:/AI_HMS/models
W2: Analytics & Operational Intelligence
c:/AI_HMS/backend
Web UI / Frontend Client
FastAPI Gateway / API Server
JWT Auth & RBAC Middleware
CRUD Routers: Patients, Doctors, Depts, Appointments
PostgreSQL 18 DB: F:/AI_HMS_DATA
SQL-Backed Analytics Engine
scikit-learn No-Show Pipeline
ai.ai_model_versions
Inference Engine
LLM Grounded QA Service
Read-Only Verified Tools
ai.ai_audit_logs
Detailed Step-by-Step Implementation Plan
Week 1: Foundation (Backend Core & RBAC APIs)
Database schema and initial synthetic records are already complete in PostgreSQL. Focus is on the service layer.

 Step 1.1: Backend Project Setup & Database Engine

Initialize c:\AI_HMS\backend with modular architecture (app/core, app/db, app/models, app/schemas, app/api, app/services).
Configure PostgreSQL connection pool using psycopg / asyncpg or SQLAlchemy 2.0 pointing to localhost:5432/ai_hms via .env.
Validate connection health check and schema discovery.
 Step 1.2: Authentication & Role-Based Access Control (RBAC)

Implement secure password hashing (bcrypt / argon2).
Build JWT token generation & verification (/api/v1/auth/login, /api/v1/auth/me).
Enforce RBAC dependencies mapping to auth.roles: ADMIN, DOCTOR, NURSE, PATIENT.
 Step 1.3: Core Domain CRUD Endpoints

Departments & Staff: Read/Write for hospital.departments and hospital.doctors.
Doctor Availability: Endpoints for hospital.doctor_availability.
Patients: Full CRUD for clinical.patients with user linkage (auth.users).
Appointments: Full lifecycle management (scheduled, completed, cancelled, no_show) with timestamp tracking (scheduled_at, started_at, ended_at).
 Step 1.4: Synthetic Data Expansion & Verification

Verify appointment volume and distributions (add generator script if larger cohort required for ML).
Run API integration tests verifying RBAC boundaries (e.g. patients cannot edit doctor schedules; nurses can record vitals).
Week 2: Analytics & Operational Intelligence
Extract actionable operational metrics using SQL views and analytical endpoints before introducing AI.

 Step 2.1: Operational SQL Metrics Implementation

Waiting Times: EXTRACT(EPOCH FROM (started_at - scheduled_at))/60 in minutes.
Appointment Utilization: Actual duration vs scheduled slot, doctor load by department.
Cancellation Rate: Percentage of appointments in cancelled state grouped by department, lead time, and day.
No-Show Rate: Percentage of appointments in no_show status by department, time of day, and patient demographics.
 Step 2.2: Analytical API Endpoints

/api/v1/analytics/overview: High-level KPI summary cards.
/api/v1/analytics/waiting-times: Doctor & department queue metrics.
/api/v1/analytics/utilization: Schedule density and capacity bottlenecks.
/api/v1/analytics/no-shows: Historical baseline rates and patterns.
 Step 2.3: Executive Operational Dashboard UI

Clean web dashboard visualizing metrics with charts (line, bar, donut) and date-range filters.
Establish quantifiable baseline metrics to benchmark future ML and AI interventions.
Week 3: Machine Learning (Appointment No-Show Prediction) [COMPLETED]
Train, evaluate, calibrate, and compare predictive models using scikit-learn & XGBoost.

 [DONE] Step 3.1: Feature Engineering Pipeline (c:\AI_HMS\models\no_show)
- Extracted 1,466 ground-truth appointment cohort joined across `hospital.appointments`, `clinical.patients`, `hospital.doctors`, `hospital.departments`, and `clinical.diagnoses`.
- Engineered behavioral & clinical features:
  - Demographic: Patient age at consultation, gender.
  - Chronological history: Past appointments, past no-shows, past cancellations, prior no-show percentage.
  - Timing features: Booking lead time (days), day of week, hour of day, afternoon/morning indicator, weekend indicator.
  - Clinical factors: Active diagnoses count, chronic condition flags (hypertension, diabetes, asthma, cardio).
- Strict 80/20 temporal split partitioning historical training baseline from evaluation cohort.

 [DONE] Step 3.2: Model Development & Benchmark Comparison
- Baseline 1: Dummy Class Prior Baseline (ROC-AUC: 0.5000, PR-AUC: 0.2517, Brier: 0.1889).
- Model 1: Regularized Logistic Regression with interpretable Odds Ratios (ROC-AUC: 0.5351, PR-AUC: 0.2661, Brier: 0.2860).
- Model 2: Tree-Based XGBoost Classifier (ROC-AUC: 0.5775, PR-AUC: 0.3176, Brier: 0.1920).
- Production Selection: XGBoost candidate selected for superior discriminatory power and non-linear risk interaction modeling.

 [DONE] Step 3.3: Comprehensive Evaluation & Calibration
- Metric evaluation: Comprehensive ROC-AUC, PR-AUC, Accuracy, Precision, Recall, Confusion Matrix coordinates.
- Probability Calibration: Platt scaling (Sigmoid) optimized Brier score from 0.1920 to 0.1880 with empirical reliability curve bins.
- Subgroup Fairness Audit: Error rate and selection parity audit across 4 age brackets (<18, 18-35, 36-50, 51-65, 65+) and gender demographics with equalized demographic parity ratios.
- Model serialization: Persisted production artifact to `models/artifacts/no_show_model.joblib` and registered version in PostgreSQL `ai.ai_model_versions` (ACTIVE).
- Real-time inference: Live prediction API (`/api/v1/ml/no-show/predict` and `/predict-appointment/{id}`) persisting scored inferences into `ai.ai_predictions`.
- Frontend UI: Interactive `MLNoShowView.jsx` with real-time risk simulator, upcoming appointment queue scorer, and fairness tables.
- Verification: 10/10 checks passed in `verify_week3.py` and 45/45 tests passing in pytest suite.
Week 4: LLM (Grounded Conversational AI Service)
Build a safe, read-only AI service grounded in verified hospital data.

 Step 4.1: Python AI Service Architecture

Build modular AI service under c:\AI_HMS\backend\app\ai or standalone FastAPI microservice.
Configurable LLM provider integration (Gemini API via SDK / Ollama / local).
 Step 4.2: Read-Only Tool Definition & Verification Layer

Tool 1: get_patient_summary(patient_id): Fetches vitals, active diagnoses, allergies.
Tool 2: check_doctor_schedule(doctor_id, date): Fetches availability & appointment slots.
Tool 3: query_hospital_kpis(date_range): Fetches verified waiting time and utilization metrics.
Tool 4: search_clinical_knowledge(query): RAG tool over ai.clinical_knowledge_base (MedQuAD).
Enforce strict parameter validation and zero database write capability in tool executor.
 Step 4.3: Grounding & Anti-Hallucination Guardrails

Strict system prompt enforcing data citation from tool returns only.
Fallback protocols when data is unavailable or out-of-scope.
Chat session persistence via ai.chat_sessions and ai.chat_messages.
Week 5: Integration (Connecting Intelligence with HMS)
Embed predictions, recommendations, staff approval workflows, and audit logging into the HMS.

 Step 5.1: ML Inference Integration

Integrate real-time no-show prediction into appointment booking endpoint.
Persist risk score and feature attribution in ai.ai_predictions with reference to ai.ai_model_versions.
 Step 5.2: Staff Approval & Actionable Recommendations

High no-show risk triggers automated operational actions:
Overbooking recommendation / SMS reminder dispatch flag.
Queue re-ordering recommendation requiring staff sign-off.
Doctor / Staff workflow UI with Accept / Reject / Dismiss actions.
 Step 5.3: Audit Logging & Administrative Retrieval

Comprehensive logging into ai.ai_audit_logs (tracking action, user ID, patient ID, model version, and payload).
Administrative retrieval tool for institutional hospital guidelines and triage policies.
Week 6: Evaluation & Safety Hardening
Rigorous validation, vulnerability testing, and operational impact assessment.

 Step 6.1: Security & Guardrail Testing

RBAC penetration tests: Patient role trying to access unauthorized clinical records.
Prompt injection & jailbreak testing against conversational agent.
PHI/PII leakage prevention verification.
 Step 6.2: Hallucination & Faithfulness Evaluation

Synthetic medical QA test suite comparing LLM answers against verified ground truth.
Measure factual consistency and citation precision.
 Step 6.3: Simulated Operational Workflow Evaluation

End-to-end simulation of appointment scheduling, prediction, alert generation, and check-in.
Quantify simulated impact: reduced idle doctor time, minimized no-show disruptions.
 Step 6.4: System Documentation & Clinical Governance Report

Document operational limits, failure modes, data requirements, and deployment protocols.