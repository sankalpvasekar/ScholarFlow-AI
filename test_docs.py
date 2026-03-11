import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd()))

from backend.doc_generator import generate_docx
from backend.pdf_generator import generate_pdf

test_md = """# Test Title
## Introduction
This is a **bold** and *italic* test.

* List item 1
* List item 2

1. Numbered 1
2. Numbered 2

## Conclusion
Done.
"""

def test_docx():
    print("Testing DOCX generation...")
    try:
        doc_bytes = generate_docx(test_md, "Test Paper")
        with open("test_output.docx", "wb") as f:
            f.write(doc_bytes.getvalue())
        print("✅ test_output.docx created.")
    except Exception as e:
        print(f"❌ DOCX Error: {e}")

def test_pdf():
    print("Testing PDF generation...")
    try:
        pdf_bytes = generate_pdf(test_md, "IEEE Double Column")
        with open("test_output.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("✅ test_output.pdf created.")
    except Exception as e:
        print(f"❌ PDF Error: {e}")

if __name__ == "__main__":
    test_docx()
    # PDF test might fail if WeasyPrint/GTK is not and we don't want to crash the whole test
    try:
        test_pdf()
    except:
        pass
