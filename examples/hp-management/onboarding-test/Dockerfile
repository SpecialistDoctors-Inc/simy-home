FROM node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da

ARG CODEX_VERSION=0.166.0
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git python3 python3-yaml \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global "@openai/codex@${CODEX_VERSION}" \
    && npm cache clean --force

USER node
WORKDIR /home/node
CMD ["codex"]
