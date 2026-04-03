import os
from dotenv import load_dotenv
from fastmcp import FastMCP
import httpx
from datetime import datetime, timedelta, timezone

load_dotenv()

TOKEN = os.getenv("dc_token")

if not TOKEN:
    raise RuntimeError("dc_token missing from .env")

HEADERS = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json"
}

BASE_URL = "https://discord.com/api/v10"

mcp = FastMCP("Esdeath Admin Bridge")


async def discord_request(method, url, **kwargs):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.request(method, url, headers=HEADERS, **kwargs)

        if response.status_code >= 400:
            raise RuntimeError(
                f"Discord API error {response.status_code}: {response.text}"
            )

        return response.json() if response.text else None


@mcp.tool()
async def send_message(channel_id: str, content: str) -> str:
    """Send message to channel."""
    await discord_request(
        "POST",
        f"{BASE_URL}/channels/{channel_id}/messages",
        json={"content": content}
    )
    return "Message sent."


@mcp.tool()
async def read_channel(channel_id: str, limit: int = 15) -> str:
    """Read recent channel messages."""
    messages = await discord_request(
        "GET",
        f"{BASE_URL}/channels/{channel_id}/messages?limit={limit}"
    )

    output = []

    for msg in reversed(messages):
        user = msg["author"]["username"]
        content = msg["content"]
        output.append(f"{user}: {content}")

    return "\n".join(output)


@mcp.tool()
async def purge_messages(channel_id: str, limit: int = 10) -> str:
    """Delete recent messages."""
    messages = await discord_request(
        "GET",
        f"{BASE_URL}/channels/{channel_id}/messages?limit={limit}"
    )

    for msg in messages:
        await discord_request(
            "DELETE",
            f"{BASE_URL}/channels/{channel_id}/messages/{msg['id']}"
        )

    return f"Deleted {len(messages)} messages."


@mcp.tool()
async def timeout_member(guild_id: str, user_id: str, minutes: int) -> str:
    """Timeout a member."""
    until = (
        datetime.now(timezone.utc) + timedelta(minutes=minutes)
    ).isoformat()

    await discord_request(
        "PATCH",
        f"{BASE_URL}/guilds/{guild_id}/members/{user_id}",
        json={"communication_disabled_until": until}
    )

    return f"Timed out user {user_id} for {minutes} minutes."


@mcp.tool()
async def kick_member(guild_id: str, user_id: str) -> str:
    """Kick member from server."""
    await discord_request(
        "DELETE",
        f"{BASE_URL}/guilds/{guild_id}/members/{user_id}"
    )

    return f"Kicked user {user_id}."


@mcp.tool()
async def ban_member(guild_id: str, user_id: str) -> str:
    """Ban member from server."""
    await discord_request(
        "PUT",
        f"{BASE_URL}/guilds/{guild_id}/bans/{user_id}"
    )

    return f"Banned user {user_id}."


@mcp.tool()
async def add_role(guild_id: str, user_id: str, role_id: str) -> str:
    """Add role to user."""
    await discord_request(
        "PUT",
        f"{BASE_URL}/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
    )

    return "Role added."


@mcp.tool()
async def remove_role(guild_id: str, user_id: str, role_id: str) -> str:
    """Remove role from user."""
    await discord_request(
        "DELETE",
        f"{BASE_URL}/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
    )

    return "Role removed."


@mcp.tool()
async def list_channels(guild_id: str) -> str:
    """List server channels."""
    channels = await discord_request(
        "GET",
        f"{BASE_URL}/guilds/{guild_id}/channels"
    )

    return "\n".join(
        f"{c['name']} ({c['id']})"
        for c in channels
        if c["type"] == 0
    )


@mcp.tool()
async def list_roles(guild_id: str) -> str:
    """List server roles."""
    roles = await discord_request(
        "GET",
        f"{BASE_URL}/guilds/{guild_id}/roles"
    )

    return "\n".join(
        f"{r['name']} ({r['id']})"
        for r in roles
    )

@mcp.tool()
async def execute_eval(code: str) -> str:
    """
    Execute Python inside Esdeath bot runtime.
    Equivalent to: esdeath eval <code>
    """

    import httpx

    headers = {"X-EVAL-TOKEN": os.getenv("EVAL_SECRET")}

    async with httpx.AsyncClient(timeout=30) as client:

        response = await client.post(
            "http://127.0.0.1:9000/eval",
            json={"code": code},
            headers=headers
        )

        data = response.json()

        if "error" in data:
            return data.get("error", "Unknown error")

        return f"Eval result: {data.get('result', 'None')}"

if __name__ == "__main__":
    mcp.run()