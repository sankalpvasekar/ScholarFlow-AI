"""
agents.py — ScholarFlow AI
Four AI agent functions using Gemini 1.5 Flash via langchain-google-genai.
Each agent has a specific persona, system prompt, and strict output contract.
All 5 academic formats (IEEE, APA, MLA, Chicago, ACM) are fully supported.
"""
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()


def _get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=temperature,
    )


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
def run_planner(topic: str, level: str, paper_format: str) -> str:
    """
    Creates a detailed academic paper outline.
    Returns: A structured bullet-point outline string.
    """
    llm = _get_llm(temperature=0.2)
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

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Create the {paper_format} academic outline for: {topic}"),
    ])
    return response.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2: THE RESEARCHER — "The Detective"
# ─────────────────────────────────────────────────────────────────────────────
def run_researcher(topic: str, outline: str, raw_research: dict) -> str:
    """
    Synthesizes raw web-scraped data into structured research notes and checks for novelty.
    Returns: A JSON string containing 'research_data', 'novelty_alert' (bool), and 'matching_citation' (str).
    """
    llm = _get_llm(temperature=0.1)

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

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Synthesize research data and check for novelty for: {topic}"),
    ])
    return response.content.strip()
# ─────────────────────────────────────────────────────────────────────────────
# Agent 3: THE CONTEXT ANALYST — "The Brain Filter"
# ─────────────────────────────────────────────────────────────────────────────
def run_context_analyst(topic: str, compiled_project_data: str) -> str:
    """
    Synthesizes massive unstructured user uploads (code, CSV data, notes)
    into a structured 'Master Investigation Document'.
    """
    llm = _get_llm(temperature=0.0)  # zero temperature for pure factual extraction

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

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Synthesize the file data for the unique project: {topic}"),
    ])
    return response.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Agent 4: THE WRITER — "The Scholar"
# ─────────────────────────────────────────────────────────────────────────────
def run_writer(
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
    llm = _get_llm(temperature=0.5)
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

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Write the complete {paper_format} academic paper on: {topic}"),
    ])
    return response.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Agent 4: THE REVIEWER — "The Strict Professor"
# ─────────────────────────────────────────────────────────────────────────────
def run_reviewer(
    draft: str,
    level: str,
    paper_format: str,
    research_data: str,
) -> dict:
    """
    Evaluates the paper draft against quality criteria.
    Returns: {"verdict": "APPROVE" | "REJECT", "feedback": "..."}
    """
    llm = _get_llm(temperature=0.1)
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

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Review this {paper_format} paper draft for {level} level:

{draft[:6000]}"""),
    ])

    raw = response.content.strip()

    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(raw)
        result["verdict"] = result.get("verdict", "REJECT").upper()
        if result["verdict"] not in ("APPROVE", "REJECT"):
            result["verdict"] = "REJECT"
        return result
    except json.JSONDecodeError:
        verdict = "APPROVE" if "APPROVE" in raw.upper() else "REJECT"
        return {"verdict": verdict, "feedback": raw}
