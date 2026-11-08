# Blockchain Academics MCP server (the bca-mcp Python package), built from this
# repository's source. It speaks MCP over stdio, so run it with docker run -i:
#
#   docker build -t bca-mcp-python .
#   docker run -i --rm bca-mcp-python                   (the demo tools need no key)
#   docker run -i --rm -e BCA_API_KEY bca-mcp-python    (passes your key from your shell)
#
# No key is baked into the image. Without BCA_API_KEY the server uses the
# public demo key that also ships in the PyPI package.

FROM python:3.12.16-slim-trixie AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY scripts ./scripts
COPY src ./src
# The demo key module is generated from scripts/demo-key.txt, as in the publish workflow.
# pyproject asks for any hatchling, so the build backend and its dependencies are
# pinned here (each release at least two weeks old) and the wheel builds without
# isolation: a new hatchling release cannot change what goes into the image.
RUN python scripts/gen_demo_key.py \
 && pip install --no-cache-dir --root-user-action=ignore \
      hatchling==1.32.4 packaging==26.1 pathspec==1.1.1 pluggy==1.6.0 \
      tomlkit==0.15.2 trove-classifiers==2026.9.21.13 \
 && pip wheel --no-cache-dir --no-deps --no-build-isolation --wheel-dir /wheels .

FROM python:3.12.16-slim-trixie
LABEL org.opencontainers.image.title="Blockchain Academics MCP (Python)" \
      org.opencontainers.image.description="Crypto news, prices, onchain data and sentiment as agent tools, each answer with its primary source and a completeness status." \
      org.opencontainers.image.source="https://github.com/blockchainacademics/bca-mcp-python" \
      org.opencontainers.image.licenses="MIT" \
      io.modelcontextprotocol.server.name="io.github.blockchainacademics/mcp"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.lock.txt /tmp/
COPY --from=build /wheels /tmp/wheels
# Dependency versions come from requirements.lock.txt (used as constraints only).
RUN pip install --no-cache-dir --root-user-action=ignore -c /tmp/requirements.lock.txt /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels /tmp/requirements.lock.txt \
 && useradd --uid 10001 --create-home --shell /usr/sbin/nologin app
USER app
WORKDIR /home/app
CMD ["python", "-m", "bca_mcp"]
