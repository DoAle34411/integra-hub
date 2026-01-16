FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Creamos las carpetas dentro del contenedor por si acaso
RUN mkdir -p inbox processed

CMD ["python", "main.py"]