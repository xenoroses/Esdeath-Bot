from fastapi import FastAPI, Request
import asyncio

app = FastAPI()

bot_instance = None


def register_bot(bot):
    global bot_instance
    bot_instance = bot


@app.post("/eval")
async def run_eval(request: Request):
    data = await request.json()

    code = data.get("code")

    if not code:
        return {"error": "No code provided"}

    if bot_instance is None:
        return {"error": "Bot not ready"}

    try:
        env = {
            "bot": bot_instance,
            "discord": __import__("discord"),
            "asyncio": asyncio
        }

        exec(
            f"async def __eval_exec__():\n"
            + "\n".join(f"    {line}" for line in code.split("\n")),
            env
        )

        result = await env["__eval_exec__"]()

        return {"result": str(result)}

    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}