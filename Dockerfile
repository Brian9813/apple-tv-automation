FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APPLE_TV_APP_HOST=0.0.0.0
ENV APPLE_TV_APP_PORT=8000
ENV HOME=/data

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY apple_tv_service.py server.py ./
COPY static ./static

RUN mkdir -p /data

VOLUME ["/data"]

EXPOSE 8000

CMD ["python", "server.py"]
