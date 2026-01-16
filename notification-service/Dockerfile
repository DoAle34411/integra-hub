FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install pika
COPY . .
CMD ["python", "main.py"]