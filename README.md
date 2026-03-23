# Nexus AI Engine

<div align="center">
  <h3>An Enterprise-Grade, Multi-Tenant GenAI Data Platform</h3>
</div>

**Nexus AI Engine** is a powerful Chat-to-SQL platform that allows users to upload raw data files (CSVs and SQL dumps) and converse with their data using a LangGraph-powered AI Agent. It is engineered with strict multi-tenancy rules to ensure physical data isolation between varying browser sessions in a true serverless PostgreSQL architecture.

---

## 🌟 Key Features

*   **Generative AI Data Agent:** Powered by OpenAI and LangGraph, the agent writes, validates, and executes complex PostgreSQL queries to answer natural language questions about uploaded datasets.
*   **True Sandbox Multi-Tenancy:** Uploading a file dynamically creates an isolated `sess_XYZ` namespace within PostgreSQL. The LangGraph agent is scoped exclusively to the user's isolated session via strict `search_path` manipulation, ensuring zero cross-tenant data leakage.
*   **Enterprise Architecture:** Container-ready, microservices architecture splitting a robust FastAPI python backend from a sleek Next.js React frontend.
*   **Zero-Dollar Cloud Deployment:** Optimized out-of-the-box to run entirely on Azure's Free (F1) tiers and Neon's serverless DBs.

---

## 🏗️ Architecture Stack

### Components
1. **Frontend:** **Next.js 15 (React)** — featuring a modern, dark-mode ChatGPT-styled UI built with TailwindCSS and Lucide-React.
2. **Backend:** **Python 3.11 (FastAPI)** — highly asynchronous routing managing multipart file streaming and streaming LLM responses.
3. **AI Logic Engine:** **LangGraph & LangChain** — utilizing a ReAct state graph architecture (`sql_coder_node`, `executor_node`, `db_executor_node`, `analyst_node`).
4. **Database:** **PostgreSQL (Neon)** — utilizing dynamically generated schemas for session management.

### Platform Integrations
*   **Azure Static Web Apps:** Global CDN hosting the compiled Next.js standalone UI.
*   **Azure App Services (Linux F1):** Executing the Uvicorn ASGI server natively.
*   **GitHub Actions:** Automated CI/CD pipelines deploying directly to the Microsoft Cloud.

---

## 🚀 Local Development Setup

To run Nexus AI Engine safely on your local machine, you will need two terminal windows.

### Prerequisites
*   Node.js v18+
*   Python 3.11+
*   A running PostgreSQL database (locally or via Neon.tech) 
*   An OpenAI API Key

### 1. Configure Secrets
Create a `.env` file at the absolute root of the repository (`nexus_ai_engine/.env`):
```ini
OPENAI_API_KEY=sk-proj-YOUR_OPENAI_KEY
DATABASE_URL=postgresql://user:password@hostname/dbname
```

### 2. Boot the Python API
```bash
# From the root directory
cd backend
python -m venv venv
source venv/bin/activate  # (On Windows use `venv\Scripts\activate`)
pip install -r requirements.txt
python -m uvicorn src.main:app --reload --port 8000
```

### 3. Boot the Next.js UI
```bash
# In a new terminal, from the root directory
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:3000` in your browser.

---

## 🛡️ Security Implementation
Because Nexus translates natural language to executable SQL against active databases, stringent security protocols were designed:
1.  **DLP & Schema Isolation:** Agents route into isolated, randomly-generated session schemas.
2.  **DDL Injection Prevention:** Input parameters like `X-Session-ID` undergo strict RegEx alphanumeric sanitization prior to interacting with SQLAlchemy text wrappers.
3.  **Read-Only Scope Protocol:** The AI node fundamentally operates strictly on `SELECT` statements, with destructive actions naturally stripped.

---
_Engineered by Koushik & Antigravity._
