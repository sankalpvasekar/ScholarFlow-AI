/**
 * script.js — ScholarFlow AI
 * Theme toggle, SSE progress streaming, paper preview, PDF download.
 * Academic Level field removed — only topic + format are sent.
 */

const API_BASE = "http://localhost:8000";

// ── Theme Toggle ──────────────────────────────────────────────────────────
const themeToggle = document.getElementById("themeToggle");
const html = document.documentElement;

// Restore saved preference
const savedTheme = localStorage.getItem("sf-theme") || "dark";
html.setAttribute("data-theme", savedTheme);

themeToggle.addEventListener("click", () => {
    const current = html.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("sf-theme", next);
});

let currentDraft = "";
let currentTitle = "research_paper";
let currentFormat = "IEEE Double Column";
let currentState = {};

// ── DOM ───────────────────────────────────────────────────────────────────
const form = document.getElementById("generateForm");
const topicInput = document.getElementById("topicInput");
const formatSelect = document.getElementById("formatSelect");
const fileUpload = document.getElementById("fileUpload");
const generateBtn = document.getElementById("generateBtn");
const btnSpinner = document.getElementById("btnSpinner");
const btnIcon = document.getElementById("btnIcon");
const btnText = document.getElementById("btnText");

const paperContent = document.getElementById("paperContent");
const previewArea = document.getElementById("previewArea");
const downloadBtn = document.getElementById("downloadBtn");

const verificationPanel = document.getElementById("verificationPanel");
const reviewFeedback = document.getElementById("reviewFeedback");
const approveBtn = document.getElementById("approveBtn");
const rejectBtn = document.getElementById("rejectBtn");

const revisionNotice = document.getElementById("revisionNotice");
const revisionText = document.getElementById("revisionText");
const sourcesLog = document.getElementById("sourcesLog");

const statSources = document.getElementById("statSources");
const statRevisions = document.getElementById("statRevisions");
const statStatus = document.getElementById("statStatus");

// ── Step keys ─────────────────────────────────────────────────────────────
const STEPS = ["planner", "researcher", "context_analyst", "writer", "validator", "reviewer"];

const STEP_DEFAULTS = {
    planner: "Idle",
    researcher: "Idle",
    context_analyst: "Idle",
    writer: "Idle",
    validator: "Idle",
    reviewer: "Idle",
};

// ── Step state updater ────────────────────────────────────────────────────
function setStep(stepKey, state, message) {
    const row = document.getElementById(`step-${stepKey}`);
    const num = document.getElementById(`num-${stepKey}`);
    const msg = document.getElementById(`msg-${stepKey}`);
    if (!row) return;

    row.classList.remove("active", "done", "rejected");
    if (state !== "pending") row.classList.add(state);
    if (message && msg) msg.textContent = message;
}

function resetAllSteps() {
    STEPS.forEach(s => setStep(s, "pending", STEP_DEFAULTS[s]));
    revisionNotice.classList.remove("visible");
    sourcesLog.innerHTML = "";
    statSources.textContent = "—";
    statRevisions.textContent = "0";
    statStatus.textContent = "Running";
    previewPlaceholder.style.display = "flex";
    paperContent.style.display = "none";
    paperContent.innerHTML = "";
    downloadBtn.classList.remove("visible");
    verificationPanel.style.display = "none";
    reviewFeedback.value = "";
    currentDraft = "";
}

// ── Button state ──────────────────────────────────────────────────────────
function setBtnLoading(loading) {
    generateBtn.disabled = loading;
    btnSpinner.classList.toggle("active", loading);
    btnIcon.classList.toggle("hidden", loading);
    btnText.textContent = loading ? "Generating..." : "Generate Paper";
}

// ── Minimal Markdown → HTML renderer ─────────────────────────────────────
function renderMarkdown(md) {
    return md
        .replace(/^# (.+)$/gm, "<h1>$1</h1>")
        .replace(/^## (.+)$/gm, "<h2>$1</h2>")
        .replace(/^### (.+)$/gm, "<h3>$1</h3>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .split("\n")
        .map(line => {
            if (/^<h[1-6]/.test(line)) return line;
            return line.trim() ? `<p>${line}</p>` : "";
        })
        .join("");
}

// ── Progress event handler ────────────────────────────────────────────────
function handleProgress(data) {
    const { step, status, message } = data;
    if (!step || !STEPS.includes(step)) return;

    setStep(step, status, message);

    if (step === "writer" && status === "active" && message.includes("Revis")) {
        revisionNotice.classList.add("visible");
        revisionText.textContent = message;
        statRevisions.textContent = String((parseInt(statRevisions.textContent) || 0) + 1);
    }
    if (step === "writer" && status === "done") {
        revisionNotice.classList.remove("visible");
    }

    // Log URLs
    if (step === "researcher" && message.includes("🔗")) {
        const urls = message.match(/https?:\/\/[^\s,]+/g) || [];
        urls.forEach(url => {
            const item = document.createElement("div");
            item.className = "source-item";
            item.innerHTML = `<span>↗</span><a href="${url}" target="_blank" rel="noopener">${url}</a>`;
            sourcesLog.appendChild(item);
        });
    }

    if (step === "researcher" && status === "done") {
        const m = message.match(/(\d+)\s+source/);
        if (m) statSources.textContent = m[1];
    }
}

// ── Complete event handler ────────────────────────────────────────────────
function handleComplete(data) {
    currentState = data || {};
    currentDraft = currentState.draft || "";

    statRevisions.textContent = currentState.revisions || 0;
    statStatus.textContent = "Ready for Review";
    if (currentState.sources?.length) statSources.textContent = currentState.sources.length;

    STEPS.forEach(s => {
        const row = document.getElementById(`step-${s}`);
        if (row && !row.classList.contains("done") && !row.classList.contains("rejected")) {
            setStep(s, "done", "Complete");
        }
    });

    if (currentDraft) {
        previewPlaceholder.style.display = "none";
        paperContent.style.display = "block";
        paperContent.innerHTML = renderMarkdown(currentDraft);

        // Show Human Verification instead of direct download
        verificationPanel.style.display = "block";
        downloadBtn.classList.remove("visible");

        previewArea.scrollTop = 0;

        const titleMatch = currentDraft.match(/^# (.+)$/m);
        if (titleMatch) currentTitle = titleMatch[1].substring(0, 80);
    }
}

// ── Shared SSE stream processor ───────────────────────────────────────────
async function processSSE(response) {
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Server error: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop();

        for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const json = line.replace(/^data: /, "").trim();
            if (!json) continue;
            try {
                const evt = JSON.parse(json);
                if (evt.type === "progress") handleProgress(evt.data);
                else if (evt.type === "complete") handleComplete(evt.data);
                else if (evt.type === "error") throw new Error(evt.data?.message || "Pipeline error");
            } catch (pe) { console.warn("[SSE]", pe); }
        }
    }
}

// ── Form submit ───────────────────────────────────────────────────────────
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const topic = topicInput.value.trim();
    const format = formatSelect.value;

    if (!topic) { topicInput.focus(); return; }

    currentFormat = format;
    setBtnLoading(true);
    resetAllSteps();

    // Send via FormData to support unlimited files
    const formData = new FormData();
    formData.append("topic", topic);
    formData.append("level", "Academic");
    formData.append("format", format);

    if (fileUpload.files.length > 0) {
        for (let i = 0; i < fileUpload.files.length; i++) {
            formData.append("files", fileUpload.files[i]);
        }
    }

    try {
        const response = await fetch(`${API_BASE}/generate`, {
            method: "POST",
            body: formData,
        });

        await processSSE(response);


    } catch (err) {
        console.error("[Generate]", err);
        statStatus.textContent = "Error";
        revisionNotice.classList.add("visible");
        revisionText.textContent = `Error: ${err.message} — Is the server running at ${API_BASE}?`;
        // Mark active step as rejected
        const active = STEPS.find(s => document.getElementById(`step-${s}`)?.classList.contains("active"));
        if (active) setStep(active, "rejected", `Error: ${err.message}`);
    } finally {
        setBtnLoading(false);
    }
});

// ── Manual Review Handlers ────────────────────────────────────────────────
approveBtn.addEventListener("click", () => {
    verificationPanel.style.display = "none";
    downloadBtn.classList.add("visible");
    statStatus.textContent = "Done ✓";
});

rejectBtn.addEventListener("click", async () => {
    const feedback = reviewFeedback.value.trim();
    if (!feedback) {
        alert("Please provide feedback in the text box before rejecting.");
        return;
    }

    verificationPanel.style.display = "none";
    statStatus.textContent = "Revising...";
    setBtnLoading(true);

    // Reset steps after context analyst for the rewrite loop
    ["writer", "validator", "reviewer"].forEach(s => setStep(s, "pending", STEP_DEFAULTS[s]));
    setStep("writer", "active", "Rewriting based on user feedback...");

    const payload = {
        topic: topicInput.value.trim() || "Manual Revision",
        level: "Academic",
        format: currentFormat,
        compiled_project_data: currentState.compiled_project_data || "",
        outline: currentState.outline || "",
        raw_research: currentState.raw_research || {},
        research_data: currentState.research_data || "",
        unique_project_summary: currentState.unique_project_summary || "",
        draft: currentState.draft || "",
        reviewer_feedback: feedback
    };

    try {
        const response = await fetch(`${API_BASE}/revise`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        await processSSE(response);

    } catch (err) {
        console.error("[Revise]", err);
        statStatus.textContent = "Error";
        revisionNotice.classList.add("visible");
        revisionText.textContent = `Error: ${err.message}`;
        setStep("writer", "rejected", `Error: ${err.message}`);
    } finally {
        setBtnLoading(false);
    }
});

// ── PDF Download ──────────────────────────────────────────────────────────
async function downloadPDF() {
    if (!currentDraft) return;
    downloadBtn.textContent = "Generating…";
    downloadBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/download-pdf`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: currentDraft, format: currentFormat, title: currentTitle }),
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Failed"); }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = `${currentTitle}.pdf`;
        document.body.appendChild(a); a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (err) {
        alert(`PDF download failed: ${err.message}\n\nNote: WeasyPrint requires GTK3 on Windows. See README.md.`);
    } finally {
        downloadBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Download PDF';
        downloadBtn.disabled = false;
    }
}
