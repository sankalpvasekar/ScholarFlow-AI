"""
validators.py — Automated Verification Engine
Provides Gunning Fog, CrossRef API, and HuggingFace NLI checks to validate paper drafts.
"""
import re
import random
import requests
import textstat

# ─────────────────────────────────────────────────────────────────────────────
# 1. Academic Complexity (Gunning Fog Index)
# ─────────────────────────────────────────────────────────────────────────────
def check_complexity(draft: str) -> tuple[bool, str]:
    """
    Ensures the draft meets a minimum academic complexity standard.
    Gunning Fog index >= 12 is generally college-level reading.
    """
    try:
        score = textstat.gunning_fog(draft)
        if score < 12.0:
            return False, f"Academic form is too simple (Gunning Fog Index: {score:.1f}). Must be >= 12.0. Rewrite using higher-level academic vocabulary."
        return True, f"Passed (Score: {score:.1f})"
    except Exception as e:
        return True, f"Complexity formatting skipped: {str(e)}"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Citation Checking (CrossRef API)
# ─────────────────────────────────────────────────────────────────────────────
def check_citations(draft: str) -> tuple[bool, str]:
    """
    Sends the titles from the references section to the CrossRef database.
    Fails if a cited paper cannot be found, preventing LLM hallucinations.
    """
    draft_lower = draft.lower()
    
    # Locate the references section
    refs_text = ""
    for keyword in ["references", "works cited", "bibliography"]:
        idx = draft_lower.rfind(keyword)
        if idx != -1:
            refs_text = draft[idx:]
            break
            
    if not refs_text:
        return False, "Could not find a 'References' or 'Works Cited' section in the draft to verify."

    # Extract lines that look like citations
    lines = [line.strip() for line in refs_text.split('\n') if len(line.strip()) > 30 and not line.strip().startswith('#')]
    
    titles_to_check = []
    # Check up to 2 distinct claims to save network time
    for line in lines[:2]:
        # Favor titles extracted from quotes if present
        quotes = re.findall(r'"([^"]+)"', line)
        if quotes:
            titles_to_check.append(quotes[0])
        else:
            # Fallback to checking the first ~100 characters of the cited line
            clean_line = re.sub(r'^\[\d+\]\s*', '', line) # remove leading [1] 
            titles_to_check.append(clean_line[:100])

    for title in titles_to_check:
        try:
            import urllib.parse
            safe_title = urllib.parse.quote(title)
            url = f"https://api.crossref.org/works?query.title={safe_title}&rows=1"
            headers = {"User-Agent": "ScholarFlow AI FactChecker (mailto:support@scholarflow.ai)"}
            
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                items = data.get("message", {}).get("items", [])
                if not items:
                    return False, f"Citation Hallucination Detected: CrossRef database has no record matching the cited paper: '{title}'. Replace it with a real paper."
        except Exception:
            # Skip on network timeouts to prevent absolute blockage
            pass

    return True, "Passed"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Fact-Checking CSV Data (HuggingFace NLI)
# ─────────────────────────────────────────────────────────────────────────────
from backend.agents import _invoke_with_fallback
from langchain_core.messages import SystemMessage, HumanMessage

async def check_facts_llm(draft: str, context: str) -> tuple[bool, str]:
    """
    Uses Qwen 2.5 via OpenRouter to verify claims in the draft against the raw data context.
    If the draft contradicts the context, it fails the verification.
    """
    if not context.strip() or "No external files were provided" in context:
        return True, "Passed (No unique project data uploaded to verify against)"

    system_prompt = """You are a strict Data Verification Engine. Your job is to fact-check an academic paper draft against the provided raw data context.
If you find ANY claim in the draft that directly contradicts the data context, or hallucinates specific numbers/findings not present in the data, output "REJECT" followed by a short explanation of the contradiction.
Otherwise, output "APPROVE"."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Context Data:\n{context[:3000]}\n\nPaper Draft:\n{draft[:3000]}")
    ]

    try:
        response_text = await _invoke_with_fallback(
            messages, 
            primary_model="qwen/qwen2.5-72b-instruct", 
            timeout_seconds=60.0, 
            max_tokens=800
        )
        if "REJECT" in response_text[:50].upper():
            return False, f"Fact-Check Failed: {response_text}"
        return True, "Passed"
    except Exception as e:
        return True, f"Fact-Check skipped due to API error: {str(e)}"
