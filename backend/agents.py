"""
agents.py — ScholarFlow AI
Four AI agent functions using Gemini 1.5 Flash via langchain-google-genai.
Each agent has a specific persona, system prompt, and strict output contract.
All 5 academic formats (IEEE, APA, MLA, Chicago, ACM) are fully supported.
"""
import os
import json
import asyncio
from langchain_groq import ChatGroq

from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

from backend.logger import log_debug

load_dotenv()


from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def _get_gemini_llm(temperature: float = 0.3, timeout: float = 60.0, max_tokens: int = None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    kwargs = {
        "model": "gemini-flash-latest",
        "google_api_key": api_key,
        "temperature": temperature,
        "convert_system_message_to_human": True,
        "max_retries": 2,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return ChatGoogleGenerativeAI(**kwargs)

def _get_openrouter_llm(model_name: str, temperature: float = 0.3, timeout: float = 45.0, max_tokens: int = None):
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables.")
    kwargs = {
        "model": model_name,
        "openai_api_key": openrouter_api_key,
        "openai_api_base": "https://openrouter.ai/api/v1",
        "temperature": temperature,
        "timeout": timeout,
        "max_retries": 0,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)

async def _invoke_with_fallback(messages, primary_model: str = "gemini-flash-latest", timeout_seconds=120.0, max_tokens=None):
    """
    Attempts to use the requested primary model first.
    Falls back to secondary models if the primary fails.
    """
    # Combined model order for maximum reliability
    models_to_try = [primary_model] + [
        "groq/llama-3.3-70b-versatile",
        "deepseek/deepseek-chat",
        "anthropic/claude-3-haiku",
        "google/gemini-flash-1.5"
    ]
    
    last_err = None
    for model_name in models_to_try:
        try:
            log_debug(f"Attempting LLM: {model_name}...")
            
            if "groq/" in model_name.lower():
                from langchain_groq import ChatGroq
                api_key = os.getenv("GROQ_API_KEY")
                llm = ChatGroq(model=model_name.replace("groq/", ""), groq_api_key=api_key, temperature=0.3)
            elif "gemini" in model_name.lower() and "google/" not in model_name:
                llm = _get_gemini_llm(max_tokens=max_tokens)
            else:
                llm = _get_openrouter_llm(model_name, timeout=timeout_seconds, max_tokens=max_tokens)
                
            res = await asyncio.wait_for(llm.ainvoke(messages), timeout=timeout_seconds)
            log_debug(f"Success with {model_name}.")
            return res.content.strip()
        except Exception as e:
            log_debug(f"Model {model_name} failed: {type(e).__name__} - {str(e)}")
            last_err = e
            
    log_debug("All primary and fallback models failed.")
    raise last_err






# ─────────────────────────────────────────────────────────────────────────────
# FORMAT RULES REGISTRY
# Contains precise, format-specific rules injected into every agent prompt
# ─────────────────────────────────────────────────────────────────────────────
FORMAT_RULES = {
    "IEEE Double Column": {
        "field":        "Computer Science, Engineering, Information Technology",
        "layout":       "Two-column layout. Title, authors, and abstract are full-width centered at top; body text splits into two columns.",
        "citation_style": "Numeric citations in square brackets: [1], [2], [3]. References are ordered sequentially by first appearance in the text, NOT alphabetically.",
        "heading_style":  "Section headings are Roman numerals: I. INTRODUCTION, II. RELATED WORK, etc. All caps, centered.",
        "sections":     "Abstract (no heading, italic), I. Introduction, II. Literature Review, III. Theoretical Framework, IV. Methodology, V. Results & Discussion, VI. Conclusion, References",
        "special_rules": "Abstract is written without a header, just the word Abstract in bold before the paragraph. Author affiliations are listed below names. No title page.",
        "citation_example": 'Example: "YOLOv3 achieves high detection speed [1]. Arduino enables real-time control [2]."',
        "ref_example":  '[1] J. Redmon and A. Farhadi, "YOLOv3: An Incremental Improvement," arXiv:1804.02767, 2018.',
    },
    "APA Style": {
        "field":        "Social Sciences, Education, Psychology, General Sciences",
        "layout":       "Single-column. 12pt Times New Roman or Arial. 1-inch margins. Double-spaced throughout.",
        "citation_style": "Author-Date in-text citations: (Smith, 2023) or Smith (2023) found that... For multiple authors: (Smith & Jones, 2023). For 3+ authors: (Smith et al., 2023).",
        "heading_style":  "5 levels: Level 1 = Centered Bold Title Case; Level 2 = Flush Left Bold Title Case; Level 3 = Flush Left Bold Italic Title Case; Level 4 = Indented Bold Title Case period; Level 5 = Indented Bold Italic Title Case period.",
        "sections":     "Title Page (separate page), Abstract (separate page, 150–250 words), Introduction, Literature Review, Theoretical Framework, Methodology, Results, Discussion, Conclusion, References",
        "special_rules": "Requires a separate Title Page with: title (bold), author name, institutional affiliation, course name, instructor name, and date. Running head at top of every page. References page is a new page titled 'References' (centered bold).",
        "citation_example": 'Example: "Traffic density prediction has improved significantly (Smith & Lee, 2022). Johnson et al. (2021) demonstrated that..."',
        "ref_example":  "Smith, J. A., & Lee, K. (2022). Traffic management using deep learning. Journal of Transportation, 45(3), 112–128. https://doi.org/10.xxxx",
    },
    "MLA Style": {
        "field":        "Humanities, Literature, Arts, Cultural Studies, Languages",
        "layout":       "Single-column. 12pt Times New Roman. 1-inch margins. Double-spaced. No separate title page.",
        "citation_style": "Author-Page in-text citations using parentheses: (Smith 45) or (Smith and Jones 112). This prioritizes WHERE in a source, not when it was published. Works Cited at end.",
        "heading_style":  "No formal heading levels required. Title is centered. Sections may use descriptive headings (not numbered).",
        "sections":     "Header block (top-left: author, professor, course, date), Title (centered), Introduction, Body sections (Literature Review, Analysis, Discussion), Conclusion, Works Cited",
        "special_rules": "No separate title page. On the first page, top-left corner: Your Name / Professor Name / Course Name / Date (all double-spaced). Then the title centered. Works Cited page at end lists all sources alphabetically. Page numbers appear as 'LastName #' in the top-right header.",
        "citation_example": 'Example: "The concept was first proposed by Thompson, who argued that \'pattern recognition is central to AI\' (Thompson 78). Visual detection systems have evolved rapidly (Kim and Park 234)."',
        "ref_example":  'Thompson, Alan R. "Pattern Recognition in Neural Architectures." AI Quarterly, vol. 12, no. 2, 2021, pp. 75–90.',
    },
    "Chicago Style": {
        "field":        "History, Business, Fine Arts, Philosophy, Religious Studies",
        "layout":       "Single-column. 12pt Times New Roman. 1-inch margins. Double-spaced body text. Footnotes single-spaced.",
        "citation_style": "Footnote/Endnote system. Superscript numbers appear in the body text¹, and full citation details appear at the bottom of the page as footnotes (Chicago A) OR at the end as endnotes (Chicago B). Bibliography at end lists all sources alphabetically.",
        "heading_style":  "No formal numbered headings required. Section titles are centered or flush left. Title is centered, bold, or in title case.",
        "sections":     "Title Page (separate), Introduction, Literature Review / Background, Theoretical Framework, Methodology, Analysis & Results, Discussion, Conclusion, Bibliography",
        "special_rules": "Use footnotes extensively. When a fact is stated, place a superscript number and add the full citation in the footnote. Footnotes allow writers to add commentary or historical context without interrupting the main paragraph. The Bibliography uses a hanging indent format.",
        "citation_example": 'Example: "The system demonstrated 94% accuracy in controlled conditions.¹" → Footnote: 1. James A. Brown, Modern Traffic Systems (Chicago: University Press, 2021), 145.',
        "ref_example":  "Brown, James A. Modern Traffic Systems. Chicago: University of Chicago Press, 2021.",
    },
    "ACM Style": {
        "field":        "Advanced Computing, Algorithms, Software Engineering, HCI, IT Research",
        "layout":       "Two-column layout (similar to IEEE). Strict typographic rules for code blocks, algorithms, and mathematical proofs.",
        "citation_style": "Numeric citations in square brackets [1], [2]. However, references are listed alphabetically by author surname at the end, then numbered. The number in-text corresponds to the alphabetical position.",
        "heading_style":  "Section headings are numbered (1 INTRODUCTION, 2 RELATED WORK, etc.). Bold. Subsections are 1.1, 1.2, etc.",
        "sections":     "Abstract (with CCS Concepts and Keywords below it), 1. Introduction, 2. Related Work, 3. System Design / Theoretical Framework, 4. Implementation / Methodology, 5. Evaluation & Results, 6. Discussion, 7. Conclusion, Acknowledgments, References",
        "special_rules": "MUST include CCS Concepts metadata below the abstract. Format: '• Computing methodologies → Machine learning; • Computer systems organization → Embedded systems.' Also include Keywords line below CCS Concepts. Code listings must use monospace font inside a numbered 'Listing' environment. Algorithms use a formal pseudocode 'Algorithm' block.",
        "citation_example": 'Example: "Our approach builds on prior object detection work [3, 7]. The Arduino integration follows established embedded patterns [12]."',
        "ref_example":  "[1] Redmon, J. and Farhadi, A. 2018. YOLOv3: An Incremental Improvement. arXiv:1804.02767.",
    },
}


def _get_format_rules(paper_format: str) -> dict:
    """Return format rules dict, defaulting to IEEE if format not recognized."""
    for key in FORMAT_RULES:
        if key.lower() in paper_format.lower() or paper_format.lower() in key.lower():
            return FORMAT_RULES[key]
    return FORMAT_RULES["IEEE Double Column"]


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1: THE PLANNER — "The Architect"
# ─────────────────────────────────────────────────────────────────────────────
async def run_planner(topic: str, level: str, paper_format: str) -> str:
    """
    Creates a detailed academic paper outline.
    Returns: A structured bullet-point outline string.
    """
    fmt = _get_format_rules(paper_format)
    fmt = _get_format_rules(paper_format)

    system_prompt = f"""You are an expert Academic Planner with decades of experience in structuring \
research papers across all disciplines. Your persona is "The Architect" — \
highly organized, strictly focused on structure, and you refuse to write actual content.

Your task: Create a highly detailed academic paper outline.

PARAMETERS:
- Topic: {topic}
- Target Audience Level: {level}
- Paper Format/Style: {paper_format}
- Primary Field: {fmt['field']}

FORMAT-SPECIFIC STRUCTURE RULES:
- Required sections (in order): {fmt['sections']}
- Heading style: {fmt['heading_style']}
- Special structural rules: {fmt['special_rules']}

INSTRUCTIONS:
1. Generate a strict academic outline following ONLY {paper_format} standards.
2. Use the EXACT section order specified above for {paper_format}.
3. Under each section, provide 3–5 bullet points describing WHAT must be covered.
4. Adjust depth and complexity appropriately for a {level} audience.
5. Note inside the outline which sections require special formatting elements \
   (e.g., footnotes for Chicago, CCS Concepts for ACM, Title Page for APA/Chicago).
6. Do NOT write actual paragraphs or content. Only output section headings and bullet points.

Output ONLY the structured outline. No preamble or commentary."""

    log_debug(f"Calling Planner LLM. Topic Length: {len(topic)} chars. Format: {paper_format}")
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Create the {paper_format} academic outline for: {topic}"),
        ]
        response_text = await _invoke_with_fallback(messages, primary_model="deepseek/deepseek-chat", timeout_seconds=45.0, max_tokens=1000)
        log_debug("Planner LLM responded successfully.")
        return response_text

    except asyncio.TimeoutError:
        log_debug("ERROR: Planner LLM timed out after 45 seconds.")
        return f"Error: Planner generation timed out. The topic might be too long ({len(topic)} chars) or the API is unresponsive."
    except Exception as e:
        log_debug(f"ERROR: Planner LLM failed: {str(e)}")
        return f"Error: Planner generation failed: {str(e)}"





# ─────────────────────────────────────────────────────────────────────────────
# Agent 2: THE RESEARCHER — "The Detective"
# ─────────────────────────────────────────────────────────────────────────────
async def run_researcher(topic: str, outline: str, raw_research: dict) -> str:
    """
    Synthesizes raw web-scraped data into structured research notes and checks for novelty.
    Returns: A JSON string containing 'research_data', 'novelty_alert' (bool), and 'matching_citation' (str).
    """

    sources_text = ""
    for i, source in enumerate(raw_research.get("sources", []), 1):
        sources_text += f"""
SOURCE [{i}]:
Title: {source['title']}
URL: {source['url']}
Snippet: {source['snippet']}
Full Text (excerpt):
{source['full_text'][:2000]}
---"""

    system_prompt = f"""You are an elite Academic Researcher with the persona of "The Detective" — \
incredibly meticulous, deeply curious, and completely fact-driven. \
You only work with evidence you can directly cite.

Your task:
1. Synthesize the following web-scraped research data into a comprehensive, structured research brief.
2. NOVELTY CHECK: Compare the user's proposed topic and methodology (from the outline) against the sources. 
   If any source is a "95% match" or an exact match to the proposed methodology, set 'novelty_alert' to true and provide the citation.

PAPER OUTLINE TO SUPPORT:
{outline}

RAW SOURCES FROM THE WEB:
{sources_text}

INSTRUCTIONS:
1. Extract ALL relevant facts, data points, statistics, formulas, quotes, and findings.
2. Match each fact to the relevant section of the outline.
3. Label each extracted fact with: [TITLE_OF_SOURCE, YEAR_IF_AVAILABLE, URL].
4. Identify key concepts, methodologies, and contradictory findings.
5. NOVELTY ALERT: If a source (e.g., Wang, 2023) already implements the proposed methodology, flag it.

OUTPUT FORMAT:
Respond ONLY in this exact JSON format:
{{
  "research_data": "the full structured research brief text here...",
  "novelty_alert": true or false,
  "matching_citation": "Citation of matching paper or empty string"
}}"""

    log_debug(f"Calling Researcher LLM. Topic: {topic[:50]}...")
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Synthesize research data and check for novelty for: {topic}"),
        ]
        response_text = await _invoke_with_fallback(messages, primary_model="mistralai/mixtral-8x7b-instruct", timeout_seconds=60.0, max_tokens=2000)
        log_debug("Researcher LLM responded successfully.")
        return response_text

    except asyncio.TimeoutError:
        log_debug("ERROR: Researcher LLM timed out after 60 seconds.")
        return json.dumps({"research_data": "Error: Researcher timed out.", "novelty_alert": False, "matching_citation": ""})
    except Exception as e:
        log_debug(f"ERROR: Researcher LLM failed: {str(e)}")
        return json.dumps({"research_data": f"Error: Researcher failed: {str(e)}", "novelty_alert": False, "matching_citation": ""})


# ─────────────────────────────────────────────────────────────────────────────
# Agent 3: THE CONTEXT ANALYST — "The Brain Filter"
# ─────────────────────────────────────────────────────────────────────────────
async def run_context_analyst(topic: str, compiled_project_data: str) -> str:
    """
    Synthesizes massive unstructured user uploads (code, CSV data, notes)
    into a structured 'Master Investigation Document'.
    """

    system_prompt = f"""You are a Senior Systems Architect and Lead Data Scientist.
The user is writing an academic research paper on: '{topic}'.

Below is a massive, raw data dump containing an unlimited number of files the user uploaded. \
This includes source code, raw CSV datasets, hardware notes, and reference documents.

RAW PROJECT FILES DATA:
{compiled_project_data}

Your strict objective is to read ALL of the provided files and synthesize them into a \
single, highly structured 'Master Investigation Document'. You must extract the \
technical truth of what the user actually built and tested.

Format your output EXACTLY with the following headings:

1. HARDWARE & ARCHITECTURE:
(List all physical components, microcontrollers, cameras, and wiring configurations found in the notes or code).

2. SOFTWARE & ALGORITHMIC METHODOLOGY:
(Explain the core logic. What libraries were used? What are the key functions? Explain the exact thresholds or if/then logic found in the source code).

3. EMPIRICAL RESULTS & DATA TRENDS:
(Analyze the CSV/Excel data. Do not just paste the table. Summarize the performance metrics. Calculate averages if necessary. State exactly how accurate the system was, latency times, or any other measurable success/failure points).

4. NOVEL CONTRIBUTION:
(In one paragraph, state exactly what makes this specific combination of hardware/software unique compared to standard baseline systems).

Do NOT write the actual research paper. Do NOT use flowery language. Output only dense, factual, \
technical specifications. The Writer Agent will use your output to draft the final academic \
methodology and results sections."""

    log_debug(f"Calling Context Analyst LLM. Topic: {topic[:50]}...")
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Synthesize the file data for the unique project: {topic}"),
        ]
        response_text = await _invoke_with_fallback(messages, primary_model="meta-llama/llama-3-8b-instruct", timeout_seconds=90.0, max_tokens=2000)
        log_debug("Context Analyst LLM responded successfully.")
        return response_text

    except asyncio.TimeoutError:
        log_debug("ERROR: Context Analyst LLM timed out after 90 seconds.")
        return "Error: Context analysis timed out. The project data might be too large."
    except Exception as e:
        log_debug(f"ERROR: Context Analyst LLM failed: {str(e)}")
        return f"Error: Context analysis failed: {str(e)}"




# ─────────────────────────────────────────────────────────────────────────────
# Agent 4: THE WRITER — "The Scholar"
# ─────────────────────────────────────────────────────────────────────────────
async def run_writer(
    topic: str,
    level: str,
    paper_format: str,
    outline: str,
    research_data: str,
    unique_project_summary: str,
    reviewer_feedback: str = "",
) -> str:
    """
    Writes the full academic paper draft or revises based on reviewer feedback.
    Returns: Complete paper in Markdown format.
    """
    fmt = _get_format_rules(paper_format)

    revision_context = ""
    if reviewer_feedback:
        revision_context = f"""
⚠️ THIS IS A REVISION — The Reviewer rejected your previous draft.
Specific feedback to address:
{reviewer_feedback}

Fix ONLY the flagged issues. Do not alter sections that passed review."""

    system_prompt = f"""You are a PhD-level Academic Writer with the persona of "The Scholar" — \
eloquent, highly educated, formal, and scrupulously accurate. \
You are NEVER allowed to fabricate facts. You use only what The Researcher provided.

Your task: Write a COMPLETE, publication-ready formal research paper.

PARAMETERS:
- Topic: {topic}
- Target Audience: {level}
- Format: {paper_format} (Field: {fmt['field']})
{revision_context}

━━━━━━━━━━ FORMAT-SPECIFIC CITATION RULES (CRITICAL) ━━━━━━━━━━
{fmt['citation_style']}

In-text citation example: {fmt['citation_example']}
Reference list example:   {fmt['ref_example']}

━━━━━━━━━━ LAYOUT & HEADING RULES ━━━━━━━━━━
{fmt['heading_style']}
Layout: {fmt['layout']}
Special rules: {fmt['special_rules']}

━━━━━━━━━━ STRICT OUTLINE TO FOLLOW ━━━━━━━━━━
{outline}

━━━━━━━━━━ EXTERNAL RESEARCH FACTS & CITATIONS ━━━━━━━━━━
{research_data}

━━━━━━━━━━ ACTUAL PROJECT SPECIFICATIONS (USE THIS FOR METHODOLOGY & RESULTS) ━━━━━━━━━━
{unique_project_summary}

━━━━━━━━━━ WRITING RULES ━━━━━━━━━━
1. Write EVERY section from the outline — no skipping, no placeholders.
2. Apply {paper_format} citation style EXACTLY as specified above for EVERY fact cited.
3. Tone: Objective, industrial, highly formal. Zero conversational language.
4. Abstract must be 150–250 words in a single paragraph.
5. Introduction: background → problem statement → paper objectives.
6. Conclusion: summarize findings → implications → future work suggestions.
7. Use Markdown: ## for primary headings, ### for subsections.
8. Write in full academic paragraphs — NO bullet points in the body text.
9. Adjust vocabulary and depth for a {level} reader.
10. End with a properly formatted References / Works Cited / Bibliography \
    section following {paper_format} conventions exactly.

Output the COMPLETE paper in Markdown, starting with the paper title as # Title."""

    log_debug(f"Calling Writer LLM. Topic: {topic[:50]}...")
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Write the complete {paper_format} academic paper on: {topic}"),
        ]
        response_text = await _invoke_with_fallback(messages, primary_model="meta-llama/llama-3-70b-instruct", timeout_seconds=120.0, max_tokens=4000)
        log_debug("Writer LLM responded successfully.")
        return response_text

    except asyncio.TimeoutError:
        log_debug("ERROR: Writer LLM timed out after 120 seconds.")
        return "# Error: Draft generation timed out.\nThe Topic or context data might be too large for the model to process in one go."
    except Exception as e:
        log_debug(f"ERROR: Writer LLM failed: {str(e)}")
        return f"# Error: Draft generation failed.\n{str(e)}"



# ─────────────────────────────────────────────────────────────────────────────
# Agent 4: THE REVIEWER — "The Strict Professor"
# ─────────────────────────────────────────────────────────────────────────────
async def run_reviewer(
    draft: str,
    level: str,
    paper_format: str,
    research_data: str,
) -> dict:
    """
    Evaluates the paper draft against quality criteria.
    Returns: {"verdict": "APPROVE" | "REJECT", "feedback": "..."}
    """
    fmt = _get_format_rules(paper_format)

    system_prompt = f"""You are a strict Peer Reviewer for a top-tier academic journal. \
Your persona is "The Strict Professor" — uncompromising, highly critical, and \
fiercely protective of academic standards.

Your task: Evaluate the submitted paper draft against STRICT quality criteria.

━━━━━━━━━━ EVALUATION CRITERIA ━━━━━━━━━━
1. LEVEL: Is language, depth, and complexity right for {level}?
2. FORMAT COMPLIANCE ({paper_format}):
   - Correct section order: {fmt['sections']}
   - Correct citation style: {fmt['citation_style']}
   - Heading format followed: {fmt['heading_style']}
   - Special rules applied: {fmt['special_rules']}
3. CITATION ACCURACY: Are ALL facts cited using {paper_format} citation format? \
   ({fmt['citation_example']})
   Flag any facts stated without a citation as a REJECT reason.
4. ACADEMIC TONE: Fully formal and objective? Any casual language?
5. COMPLETENESS: All sections written fully? No "TBD" or placeholder text?
6. REFERENCE LIST: Formatted correctly per {paper_format} conventions? \
   ({fmt['ref_example']})

RESEARCH DATA (what the Writer was given to cite):
{research_data[:3000]}

━━━━━━━━━━ OUTPUT FORMAT ━━━━━━━━━━
Respond ONLY in this exact JSON format (no extra text):
{{
  "verdict": "APPROVE" or "REJECT",
  "feedback": "APPROVE → brief praise of strengths. REJECT → numbered list of \
specific issues with exact section names and what must be fixed."
}}"""

    log_debug(f"Calling Reviewer LLM for {paper_format} draft...")
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Review this {paper_format} paper draft for {level} level:

{draft[:6000]}"""),
        ]
        raw = await _invoke_with_fallback(messages, primary_model="anthropic/claude-3-haiku", timeout_seconds=60.0, max_tokens=1000)
        log_debug("Reviewer LLM responded successfully.")

    except asyncio.TimeoutError:
        log_debug("ERROR: Reviewer LLM timed out after 60 seconds.")
        return {"verdict": "APPROVE", "feedback": "Reviewer timed out. Assuming approval to continue."}
    except Exception as e:
        log_debug(f"ERROR: Reviewer LLM failed: {str(e)}")
        return {"verdict": "APPROVE", "feedback": f"Reviewer failed: {str(e)}. Assuming approval."}

    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
            
        result = json.loads(raw)
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
            
        if not isinstance(result, dict):
            raise ValueError("Parsed JSON is not a dictionary.")
            
        v = result.get("verdict", "REJECT")
        if isinstance(v, str):
            result["verdict"] = v.upper()
        else:
            result["verdict"] = "REJECT"
            
        if result["verdict"] not in ("APPROVE", "REJECT"):
            result["verdict"] = "REJECT"
        return result
    except Exception as e:
        verdict = "APPROVE" if "APPROVE" in raw.upper() else "REJECT"
        return {"verdict": verdict, "feedback": raw}

