"""
graph.py — ScholarFlow AI
LangGraph state machine orchestrating the 4 AI agents with a Reviewer fallback loop.
Supports async streaming of progress events via an async generator.
"""
import asyncio
from typing import TypedDict, AsyncGenerator
from langgraph.graph import StateGraph, END

from backend.tools import research_web
from backend.agents import run_planner, run_researcher, run_context_analyst, run_writer, run_reviewer
from backend.validators import check_complexity, check_citations, check_facts_nli

MAX_REVISIONS = 3


# ─────────────────────────────────────────────────────────────────────────────
# State Definition
# ─────────────────────────────────────────────────────────────────────────────
class ResearchState(TypedDict):
    topic: str
    level: str
    paper_format: str
    compiled_project_data: str
    is_revision: bool

    # Agent produced fields
    outline: str
    raw_research: dict
    research_data: str
    unique_project_summary: str
    draft: str
    automated_feedback: str
    reviewer_result: dict
    reviewer_feedback: str
    revision_count: int

    # Progress streaming
    events: list[dict]


# ─────────────────────────────────────────────────────────────────────────────
# Node Functions
# ─────────────────────────────────────────────────────────────────────────────
def planner_node(state: ResearchState) -> ResearchState:
    if state.get("is_revision"):
        return state

    print("[Graph] Running Planner Agent...")
    state["events"] = state.get("events", []) + [{
        "step": "planner",
        "status": "active",
        "message": "📝 The Planner is structuring the outline..."
    }]

    outline = run_planner(
        topic=state["topic"],
        level=state["level"],
        paper_format=state["paper_format"],
    )
    state["outline"] = outline

    state["events"].append({
        "step": "planner",
        "status": "done",
        "message": "✅ Outline complete.",
    })
    return state


def researcher_node(state: ResearchState) -> ResearchState:
    if state.get("is_revision"):
        return state

    print("[Graph] Running Researcher Agent...")
    state["events"].append({
        "step": "researcher",
        "status": "active",
        "message": "🔍 The Researcher is scraping the web for sources..."
    })

    # Step 1: Scrape the web
    raw_research = research_web(topic=state["topic"], outline=state["outline"])
    state["raw_research"] = raw_research

    # Emit URLs found
    urls = raw_research.get("urls", [])
    if urls:
        state["events"].append({
            "step": "researcher",
            "status": "active",
            "message": f"🔗 Found {len(urls)} sources: {', '.join(urls[:2])}..."
        })

    # Step 2: Synthesize research data with LLM
    research_data = run_researcher(
        topic=state["topic"],
        outline=state["outline"],
        raw_research=raw_research,
    )
    state["research_data"] = research_data

    state["events"].append({
        "step": "researcher",
        "status": "done",
        "message": f"✅ Research complete. {len(urls)} sources analyzed.",
    })
    return state


def context_analyst_node(state: ResearchState) -> ResearchState:
    if state.get("is_revision"):
        return state

    print("[Graph] Running Context Analyst Agent...")
    state["events"].append({
        "step": "context_analyst",
        "status": "active",
        "message": "🧠 The Brain Filter is reading your uploaded files..."
    })

    if state.get("compiled_project_data"):
        summary = run_context_analyst(
            topic=state["topic"],
            compiled_project_data=state["compiled_project_data"]
        )
        state["unique_project_summary"] = summary
        state["events"].append({
            "step": "context_analyst",
            "status": "done",
            "message": "✅ Master Investigation Document generated.",
        })
    else:
        state["unique_project_summary"] = "No external files were provided. The paper will rely purely on web research."
        state["events"].append({
            "step": "context_analyst",
            "status": "done",
            "message": "⏩ No files uploaded. Skipping data analysis.",
        })

    return state


def writer_node(state: ResearchState) -> ResearchState:
    revision_count = state.get("revision_count", 0)
    feedback = state.get("reviewer_feedback", "")

    if revision_count > 0:
        print(f"[Graph] Running Writer Agent (Revision #{revision_count})...")
        state["events"].append({
            "step": "writer",
            "status": "active",
            "message": f"⚠️ Revising missing components... (Attempt {revision_count + 1})"
        })
    else:
        print("[Graph] Running Writer Agent...")
        state["events"].append({
            "step": "writer",
            "status": "active",
            "message": "✍️ The Writer is drafting the paper..."
        })

    draft = run_writer(
        topic=state["topic"],
        level=state["level"],
        paper_format=state["paper_format"],
        outline=state["outline"],
        research_data=state["research_data"],
        unique_project_summary=state["unique_project_summary"],
        reviewer_feedback=feedback,
    )
    state["draft"] = draft

    state["events"].append({
        "step": "writer",
        "status": "done" if revision_count == 0 else "done",
        "message": "✅ Draft complete. Running Automated Checks..."
    })
    return state


def automated_validator_node(state: ResearchState) -> ResearchState:
    print("[Graph] Running Automated Validator Node...")
    
    draft = state.get("draft", "")
    context = state.get("unique_project_summary", "")
    
    state["events"].append({
        "step": "validator",
        "status": "active",
        "message": "⚙️ Running Gunning Fog, CrossRef, and NLI Fact-Check..."
    })

    # 1. Complexity
    passed_comp, msg_comp = check_complexity(draft)
    if not passed_comp:
        state["automated_feedback"] = f"Automated Check Failed (Complexity): {msg_comp}"
        state["events"].append({"step": "validator", "status": "rejected", "message": f"❌ {msg_comp}"})
        return state

    # 2. Citations
    passed_cit, msg_cit = check_citations(draft)
    if not passed_cit:
        state["automated_feedback"] = f"Automated Check Failed (Citations): {msg_cit}"
        state["events"].append({"step": "validator", "status": "rejected", "message": f"❌ {msg_cit}"})
        return state

    # 3. Fact-Checking NLI
    passed_nli, msg_nli = check_facts_nli(draft, context)
    if not passed_nli:
        state["automated_feedback"] = f"Automated Check Failed (Fact-Check): {msg_nli}"
        state["events"].append({"step": "validator", "status": "rejected", "message": f"❌ {msg_nli}"})
        return state

    state["automated_feedback"] = ""
    state["events"].append({
        "step": "validator",
        "status": "done",
        "message": "✅ All automated checks passed."
    })
    return state


def reviewer_node(state: ResearchState) -> ResearchState:
    print("[Graph] Running Reviewer Agent...")
    state["events"].append({
        "step": "reviewer",
        "status": "active",
        "message": "🧐 The Reviewer is evaluating quality..."
    })

    result = run_reviewer(
        draft=state["draft"],
        level=state["level"],
        paper_format=state["paper_format"],
        research_data=state["research_data"],
    )
    state["reviewer_result"] = result
    state["reviewer_feedback"] = result.get("feedback", "")

    verdict = result.get("verdict", "REJECT")
    if verdict == "APPROVE":
        state["events"].append({
            "step": "reviewer",
            "status": "done",
            "message": "✅ Paper APPROVED by the Reviewer!"
        })
    else:
        state["events"].append({
            "step": "reviewer",
            "status": "rejected",
            "message": f"❌ Draft REJECTED. Feedback: {state['reviewer_feedback'][:200]}..."
        })

    return state


# ─────────────────────────────────────────────────────────────────────────────
# Conditional Edge — Reviewer Decision
# ─────────────────────────────────────────────────────────────────────────────
def reviewer_decision(state: ResearchState) -> str:
    verdict = state.get("reviewer_result", {}).get("verdict", "REJECT")
    revision_count = state.get("revision_count", 0)

    if verdict == "APPROVE":
        return "approved"

    if revision_count >= MAX_REVISIONS:
        print(f"[Graph] Max revisions ({MAX_REVISIONS}) reached. Proceeding anyway.")
        return "approved"

    # Increment revision counter and loop back
    state["revision_count"] = revision_count + 1
    return "rejected"


def automated_decision(state: ResearchState) -> str:
    feedback = state.get("automated_feedback", "")
    revision_count = state.get("revision_count", 0)

    if not feedback:
        return "passed"

    if revision_count >= MAX_REVISIONS:
        print(f"[Graph] Max revisions ({MAX_REVISIONS}) reached in automated checks. Proceeding anyway.")
        return "passed"

    state["revision_count"] = revision_count + 1
    # We must push the automated feedback into the reviewer_feedback so the writer sees it
    state["reviewer_feedback"] = feedback
    return "failed"


# ─────────────────────────────────────────────────────────────────────────────
# Build the Graph
# ─────────────────────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    workflow = StateGraph(ResearchState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("context_analyst", context_analyst_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("automated_validator", automated_validator_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "context_analyst")
    workflow.add_edge("context_analyst", "writer")
    workflow.add_edge("writer", "automated_validator")
    
    workflow.add_conditional_edges(
        "automated_validator",
        automated_decision,
        {
            "passed": "reviewer",
            "failed": "writer",
        }
    )

    workflow.add_conditional_edges(
        "reviewer",
        reviewer_decision,
        {
            "approved": END,
            "rejected": "writer",  # Loop back to writer with feedback
        }
    )

    return workflow.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Async Generator for SSE Streaming
# ─────────────────────────────────────────────────────────────────────────────
async def run_pipeline_stream(
    topic: str,
    level: str,
    paper_format: str,
    **kwargs
) -> AsyncGenerator[dict, None]:
    """
    Runs the full agent pipeline and yields SSE-compatible event dicts.
    Final event contains the completed paper draft.
    """
    graph = build_graph()

    initial_state: ResearchState = {
        "topic": topic,
        "level": level,
        "paper_format": paper_format,
        "compiled_project_data": kwargs.get("compiled_project_data", ""),
        "is_revision": kwargs.get("is_revision", False),
        "outline": kwargs.get("outline", ""),
        "raw_research": kwargs.get("raw_research", {}),
        "research_data": kwargs.get("research_data", ""),
        "unique_project_summary": kwargs.get("unique_project_summary", ""),
        "draft": kwargs.get("draft", ""),
        "automated_feedback": "",
        "reviewer_result": {},
        "reviewer_feedback": kwargs.get("reviewer_feedback", ""),
        "revision_count": 0 if not kwargs.get("is_revision") else 1,
        "events": [],
    }

    # Run graph in thread pool to not block event loop
    loop = asyncio.get_event_loop()
    final_state = await loop.run_in_executor(None, graph.invoke, initial_state)

    # Yield all accumulated events
    for event in final_state.get("events", []):
        yield {"type": "progress", "data": event}
        await asyncio.sleep(0)  # Yield control

    # Final result
    yield {
        "type": "complete",
        "data": {
            "draft": final_state.get("draft", ""),
            "outline": final_state.get("outline", ""),
            "raw_research": final_state.get("raw_research", {}),
            "research_data": final_state.get("research_data", ""),
            "unique_project_summary": final_state.get("unique_project_summary", ""),
            "compiled_project_data": final_state.get("compiled_project_data", ""),
            "sources": final_state.get("raw_research", {}).get("sources", []),
            "verdict": final_state.get("reviewer_result", {}).get("verdict", ""),
            "revisions": final_state.get("revision_count", 0),
        }
    }
