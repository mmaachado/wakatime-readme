# Two stages so the published image carries the wheel and its interpreter
# and nothing else: no uv, no build tools, no git. Writing happens through
# the Contents API, so there is no reason for a git binary to be in here.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS build

WORKDIR /src
# README and LICENSE are not decoration: the build backend reads both
# while assembling the wheel metadata.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN uv build --wheel --out-dir /dist

FROM python:3.14-slim

LABEL org.opencontainers.image.source=https://github.com/mmaachado/wakatime-readme
LABEL org.opencontainers.image.description="dev metrics with Wakatime for your README.md"
LABEL org.opencontainers.image.licenses=MIT

COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

# Container actions run as root on purpose: the workspace GitHub mounts
# is owned by root, and a lesser user could not write to it.
ENTRYPOINT ["wakatime-readme"]
