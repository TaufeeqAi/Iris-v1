# bot/test_telegram_only.py

import os
import asyncio
import logging
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

# --------- Load environment variables ---------
load_dotenv()

# --------- Logging Setup ---------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --------- Main Async Entry ---------
async def main():
    # --- Load Groq API Key ---
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("❌ GROQ_API_KEY not set in .env")

    # --- Initialize LLM ---
    llm = ChatGroq(
        model_name="llama3-70b-8192",
        groq_api_key=groq_api_key,
        temperature=0.3
    )
    logger.info("✅ Initialized Groq LLM with llama3-70b-8192")

    # --- Test only RAG server ---
    mcp_config = {
        "telegram": {"url": "http://localhost:9003/mcp/", "transport": "streamable_http"},
    }
    
    try:
        # Test basic connectivity first
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:9003/mcp/")
            logger.info(f"✅ RAG server base endpoint response: {response.status_code}")
            
        # Now try MCP client
        client = MultiServerMCPClient(mcp_config)
        tools = await client.get_tools()
        logger.info(f"🔧 Loaded {len(tools)} tools from RAG server: {[tool.name for tool in tools]}")
        
        # --- Build LangGraph Agent ---
        agent = create_react_agent(llm, tools)
        logger.info("🧠 ReAct agent initialized with RAG tools")

        # --- Test prompt ---
        user_query = "reply"
        response = await agent.ainvoke({"messages": [{"role": "user", "content": user_query}]})
        
        msgs = response.get("messages", [])
        if msgs:
            last_msg = msgs[-1]
            print(f"\n🗨️ Query: {user_query}\n💬 Response: {last_msg.content}")
        else:
            print("⚠️ No messages returned.")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Failed to connect to RAG server: {e}")

# --------- Entry Point ---------
if __name__ == "__main__":
    asyncio.run(main())