FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Usamos python directamente, no uvicorn, porque es un script, no una API
CMD ["python", "main.py"]