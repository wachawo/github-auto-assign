FROM python:3.11-alpine

# Install runtime deps (git is handy for debug; ca-certificates for HTTPS)
RUN apk add --no-cache ca-certificates && update-ca-certificates

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

# Non-root
RUN adduser -D appuser
USER appuser

ENTRYPOINT ["python", "-u", "/app/src/main.py"]
