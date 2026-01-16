import os
import json
import uuid
import pika
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from tortoise.contrib.fastapi import register_tortoise
from decimal import Decimal

# Importamos nuestros módulos
from models import Order
from schemas import OrderCreate, OrderResponse, Token
from auth import create_access_token, verify_password, get_current_user, FAKE_USERS_DB

app = FastAPI(title="IntegraHub API")

# --- Configuración RabbitMQ ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def publish_event(event_type: str, data: dict):
    """Publica un mensaje en RabbitMQ (Patrón Fire-and-Forget para este paso)"""
    try:
        # Conexión básica (en prod usaríamos un pool o conexión persistente)
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # Declaramos la cola para asegurar que existe (Idempotencia en infraestructura)
        channel.queue_declare(queue='orders_queue', durable=True)
        
        message_body = json.dumps({
            "event": event_type,
            "payload": data
        })
        
        channel.basic_publish(
            exchange='',
            routing_key='orders_queue',
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Mensaje persistente
                correlation_id=data.get('order_uuid') # Para trazabilidad
            )
        )
        connection.close()
        print(f" [x] Evento enviado: {event_type}")
    except Exception as e:
        print(f" [!] Error conectando a RabbitMQ: {e}")
        # En un sistema real, aquí podríamos guardar en una tabla 'outbox' para reintentar luego

# --- Endpoints de Autenticación ---
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user['username']})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Endpoint de Pedidos (Protegido) ---
@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate, current_user: str = Depends(get_current_user)):
    # 1. Calcular total
    total = sum(item.price * item.quantity for item in order_data.items)
    
    # 2. Generar UUID para trazabilidad
    new_uuid = uuid.uuid4()
    
    # 3. Guardar en Base de Datos (Estado PENDING)
    new_order = await Order.create(
        order_uuid=new_uuid,
        customer_name=order_data.customer_name,
        total_amount=Decimal(total),
        items=[item.dict() for item in order_data.items],
        status="PENDING"
    )
    
    # 4. Publicar Evento 'OrderCreated' a RabbitMQ [cite: 22]
    event_payload = {
        "order_uuid": str(new_uuid),
        "customer_name": order_data.customer_name,
        "items": [item.dict() for item in order_data.items],
        "total": float(total)
    }
    publish_event("OrderCreated", event_payload)

    return new_order

# --- Endpoint de Analítica (Dashboard) ---
@app.get("/analytics/dashboard")
async def get_analytics(current_user: str = Depends(get_current_user)):
    """
    Retorna métricas simples para el dashboard:
    1. Total de pedidos
    2. Total de ventas ($)
    3. Conteo por estado
    """
    from tortoise.functions import Count, Sum
    
    total_orders = await Order.all().count()
    
    # Suma total de ventas (cuidado con nulos)
    sales_result = await Order.all().annotate(sum=Sum("total_amount")).first()
    total_sales = sales_result.sum if sales_result else 0
    
    # Agrupación por estado
    # Nota: Tortoise ORM tiene soporte limitado para 'group_by' complejos en versiones simples,
    # así que hacemos algo pythonico rápido para el MVP:
    pending = await Order.filter(status="PENDING").count()
    confirmed = await Order.filter(status="CONFIRMED").count()
    
    return {
        "total_orders": total_orders,
        "total_sales": float(total_sales or 0),
        "by_status": {
            "PENDING": pending,
            "CONFIRMED": confirmed
        }
    }

# --- Configuración DB ---
register_tortoise(
    app,
    db_url=os.getenv("DATABASE_URL"),
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)