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

# Apply the starting bug after initial build, then rebuild broken binary and snapshot clean baseline
COPY inject_bug.patch /tmp/inject_bug.patch
RUN git apply /tmp/inject_bug.patch \
    && rm /tmp/inject_bug.patch \
    && make \
    && rm -rf .git \
    && git init -q \
    && git config user.email "harness@adzzatlabs.com" \
    && git config user.name "Adzzat Harness" \
    && git add -A \
    && git commit -q -m "baseline"
