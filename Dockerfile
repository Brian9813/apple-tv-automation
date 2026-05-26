FROM python:3.9-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APPLE_TV_APP_HOST=0.0.0.0
ENV APPLE_TV_APP_PORT=2332
ENV APPLE_TV_TIME_ZONE=America/Chicago
ENV TZ=America/Chicago
ENV HOME=/data

WORKDIR /app

COPY requirements.txt .
COPY apple_tv_service.py scheduler.py server.py ./
COPY static ./static
COPY docker-entrypoint.sh ./

RUN mkdir -p /data

VOLUME ["/data"]

EXPOSE 2332

HEALTHCHECK --interval=30s --timeout=5s --start-period=5m --retries=3 \
    CMD python -c "import json, urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:2332/api/health', timeout=4))['status'])"

CMD ["sh", "/app/docker-entrypoint.sh"]
