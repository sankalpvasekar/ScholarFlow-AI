import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.getcwd()))

from backend.doc_generator import generate_docx

test_md = """# Test Title
## Introduction
This is a test document to ensure the Word generator works.

### Key Points
* One
* Two
* Three
"""

def test_docx():
    print("Testing DOCX generation...")
    try:
        doc_bytes = generate_docx(test_md, "Research Paper")
        with open("test_output.docx", "wb") as f:
            f.write(doc_bytes.getvalue())
        print("✅ test_output.docx created.")
    except Exception as e:
        print(f"❌ DOCX Error: {e}")

if __name__ == "__main__":
    test_docx()
