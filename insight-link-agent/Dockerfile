# Agent 镜像只安装锁文件中的运行依赖，不包含开发缓存、测试数据或本地凭据。
FROM python:3.13-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.5
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable --no-cache

# 仅复制 Docker 客户端；容器通过挂载的 socket 使用宿主引擎，不运行嵌套守护进程。
FROM docker:28-cli AS docker-cli
FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=builder /app/.venv /app/.venv
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "insight_link_agent.app.api:app", "--host", "0.0.0.0", "--port", "8001"]
