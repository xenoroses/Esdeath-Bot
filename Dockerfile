FROM python:3.11-slim
# Using slim to reduce image size, but adding necessary build tools if needed
# Note: PyNaCl might need build-essential for some architectures, but on x86_64 it's usually fine as a wheel.

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app

COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user . /app

CMD ["python", "bot.py"]