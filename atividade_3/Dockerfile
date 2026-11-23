FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    pkg-config \
    libns3-dev \
    ns3 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-dev \
    libgsl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
