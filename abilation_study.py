"""
Ablation Study: Hybrid Intent Routing (HIR) vs. LLM-Only Classification
--------------------------------------------------------------------------
"""

import os
import json
import time
import statistics
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage

load_dotenv()
GROQ_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_KEY:
    raise RuntimeError("GROQ_API_KEY not set in environment. Set it before running.")

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=GROQ_KEY)

visual_keywords = ["plot", "chart", "graph", "visualize", "dashboard", "show me", "draw", "display"]
numeric_keywords = ["calculate", "what is", "how many", "average", "mean", "median", "sum", "count", "min", "max", "ratio", "%", "percentage"]
greeting_keywords = ["hi", "hello", "hey", "thanks", "thank you", "reset", "clear", "good morning", "good evening"]


def llm_classify(query: str) -> str:
    prompt = f"""
    Classify the user's intent into one of three labels ONLY:
    - update_dashboard
    - answer_question
    - greeting

    Reply with a single label.

    USER MESSAGE:
    \"\"\"{query}\"\"\"
    """
    out = llm.invoke([HumanMessage(content=prompt)])
    label = out.content.strip().lower()
    if label in {"update_dashboard", "answer_question", "greeting"}:
        return label
    return "answer_question"  # safe default, matches your existing fallback


def hir_route(query: str) -> tuple[str, bool]:
    """Returns (intent, used_llm_call). Mirrors your production intent_router."""
    text = query.lower().strip()
    if any(k in text for k in visual_keywords):
        return "update_dashboard", False
    if any(k in text for k in numeric_keywords):
        return "answer_question", False
    if any(k == text for k in greeting_keywords):
        return "greeting", False
    # fallback to LLM
    return llm_classify(query), True


def llm_only_route(query: str) -> tuple[str, bool]:
    """Forces every query through LLM classification (the ablated condition)."""
    return llm_classify(query), True


def run_condition(queries: list[dict], route_fn) -> dict:
    latencies = []
    llm_calls = 0
    results = []

    for item in queries:
        q = item["query"]
        start = time.time()
        intent, used_llm = route_fn(q)
        elapsed = time.time() - start

        latencies.append(elapsed)
        if used_llm:
            llm_calls += 1

        results.append({
            "query": q,
            "category": item.get("category"),
            "predicted_intent": intent,
            "latency_sec": round(elapsed, 4),
            "used_llm": used_llm
        })

    return {
        "avg_latency_sec": round(statistics.mean(latencies), 4),
        "median_latency_sec": round(statistics.median(latencies), 4),
        "total_llm_calls": llm_calls,
        "llm_call_rate_pct": round(100 * llm_calls / len(queries), 2),
        "total_queries": len(queries),
        "per_query_results": results
    }


def main():
    with open("queries.json", "r") as f:
        queries = json.load(f)

    print(f"Loaded {len(queries)} queries. Running HIR condition...")
    hir_results = run_condition(queries, hir_route)

    print("Running LLM-only (ablated) condition...")
    llm_only_results = run_condition(queries, llm_only_route)

    summary = {
        "HIR": {
            "avg_latency_sec": hir_results["avg_latency_sec"],
            "llm_call_rate_pct": hir_results["llm_call_rate_pct"],
            "total_llm_calls": hir_results["total_llm_calls"],
        },
        "LLM_only": {
            "avg_latency_sec": llm_only_results["avg_latency_sec"],
            "llm_call_rate_pct": llm_only_results["llm_call_rate_pct"],
            "total_llm_calls": llm_only_results["total_llm_calls"],
        }
    }

    latency_reduction_pct = round(
        100 * (llm_only_results["avg_latency_sec"] - hir_results["avg_latency_sec"])
        / llm_only_results["avg_latency_sec"], 2
    )
    call_reduction_pct = round(
        100 * (llm_only_results["total_llm_calls"] - hir_results["total_llm_calls"])
        / llm_only_results["total_llm_calls"], 2
    )

    print("\n=== ABLATION SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nLatency reduction from HIR: {latency_reduction_pct}%")
    print(f"LLM call reduction from HIR: {call_reduction_pct}%")

    with open("ablation_results.json", "w") as f:
        json.dump({
            "summary": summary,
            "latency_reduction_pct": latency_reduction_pct,
            "llm_call_reduction_pct": call_reduction_pct,
            "hir_detail": hir_results,
            "llm_only_detail": llm_only_results
        }, f, indent=2)

    print("\nFull results saved to ablation_results.json")


if __name__ == "__main__":
    main()