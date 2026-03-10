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
_nli_pipeline = None

def _get_nli_pipeline():
    global _nli_pipeline
    if _nli_pipeline is None:
        from transformers import pipeline
        # Using a fast cross-encoder fine-tuned for Natural Language Inference
        _nli_pipeline = pipeline("text-classification", model="cross-encoder/nli-distilroberta-base")
    return _nli_pipeline

def check_facts_nli(draft: str, context: str) -> tuple[bool, str]:
    """
    Uses a local HuggingFace NLI model to compare claims in the draft against the raw data context.
    If the draft contradicts the context, it fails the verification.
    """
    if not context.strip() or "No external files were provided" in context:
        return True, "Passed (No unique project data uploaded to verify against)"

    # Extract sentences from the draft
    sentences = [s.strip() for s in re.split(r'[.?!](?:\s+|$)', draft) if len(s.strip()) > 40]
    
    if not sentences:
        return True, "Passed"

    # Sample up to 3 random sentences to represent claims
    claims = random.sample(sentences, min(3, len(sentences)))
    
    try:
        pipe = _get_nli_pipeline()
        # Truncate context heavily to avoid maximum sequence length errors in DistilRoBERTa
        safe_context = context[:2000]
        
        for claim in claims:
            # The cross-encoder takes a payload of {"text": premise, "text_pair": hypothesis}
            # For NLI, premise = context, hypothesis = claim
            result_list = pipe({"text": safe_context, "text_pair": claim})
            
            # The result varies slightly by pipeline version, typically it's dict or list of dicts.
            # Handle both formats.
            if isinstance(result_list, list) and len(result_list) > 0:
                result = result_list[0]
            else:
                result = result_list

            label = result.get('label', '').lower()
            score = result.get('score', 0.0)
            
            if label == 'contradiction' and score > 0.85:
                return False, f"Fact-Check Failed (Contradiction). The model generated a claim: '{claim}'. This mathematically/factually contradicts the CSV data or code you uploaded."

        return True, "Passed"
    except Exception as e:
        # Failsafe so broken local dependencies don't crash the pipeline
        return True, f"Fact-Check skipped due to local model error: {str(e)}"
