import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.agents import run_planner
from dotenv import load_dotenv

load_dotenv()

async def debug():
    topic = "Impact of AI on Healthcare"
    level = "Academic"
    paper_format = "IEEE Double Column"
    
    print(f"Testing Planner Agent for topic: {topic}", flush=True)
    print("This might take a few seconds if the API is responding...", flush=True)
    
    try:
        outline = await run_planner(topic, level, paper_format)
        print("\n--- PLANNER OUTPUT ---", flush=True)
        print(outline, flush=True)
        print("--- END OUTPUT ---\n", flush=True)
        print("✅ Planner Agent responded successfully.", flush=True)
    except Exception as e:
        print(f"❌ Error during Planner execution: {e}", flush=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug())

