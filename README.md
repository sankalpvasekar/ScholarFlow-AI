# ScholarFlow AI 🧠🔬
**Ultra-Premium Multi-Agent Academic Research Suite**

ScholarFlow AI is a decentralized, multi-agent AI system designed to autonomously generate publication-ready academic research papers. It combines deep web scraping, unlimited file context ingestion, and an orchestrated team of specialized AI agents to plan, research, write, and rigorously validate academic literature.

![Stitch Premium UI](frontend/style.css) *(Themed with a bespoke glassmorphic cyber-core UI)*

## 🚀 The Agent Pipeline & API Architecture
The system utilizes **LangGraph** to construct a stateful directed acyclic graph (DAG). The pipeline runs sequentially through the following agents and automated verifiers:

### 1. The Strategic Planner (Agent 01)
- **Role:** Generates the structural blueprint and semantic nodes of the paper.
- **API Required:** `GEMINI_API_KEY` (Google Gemini 1.5 Flash via LangChain).
- **Output:** Strict format-compliant outline (IEEE, APA, MLA, Chicago, ACM).

### 2. The Deep Researcher (Agent 02)
- **Role:** Scans the academic web, scrapes highly relevant papers, and synthesizes empirical evidence.
- **APIs Required:** 
  - `TAVILY_API_KEY` (Tavily AI Search - for finding academic literature).
  - `BeautifulSoup4` (Local HTML parsing of the URLs Tavily discovers).
  - `GEMINI_API_KEY` (To synthesize the scraped HTML into research notes).

### 3. The Context Analyst (Agent 03)
- **Role:** Processes unlimited user file uploads (PDFs, Source Code, CSVs) from the frontend.
- **API Required:** `GEMINI_API_KEY` (Extracts hardware/software methodologies and empirical results from raw data dumps).

### 4. The Synthesis Writer (Agent 04)
- **Role:** Drafts the complete academic paper using the Planner's outline, the Researcher's external citations, and the Context Analyst's internal project data.
- **API Required:** `GEMINI_API_KEY`.

### 5. Automated Validation Engine (Agent 05)
This is a deterministic validation step that acts as a rigorous quality gate *before* human review.
- **Complexity Check:** `textstat` (Local - Calculates Gunning Fog Index to ensure academic vocabulary).
- **Citation Hallucination Check:** `CrossRef API` (Free REST API - Queries actual DOI databases to verify the existence of cited papers).
- **Factual Contradiction Check:** `HuggingFace NLI` (Local AI Model - Uses `cross-encoder/nli-distilroberta-base` to compare the generated draft against the user's uploaded context to catch hallucinations).

### 6. The Senior Reviewer (Agent 06)
- **Role:** The final AI gatekeeper. Critiques formatting, tone, and citation compliance.
- **API Required:** `GEMINI_API_KEY`.
- **Action:** If the draft fails, it triggers a recursive loop back to the *Writer* agent with specific critique notes.

### 7. Human Verification Loop
- The generated paper is streamed to the modern Stitch UI.
- The user can **Approve** the paper or provide manual context and click **Reject & Rewrite** to send it back down the pipeline natively.

## 🛠️ Quick Start

### 1. Prerequisites
You must have Python 3.10+ installed.

### 2. API Keys
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY="your_google_gemini_key_here"
TAVILY_API_KEY="your_tavily_search_key_here"
```

### 3. Installation
```bash
# Clone the repository
git clone https://github.com/sankalpvasekar/ScholarFlow-AI.git
cd ScholarFlow-AI

# Create a virtual environment (optional but recommended)
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 4. Running the Application
```bash
# Start the FastAPI backend and serve the modern UI
uvicorn backend.main:app --reload --port 8000
```
Open your browser and navigate to `http://localhost:8000`.

## 🎨 UI/UX Design
The frontend uses a custom premium **Stitch** generated design featuring:
- **Aurora Deep Backgrounds:** Radial gradient twilight effects.
- **Frosted Glassmorphism:** actively blurs the background.
- **Neon Accents:** Material Symbol icons that pulse when active.

## 📄 License
MIT License
