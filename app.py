import threading
import asyncio
import os
import time
import httpx
import gradio as gr

# Start Hyacine Bot in a background thread after Gradio initializes
def run_discord_bot():
    time.sleep(3)  # Short delay to allow Gradio to bind port 7860 first
    try:
        import bot
        asyncio.run(bot.main())
    except Exception as e:
        print(f"Discord Bot Execution Error: {e}")

bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
bot_thread.start()

# Background Self-Ping / Keep-Alive Monitor
SPACE_HOST = os.getenv("SPACE_HOST", "")

def self_ping_loop():
    if not SPACE_HOST:
        print("Self-ping notice: SPACE_HOST env var not present (running locally or direct).")
        return
    url = f"https://{SPACE_HOST}"
    print(f"Self-ping initialized targeting: {url}")
    time.sleep(45)
    while True:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
                print(f"Self-ping heartbeat sent to {url} - Status {r.status_code}")
        except Exception as e:
            print(f"Self-ping heartbeat notice: {e}")
        time.sleep(240)

ping_thread = threading.Thread(target=self_ping_loop, daemon=True)
ping_thread.start()

# Sleek Gradio Interface for Hugging Face Space Heartbeat
with gr.Blocks(title="Hyacine Protocol") as demo:
    gr.Markdown("# ⌬ ⟡ Hyacine Protocol")
    gr.Markdown("### Status: **Operational ✧**")
    gr.Markdown("Hyacine Discord Bot is active and running 24/7 on Hugging Face Spaces.")
    gr.Markdown("---")
    gr.Markdown("💡 **Uptime Monitor Tip:** To guarantee 100% 24/7 uptime without sleeping, add your Space URL (`https://xenoroses-hyacine-bot.hf.space`) to [UptimeRobot](https://uptimerobot.com) (HTTP Monitor, 5-minute interval).")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, ssr_mode=False)
