FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV AIR_DB_PATH=/data/readings.sqlite

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["air-monitor"]
