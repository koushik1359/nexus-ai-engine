"""
Nexus AI Engine — LangGraph Multi-Agent SQL System
Agents: Router -> SQL Coder -> Executor -> Analyst
"""

import os
import json
from typing import TypedDict, Annotated, Literal
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from sqlalchemy import create_engine, text

load_dotenv()

# ============================================================
# STATE DEFINITION (Shared memory between all agents)
# ============================================================

class NexusState(TypedDict):
    """The shared state that flows through the entire agent graph."""
    user_query: str
    query_intent:str
    sql_query: str
    sql_result: str
    sql_error: str
    retry_count: int
    final_answer: str
    agent_steps: list[str]
    session_id: str


# ============================================================
# DATABASE CONNECTION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")
db_engine = create_engine(DATABASE_URL)

# The schema description that the SQL Coder agent will use
DB_SCHEMA = """
You have access to a PostgreSQL database with the following tables:

1. venues (venue_id, name, city, state, capacity, base_operating_cost, venue_type)
   - Contains 15 venues across major US cities.

2. events (event_id, venue_id, event_name, artist_name, genre, event_date, fan_satisfaction_score)
   - Contains 200 events linked to venues. fan_satisfaction_score is 0-100.

3. ticket_sales (sale_id, event_id, ticket_type, price_paid, quantity, purchase_date, channel)
   - Contains 10,000+ ticket transactions. ticket_type: General, VIP, Premium, Student.
   - channel: Online, Box Office, Mobile App, Reseller.

4. merchandise_inventory (item_id, event_id, product_name, category, stock_quantity, units_sold, unit_price, restock_threshold)
   - Contains 1,000+ merchandise records per event.
   - category: Apparel, Accessories, Collectibles, Food & Beverage.

IMPORTANT RELATIONSHIPS:
- events.venue_id -> venues.venue_id
- ticket_sales.event_id -> events.event_id
- merchandise_inventory.event_id -> events.event_id
"""

# ============================================================
# LLM INITIALIZATION
# ============================================================

llm = ChatOpenAI(model="gpt-4o", temperature=0)


# ============================================================
# AGENT NODES
# ============================================================
def router_node(state: NexusState) -> NexusState:
    """Agent 0: Routes the query — is it a SQL question or a general question?"""
    steps = state.get("agent_steps", [])
    steps.append("🧭 Router: Analyzing query intent...")

    messages = [
        SystemMessage(content="""You are a query intent classifier.
Given a user's question, classify it into one of two categories:

1. "sql" — The question requires querying a database (e.g., "What are the top venues?", "Show me revenue by genre")
2. "general" — The question is general (e.g., "Hello", "What tables do you have?", "How does this work?")

Respond with ONLY the single word: sql or general"""),
        HumanMessage(content=state["user_query"]),
    ]

    response = llm.invoke(messages)
    intent = response.content.strip().lower()

    steps.append(f"📋 Intent classified: {intent}")
    return {**state, "query_intent": intent, "agent_steps": steps}


def general_response_node(state: NexusState) -> NexusState:
    """Handles general (non-SQL) questions."""
    steps = state.get("agent_steps", [])
    steps.append("💬 General Agent: Crafting response...")

    messages = [
        SystemMessage(content=f"""You are Nexus, an AI data assistant for an event management company.
You have access to a PostgreSQL database with these tables: venues, events, ticket_sales, merchandise_inventory.

The user asked a general question (not a SQL query). Respond helpfully.
If they're asking what you can do, explain your capabilities.
If they're greeting you, greet them back and suggest what they can ask.
Keep it concise and professional."""),
        HumanMessage(content=state["user_query"]),
    ]

    response = llm.invoke(messages)
    steps.append("✅ Response ready.")
    return {**state, "final_answer": response.content, "agent_steps": steps}

# ============================================================
# DYNAMIC SCHEMA DISCOVERY
# ============================================================

def get_dynamic_schema(session_id: str = None) -> str:
    """Dynamically reads all tables/columns from PostgreSQL, isolating schemas per session."""
    from sqlalchemy import inspect
    inspector = inspect(db_engine)
    
    lines = ["You have access to a PostgreSQL database with the following tables:\n"]
    clean_sid = "".join(c for c in (session_id or "default_session") if c.isalnum() or c in "-_")
    schemas_to_check = [clean_sid, "public"]
    table_dict = {}
    
    for db_schema in schemas_to_check:
        if db_schema not in inspector.get_schema_names():
            continue
        for table_name in inspector.get_table_names(schema=db_schema):
            if table_name in table_dict:
                continue
                
            columns = inspector.get_columns(table_name, schema=db_schema)
            col_names = ", ".join(c["name"] for c in columns)
            
            # Get row count
            try:
                with db_engine.connect() as conn:
                    row_count = conn.execute(text(f'SELECT COUNT(*) FROM "{db_schema}"."{table_name}"')).scalar()
            except Exception:
                row_count = "?"
            
            table_dict[table_name] = f"({col_names}) - Contains {row_count} rows."
    
    for i, (table_name, desc) in enumerate(table_dict.items(), 1):
        lines.append(f"{i}. {table_name} {desc}\n")
    
    # Add relationships from the original schema
    lines.append("IMPORTANT RELATIONSHIPS (for standard tables):")
    lines.append("- events.venue_id -> venues.venue_id")
    lines.append("- ticket_sales.event_id -> events.event_id")
    lines.append("- merchandise_inventory.event_id -> events.event_id")
    
    return "\n".join(lines)


def sql_coder_node(state: NexusState) -> NexusState:
    """Agent 1: Converts user question into a PostgreSQL query."""
    steps = state.get("agent_steps", [])
    steps.append("✏️ SQL Coder: Generating PostgreSQL query...")

    # If there was a previous error, include it for self-correction
    error_context = ""
    if state.get("sql_error"):
        error_context = f"""
Your previous SQL query failed with this error:
{state['sql_error']}

Please fix the query and try again. Do NOT repeat the same mistake.
"""

    # Use dynamic schema so uploaded tables are auto-discovered for this user's session
    dynamic_schema = get_dynamic_schema(state.get("session_id"))

    messages = [
        SystemMessage(content=f"""You are an expert PostgreSQL query writer.
Given a user's natural language question, write a SINGLE valid PostgreSQL query.

{dynamic_schema}

RULES:
- Return ONLY the raw SQL query, no markdown, no explanation.
- Use proper JOINs when data spans multiple tables.
- Always use aliases for readability.
- LIMIT results to 20 rows max unless the user asks for more.
- Use aggregations (SUM, AVG, COUNT) when appropriate.
{error_context}"""),
        HumanMessage(content=state["user_query"]),
    ]

    response = llm.invoke(messages)
    sql = response.content.strip().replace("```sql", "").replace("```", "").strip()

    steps.append(f"📝 SQL Generated: {sql}")
    return {**state, "sql_query": sql, "agent_steps": steps}


def executor_node(state: NexusState) -> NexusState:
    """Agent 2: Executes the SQL query against PostgreSQL."""
    steps = state.get("agent_steps", [])
    steps.append("⚡ Executor: Running query against PostgreSQL...")

    try:
        from decimal import Decimal
        with db_engine.connect() as conn:
            # Set search_path dynamically to prioritize session isolation!
            session_id = state.get("session_id")
            clean_sid = "".join(c for c in (session_id or "default_session") if c.isalnum() or c in "-_")
            conn.execute(text(f'SET search_path TO "{clean_sid}", public;'))
            
            result = conn.execute(text(state["sql_query"]))
            rows = result.fetchall()
            columns = list(result.keys())

            # Convert to list of dicts for readability, and handle Decimals
            data = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    if isinstance(val, Decimal):
                        row_dict[col] = float(val)
                    else:
                        row_dict[col] = val
                data.append(row_dict)
                
            # Compact json string for SSE stream
            result_str = json.dumps(data, default=str)

            steps.append(f"✅ Query returned {len(data)} rows.")
            return {
                **state,
                "sql_result": result_str,
                "sql_error": "",
                "agent_steps": steps,
            }

    except Exception as e:
        error_msg = str(e)
        retry = state.get("retry_count", 0) + 1
        steps.append(f"❌ SQL Error (Attempt {retry}): {error_msg}")
        return {
            **state,
            "sql_result": "",
            "sql_error": error_msg,
            "retry_count": retry,
            "agent_steps": steps,
        }


def analyst_node(state: NexusState) -> NexusState:
    """Agent 3: Analyzes the SQL results and writes a business-friendly report."""
    steps = state.get("agent_steps", [])
    steps.append("📊 Analyst: Interpreting results and writing report...")

    messages = [
        SystemMessage(content="""You are a senior data analyst at an event management company.
Given raw SQL query results, write a clear, professional, business-friendly summary.

RULES:
- Start with a direct answer to the user's question.
- Use bullet points for key findings.
- Include specific numbers and percentages.
- If relevant, suggest an actionable business recommendation.
- Format currency values with $ signs and commas.
- Keep your response concise but insightful."""),
        HumanMessage(content=f"""
User's Question: {state['user_query']}

SQL Query Used: {state['sql_query']}

Raw Data Results:
{state['sql_result']}
"""),
    ]

    response = llm.invoke(messages)
    steps.append("✅ Analysis complete.")
    return {**state, "final_answer": response.content, "agent_steps": steps}


# ============================================================
# CONDITIONAL ROUTING (The "Self-Correction" Logic)
# ============================================================

def should_retry_or_analyze(state: NexusState) -> Literal["sql_coder", "analyst", "error_out"]:
    """After execution, decide: retry SQL or proceed to analysis."""
    if state.get("sql_error"):
        if state.get("retry_count", 0) < 3:
            return "sql_coder"  # Loop back to fix the SQL
        else:
            return "error_out"  # Give up after 3 attempts
    return "analyst"  # Success! Move to analysis

def route_by_intent(state: NexusState) -> Literal["sql_coder", "general_response"]:
    """Routes based on the classified intent."""
    if state.get("query_intent") == "sql":
        return "sql_coder"
    return "general_response"


def error_out_node(state: NexusState) -> NexusState:
    """Fallback node if SQL fails after 3 retries."""
    steps = state.get("agent_steps", [])
    steps.append("🚫 System: Failed after 3 attempts. Please rephrase your question.")
    return {
        **state,
        "final_answer": "I was unable to generate a valid SQL query for your question after multiple attempts. Please try rephrasing your question.",
        "agent_steps": steps,
    }


# ============================================================
# BUILD THE GRAPH (The State Machine)
# ============================================================

def build_nexus_graph():
    """Constructs and compiles the LangGraph state machine."""
    graph = StateGraph(NexusState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("sql_coder", sql_coder_node)
    graph.add_node("executor", executor_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("general_response", general_response_node)
    graph.add_node("error_out", error_out_node)

    # Entry point: Router decides the path
    graph.set_entry_point("router")

    # Conditional: Route by intent
    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "sql_coder": "sql_coder",
            "general_response": "general_response",
        },
    )

    graph.add_edge("sql_coder", "executor")

    # Conditional: after execution, retry or analyze
    graph.add_conditional_edges(
        "executor",
        should_retry_or_analyze,
        {
            "sql_coder": "sql_coder",
            "analyst": "analyst",
            "error_out": "error_out",
        },
    )

    graph.add_edge("analyst", END)
    graph.add_edge("general_response", END)
    graph.add_edge("error_out", END)

    return graph.compile()



# ============================================================
# ENTRY POINT (For testing in terminal)
# ============================================================

if __name__ == "__main__":
    nexus = build_nexus_graph()

    test_query = "What are the top 5 venues by total ticket revenue?"

    print(f"\n🧠 Nexus AI Engine")
    print(f"{'='*50}")
    print(f"Query: {test_query}\n")

    result = nexus.invoke({
        "user_query": test_query,
        "query_intent":"",
        "sql_query": "",
        "sql_result": "",
        "sql_error": "",
        "retry_count": 0,
        "final_answer": "",
        "agent_steps": [],
        "session_id": "default_session",
    })

    print("\n--- Agent Reasoning Steps ---")
    for step in result["agent_steps"]:
        print(f"  {step}")

    print(f"\n--- Final Answer ---")
    print(result["final_answer"])
