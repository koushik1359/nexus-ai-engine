"""
Nexus AI Engine — FastAPI Backend
Exposes the LangGraph Multi-Agent system via SSE streaming.
"""

import os
import json
import asyncio
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd
import re

load_dotenv()

# Import our LangGraph engine
from backend.src.agents.graph import build_nexus_graph, db_engine

# Track user-uploaded tables so we can distinguish them
uploaded_tables: set[str] = set()

app = FastAPI(title="Nexus AI Engine", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the graph once at startup
nexus_graph = build_nexus_graph()


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Nexus AI Engine"}


@app.post("/query")
async def query_endpoint(request: QueryRequest, x_session_id: str = Header(None)):
    """Standard (non-streaming) endpoint for the multi-agent system."""
    result = nexus_graph.invoke({
        "user_query": request.query,
        "query_intent":"",
        "sql_query": "",
        "sql_result": "",
        "sql_error": "",
        "retry_count": 0,
        "final_answer": "",
        "agent_steps": [],
        "session_id": x_session_id or "default_session",
    })

    return {
        "answer": result["final_answer"],
        "sql_query": result["sql_query"],
        "steps": result["agent_steps"],
    }


@app.post("/query/stream")
async def query_stream_endpoint(request: QueryRequest, x_session_id: str = Header(None)):
    """SSE streaming endpoint — streams agent reasoning steps in real-time."""

    async def event_generator():
        initial_state = {
            "user_query": request.query,
            "query_intent":"",
            "sql_query": "",
            "sql_result": "",
            "sql_error": "",
            "retry_count": 0,
            "final_answer": "",
            "agent_steps": [],
            "session_id": x_session_id or "default_session",
        }

        sent_steps = 0
        final_state = initial_state

        # Stream the graph in REAL-TIME step-by-step
        for state in nexus_graph.stream(initial_state, stream_mode="values"):
            final_state = state
            
            # If a new step was added, stream it immediately
            current_steps = state.get("agent_steps", [])
            while sent_steps < len(current_steps):
                new_step = current_steps[sent_steps]
                data = json.dumps({"type": "step", "content": new_step})
                yield f"data: {data}\n\n"
                sent_steps += 1
                await asyncio.sleep(0.05) # Tiny pause for smooth UI animation

        result = final_state

        # Stream the SQL query used
        data = json.dumps({"type": "sql", "content": result["sql_query"]})
        yield f"data: {data}\n\n"
       
        # Stream the raw SQL result (for Export CSV button)
        data = json.dumps({"type": "result", "content": result["sql_result"]})
        yield f"data: {data}\n\n"

        # Build and stream chart-ready data (strip IDs, convert Decimals)
        chart_data = None
        if result.get("sql_result"):
            try:
                raw = json.loads(result["sql_result"])
                if isinstance(raw, list) and 0 < len(raw) <= 20:
                    keys = list(raw[0].keys())
                    # Ignore ID columns
                    id_cols = [k for k in keys if k.lower() == "id" or k.lower().endswith("_id")]
                    # Find numeric vs label columns (excluding IDs)
                    remaining = [k for k in keys if k not in id_cols]
                    numeric_cols = []
                    label_col = None
                    for k in remaining:
                        vals = [row.get(k) for row in raw]
                        # Check if all non-None values can be cast to float
                        non_none_vals = [v for v in vals if v is not None]
                        
                        is_numeric = False
                        if len(non_none_vals) > 0:
                            try:
                                [float(v) for v in non_none_vals]
                                is_numeric = True
                            except (ValueError, TypeError):
                                pass
                                
                        if is_numeric:
                            numeric_cols.append(k)
                        elif label_col is None:
                            label_col = k
                    
                    if label_col and numeric_cols:
                        # Prioritize revenue/total/count columns
                        priority = ["revenue", "total", "count", "sales", "price", "amount", "sum", "avg", "quantity"]
                        numeric_cols.sort(key=lambda c: next((i for i, p in enumerate(priority) if p in c.lower()), 999))
                        use_cols = numeric_cols[:2]
                        
                        chart_data = []
                        for row in raw:
                            item = {"name": str(row[label_col])[:25] if row[label_col] is not None else "Unknown"}
                            for c in use_cols:
                                val = row.get(c)
                                item[c] = round(float(val), 2) if val is not None else 0
                            chart_data.append(item)
            except Exception as e:
                print(f"Chart error: {e}")
                pass
        
        if chart_data:
            data = json.dumps({"type": "chart", "content": chart_data})
            yield f"data: {data}\n\n"

        # Stream the final answer
        data = json.dumps({"type": "answer", "content": result["final_answer"]})
        yield f"data: {data}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/schema")
async def get_schema(x_session_id: str = Header(None)):
    """Returns the database schema for the frontend sidebar."""
    from sqlalchemy import inspect, text
    from backend.src.agents.graph import db_engine
    
    session_id = x_session_id or "default_session"
    clean_sid = "".join(c for c in session_id if c.isalnum() or c in "-_")
    
    inspector = inspect(db_engine)
    schema = {}
    
    def fetch_tables(db_schema):
        if db_schema not in inspector.get_schema_names():
            return
            
        for table_name in inspector.get_table_names(schema=db_schema):
            columns = []
            for col in inspector.get_columns(table_name, schema=db_schema):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                })
            
            # Get primary keys
            pk = inspector.get_pk_constraint(table_name, schema=db_schema)
            pk_columns = pk["constrained_columns"] if pk else []
            
            # Get foreign keys
            fks = []
            for fk in inspector.get_foreign_keys(table_name, schema=db_schema):
                fks.append({
                    "column": fk["constrained_columns"],
                    "references": f"{fk['referred_table']}.{fk['referred_columns'][0]}",
                })
            
            # Get row count
            try:
                with db_engine.connect() as conn:
                    result = conn.execute(text(f'SELECT COUNT(*) FROM "{db_schema}"."{table_name}"'))
                    row_count = result.scalar()
            except:
                row_count = 0
            
            if table_name not in schema:
                schema[table_name] = {
                    "schema": db_schema,
                    "columns": columns,
                    "primary_keys": pk_columns,
                    "foreign_keys": fks,
                    "row_count": row_count,
                }
                
    fetch_tables(clean_sid)
    fetch_tables("public")
    
    return {"schema": schema}

# ============================================================
# FILE UPLOAD ENDPOINTS
# ============================================================

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), x_session_id: str = Header(None)):
    """Upload a CSV or SQL file and load it into PostgreSQL as a new schema table."""
    from sqlalchemy import text, inspect
    
    session_id = x_session_id or "default_session"
    clean_sid = "".join(c for c in session_id if c.isalnum() or c in "-_")
    
    filename = file.filename or "uploaded_file"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if ext not in ("csv", "sql"):
        return {"error": "Only .csv and .sql files are supported."}
    
    content = await file.read()
    
    # Create the user schema if it doesn't exist
    from backend.src.agents.graph import db_engine
    with db_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{clean_sid}";'))
    
    if ext == "csv":
        import io
        # Sanitize table name from filename
        table_name = re.sub(r"[^a-z0-9_]", "_", filename.rsplit(".", 1)[0].lower())
        table_name = re.sub(r"_+", "_", table_name).strip("_")
        if not table_name:
            table_name = "uploaded_data"
        
        # Read CSV with pandas
        df = pd.read_csv(io.BytesIO(content))
        
        # Sanitize column names
        df.columns = [re.sub(r"[^a-z0-9_]", "_", c.lower().strip()).strip("_") for c in df.columns]
        
        # Load into PostgreSQL (replace if exists, inside specific schema)
        df.to_sql(table_name, db_engine, schema=clean_sid, if_exists="replace", index=False)
        uploaded_tables.add(table_name)
        
        # Get column info
        inspector = inspect(db_engine)
        columns = [{"name": c["name"], "type": str(c["type"])} for c in inspector.get_columns(table_name, schema=clean_sid)]
        
        return {
            "table_name": table_name,
            "columns": columns,
            "row_count": len(df),
            "message": f"Successfully loaded {len(df)} rows into isolated schema '{clean_sid}', table '{table_name}'."
        }
    
    elif ext == "sql":
        # Execute raw SQL statements
        sql_content = content.decode("utf-8")
        with db_engine.connect() as conn:
            for statement in sql_content.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
            conn.commit()
        
        return {"message": "SQL file executed successfully."}


@app.get("/upload/tables")
async def list_uploaded_tables(x_session_id: str = Header(None)):
    """List all user-uploaded tables for the exact session."""
    from sqlalchemy import inspect
    session_id = x_session_id or "default_session"
    clean_sid = "".join(c for c in session_id if c.isalnum() or c in "-_")
    
    from backend.src.agents.graph import db_engine
    inspector = inspect(db_engine)
    
    all_tables = []
    if clean_sid in inspector.get_schema_names():
        all_tables = inspector.get_table_names(schema=clean_sid)
    
    return {
        "uploaded_tables": all_tables,
        "all_tables": all_tables
    }


@app.delete("/upload/{table_name}")
async def delete_uploaded_table(table_name: str, x_session_id: str = Header(None)):
    """Drop a user-uploaded table from their schema."""
    from sqlalchemy import text
    from backend.src.agents.graph import db_engine
    
    session_id = x_session_id or "default_session"
    clean_sid = "".join(c for c in session_id if c.isalnum() or c in "-_")
    
    with db_engine.connect() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{clean_sid}"."{table_name}"'))
        conn.commit()
    
    return {"message": f"Table '{table_name}' deleted successfully from your session."}


@app.post("/export")
async def export_csv(request: QueryRequest, x_session_id: str = Header(None)):
    """Runs the SQL and returns results as a downloadable CSV."""
    import csv
    import io
    from backend.src.agents.graph import db_engine
    from sqlalchemy import text
    
    # First, get the SQL from the agent
    result = nexus_graph.invoke({
        "user_query": request.query,
        "query_intent":"",
        "sql_query": "",
        "sql_result": "",
        "sql_error": "",
        "retry_count": 0,
        "final_answer": "",
        "agent_steps": [],
        "session_id": x_session_id or "default_session", # Could pass header here if strictly needed
    })
    
    # Execute the SQL and build CSV
    with db_engine.connect() as conn:
        db_result = conn.execute(text(result["sql_query"]))
        rows = db_result.fetchall()
        columns = list(db_result.keys())
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nexus_export.csv"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
