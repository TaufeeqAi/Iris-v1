# bot/agent_app.py

import os
import asyncio
import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Dict, Any, List,Union
from langchain.tools import BaseTool


# --------- Load environment variables ---------
load_dotenv()

# --------- Logging Setup ---------
logger = logging.getLogger(__name__)
# Assume common.utils.setup_logging is available
try:
    from common.utils import setup_logging
    setup_logging(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.warning("Could not import common.utils.setup_logging. Using default logging.")

# --------- Determine Local or Cluster Mode ---------
LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"
logger.info(f"Running in LOCAL_MODE: {LOCAL_MODE}")

# --------- Configure MCP Servers ---------
if LOCAL_MODE:
    mcp_config = {
        "web": {"url": "http://localhost:9000/mcp/", "transport": "streamable_http"},
        "finance": {"url": "http://localhost:9001/mcp/", "transport": "streamable_http"},
        "rag": {"url": "http://localhost:9002/mcp/", "transport": "streamable_http"},
        "telegram": {"url": "http://localhost:9003/mcp/", "transport": "streamable_http"},
        "discord": {"url": "http://localhost:9004/mcp/", "transport": "streamable_http"},
    }
else:
    mcp_config = {
        "web": {"url": "http://web-mcp-svc:9000/mcp", "transport": "streamable_http"},
        "finance": {"url": "http://finance-mcp-svc:9000/mcp", "transport": "streamable_http"},
        "rag": {"url": "http://rag-mcp-svc:9000/mcp", "transport": "streamable_http"},
        "telegram": {"url": "http://telegram-mcp-svc:9000/mcp", "transport": "streamable_http"},
        "discord": {"url": "http://discord-mcp-svc:9000/mcp", "transport": "streamable_http"},
    }


# --------- Agent Component Initialization Function ---------
async def _initialize_agent_components() -> Dict[str, Any]:
    """
    Initializes the LLM, MCP client, fetches tools, and builds the LangGraph agent.
    Returns a dictionary containing the initialized components.
    """
    logger.info("Initializing agent components...")
    
    # --- Load Groq API Key ---
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.critical("❌ GROQ_API_KEY not set in .env. Agent will not function.")
        raise ValueError("GROQ_API_KEY is required for ChatGroq.")

    # --- Initialize LLM ---
    llm = ChatGroq(
        model_name="llama3-70b-8192",
        groq_api_key=groq_api_key,
        temperature=0.3
    )
    logger.info(f"✅ Initialized Groq LLM with {llm.model_name}")

    # --- Create MCP client & fetch tools from all servers ---
    mcp_client = MultiServerMCPClient(mcp_config)
    tools: List[BaseTool] = []
    tools_by_name: Dict[str, BaseTool] = {}
    
    try:
        raw_tools = await mcp_client.get_tools()
        for tool in raw_tools:
            tools.append(tool)
            tools_by_name[tool.name] = tool
            logger.info(f"Loaded tool: {tool.name}")
        
        logger.info(f"🔧 Loaded {len(tools)} tools from MCP servers.")
    except Exception as e:
        logger.critical(f"❌ Failed to load tools from MCP servers: {e}", exc_info=True)
        if os.getenv("LOCAL_MODE", "False").lower() == "true":
            logger.warning("Running in LOCAL_MODE, agent will initialize with no tools due to MCP errors.")
        tools = [] # Proceed with an empty tool list if fetching fails


    # --- Build LangGraph Agent ---
    agent_executor = create_react_agent(llm, tools, name="Iris")
    logger.info(f"🧠 Agent: {agent_executor.name} initialized with tools.")
    
    return {
        "llm": llm,
        "mcp_client": mcp_client,
        "tools": tools,
        "tools_by_name": tools_by_name,
        "agent_executor": agent_executor
    }


# --------- FastAPI Lifespan Context Manager ---------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for initializing and cleaning up resources.
    """
    logger.info("Agent app startup: Initializing agent components...")
    components = await _initialize_agent_components()
    app.state.llm = components["llm"]
    app.state.mcp_client = components["mcp_client"]
    app.state.tools = components["tools"]
    app.state.tools_by_name = components["tools_by_name"]
    app.state.agent = components["agent_executor"] # Store the agent executor
    logger.info("Agent app startup complete. Agent is ready.")
    yield
    # Cleanup resources on shutdown (e.g., disconnect client, close sessions)
    logger.info("Agent app shutdown.")

# --------- Main FastAPI Application Instance ---------
agent_app = FastAPI(lifespan=lifespan)

# --------- Main Async Entry (for standalone execution/testing) ---------
async def main():
    """
    Main function to run the agent app in a standalone capacity (e.g., for testing).
    """
    # This will trigger the lifespan event to initialize components
    async with lifespan(agent_app):
        logger.info("Agent app running in standalone mode. Agent is ready.")
        logger.info("To test, you might add an interactive loop here or specific test calls.")
        # Example of a simple interactive loop for standalone testing:
        # while True:
        #     user_input = input("You: ")
        #     if user_input.lower() == 'exit':
        #         break
        #     chat_id = "test_chat_standalone" # Dummy chat ID for standalone testing
        #     response = await agent_app.state.agent.ainvoke({
        #         "messages": [HumanMessage(content=user_input)],
        #         "chat_id": chat_id
        #     })
        #     print(f"Agent: {response.get('messages', [])[-1].content if response.get('messages') else response}")


# --------- Entry Point ---------
if __name__ == "__main__":
    asyncio.run(main())
