import asyncio
import os
import json
from backend.graph import build_graph, run_pipeline_stream
from backend.agents import run_reviewer

async def test_full_stream():
    print("Starting full stream test...")
    try:
        stream = run_pipeline_stream(
            topic="Test Topic that should fail checking quickly",
            level="Academic",
            paper_format="APA Style",
        )
        async for evt in stream:
            print(evt)
    except Exception as e:
        print(f"Exception caught in stream: {e}")

if __name__ == "__main__":
    asyncio.run(test_full_stream())
