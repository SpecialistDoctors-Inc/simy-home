FROM node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da
ARG CODEX_VERSION=0.166.0
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates git python3 python3-venv procps \
 && rm -rf /var/lib/apt/lists/* \
 && npm install --global "@openai/codex@${CODEX_VERSION}" \
 && npm cache clean --force \
 && python3 -m venv /opt/hp-python
COPY requirements.txt /opt/hp-agent/requirements.txt
RUN /opt/hp-python/bin/pip install --no-cache-dir -r /opt/hp-agent/requirements.txt
COPY *.py /opt/hp-agent/
RUN install -d -m 700 /state /control \
 && install -d -m 711 /work \
 && install -d -m 700 -o node -g node /home/node/.codex
WORKDIR /opt/hp-agent
ENV PATH="/opt/hp-python/bin:/usr/local/bin:/usr/bin:/bin" \
    CODEX_HOME="/home/node/.codex" \
    HOME="/home/node"
ENTRYPOINT ["python3", "/opt/hp-agent/agent.py"]
CMD ["--config", "/control/config.json", "--db", "/state/agent.sqlite3"]
