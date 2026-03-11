print("Importing langchain_groq...", flush=True)
from langchain_groq import ChatGroq
print("Import successful", flush=True)
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
print(f"API Key found: {bool(api_key)}", flush=True)
if api_key:
    print("Initializing ChatGroq...", flush=True)
    llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=api_key)
    print("Done. Attempting a simple invoke...", flush=True)
    try:
        res = llm.invoke("Hi")
        print(f"Result: {res.content}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)
