import asyncio
import os
import logging
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp_server_tester")

LOCAL_MODE = os.getenv("LOCAL_MODE", "false").lower() == "true"
logger.info(f"Running in LOCAL_MODE: {LOCAL_MODE}")

# MCP server definitions
mcp_config = {
    "web": {
        "url": LOCAL_MODE and "http://localhost:9000/mcp/" or "http://web-mcp-svc:9000/mcp",
        "transport": "streamable_http"
    },
    "finance": {
        "url": LOCAL_MODE and "http://localhost:9001/mcp/" or "http://finance-mcp-svc:9000/mcp",
        "transport": "streamable_http"
    },
    "rag": {
        "url": LOCAL_MODE and "http://localhost:9002/mcp/" or "http://rag-mcp-svc:9000/mcp",
        "transport": "streamable_http"
    },
    "telegram": {
        "url": LOCAL_MODE and "http://localhost:9003/mcp/" or "http://telegram-mcp-svc:9000/mcp",
        "transport": "streamable_http"
    },
    "discord": {
        "url": LOCAL_MODE and "http://localhost:9004/mcp/" or "http://discord-mcp-svc:9000/mcp",
        "transport": "streamable_http"
    },
}

async def test_server(name: str, cfg: dict):
    logger.info(f"\n--- Testing {name.upper()} ---")
    client = MultiServerMCPClient({name: cfg})

    try:
        tools = await client.get_tools(server_name=name)
        logger.info(f"✅ Found {len(tools)} tools: {[t.name for t in tools]}")
        if not tools:
            return
    except Exception as e:
        logger.error(f"❌ Discovery failed for {name}: {e}", exc_info=True)
        return

    # Choose default test tool + args
    if name == "finance":
        tool_name, args = "get_stock", {"symbol": "MSFT"}
    elif name == "web":
        tool_name, args = "newsapi_org", {"query": "latest AI news headlines"}
    elif name == "rag":
        tool_name, args = "query_docs", {"query": "what is Project Alpha"}
    elif name == "telegram":
        tool_name, args = "send_message", {"chat_id": "-1002818926283", "message": "Hello!"}
        logger.warning("⚠️ Telegram test needs a valid chat_id.")
    elif name == "discord":
        tool_name, args = "send_message", {"channel_id": "1387173002545856644", "message": "Hello!"}
        logger.warning("⚠️ Discord test needs a valid channel_id.")
    else:
        logger.warning(f"No test defined for {name}.")
        return

    # Run the tool within a session context
    try:
        async with client.session(name,auto_initialize=True) as session:
            await session.call_tool("add_document", arguments={
                "content": "The capital of Canada is Ottawa.",
                "metadata": {"source": "mcp_test"}
            })
            logger.info(f"▶️ Calling {tool_name} with {args}")
            result = await session.call_tool(tool_name, arguments=args)
            output = getattr(result, "content", result)
            logger.info(f"✅ Result for {name}: {output}")
    except Exception as e:
        logger.error(f"❌ Execution failed for {name}: {e}", exc_info=True)

async def main():
    tasks = [test_server(name, cfg) for name, cfg in mcp_config.items()]
    await asyncio.gather(*tasks)
    logger.info("✅ All tests complete")

if __name__ == "__main__":
    asyncio.run(main())
