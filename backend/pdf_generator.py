"""
pdf_generator.py — ScholarFlow AI
Converts Markdown paper text to a professionally formatted PDF.
Supports all 5 academic formats: IEEE, APA, MLA, Chicago/Turabian, ACM.
Uses WeasyPrint for rendering (requires GTK3 on Windows).
"""
import io
import markdown as md


# ─────────────────────────────────────────────────────────────────────────────
# Shared base rules
# ─────────────────────────────────────────────────────────────────────────────
_BASE_RESET = """
*, *::before, *::after { box-sizing: border-box; }
body { color: #000000; }
a { color: #0000ff; text-decoration: underline; }
pre, code { font-family: "Courier New", Courier, monospace; font-size: 8.5pt; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# 1. IEEE DOUBLE COLUMN
# Two-column, 10pt Times New Roman, numeric [1] citations
# ─────────────────────────────────────────────────────────────────────────────
IEEE_CSS = _BASE_RESET + """
@page {
    size: A4;
    margin: 19mm 15mm 25mm 15mm;
    @top-center { content: "ScholarFlow AI — IEEE Format"; font-size: 7pt; color: #888; }
    @bottom-center { content: counter(page); font-size: 8pt; }
}
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 10pt; line-height: 1.4;
    column-count: 2; column-gap: 6mm;
    column-rule: 0.5pt solid #ccc;
    text-align: justify; hyphens: auto;
}
h1 { font-size: 22pt; font-weight: bold; text-align: center; column-span: all; margin: 0 0 6pt 0; }
h2 { font-size: 10pt; font-weight: bold; text-align: center; text-transform: uppercase; letter-spacing: 0.5pt; margin: 8pt 0 4pt; }
h3 { font-size: 10pt; font-style: italic; font-weight: bold; margin: 6pt 0 3pt; }
p  { margin: 0 0 5pt; text-indent: 3mm; }
ul, ol { margin: 2pt 0 5pt 10mm; }
pre  { background: #f5f5f5; padding: 2pt 4pt; border-left: 2pt solid #000; font-size: 8pt; }
hr   { border: none; border-top: 0.5pt solid #000; margin: 8pt 0; }
"""

# ─────────────────────────────────────────────────────────────────────────────
# 2. APA STYLE
# Single-column, 12pt Times New Roman, double-spaced, (Author, Year) citations
# ─────────────────────────────────────────────────────────────────────────────
APA_CSS = _BASE_RESET + """
@page {
    size: A4;
    margin: 25.4mm 25.4mm 25.4mm 25.4mm;
    @top-right { content: "Running head: PAPER TITLE       " counter(page); font-size: 11pt; }
}
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt; line-height: 2.0;
    text-align: left;
}
h1 { font-size: 12pt; font-weight: bold; text-align: center; margin: 12pt 0 0; }
h2 { font-size: 12pt; font-weight: bold; text-align: center; margin: 12pt 0 0; }
h3 { font-size: 12pt; font-weight: bold; font-style: italic; text-indent: 12.7mm; margin: 12pt 0 0; display: inline; }
h4 { font-size: 12pt; font-weight: bold; text-indent: 12.7mm; margin: 12pt 0 0; display: inline; }
p  { text-indent: 12.7mm; margin: 0; }
ul, ol { margin: 0 0 0 12.7mm; }
pre { font-size: 10pt; margin: 6pt 0 6pt 12.7mm; }
"""

# ─────────────────────────────────────────────────────────────────────────────
# 3. MLA STYLE
# Single-column, 12pt Times New Roman, double-spaced, (Author Page) citations
# ─────────────────────────────────────────────────────────────────────────────
MLA_CSS = _BASE_RESET + """
@page {
    size: A4;
    margin: 25.4mm 25.4mm 25.4mm 25.4mm;
    @top-right { content: "LastName " counter(page); font-size: 12pt; }
}
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt; line-height: 2.0;
    text-align: left;
}
/* No separate title page — header block is part of body */
h1 { font-size: 12pt; font-weight: normal; text-align: center; margin: 0 0 0 0; }
h2 { font-size: 12pt; font-weight: bold; text-align: left; margin: 12pt 0 0; }
h3 { font-size: 12pt; font-weight: bold; font-style: italic; margin: 12pt 0 0; }
p  { text-indent: 12.7mm; margin: 0; }
/* Works Cited page */
.works-cited p { text-indent: -12.7mm; padding-left: 12.7mm; }
ul, ol { margin: 0 0 0 12.7mm; }
pre { font-size: 10pt; }
"""

# ─────────────────────────────────────────────────────────────────────────────
# 4. CHICAGO / TURABIAN STYLE
# Single-column, 12pt Times New Roman, double-spaced body, footnotes
# ─────────────────────────────────────────────────────────────────────────────
CHICAGO_CSS = _BASE_RESET + """
@page {
    size: A4;
    margin: 25.4mm 25.4mm 25.4mm 25.4mm;
    @bottom-center { content: counter(page); font-size: 12pt; }
}
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt; line-height: 2.0;
    text-align: left;
}
h1 { font-size: 12pt; font-weight: bold; text-align: center; margin: 48pt 0 12pt; }
h2 { font-size: 12pt; font-weight: bold; text-align: center; margin: 12pt 0 0; }
h3 { font-size: 12pt; font-weight: bold; text-align: left; margin: 12pt 0 0; }
h4 { font-size: 12pt; font-weight: bold; font-style: italic; text-align: left; margin: 12pt 0 0; }
p  { text-indent: 12.7mm; margin: 0; }
/* Footnote styling - WeasyPrint renders standard HTML footnotes */
.footnote { font-size: 10pt; line-height: 1.4; border-top: 0.5pt solid #000; padding-top: 4pt; margin-top: 8pt; }
/* Bibliography hanging indent */
.bibliography p { text-indent: -12.7mm; padding-left: 12.7mm; margin: 0; line-height: 2.0; }
ul, ol { margin: 0 0 0 12.7mm; }
pre { font-size: 10pt; }
"""

# ─────────────────────────────────────────────────────────────────────────────
# 5. ACM STYLE
# Two-column with strict typography, algorithm/code blocks, CCS Concepts
# ─────────────────────────────────────────────────────────────────────────────
ACM_CSS = _BASE_RESET + """
@page {
    size: A4;
    margin: 20mm 14mm 26mm 14mm;
    @top-left   { content: "ScholarFlow AI"; font-size: 7pt; color: #555; }
    @top-right  { content: "ACM Format"; font-size: 7pt; color: #555; }
    @bottom-center { content: counter(page); font-size: 8pt; }
}
body {
    font-family: "Linux Libertine", "Times New Roman", Times, serif;
    font-size: 9pt; line-height: 1.35;
    column-count: 2; column-gap: 5mm;
    column-rule: 0.4pt solid #ccc;
    text-align: justify; hyphens: auto;
}
h1 { font-size: 18pt; font-weight: bold; text-align: center; column-span: all; margin: 0 0 4pt; }
/* CCS Concepts and Keywords block */
.ccs-concepts { font-size: 8pt; column-span: all; margin: 0 0 8pt; font-style: italic; }
/* Numbered section headings: 1 INTRODUCTION */
h2 { font-size: 9pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.3pt; margin: 7pt 0 3pt; }
/* Subsection: 1.1 Subsection */
h3 { font-size: 9pt; font-style: italic; font-weight: bold; margin: 5pt 0 2pt; }
h4 { font-size: 9pt; font-weight: bold; margin: 4pt 0 2pt; }
p  { margin: 0 0 4pt; text-indent: 2.5mm; }
/* Algorithm block */
pre {
    background: #f8f8f8; border: 0.5pt solid #aaa;
    font-size: 7.5pt; padding: 3pt 5pt; margin: 4pt 0;
    break-inside: avoid;
}
/* Code listing */
code { font-size: 8pt; background: #f8f8f8; padding: 0 2pt; }
ul, ol { margin: 2pt 0 4pt 8mm; font-size: 9pt; }
hr { border: none; border-top: 0.5pt solid #000; margin: 6pt 0; }
/* ACKNOWLEDGMENTS and REFERENCES smaller */
.references { font-size: 8pt; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# Format → CSS mapping
# ─────────────────────────────────────────────────────────────────────────────
FORMAT_CSS_MAP = {
    "ieee":    IEEE_CSS,
    "apa":     APA_CSS,
    "mla":     MLA_CSS,
    "chicago": CHICAGO_CSS,
    "turabian": CHICAGO_CSS,  # Turabian is Chicago for students
    "acm":     ACM_CSS,
}


def _pick_css(format_style: str) -> str:
    """Select the right CSS stylesheet based on the format_style string."""
    style_lower = format_style.lower()
    for key, css in FORMAT_CSS_MAP.items():
        if key in style_lower:
            return css
    return IEEE_CSS  # fallback


# ─────────────────────────────────────────────────────────────────────────────
# Core PDF Generator
# ─────────────────────────────────────────────────────────────────────────────
def generate_pdf(markdown_text: str, format_style: str = "IEEE Double Column") -> bytes:
    """
    Convert Markdown paper to a properly formatted PDF bytes.

    Args:
        markdown_text: Full paper content in Markdown.
        format_style:  One of: "IEEE Double Column", "APA Style",
                       "MLA Style", "Chicago Style", "ACM Style"

    Returns:
        PDF as bytes.

    Raises:
        ImportError: If WeasyPrint / GTK is not installed.
        RuntimeError: On PDF generation failure.
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError as e:
        raise ImportError(
            "WeasyPrint is not installed or GTK3 runtime is missing.\n"
            "Windows: install GTK from https://github.com/tschoonj/"
            "GTK-for-Windows-Runtime-Environment-Installer/releases\n"
            f"Original error: {e}"
        )

    # Convert markdown → HTML
    html_body = md.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "toc", "nl2br", "footnotes"]
    )

    css_content = _pick_css(format_style)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ScholarFlow AI — {format_style} Research Paper</title>
</head>
<body>
{html_body}
</body>
</html>"""

    try:
        pdf_bytes_io = io.BytesIO()
        HTML(string=html_doc).write_pdf(
            pdf_bytes_io,
            stylesheets=[CSS(string=css_content)]
        )
        return pdf_bytes_io.getvalue()
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}")
