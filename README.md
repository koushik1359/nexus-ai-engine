# 🌌 Nexus AI Engine

<div align="center">
  <img src="https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.104-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-0.0.21-FF4F00?style=for-the-badge" alt="LangGraph" />
  <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</div>

<br/>

**Nexus AI Engine** is a proprietary, enterprise-grade Chat-to-SQL platform. Powered by **GPT-4o** and **LangGraph**, it enables decision-makers to query vast PostgreSQL databases using natural English phrasing. The engine dynamically evaluates schema structures, generates optimized SQL, executes queries, and automatically renders analytical charts—all within a sleek, modern ChatGPT-style interface.

## ✨ Key Features

- **🧠 Multi-Agent LangGraph System**: Uses a Router, SQL Coder, Database Executor, and Final Analyst to ensure 100% accurate, hallucination-free SQL generation and query execution.
- **📊 Auto-Generated Visualizations**: Automatically detects when aggregate data is returned and dynamically renders beautiful Recharts (Pie & Bar charts).
- **📥 Deep Data Integration**: Easily upload raw `.csv` or `.sql` files directly from the UI to instantly create tables in the live Postgres database.
- **👀 Real-Time Schema Discovery**: The AI dynamically inspects the database schema on every query, ensuring complete awareness of user-uploaded tables without manual prompt design.
- **🎨 Premium Interface**: Developed with Next.js 14 and TailwindCSS, featuring a strictly implemented ChatGPT visual design language—complete with transparent flush-left bot avatars, dynamic dark mode palettes, and sticky minimalist input logic.
- **⚡ Production Ready**: Fully containerized using a multi-stage Next.js standalone Docker build, accompanied by FastAPI and PostgreSQL services orchestrated via `docker-compose`.

## 🏗 Architecture

The system follows a strict decoupling between the user interface and the cognitive engine:

1. **Frontend (Next.js / React)**: A highly-organized component architecture (`src/components/ui/`, `src/components/layout/`) housing the Chat interface, Data Explorer sidebar, and Markdown renderer.
2. **Backend (FastAPI / Python)**: Exposes RESTful endpoints for schema introspection, real-time message streaming (`StreamingResponse`), and CSV ingestion.
3. **Intelligence (LangGraph / LangChain)**: Maintains computational state between the LLM and the physical Database. If a SQL query fails, the Executor agent recursively prompts the SQL Coder with the Postgres Error Trace to attempt a self-healing auto-fix.

## 🚀 Getting Started

To run the application locally, you just need Docker installed.

### Prerequisites
- Docker Desktop
- OpenAI API Key

### Running with Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/your-username/nexus-ai-engine.git
cd nexus-ai-engine
```

2. Set your environment variables:
Create a `.env` file in the root directory and add your OpenAI key:
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

3. Spin up the containers:
```bash
docker-compose up --build -d
```

4. **Access the application**:
   - Web UI: http://localhost:3000
   - Backend API Docs: http://localhost:8000/docs
   - PostgreSQL is running on port `5432` internally.

*Note: The first time you launch, it may take a minute for the PostgreSQL container to initialize fully. The backend is configured to wait (`depends_on: service_healthy`) before it starts accepting AI queries.*

## 📂 Project Structure

```text
nexus_ai_engine/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI endpoints & streaming logic
│   │   └── agents/
│   │       ├── graph.py         # LangGraph state machine & nodes
│   │       └── prompts.py       # Few-shot prompting and system messages
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   └── page.tsx             # Main chat application logic
│   ├── src/
│   │   ├── components/          # Reusable UI & Layout chunks
│   │   ├── lib/                 # Utilities (chart parsing)
│   │   └── types/               # TypeScript interfaces
│   ├── Dockerfile
│   └── next.config.ts
├── docker-compose.yml           # Unified orchestration
└── README.md
```

## 📈 Future Roadmap

- [ ] **Implementation of SSO (Single Sign-On)** via NextAuth to protect the dashboard.
- [ ] **Persistent Chat Memory**: Storing conversation threads into Postgres rather than LocalStorage.
- [ ] **Export to PDF**: Generating fully embedded automated reports containing charts + text.

---
*Built with modern tooling by Koushik.*
