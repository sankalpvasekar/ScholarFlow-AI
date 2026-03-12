"""
main.py — ScholarFlow AI
FastAPI server: serves frontend, streams SSE progress events, and handles PDF download.
"""
import json
import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ScholarFlow AI", version="1.0.0")

# ─────────────────────────────────────────────────────────────────────────────
# CORS — allow frontend served from file:// or localhost
# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Serve frontend static files — mount at root so relative paths (style.css,
# script.js) resolve correctly from index.html served at /
# ─────────────────────────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/style.css")
async def serve_css():
    return FileResponse(str(FRONTEND_DIR / "style.css"), media_type="text/css")

@app.get("/script.js")
async def serve_js():
    return FileResponse(str(FRONTEND_DIR / "script.js"), media_type="application/javascript")


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────
class DownloadPDFRequest(BaseModel):
    content: str
    format: str = "IEEE Double Column"
    title: str = "research_paper"

class DownloadWordRequest(BaseModel):
    content: str
    title: str = "research_paper"


class ReviseRequest(BaseModel):
    topic: str
    level: str
    format: str
    compiled_project_data: str = ""
    outline: str = ""
    raw_research: dict = {}
    research_data: str = ""
    unique_project_summary: str = ""
    draft: str = ""
    reviewer_feedback: str = ""


class ReviseRequest(BaseModel):
    topic: str
    level: str
    format: str
    compiled_project_data: str = ""
    outline: str = ""
    raw_research: dict = {}
    research_data: str = ""
    unique_project_summary: str = ""
    draft: str = ""
    reviewer_feedback: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# POST /generate — SSE streaming endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/generate")
async def generate_paper(
    topic: str = Form(...),
    level: str = Form(...),
    format: str = Form(...),
    files: List[UploadFile] = File(default=[]),
):
    """
    Streams Server-Sent Events (SSE) as the agent pipeline runs.
    Ingests unlimited files, extracts their content, and builds the memory string.
    """
    if not topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")
    if len(topic) > 10000:
        raise HTTPException(status_code=400, detail="Topic too long (max 10000 chars).")

    # 1. Compile all uploaded files into one massive string
    compiled_project_data = ""
    if files and isinstance(files, list):
        for file in files:
            # Skip empty file objects from empty file inputs
            if not file.filename:
                continue
                
            content_bytes = await file.read()
            filename = file.filename
            
            compiled_project_data += f"\n\n--- START OF FILE: {filename} ---\n"
            
            # Simple parsing rule based on extension
            if filename.lower().endswith(('.py', '.c', '.cpp', '.txt', '.json', '.md', '.html', '.css', '.js', '.ts', '.html', '.java')):
                try:
                    compiled_project_data += content_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    compiled_project_data += f"[Error decoding text file: {e}]"
                    
            elif filename.lower().endswith('.csv'):
                try:
                    import pandas as pd
                    import io
                    df = pd.read_csv(io.BytesIO(content_bytes))
                    compiled_project_data += df.to_markdown()
                except Exception as e:
                    compiled_project_data += f"[Error parsing CSV file: {e}]"
            else:
                compiled_project_data += f"[File uploaded but extension not strictly parsed as text or CSV. Size: {len(content_bytes)} bytes]"
                
            compiled_project_data += f"\n--- END OF FILE: {filename} ---\n"

    async def event_stream():
        try:
            from backend.graph import run_pipeline_stream

            # 1. Create the pipeline generator
            pipeline = run_pipeline_stream(
                topic=topic,
                level=level,
                paper_format=format,
                compiled_project_data=compiled_project_data,
            )

            # 2. Iterate manually to allow heartbeat injection
            async for event in pipeline:
                data = json.dumps(event)
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.01)  # Minimal sleep to allow context switching

        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "data": {"message": str(e)}
            })
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /revise — SSE streaming endpoint for human feedback loops
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/revise")
async def revise_paper(request: ReviseRequest):
    """
    Resumes the pipeline from the Writer node using prior state and new human feedback.
    """
    async def event_stream():
        try:
            from backend.graph import run_pipeline_stream

            pipeline = run_pipeline_stream(
                topic=request.topic,
                level=request.level,
                paper_format=request.format,
                compiled_project_data=request.compiled_project_data,
                is_revision=True,
                outline=request.outline,
                raw_research=request.raw_research,
                research_data=request.research_data,
                unique_project_summary=request.unique_project_summary,
                draft=request.draft,
                reviewer_feedback=request.reviewer_feedback,
            )

            async for event in pipeline:
                data = json.dumps(event)
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.01)

        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "data": {"message": str(e)}
            })
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /download-docx — Word generation endpoint
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/download-docx")
async def download_docx(request: DownloadWordRequest):
    """
    Accepts Markdown content and returns a formatted DOCX binary.
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")

    try:
        from backend.doc_generator import generate_docx
        loop = asyncio.get_event_loop()
        doc_bytes = await loop.run_in_executor(
            None, generate_docx, request.content, request.title
        )
        
        filename = f"{request.title.replace(' ', '_')}.docx"
        return Response(
            content=doc_bytes.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Word generation failed: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /health — Sanity check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
        "gemini_key_set": bool(os.getenv("GEMINI_API_KEY")),
        "tavily_key_set": bool(os.getenv("TAVILY_API_KEY")),
    }
