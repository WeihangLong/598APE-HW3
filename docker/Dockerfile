FROM gcc:15.2.0@sha256:3ae15afe768b06d0c0fe088d822ba5f8045c26630bdacc8d8e7713cf5d8e7289

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
CMD ["python3", "scripts/reproduce.py", "--output", "/results"]
