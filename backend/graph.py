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
    novelty_alert: bool
    matching_citation: str
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
    raw_output = run_researcher(
        topic=state["topic"],
        outline=state["outline"],
        raw_research=raw_research,
    )
    
    # Parse JSON output
    try:
        import json
        clean_json = raw_output
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
            
        data = json.loads(clean_json)
        state["research_data"] = data.get("research_data", "")
        state["novelty_alert"] = data.get("novelty_alert", False)
        state["matching_citation"] = data.get("matching_citation", "")
    except Exception as e:
        print(f"[Graph] Error parsing Researcher output: {e}")
        state["research_data"] = raw_output
        state["novelty_alert"] = False
        state["matching_citation"] = ""

    if state.get("novelty_alert"):
        state["events"].append({
            "step": "researcher",
            "status": "rejected",
            "message": f"⚠️ Novelty Alert: Exact match found ({state['matching_citation']}).",
            "novelty_data": {
                "citation": state["matching_citation"]
            }
        })
    else:
        state["events"].append({
            "step": "researcher",
            "status": "done",
            "message": f"✅ Research complete. {len(urls)} sources analyzed.",
        })
    return state


def context_analyst_node(state: ResearchState) -> ResearchState:
    # Skip only if we already have the summary AND it's a revision 
    # (prevents re-running if we are just fixing the draft)
    if state.get("is_revision") and state.get("unique_project_summary") and "No external files were provided" not in state["unique_project_summary"]:
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


def researcher_decision(state: ResearchState) -> str:
    if state.get("novelty_alert"):
        return "alert"
    return "continue"


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
    
    workflow.add_conditional_edges(
        "researcher",
        researcher_decision,
        {
            "alert": END,
            "continue": "context_analyst",
        }
    )
    
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
        "novelty_alert": kwargs.get("novelty_alert", False),
        "matching_citation": kwargs.get("matching_citation", ""),
        "unique_project_summary": kwargs.get("unique_project_summary", ""),
        "draft": kwargs.get("draft", ""),
        "automated_feedback": "",
        "reviewer_result": {},
        "reviewer_feedback": kwargs.get("reviewer_feedback", ""),
        "revision_count": 0 if not kwargs.get("is_revision") else 1,
        "events": [],
    }

    # Run graph using astream_events to get granular updates
    # We yield a "Starting" event immediately
    yield {
        "type": "progress", 
        "data": {
            "step": "planner", 
            "status": "pending", 
            "message": "Initializing Neural Pipeline..."
        }
    }

    emitted_count = 0
    final_state = None

    async for event in graph.astream_events(initial_state, version="v2"):
        kind = event.get("event")
        name = event.get("name")
        
        # When a node starts, we can immediately signal the UI
        if kind == "on_chain_start" and name in ["planner", "researcher", "context_analyst", "writer", "automated_validator", "reviewer"]:
            node_map = {
                "planner": "planner",
                "researcher": "researcher",
                "context_analyst": "context_analyst",
                "writer": "writer",
                "automated_validator": "validator",
                "reviewer": "reviewer"
            }
            step = node_map.get(name)
            if step:
                yield {
                    "type": "progress",
                    "data": {
                        "step": step,
                        "status": "active",
                        "message": f"Agent {name} is starting..."
                    }
                }
        
        # When a node finishes, we check for new events added to the state
        elif kind == "on_chain_end" and name == "LangGraph":
            final_state = event.get("data", {}).get("output")

        # Periodically check state for progress events appended by nodes
        if kind.startswith("on_chain_"):
            data = event.get("data", {})
            # Some event types include the state update
            output = data.get("output")
            if isinstance(output, dict) and "events" in output:
                current_events = output["events"]
                while emitted_count < len(current_events):
                    yield {"type": "progress", "data": current_events[emitted_count]}
                    emitted_count += 1
                    await asyncio.sleep(0.05)

    # Yield all accumulated events that might have been missed
    if final_state and "events" in final_state:
        current_events = final_state["events"]
        while emitted_count < len(current_events):
            yield {"type": "progress", "data": current_events[emitted_count]}
            emitted_count += 1

    # Final result
    if final_state:
        yield {
            "type": "complete",
            "data": {
                "draft": final_state.get("draft", ""),
                "outline": final_state.get("outline", ""),
                "raw_research": final_state.get("raw_research", {}),
                "research_data": final_state.get("research_data", ""),
                "novelty_alert": final_state.get("novelty_alert", False),
                "matching_citation": final_state.get("matching_citation", ""),
                "unique_project_summary": final_state.get("unique_project_summary", ""),
                "compiled_project_data": final_state.get("compiled_project_data", ""),
                "sources": final_state.get("raw_research", {}).get("sources", []),
                "verdict": final_state.get("reviewer_result", {}).get("verdict", ""),
                "revisions": final_state.get("revision_count", 0),
            }
        }
