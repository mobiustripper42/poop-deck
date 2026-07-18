# Poop Deck :: ingest daemon image
# Small Python base + the two deps the daemon needs. One image per producer
# daemon; the compose stack runs it with restart: unless-stopped so ingest is
# always-on and survives host reboots (#14).
FROM python:3.12.8-slim

WORKDIR /app

# Pinned deps — the daemon is deliberately tiny (paho for MQTT, psycopg for PG).
RUN pip install --no-cache-dir \
        "paho-mqtt==2.1.0" \
        "psycopg[binary]==3.2.3"

COPY irrigation_ingest.py .

# -u: unbuffered, so container logs stream in real time.
CMD ["python", "-u", "irrigation_ingest.py"]
