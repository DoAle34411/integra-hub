import pika
import os
import json
import time

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE_NAME = "notifications_exchange"

def callback(ch, method, properties, body):
    data = json.loads(body)
    print(f" [📧] NOTIFICACIÓN: Enviando correo a {data.get('customer_name')}...")
    print(f"      -> Asunto: Tu pedido {data.get('order_uuid')} ha sido confirmado.")
    time.sleep(0.5) # Simular envío
    print(" [✔] Correo enviado exitosamente.")

def start():
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # 1. Declarar el Exchange tipo FANOUT (Broadcast)
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='fanout')

    # 2. Crear una cola temporal y exclusiva para este servicio
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # 3. "Suscribirse" al Exchange
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=queue_name)

    print(' [*] Servicio de Notificaciones esperando eventos...')
    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

if __name__ == "__main__":
    time.sleep(10) # Esperar a RabbitMQ
    start()