FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    gnucobol \
    zlib1g-dev \
    curl \
    openjdk-21-jre-headless \
    git \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the clean CobolCraft repository into /app (NEVER copy Harbor's tests/ or solution/)
COPY cobolcraft/ /app/

# Pre-build dependencies once so incremental agent rebuilds are fast
RUN make

# Strip crafting grid matching & consumption logic after initial build, then rebuild and snapshot clean baseline
COPY strip_crafting.patch /tmp/strip_crafting.patch
RUN git apply /tmp/strip_crafting.patch \
    && rm /tmp/strip_crafting.patch \
    && make \
    && rm -rf .git \
    && git init -q \
    && git config user.email "harness@adzzatlabs.com" \
    && git config user.name "Adzzat Harness" \
    && git add -A \
    && git commit -q -m "baseline"
