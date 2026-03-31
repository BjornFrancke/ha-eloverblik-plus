FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid 1000 -m vscode

USER vscode
ENV PATH="/home/vscode/.local/bin:${PATH}"

WORKDIR /workspaces/ha-eloverblik
