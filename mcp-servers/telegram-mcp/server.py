# mcp-servers/telegram-mcp/server.py

import os
from fastapi import FastAPI
from fastmcp import FastMCP
from telethon import TelegramClient, events
import logging
import json
from contextlib import asynccontextmanager 

logger = logging.getLogger(__name__)
from common.utils import setup_logging
setup_logging(__name__)

logging.getLogger('telethon').setLevel(logging.DEBUG) 

# Environment variables for Telegram API credentials
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.critical("TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_BOT_TOKEN environment variables must be set.")
    raise ValueError("Missing Telegram API credentials.")

# Initialize Telethon Client
telegram_client = TelegramClient('bot_session', int(API_ID), API_HASH)

# Create the FastMCP instance
mcp = FastMCP("telegram") # Unique name for this MCP

# Get the FastAPI app from the FastMCP instance. This app has FastMCP's own lifespan.
http_mcp = mcp.http_app(transport="streamable-http")

# Define a combined lifespan context manager
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    # --- Step 1: Startup your custom services (e.g., Telethon client) ---
    logger.info("Application lifespan startup initiated.")
    try:
        logger.info("Attempting to connect Telethon Telegram Client (bot mode)...")
        await telegram_client.start(bot_token=BOT_TOKEN)
        
        if telegram_client.is_connected():
            logger.info("Telethon Telegram Client (bot mode) started and connected successfully.")
        else:
            logger.critical("Telethon Telegram Client started but reported as NOT connected after start call. This indicates a deep connection issue.")
            raise ConnectionError("Telethon client could not establish an active connection to Telegram.")
    except Exception as e:
        logger.critical(f"Error during Telethon client startup: {e}", exc_info=True) 
        raise 

    # --- Step 2: Yield control to the inner FastMCP lifespan ---
    async with http_mcp.router.lifespan_context(app) as maybe_state:
        yield maybe_state 

    # --- Step 3: Shutdown your custom services (e.g., Telethon client) ---
    logger.info("Application lifespan shutdown initiated (combined_lifespan). Shutting down Telethon client...")
    if telegram_client.is_connected():
        await telegram_client.disconnect()
        logger.info("Telethon client disconnected successfully.")
    else:
        logger.info("Telethon client was not connected at shutdown.")

# Register tools with the mcp instance
@mcp.tool()
async def send_message_telegram(chat_id: str, message: str) -> str:
    """
    Sends a message to a specific Telegram chat.
    Args:
        chat_id: The ID or username of the chat/user/channel.
        message: The content of the message to send.
    Returns:
        A confirmation message or error.
    """
    logger.info(f"Attempting to send message to Telegram chat {chat_id}: {message[:50]}...")
    
    if not telegram_client.is_connected():
        logger.error(f"Telethon client is NOT connected when attempting to send message to {chat_id}. Cannot proceed.")
        return "Error sending message: Telethon client is not connected."
    
    try:
        target_entity = None
        try:
            # Attempt to convert chat_id to integer (for direct use with ID)
            target_entity = int(chat_id)
            logger.debug(f"Directly using integer chat_id for send_message: {target_entity}")
        except ValueError:
            # If not an integer, assume it's a username or similar, and try to get entity
            logger.debug(f"chat_id '{chat_id}' is not an integer. Attempting to get entity using get_entity.")
            target_entity = await telegram_client.get_entity(chat_id)
            logger.debug(f"Entity obtained for '{chat_id}': {target_entity.id} (username/title: {target_entity.username or target_entity.title or 'N/A'})")
        
        logger.info(f"Sending message to target_entity: {target_entity}...")
        sent_message = await telegram_client.send_message(target_entity, message) 
        logger.info(f"Message successfully sent to {chat_id}. Message ID: {sent_message.id}")
        return f"Message successfully sent to {chat_id}."
    except Exception as e:
        logger.error(f"Error sending message to Telegram chat {chat_id}: {e}", exc_info=True) 
        return f"Error sending message: {e}"

@mcp.tool()
async def get_chat_history(chat_id: str, limit: int = 10) -> str:
    """
    Retrieves the recent message history from a Telegram chat.
    Args:
        chat_id: The ID or username of the chat/user/channel.
        limit: The maximum number of messages to retrieve.
    Returns:
        A JSON string of recent messages.
    """
    logger.info(f"Attempting to retrieve chat history for Telegram chat {chat_id} (limit: {limit}).")
    
    if not telegram_client.is_connected():
        logger.error(f"Telethon client is NOT connected when attempting to get chat history for {chat_id}. Cannot proceed.")
        return "Error retrieving chat history: Telethon client is not connected."

    try:
        target_entity = None
        try:
            target_entity = int(chat_id)
            logger.debug(f"Directly using integer chat_id for history: {target_entity}")
        except ValueError:
            # If not an integer, assume it's a username or similar, and try to get entity
            logger.debug(f"chat_id '{chat_id}' is not an integer. Attempting to get entity for history.")
            target_entity = await telegram_client.get_entity(chat_id)
            logger.debug(f"Entity obtained for history: {target_entity.id}")

        messages_list = []
        async for msg in telegram_client.iter_messages(target_entity, limit=limit): 
            messages_list.append({
                "id": str(msg.id),
                "sender": msg.sender.username or msg.sender.first_name or "Unknown",
                "text": msg.text,
                "date": msg.date.isoformat() if msg.date else None
            })
        logger.info(f"Retrieved {len(messages_list)} messages from {chat_id}.")
        return json.dumps(messages_list, indent=2)
    except Exception as e:
        logger.error(f"Error retrieving chat history for Telegram chat {chat_id}: {e}", exc_info=True)
        return f"Error retrieving chat history: {e}"

# Create the main FastAPI app, pass combined lifespan manager

app = FastAPI(lifespan=combined_lifespan)

app.mount("/", http_mcp)
logger.info("Telegram MCP server initialized and tools registered.")