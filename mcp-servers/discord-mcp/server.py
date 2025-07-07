import os
from fastapi import FastAPI
from fastmcp import FastMCP
import discord
from discord.ext import commands
import asyncio 
import logging
import json
import httpx 
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# Logging setup
logger = logging.getLogger(__name__)
from common.utils import setup_logging
setup_logging(__name__)

mcp = FastMCP("discord")

# Discord Bot Token from environment variable
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    logger.critical("DISCORD_BOT_TOKEN environment variable not set.")
    raise ValueError("Missing Discord bot token.")

# Environment variable for the main bot API URL (where /discord/receive_message is)
BOT_API_BASE_URL = os.getenv("BOT_API_BASE_URL", "http://localhost:8000") # Default to local bot_api URL

# Discord client setup with necessary intents
intents = discord.Intents.default()
intents.message_content = True # Required for reading message content
intents.members = True       # Required for getting member info (e.g., display_name)

bot_client = commands.Bot(command_prefix="!", intents=intents)

# Discord client event: Bot ready
@bot_client.event
async def on_ready():
    logger.info(f'Logged in as {bot_client.user} (ID: {bot_client.user.id})')
    logger.info('Discord client ready!')

# Discord client event: Message received
@bot_client.event
async def on_message(message: discord.Message):
    """
    Handles incoming Discord messages received via WebSocket.
    Forwards user messages to the main bot API for agent processing.
    """
    # Ignore messages from the bot itself to prevent infinite loops
    if message.author == bot_client.user:
        return

    # Ignore messages from other bots
    if message.author.bot:
        return

    logger.info(f"Discord WebSocket received message from {message.author.display_name} ({message.author.id}) in channel {message.channel.id}: {message.content[:100]}...")

    # Prepare message data to send to the main bot API
    msg_data = {
        "content": message.content,
        "channel_id": str(message.channel.id),
        "author_id": str(message.author.id),
        "author_name": message.author.display_name
    }

    # Send the message data to the main bot API's /discord/receive_message endpoint
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BOT_API_BASE_URL}/discord/receive_message",
                json=msg_data,
                timeout=30.0 
            )
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            logger.info(f"Successfully forwarded message to bot API. Response: {response.status_code}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to forward Discord message to bot API (HTTP error): {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Failed to forward Discord message to bot API (Request error): {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while forwarding Discord message: {e}")


@mcp.tool()
async def send_message(channel_id: str, message: str) -> str:
    """
    Sends a message to a specific Discord channel.
    Args:
        channel_id: The ID of the Discord channel.
        message: The content of the message to send.
    Returns:
        A confirmation message or error.
    """
    logger.info(f"Attempting to send message to Discord channel {channel_id}: {message[:50]}...")
    try:
        # Try to get channel from cache first, then fetch if not found
        channel = bot_client.get_channel(int(channel_id))
        if not channel:
            channel = await bot_client.fetch_channel(int(channel_id)) # fetch channel if not in cache
        if not channel:
            raise ValueError(f"Discord channel with ID {channel_id} not found or inaccessible.")

        await channel.send(message)
        logger.info(f"Message successfully sent to Discord channel {channel_id}.")
        return f"Message successfully sent to Discord channel {channel_id}."
    except Exception as e:
        logger.error(f"Error sending message to Discord channel {channel_id}: {e}")
        return f"Error sending message: {e}"

@mcp.tool()
async def get_channel_messages(channel_id: str, limit: int = 10) -> str:
    """
    Retrieves the recent message history from a Discord channel.
    Args:
        channel_id: The ID of the Discord channel.
        limit: The maximum number of messages to retrieve.
    Returns:
        A JSON string of recent messages.
    """
    logger.info(f"Attempting to retrieve messages from Discord channel {channel_id} (limit: {limit}).")
    try:
        channel = bot_client.get_channel(int(channel_id))
        if not channel:
            channel = await bot_client.fetch_channel(int(channel_id))
        if not channel:
            raise ValueError(f"Discord channel with ID {channel_id} not found or inaccessible.")

        messages_list = []
        async for msg in channel.history(limit=limit):
            messages_list.append({
                "id": str(msg.id),
                "author": msg.author.display_name if msg.author else "Unknown",
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "channel_name": channel.name,
                "guild_name": channel.guild.name if channel.guild else "Direct Message"
            })
        logger.info(f"Retrieved {len(messages_list)} messages from Discord channel {channel_id}.")
        return json.dumps(messages_list, indent=2)
    except Exception as e:
        logger.error(f"Error retrieving messages from Discord channel {channel_id}: {e}")
        return f"Error retrieving messages: {e}"
    
http_mcp = mcp.http_app(transport="streamable-http")

# Define a combined lifespan context manager for the FastAPI app
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    # --- Startup Logic for Discord Client ---
    logger.info("Starting Discord client lifecycle in combined lifespan startup...")
    discord_task = asyncio.create_task(bot_client.start(TOKEN))
    
    logger.info("Yielding to FastMCP's lifespan context...")
    async with http_mcp.router.lifespan_context(app) as fastmcp_lifespan_yield:
        yield
    logger.info("Shutting down Discord client in combined lifespan shutdown...")
    discord_task.cancel()
    try:
        await discord_task 
    except asyncio.CancelledError:
        logger.info("Discord client startup task cancelled.")
    
    await bot_client.close()
    logger.info("Discord client closed.")


# FastMCP app setup

app = FastAPI(lifespan=combined_lifespan)
app.mount("/", http_mcp) # Mount FastMCP's app at the root
logger.info("Discord MCP server initialized and tools registered.")
