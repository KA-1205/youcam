FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.4
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY apps/api apps/api
COPY apps/worker apps/worker
COPY apps/__init__.py apps/__init__.py
COPY services services
COPY contracts contracts
COPY infra/migrations infra/migrations
RUN useradd --uid 10001 --create-home anchor
USER 10001
EXPOSE 8000
CMD [".venv/bin/uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
