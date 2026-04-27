
####################################################################################
# Specter Analytics - Production-ready AI Dashboard Generator
# Complete Streamlit app
# Requirements: streamlit, pandas, plotly, python-dotenv, langchain_groq (or replace with your LLM wrapper)
# Place GROQ API key in .env as GROQ_API_KEY
# Save as ai_dashboard_app_prod.py

import io
import os
import json
import time
import math
import traceback
import warnings
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict, Annotated
import pandas as pd
import numpy as np  
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# LLM client (kept identical to your existing wrapper - replace if needed)
try:
    from langchain_groq import ChatGroq
    from langchain.schema import HumanMessage, AIMessage, SystemMessage
except Exception:
    # Provide a stub so the module file can be linted without the package.
    class ChatGroq:
        def __init__(self, *a, **k): raise RuntimeError("langchain_groq not installed")
    class HumanMessage: pass
    class AIMessage: pass
    class SystemMessage: pass

# ---------------------------
# Basic app configuration
# ---------------------------
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
st.set_page_config(page_title="Specter Analytics", layout="wide")
load_dotenv()
_start_time = time.time()
# ---------------------------
# Helper: Check API Key
# ---------------------------
GROQ_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_KEY:
    st.error("GROQ_API_KEY missing in environment (.env). Add GROQ_API_KEY and restart.")
    st.stop()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=GROQ_KEY)

COLORS = {
    "bg": "#0d0d0d",            
    "card": "#1a1a1a",          
    "text": "#f0f2f6",          
    "accent": "#ffb703",        
    "accent2": "#219ebc",       
    "chart_sequence": [
        "#ffb703",  
        "#219ebc",  
        "#fb8500",  
        "#8ecae6",  
        "#d4a373",  
        "#e63946"   
    ]
}

st.markdown(
    f"""
    <style>
    /* 1. GLOBAL RESET for Dark Mode Compatibility */
    .stApp {{
        background-color: {COLORS['bg']};
    }}
    h1, h2, h3, h4, h5, h6, p, div, span, li {{
        color: {COLORS['text']} !important;
        font-family: 'Helvetica Neue', sans-serif;
    }}
    
    /* 2. CUSTOM GLASS KPI CARDS (Structural Change) */
    .kpi-card {{
        background: linear-gradient(145deg, rgba(22,27,34, 0.9), rgba(22,27,34, 0.4));
        border: 1px solid rgba(255,255,255, 0.1);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }}
    .kpi-value {{
        font-size: 2rem;
        font-weight: 700;
        color: {COLORS['accent']} !important;
        margin: 10px 0;
        text-shadow: 0 0 10px rgba(0, 255, 148, 0.3);
    }}
    .kpi-label {{
        font-size: 0.9rem;
        color: #8b949e !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* 3. CHART CONTAINER STYLING */
    .chart-container {{
        background-color: {COLORS['card']};
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }}

    /* 4. CHAT INTERFACE OVERHAUL */
    .chat-user {{
        background: rgba(0, 255, 148, 0.1);
        border: 1px solid {COLORS['accent']};
        color: white !important;
        padding: 15px;
        border-radius: 15px 15px 0 15px;
        text-align: right;
        margin: 10px 0 10px auto;
        width: fit-content;
        max-width: 80%;
    }}
    .chat-ai {{
        background: #21262d;
        border-left: 3px solid {COLORS['accent2']};
        padding: 15px;
        border-radius: 0 15px 15px 15px;
        margin: 10px 0;
        width: fit-content;
        max-width: 80%;
    }}
    
    /* Hide Streamlit default elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True
)
#This Function checks the values in a pandas Series and attempts to convert them to datetime format if a certain threshold of values can be successfully parsed.
def safe_to_datetime(series: pd.Series, threshold: float = 0.8) -> Optional[pd.Series]:
    """If >threshold of values parse as datetime, convert, else return None."""
    try:
        parsed = pd.to_datetime(series, errors="coerce", format='mixed')
        if parsed.notna().mean() >= threshold:
            return parsed
    except Exception:
        pass
    return None

#this function optimizes the data types of a pandas DataFrame to improve memory usage and performance.
def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Smart conversions to improve types and memory footprint."""
    df = df.copy()
    for col in df.columns:
        try:
            if df[col].dtype == object:
                dt = safe_to_datetime(df[col])
                if dt is not None:
                    df[col] = dt
                    continue
                # numeric detection
                coerced = pd.to_numeric(df[col], errors="coerce")
                if coerced.notna().mean() > 0.8:
                    df[col] = coerced
            # downcast numeric types for memory
            if pd.api.types.is_float_dtype(df[col].dtype):
                df[col] = pd.to_numeric(df[col], downcast="float")
            if pd.api.types.is_integer_dtype(df[col].dtype):
                df[col] = pd.to_numeric(df[col], downcast="integer")
        except Exception:
            continue
    return df
#this function generates a structured JSON profile of a pandas DataFrame,
#summarizing its shape, column data types, null counts, unique value counts, and sample values.
def get_data_profile(df: pd.DataFrame) -> str:
    """
    Return a compact, structured JSON string describing the dataframe.
    This is optimized for LLM consumption.
    """
    profile = {}
    profile["shape"] = {"rows": int(df.shape[0]), "cols": int(df.shape[1])}
    profile["columns"] = []
    for col in df.columns:
        s = df[col]
        col_info = {
            "name": str(col),
            "dtype": str(s.dtype),
            "n_null": int(s.isna().sum()),
            "n_unique": int(s.nunique(dropna=True)),
            "sample_values": s.dropna().astype(str).head(5).tolist()
        }
        # Add summary for numeric/date if applicable
        try:
            if pd.api.types.is_numeric_dtype(s):
                col_info["summary"] = {
                    "min": float(s.min()) if not s.dropna().empty else None,
                    "max": float(s.max()) if not s.dropna().empty else None,
                    "mean": float(s.mean()) if not s.dropna().empty else None,
                    "median": float(s.median()) if not s.dropna().empty else None,
                    "std": float(s.std()) if not s.dropna().empty else None
                }
            elif pd.api.types.is_datetime64_any_dtype(s):
                col_info["summary"] = {
                    "min": str(s.min()) if not s.dropna().empty else None,
                    "max": str(s.max()) if not s.dropna().empty else None
                }
        except Exception:
            pass
        profile["columns"].append(col_info)
    return json.dumps(profile, default=str)

# ---------------------------
# Agent State definition for workflow graph
# ---------------------------
class AgentState(TypedDict):
    messages: Annotated[List[Any], ...] #Stores all the msg between user and AI
    df_head: str #Gets the head of the dataframe
    data_profile: str #Gets the profile of the data
    dashboard_plan: Optional[List[Dict[str, Any]]] #Gets the dashboard plan
    generated_kpis: Optional[List[Dict[str, Any]]] #Gets the generated KPIs(key performance indicators/Vitals)
    filter_query: Optional[str]#Gets the filter query
    intent: Optional[str] #Gets the intent(like what to do with the data)
    analysis_text: Optional[str] #Gets the analysis text 

# ---------------------------
# Utilities: JSON validation / safe parsing
# ---------------------------

def safe_json_loads(text: str) -> Any:
    """Try progressively to parse JSON-like outputs from LLM safely."""
    if not text:
        return None
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        # remove surrounding fences
        parts = text.split("```")
        # take the longest chunk that looks like JSON
        candidates = [p for p in parts if p.strip().startswith("{") or p.strip().startswith("[")]
        if candidates:
            text = candidates[0].strip()
    try:
        return json.loads(text)
    except Exception:
        # try to find the first JSON object in the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
        # fallback: try eval (last resort) in restricted environment
        try:
            obj = eval(text, {"__builtins__": {}}, {})
            return obj
        except Exception:
            return None

def validate_chart_object(chart: Dict[str, Any]) -> bool:
    """Lightweight validation of chart plan pieces."""
    if not isinstance(chart, dict):
        return False
    if "type" not in chart or "x" not in chart:
        return False
    # known chart types
    if chart["type"] not in {"bar", "line", "scatter", "histogram", "pie", "box"}:
        return False
    return True

# ---------------------------
# Intent router: robust blend of rules + LLM fallback
# ---------------------------

def intent_router(state: AgentState):
    """Return dictionary with 'intent' key value in {"update_dashboard","answer_question","greeting"}"""
    msg = state["messages"][-1].content
    text = msg.lower().strip()

    # quick rules for deterministic routing (fast and reliable)
    visual_keywords = ["plot", "chart", "graph", "visualize", "dashboard", "show me", "plot", "draw", "display"]
    numeric_keywords = ["calculate", "what is", "how many", "average", "mean", "median", "sum", "count", "min", "max", "ratio", "%", "percentage"]
    greeting_keywords = ["hi", "hello", "hey", "thanks", "thank you", "reset", "clear", "good morning", "good evening"]

    if any(k in text for k in visual_keywords):
        return {"intent": "update_dashboard"}
    if any(k in text for k in numeric_keywords):
        return {"intent": "answer_question"}
    # if any(k in text for k in greeting_keywords) or len(text.split()) <= 2:
    #     # short utterances more likely conversational
    #     return {"intent": "greeting"}
    if any(k == text.strip() for k in greeting_keywords):  
        return {"intent": "greeting"}


    # LLM fallback classification (conservative)
    prompt = f"""
    Classify the user's intent into one of three labels ONLY:
    - update_dashboard
    - answer_question
    - greeting

    Reply with a single label.

    USER MESSAGE:
    \"\"\"{msg}\"\"\"
    """
    try:
        out = llm.invoke([HumanMessage(content=prompt)])
        label = out.content.strip().lower()
        if label in {"update_dashboard", "answer_question", "greeting"}:
            return {"intent": label}
    except Exception:
        pass

    # safe default
    return {"intent": "answer_question"}

# ---------------------------
# Dashboard architect: produce strict JSON plan with KPIs + charts
# ---------------------------
def dashboard_architect(state: AgentState):
    """
    Build a dashboard plan:
    returns keys: dashboard_plan (list of charts), generated_kpis (list), filter_query (or None), analysis_text
    """
    query = state["messages"][-1].content
    profile = state["data_profile"]
    try:
        profile_obj = json.loads(profile)
    except Exception:
        profile_obj = {"columns": []}

    # Helper to pick numeric columns
    numeric_cols = [c["name"] for c in profile_obj.get("columns", []) if c.get("dtype", "").startswith(("int", "float", "float32", "float64", "int32", "int64"))]
    datetime_cols = [c["name"] for c in profile_obj.get("columns", []) if "datetime" in c.get("dtype", "")]
    categorical_cols = [c["name"] for c in profile_obj.get("columns", []) if c.get("dtype","").startswith("object") or c.get("n_unique",0) < 50]

    # Prepare prompt for the LLM, but keep strict output format requirements
    prompt = f"""
    You are a Dashboard Architect. The user asked: "{query}"

    Data profile (json): {profile}

    REQUIREMENTS:
    - Output strictly valid JSON (no explanation).
    - JSON shape:
      {{
        "filter_query": null or "pandas-query-string",
        "kpis": [{{"label": str,"column": str,"agg": "sum"|"mean"|"count"|"median"}}],
        "charts": [
          {{
            "id": int, "type": "bar"|"line"|"scatter"|"histogram"|"pie"|"box",
            "title": str, "x": str, "y": str or null, "aggregation": "none"|"sum"|"mean"|"count"|"median",
            "color": str or null, "insight": str
          }}
        ],
        "analysis_summary": str
      }}

    GUIDELINES:
    - Choose 4-5 KPIs from numeric columns if possible.
    - Use datetime column for time-series (line) if present and user mentions time.
    - For categorical X with >15 unique values, aggregate and limit to top 10.
    - For part-to-whole use pie ONLY if unique categories < 6.
    - Provide short one-sentence insight for every chart.
    """
    # Ask LLM
    try:
        resp = llm.invoke([SystemMessage(content="Respond ONLY with valid JSON. Do not include any additional text."), HumanMessage(content=prompt)])
        plan_raw = resp.content
    except Exception as e:
        return {"analysis_text": f"Architect LLM error: {e}", "dashboard_plan": [], "generated_kpis": [], "filter_query": None}

    plan = safe_json_loads(plan_raw)
    if not plan:
        # fallback simple heuristic plan if LLM fails to provide valid JSON
        # Build simple top charts using heuristics
        kpis = []
        for c in numeric_cols[:3]:
            kpis.append({"label": f"Sum {c}", "column": c, "agg": "sum"})
        charts = []
        if datetime_cols and numeric_cols:
            charts.append({
                "id": 1, "type": "line", "title": f"Trend of {numeric_cols[0]} over time",
                "x": datetime_cols[0], "y": numeric_cols[0], "aggregation": "none",
                "color": None, "insight": "Look for trends and seasonality."
            })
        if categorical_cols and numeric_cols:
            charts.append({
                "id": 2, "type": "bar", "title": f"Top by {categorical_cols[0]}",
                "x": categorical_cols[0], "y": numeric_cols[0], "aggregation": "sum",
                "color": None, "insight": "Compare top categories."
            })
        if numeric_cols:
            charts.append({
                "id": 3, "type": "histogram", "title": f"Distribution of {numeric_cols[0]}",
                "x": numeric_cols[0], "y": None, "aggregation": "none",
                "color": None, "insight": "Check distribution and skewness."
            })
        return {
            "dashboard_plan": charts,
            "generated_kpis": kpis,
            "filter_query": None,
            "analysis_text": "Auto-generated fallback dashboard plan."
        }

    # Validate and normalize plan
    charts = []
    kpis = []
    try:
        for kpi in plan.get("kpis", []):
            if isinstance(kpi, dict) and "column" in kpi:
                kpis.append(kpi)
        for c in plan.get("charts", []):
            if validate_chart_object(c):
                charts.append(c)
        return {
            "dashboard_plan": charts,
            "generated_kpis": kpis,
            "filter_query": plan.get("filter_query"),
            "analysis_text": plan.get("analysis_summary", "Dashboard planned.")
        }
    except Exception as e:
        return {"analysis_text": f"Error parsing plan: {e}", "dashboard_plan": [], "generated_kpis": [], "filter_query": None}

# ---------------------------
# Safe execution environment for Python code produced by LLM
# ---------------------------

def run_user_code_safe(code: str, df: pd.DataFrame, timeout_seconds: int = 8) -> Dict[str, Any]:
    """
    Execute user-supplied code (generated by LLM) in a controlled environment.
    - The LLM MUST place final output in variable named `result`.
    - A simple timeout is implemented via time checks (cooperative).
    - Builtins are restricted.
    """
    SAFE_BUILTINS = {
    "Exception": Exception,
    "TimeoutError": TimeoutError,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "round": round,
    "len": len,
    "range": range,
    "print": print,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "__import__": __import__,
    "map": map,          # ← ADD THIS
    "zip": zip,          # (optional but recommended)
    "any": any,          # (optional but recommended)
    "all": all,          # (optional but recommended)
}
    # Prepare restricted globals/locals
    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "None": None,
        "True": True,
        "False": False,
        "len": len,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
        "enumerate": enumerate,
        "range": range,
        "TimeoutError": TimeoutError
    }

    local_env = {"df": df.copy(), "pd": pd, "np": np, "result": None, "_start_time": time.time(), "_timeout": timeout_seconds}

    # Add a small helper the LLM can call to check timeout (cooperative)
    timeout_helper = """
def check_timeout():
    import time
    if time.time() - _start_time > _timeout:
        raise TimeoutError("Execution timeout")
"""
    exec(timeout_helper, safe_globals, local_env)

    # Defensive wrapper: ensure the code does not try to import or access dangerous attributes
    forbidden_tokens = ["import os", "import sys", "__import__", "open(", "exec(", "eval(", "subprocess", "socket", "requests", "ftp", "ssh", "pickle", "compile("]
    for tok in forbidden_tokens:
        if tok in code:
            return {"error": f"Forbidden token detected in code: {tok}", "result": None}

    # Wrap code in try/except to capture errors
    wrapped_code = f"""
try:
{chr(10).join('    '+line for line in code.splitlines())}
except TimeoutError as _te:
    result = f'Error: timeout during execution - {{str(_te)}}'
except Exception as _e:
    import traceback
    result = 'Error during execution: ' + str(_e) + '\\n' + traceback.format_exc()
"""
    try:
        exec(wrapped_code, safe_globals, local_env)
        return {"result": local_env.get("result", None), "error": None}
    except Exception as e:
        return {"result": None, "error": f"Execution failed: {e}\n{traceback.format_exc()}"}

# ---------------------------
# Text analyst: produce Python code, run it safely, return result text
# ---------------------------
def text_analyst(state: AgentState):
    query = state["messages"][-1].content
    profile = state["data_profile"]

    code_prompt = f"""
You are an expert-level Python Data Analyst specializing in pandas,numpy. 
You have access to a pandas DataFrame named `df`.

DATA PROFILE (for understanding the dataset):
{profile}

USER QUESTION:
\"\"\"{query}\"\"\"

======================
STRICT CODING RULES
======================
1️⃣ **Output Format**
- You must produce ONLY executable Python code.
- Your final answer MUST be assigned to a variable named `result`.
- Do NOT print anything. No comments. No explanation.

2️⃣ **Column Safety**
- Before using ANY column, always check:
      if 'colname' in df.columns:
- If a required column is missing, set:
      result = "Column <name> not found."
  and STOP.

3️⃣ **Working With Lists / Arrays**
❗ NEVER concatenate lists, numpy arrays, or pandas objects directly with strings.
❗ ALWAYS convert list-like objects:
    for example:'
      vals = df['col'].unique().tolist()
      vals_str = ", ".join(map(str, vals))
      result = "Unique values: " + vals_str
'
4️⃣ **Formatting Rules**
- If the output involves multiple rows → format using `df.to_markdown(index=False)`.
- If computing stats (mean, sum, etc.) → round to 2 decimals.
- If returning a single number → format as:
      result = f"Average age is {{value:.2f}}"

5️⃣ **Filtering & Grouping**
- You may use:
      df.query()
      df.groupby()
      df.sort_values()
      df.value_counts()
  ONLY if the required columns exist.

6️⃣ **Allowed Functions**
- All pandas operations.
- Python built-in functions allowed in the sandbox.
- Do NOT import anything.
- Do NOT use eval/exec.

7️⃣ **Long Operations Safety**
- If using loops or expensive operations, call:
      check_timeout()
      no infinite loops allowed in query, if occurs the code will show timeout error.
      if the user says "any loop" or anything else i don't want u to execute it.
  periodically to avoid long execution.

**Any command that involves unnecessary loops or operations should be avoided.**
======================
EXPECTED PATTERN
======================

# Example structure:
if 'Category' in df.columns and 'Sales' in df.columns:
    grouped = df.groupby('Category')['Sales'].sum().reset_index()
    grouped['Sales'] = grouped['Sales'].round(2)
    table = grouped.to_markdown(index=False)
    result = "Sales by category:\\n\\n" + table
else:
    result = "Required columns not found."

======================
NOW GENERATE THE CODE
======================
Write PYTHON CODE ONLY (no markdown, no comments), 
that answers the user's question correctly, safely, and concisely.
"""

    try:
        code_resp = llm.invoke([HumanMessage(content=code_prompt)])
        code = code_resp.content
        # Strip markdown fences if present
        if code.startswith("```"):
            code = "\n".join(code.strip().splitlines()[1:-1])
    except Exception as e:
        return {"analysis_text": f"LLM code generation failed: {e}"}

    # Execute code safely
    if st.session_state.df is None:
        return {"analysis_text": "Please upload a dataset first."}

    exec_out = run_user_code_safe(code, st.session_state.df, timeout_seconds=10)
    if exec_out.get("error"):
        return {"analysis_text": f"Execution error: {exec_out['error']}"}
    raw_res = exec_out.get("result")
    if raw_res is None:
        return {"analysis_text": "No result produced by the script."}
    return {"analysis_text": str(raw_res)}

# ---------------------------
# Chart processing and rendering
# ---------------------------
def process_chart_data(df: pd.DataFrame, chart_conf: Dict[str, Any]) -> pd.DataFrame:
    temp_df = df.copy()
    agg = chart_conf.get("aggregation", "none")
    x = chart_conf.get("x")
    y = chart_conf.get("y")
    color = chart_conf.get("color")

    # Defensive presence checks
    if x and x not in temp_df.columns:
        return pd.DataFrame()
    if y and y not in temp_df.columns and chart_conf.get("type") != "histogram":
        return pd.DataFrame()

    # Aggregation rules
    try:
        if agg in {"sum", "mean", "count", "median"} and x and y:
            group_cols = [x]
            if color and color in temp_df.columns:
                group_cols.append(color)
            if agg == "sum":
                temp_df = temp_df.groupby(group_cols, as_index=False)[y].sum()
            elif agg == "mean":
                temp_df = temp_df.groupby(group_cols, as_index=False)[y].mean()
            elif agg == "count":
                temp_df = temp_df.groupby(group_cols, as_index=False)[y].count()
            elif agg == "median":
                temp_df = temp_df.groupby(group_cols, as_index=False)[y].median()
        # If X is datetime, sort by it
        if x and pd.api.types.is_datetime64_any_dtype(temp_df[x]):
            temp_df = temp_df.sort_values(x)
        # For bar charts, sort desc by y if present
        if chart_conf.get("type") == "bar" and y and y in temp_df.columns:
            temp_df = temp_df.sort_values(y, ascending=False)
    except Exception:
        pass
    return temp_df

def render_chart(df: pd.DataFrame, conf: Dict[str, Any]):
    try:
        plot_df = process_chart_data(df, conf)
        if plot_df.empty:
            return None
        ctype = conf.get("type")
        title = conf.get("title", "")
        color_col = conf.get("color") if conf.get("color") in plot_df.columns else None

        common_args = dict(data_frame=plot_df, x=conf.get("x"), y=conf.get("y"), title=title,
                           color=color_col, color_discrete_sequence=COLORS["chart_sequence"], template="plotly_white")
        if ctype == "bar":
            fig = px.bar(**common_args)
        elif ctype == "line":
            fig = px.line(**common_args)
        elif ctype == "scatter":
            fig = px.scatter(**common_args)
        elif ctype == "histogram":
            # histogram usually uses x only
            fig = px.histogram(plot_df, x=conf.get("x"), title=title)
        elif ctype == "box":
            fig = px.box(**common_args)
        elif ctype == "pie":
            # for pie, use names and values
            fig = px.pie(plot_df, names=conf.get("x"), values=conf.get("y"), title=title)
        else:
            return None
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=20), title_font_size=16)
        return fig
    except Exception:
        return None

# ---------------------------
# Workflow (simple, deterministic graph)
# ---------------------------
def process_user_message(message: str):
    """High-level coordinator: route intent, produce response or dashboard."""
    # Build initial state
    state: AgentState = {
        "messages": st.session_state.messages.copy(),
        "df_head": "" if st.session_state.df is None else st.session_state.df.head().to_string(),
        "data_profile": get_data_profile(st.session_state.df) if st.session_state.df is not None else "{}",
        "dashboard_plan": st.session_state.dashboard_data.get("charts", []),
        "generated_kpis": st.session_state.dashboard_data.get("kpis", []),
        "filter_query": st.session_state.dashboard_data.get("filter"),
        "intent": None,
        "analysis_text": None
    }
    # Append the new user message to state messages
    state["messages"].append(HumanMessage(content=message))

    # 1. Intent routing
    intent_res = intent_router(state)
    state["intent"] = intent_res.get("intent")

    # 2. Route to appropriate handler
    if state["intent"] == "update_dashboard":
        arch_out = dashboard_architect(state)
        # update stored dashboard
        st.session_state.dashboard_data["charts"] = arch_out.get("dashboard_plan", [])
        st.session_state.dashboard_data["kpis"] = arch_out.get("generated_kpis", [])
        st.session_state.dashboard_data["filter"] = arch_out.get("filter_query")
        response_text = arch_out.get("analysis_text", "Dashboard updated.")
    elif state["intent"] == "answer_question":
        analyst_out = text_analyst(state)
        response_text = analyst_out.get("analysis_text", "Analysis complete.")
    else:
        # greeting / small talk
        response_text = "Hi! I can help analyze your dataset or build dashboards. Try asking: 'Show sales by region as a bar chart' or 'What is the average age?'"

    return response_text

# ---------------------------
# Streamlit UI and app logic
# ---------------------------
def main():
    # Initialize session state
    if "df" not in st.session_state:
        st.session_state.df = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "dashboard_data" not in st.session_state:
        st.session_state.dashboard_data = {"kpis": [], "charts": [], "filter": None}

    # Sidebar controls
    with st.sidebar:
        st.title("Specter Analytics")
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded_file is not None and st.session_state.df is None:
            try:
                # read with best effort encoding
                raw = uploaded_file.getvalue()
                try:
                    content = raw.decode("utf-8")
                except Exception:
                    content = raw.decode("latin-1")
                df = pd.read_csv(io.StringIO(content))
                st.session_state.df = optimize_dataframe(df)
                # clear previous messages/dashboard
                st.session_state.messages = []
                st.session_state.dashboard_data = {"kpis": [], "charts": [], "filter": None}
                st.success("Data uploaded and optimized.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
        if st.session_state.df is not None:
            with st.expander("Data Preview"):
                st.dataframe(st.session_state.df.head(5), width=True)
            if st.button("Clear session and data"):
                # Clear everything safely
                st.session_state.df = None
                st.session_state.messages = []
                st.session_state.dashboard_data = {"kpis": [], "charts": [], "filter": None}
                st.rerun()

    # Main layout
    tab_chat, tab_report = st.tabs(["💬 Analyst Workspace", "📊 Live Executive Report"])

    # Chat workspace
    with tab_chat:
        st.header("AI Analyst")
        chat_area = st.container()
        with chat_area:
            # Render history
            for msg in st.session_state.messages:
                if isinstance(msg, HumanMessage):
                    st.markdown(f"<div class='chat-user'><p>{st.markdown.__wrapped__ and msg.content or msg.content}</p></div>", unsafe_allow_html=True)
                else:
                    # AIMessage or plain text dict entries
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    st.markdown(f"<div class='chat-ai'><p>{content}</p></div>", unsafe_allow_html=True)

        # Chat input
        user_input = st.chat_input("Ask: 'Show sales by region', 'Average age', 'Create a dashboard'")
        if user_input:
            if st.session_state.df is None:
                st.warning("Please upload a CSV file before asking questions.")
            else:
                # Append message to history (streamlit-friendly types)
                st.session_state.messages.append(HumanMessage(content=user_input))
                # Display user message immediately
                st.markdown(f"<div class='chat-user'><p>{user_input}</p></div>", unsafe_allow_html=True)
                # Process user message
                with st.spinner("Thinking..."):
                    try:
                        response_text = process_user_message(user_input)
                    except Exception as e:
                        response_text = f"Internal error while processing: {e}\n{traceback.format_exc()}"
                # Append AI response to session history as AIMessage (for rendering)
                st.session_state.messages.append(AIMessage(content=response_text))
                # Display AI response
                st.markdown(f"<div class='chat-ai'><p>{response_text}</p></div>", unsafe_allow_html=True)
                # Rerun to ensure charts and report reflect new dashboard plan
                st.rerun()

    # Report tab
    with tab_report:
        st.markdown("<h2 style='text-align:center'>Executive Data Overview</h2>", unsafe_allow_html=True)
        if st.session_state.df is None:
            st.info("Upload a dataset to generate a live report.")
        else:
            active_df = st.session_state.df.copy()
            # Apply filter if present
            flt = st.session_state.dashboard_data.get("filter")
            if flt:
                try:
                    active_df = active_df.query(flt)
                except Exception:
                    pass

            # Render KPIs
            kpis = st.session_state.dashboard_data.get("kpis", [])
            if kpis:
                cols = st.columns(min(len(kpis), 4))
                for i, kpi in enumerate(kpis[:4]):
                    try:
                        col_name = kpi.get("column")
                        agg_type = kpi.get("agg", "sum")
                        val = None
                        if col_name in active_df.columns:
                            if agg_type == "sum":
                                val = active_df[col_name].sum()
                            elif agg_type == "mean":
                                val = active_df[col_name].mean()
                            elif agg_type == "median":
                                val = active_df[col_name].median()
                            elif agg_type == "count":
                                val = active_df[col_name].count()
                        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                            disp = "N/A"
                        else:
                            # format
                            if isinstance(val, float):
                                if abs(val) >= 1000:
                                    disp = f"{val:,.0f}"
                                else:
                                    disp = f"{val:,.2f}"
                            else:
                                disp = str(val)
                        cols[i].metric(kpi.get("label", col_name), disp)
                    except Exception:
                        cols[i].metric("Metric", "N/A")

            # Render charts two-per-row
            charts = st.session_state.dashboard_data.get("charts", [])
            if not charts:
                st.markdown("<div style='text-align:center; padding:40px; color:#475569;'><h3>Ask the AI to build a dashboard.</h3></div>", unsafe_allow_html=True)
            else:
                for i in range(0, len(charts), 2):
                    left = charts[i]
                    right = charts[i+1] if i+1 < len(charts) else None
                    c1, c2 = st.columns([1,1])
                    with c1:
                        fig = render_chart(active_df, left)
                        if fig:
                            st.markdown('<div class="report-card">', unsafe_allow_html=True)
                            st.plotly_chart(fig, width=True)
                            if left.get("insight"):
                                st.markdown(f'<div class="insight-box"><p>💡 <b>Insight:</b> {left.get("insight")}</p></div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        else:
                            st.info("Could not render chart (check config).")
                    if right:
                        with c2:
                            fig = render_chart(active_df, right)
                            if fig:
                                st.markdown('<div class="report-card">', unsafe_allow_html=True)
                                st.plotly_chart(fig, width=True)
                                if right.get("insight"):
                                    st.markdown(f'<div class="insight-box"><p>💡 <b>Insight:</b> {right.get("insight")}</p></div>', unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)
                            else:
                                st.info("Could not render chart (check config).")

            # Offer CSV download of filtered dataset
            csv = active_df.to_csv(index=False)
            st.download_button("Download current view as CSV", csv, file_name="Specter_view.csv", mime="text/csv")

if __name__ == "__main__":
    main()