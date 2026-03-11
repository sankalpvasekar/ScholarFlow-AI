import asyncio
import os
from backend.agents import run_reviewer
from dotenv import load_dotenv

load_dotenv()

async def debug_reviewer():
    print("Testing Reviewer Agent...")
    try:
        mock_draft = "# Title\n\nThis is a mock draft.\n\n## References\n\n[1] Mock Reference, 2024.\n"
        mock_research = "This is mock research data."
        
        result = await asyncio.wait_for(
            run_reviewer(
                draft=mock_draft,
                level="Undergraduate",
                paper_format="APA Style",
                research_data=mock_research
            ),
            timeout=120
        )
        print("Reviewer returned:")
        print(result)
    except asyncio.TimeoutError:
        print("Reviewer timed out!")
    except Exception as e:
        print(f"Reviewer failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_reviewer())

