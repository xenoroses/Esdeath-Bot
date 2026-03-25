import os
from dotenv import load_dotenv
from fastmcp import FastMCP
import httpx

# Load your existing .env file
load_dotenv()

TOKEN = os.getenv("dc_token")
HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json"
}
BASE_URL = "https://discord.com/api/v10"

# Initialize the MCP server
mcp = FastMCP("Esdeath Bridge")

@mcp.tool()
async def read_channel(channel_id: str, limit: int = 15) -> str:
    """Read the most recent messages from a Discord channel."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/channels/{channel_id}/messages?limit={limit}",
            headers=HEADERS
        )
        response.raise_for_status()
        messages = response.json()
        
        formatted = []
        # Reverse so the newest is at the bottom
        for msg in reversed(messages): 
            author = msg.get('author', {}).get('username', 'Unknown')
            author_id = msg.get('author', {}).get('id', 'Unknown')
            formatted.append(f"{author} (ID: {author_id}): {msg.get('content', '')}")
            
        return "\n".join(formatted) if formatted else "No messages found."

@mcp.tool()
async def send_message(channel_id: str, content: str) -> str:
    """Send a message to a specific Discord channel as Esdeath."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/channels/{channel_id}/messages",
            headers=HEADERS,
            json={"content": content}
        )
        response.raise_for_status()
        return f"Message sent successfully to channel {channel_id}."

@mcp.tool()
async def impersonate_user(channel_id: str, target_user_id: str, content: str) -> str:
    """Impersonate a Discord user by stealing their name/avatar and sending a message via webhook."""
    async with httpx.AsyncClient() as client:
        # 1. Fetch the target user's profile to get their name and avatar hash
        user_res = await client.get(f"{BASE_URL}/users/{target_user_id}", headers=HEADERS)
        user_res.raise_for_status()
        user_data = user_res.json()
        
        username = user_data.get("username")
        avatar_hash = user_data.get("avatar")
        
        # Build the avatar URL (fallback to default if they don't have a custom one)
        if avatar_hash:
            avatar_url = f"https://cdn.discordapp.com/avatars/{target_user_id}/{avatar_hash}.png"
        else:
            disc = int(user_data.get("discriminator", "0") or "0")
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{disc % 5}.png"

        # 2. Check if the Esdeath-Impersonator webhook already exists in this channel
        wh_res = await client.get(f"{BASE_URL}/channels/{channel_id}/webhooks", headers=HEADERS)
        wh_res.raise_for_status()
        webhooks = wh_res.json()
        
        webhook = next((wh for wh in webhooks if wh.get("name") == "Esdeath-Impersonator"), None)
        
        # 3. Create the webhook if it doesn't exist
        if not webhook:
            create_wh_res = await client.post(
                f"{BASE_URL}/channels/{channel_id}/webhooks",
                headers=HEADERS,
                json={"name": "Esdeath-Impersonator"}
            )
            create_wh_res.raise_for_status()
            webhook = create_wh_res.json()
            
        webhook_id = webhook["id"]
        webhook_token = webhook["token"]
        
        # 4. Fire the fake message!
        exec_res = await client.post(
            f"{BASE_URL}/webhooks/{webhook_id}/{webhook_token}",
            json={
                "content": content,
                "username": username,
                "avatar_url": avatar_url
            }
        )
        exec_res.raise_for_status()
        return f"Successfully impersonated {username} in channel {channel_id}."

if __name__ == "__main__":
    mcp.run()