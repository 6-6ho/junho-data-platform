FROM python:3.11-slim

ENV TZ=Asia/Seoul \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sources ./sources
COPY main.py filters.py dedupe.py notifier.py ./

CMD ["python", "-u", "main.py"]
