import threading
import asyncio
import os
import gradio as gr
import bot

# Start Hyacine Bot in a background thread
def run_discord_bot():
    try:
        asyncio.run(bot.main())
    except Exception as e:
        print(f"Discord Bot Execution Error: {e}")

bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
bot_thread.start()

# Sleek Gradio Interface for Hugging Face Space Heartbeat
with gr.Blocks(title="Hyacine Protocol") as demo:
    gr.Markdown("# ⌬ ⟡ Hyacine Protocol")
    gr.Markdown("### Status: **Operational ✧**")
    gr.Markdown("Hyacine Discord Bot is active and running 24/7 on Hugging Face Spaces.")

if __name__ == "__main__":
    demo.launch()
