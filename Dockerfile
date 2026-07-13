# Single image, multiple services. Pick the app with SERVICE (gateway|vision|agents|privacy|mlops).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 SERVICE=gateway
WORKDIR /app

COPY pyproject.toml README.md ./
COPY aetheris ./aetheris

RUN pip install --no-cache-dir -e ".[server]"

EXPOSE 8000

# The CLI maps SERVICE -> the right FastAPI app.
CMD ["sh", "-c", "aetheris serve ${SERVICE} --host 0.0.0.0 --port 8000"]
