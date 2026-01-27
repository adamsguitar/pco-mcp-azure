FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services.py /app/services.py

EXPOSE 8080

CMD ["fastmcp", "run", "services.py", "--host", "0.0.0.0", "--port", "8080"]
