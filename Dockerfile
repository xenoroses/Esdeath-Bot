FROM python:3.11

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app

# --- THE FIX: Hardcode Discord DNS into the container ---
# This ensures that even if Hugging Face DNS is broken, the OS knows where to go.
RUN echo "162.159.138.232 discord.com" | sudo tee -a /etc/hosts || true

COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user . /app

CMD ["python", "bot.py"]