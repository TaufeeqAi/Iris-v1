import httpx
from dotenv import load_dotenv
import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException, status
from langchain_core.messages import HumanMessage, AIMessage
from bot.agent_app import agent_app, lifespan as agent_app_lifespan

load_dotenv()

# --------- Logging Setup ---------
logger = logging.getLogger(__name__)
try:
    from common.utils import setup_logging
    setup_logging(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.warning("Could not import common.utils.setup_logging. Using default logging.")

# agent_app's lifespan context to ensure agent components are initialized
app = FastAPI(lifespan=agent_app_lifespan) 

app.mount("/agent_components", agent_app) 

logger.info(f"Bot API running in LOCAL_MODE: {os.getenv('LOCAL_MODE', 'False').lower() == 'true'}")

DISCORD_EVENTS_ENDPOINT = os.getenv("DISCORD_EVENTS_ENDPOINT", "http://localhost:8000/discord/receive_message")
# --------- Telegram Webhook Endpoint ---------
@app.post("/telegram/webhook")
async def tg_webhook(req: Request):
    """
    Handles incoming Telegram webhook updates.
    Extracts the message and passes it to the agent for processing.
    """
    agent_instance = app.state.agent
    tools_by_name = app.state.tools_by_name
    
    if agent_instance is None or tools_by_name is None:
        logger.error("Telegram webhook received but agent or tools are not initialized.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bot service not ready.")

    try:
        update = await req.json()
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text")
        user_id = str(message.get("from", {}).get("id"))

        if not text or not chat_id:
            logger.warning(f"Received Telegram update with no text or chat_id: {update}")
            return {"status": "ignored", "reason": "No text or chat_id found."}

        logger.info(f"Received Telegram message from user {user_id} in chat {chat_id}: {text[:100]}...")

        # Invoke agent and await response
        logger.info("Invoking agent and awaiting response for debugging...")
        
        # Pass chat_id as part of the agent's initial state
        agent_output = await agent_instance.ainvoke({
            "messages": [HumanMessage(content=text)],
            "chat_id": str(chat_id)
        })
        
        logger.info(f"Agent finished processing. Raw output: {agent_output}")
        final_message_content = None
        # Agent output for create_react_agent is a dict with a 'messages' key
        if isinstance(agent_output, dict) and "messages" in agent_output:
            # Get the last message from the agent's output
            last_message = agent_output["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.content:
                final_message_content = last_message.content
        elif isinstance(agent_output, AIMessage) and agent_output.content:
            final_message_content = agent_output.content
        
        if final_message_content:
            logger.info(f"Agent generated a final message: {final_message_content[:100]}")
            try:
                # Call the send_message tool to send the agent's reply back to Telegram
                telegram_send_message_tool = tools_by_name.get("send_message_telegram")

                if not telegram_send_message_tool:
                    logger.error("Telegram send_message tool not found in loaded tools. Cannot send reply.")
                    # You might send a fallback message via logging or a different channel if possible
                    return {"status": "error", "reason": "Telegram send_message tool not available."}
                
                logger.info(f"Attempting to send agent's reply to chat {chat_id} using telegram/send_message tool...")
                send_result = await telegram_send_message_tool.ainvoke(
                    {"chat_id": str(chat_id), "message": final_message_content}
                )
                logger.info(f"Telegram send_message tool call result: {send_result}")
            
            except Exception as e:
                logger.error(f"Error calling send_message tool for Telegram reply: {e}")
        else:
            logger.warning("Agent did not produce a final AIMessage with content to reply.")

        return {"status": "processing"}

    except Exception as e:
        logger.exception(f"Error processing Telegram webhook: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

# ------------ Receive messages from discord-mcp via its WebSocket client-----------
@app.post("/discord/receive_message")
async def receive_discord_message(msg_data: dict):
    """
    Receives incoming Discord messages pushed from the Discord MCP server's WebSocket client.
    Passes the message to the agent for processing.
    """
    agent_instance = app.state.agent
    tools_by_name = app.state.tools_by_name 

    if agent_instance is None or tools_by_name is None:
        logger.error("Discord message received but agent or tools are not initialized.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bot service not ready.")

    try:
        content = msg_data.get("content")
        channel_id = msg_data.get("channel_id")
        author_id = msg_data.get("author_id")
        author_name = msg_data.get("author_name")

        if not content or not channel_id or not author_id:
            logger.warning(f"Received incomplete Discord message data: {msg_data}")
            return {"status": "ignored", "reason": "Incomplete message data."}

        logger.info(f"Received Discord message from {author_name} ({author_id}) in channel {channel_id}: {content[:100]}...")

        # Invoke agent and await response
        logger.info("Invoking agent with Discord message...")
        agent_output = await agent_instance.ainvoke({
            "messages": [HumanMessage(content=content)],
            "chat_id": str(channel_id) # Pass Discord channel ID as chat_id
        })
        
        logger.info(f"Agent finished processing Discord message. Raw output: {agent_output}")

        final_message_content = None
        if isinstance(agent_output, dict) and "messages" in agent_output:
            last_message = agent_output["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.content:
                final_message_content = last_message.content
        elif isinstance(agent_output, AIMessage) and agent_output.content:
            final_message_content = agent_output.content
        
        if final_message_content:
            logger.info(f"Agent generated Discord reply: {final_message_content[:100]}")
            try:
                # Call the Discord send_message tool from the MCP
                discord_send_message_tool = tools_by_name.get("send_message") # Note: tool name is 'send_message'

                if not discord_send_message_tool:
                    logger.error("Discord send_message tool not found in loaded tools. Cannot send reply.")
                    return {"status": "error", "reason": "Discord send_message tool not available."}
                
                logger.info(f"Attempting to send agent's Discord reply to channel {channel_id} using discord/send_message tool...")
                send_result = await discord_send_message_tool.ainvoke(
                    {"channel_id": str(channel_id), "message": final_message_content}
                )
                logger.info(f"Discord send_message tool call result: {send_result}")
            except Exception as e:
                logger.error(f"Error calling Discord send_message tool for reply: {e}")
                return {"status": "error", "reason": f"Failed to send Discord reply: {e}"}
        else:
            logger.warning("Agent did not produce a final AIMessage with content to reply to Discord.")

        return {"status": "processed"}

    except Exception as e:
        logger.exception(f"Error processing received Discord message: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

