import os
import asyncio
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

async def test():
    groq_api_key = os.getenv("GROQ_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    print("GROQ KEY:", "Loaded" if groq_api_key else "Missing")
    print("GEMINI KEY:", "Loaded" if gemini_api_key else "Missing")
    
    llm_groq = ChatGroq(model="llama-3.3-70b-versatile", max_retries=0)
    llm_gemini = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=gemini_api_key, max_retries=1)
    llm = llm_groq.with_fallbacks([llm_gemini])

    
    print("Invoking LLM with fallbacks...")
    try:
        res = await llm.ainvoke([HumanMessage(content="Hello")])
        with open("test_out.txt", "w") as f:
            f.write(res.content)
        print("Success: Written to test_out.txt")
    except Exception as e:
        with open("test_out.txt", "w") as f:
            f.write(f"Failed: {type(e)} {str(e)}")
        print("Failed: Written to test_out.txt")


if __name__ == "__main__":
    asyncio.run(test())
