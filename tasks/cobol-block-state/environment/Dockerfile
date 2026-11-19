FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gnucobol \
    g++ \
    make \
    zlib1g-dev \
    git \
    python3 \
    python3-pytest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the clean CobolCraft repository into /app (NEVER copy Harbor's tests/ or solution/)
COPY cobolcraft/ /app/

# Pre-build dependencies once so incremental agent rebuilds are fast
RUN make

# Apply the starting bug after initial build, then rebuild broken binary
COPY inject_bug.patch /tmp/inject_bug.patch
RUN git apply /tmp/inject_bug.patch && rm /tmp/inject_bug.patch && make
