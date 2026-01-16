import os
import json
import uuid
import pika
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from tortoise.contrib.fastapi import register_tortoise
from decimal import Decimal

# --- IMPORTACIÓN NUEVA PARA CORS ---
from fastapi.middleware.cors import CORSMiddleware

# Importamos nuestros módulos
from models import Order
from schemas import OrderCreate, OrderResponse, Token
from auth import create_access_token, verify_password, get_current_user, FAKE_USERS_DB

app = FastAPI(title="IntegraHub API")

# --- CONFIGURACIÓN DE CORS (¡LA SOLUCIÓN!) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción poner ["http://localhost:3000"], "*" permite a cualquiera
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los headers (Authorization, etc.)
)

# --- Configuración RabbitMQ ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def publish_event(event_type: str, data: dict):
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue='orders_queue', durable=True)
        message_body = json.dumps({"event": event_type, "payload": data})
        channel.basic_publish(
            exchange='',
            routing_key='orders_queue',
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                correlation_id=data.get('order_uuid')
            )
        )
        connection.close()
    except Exception as e:
        print(f" [!] Error conectando a RabbitMQ: {e}")

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok", "service": "IntegraHub API running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    # Nota: Asegúrate de tener el fix de contraseña en auth.py o usa las credenciales correctas
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user['username']})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate, current_user: str = Depends(get_current_user)):
    total = sum(item.price * item.quantity for item in order_data.items)
    new_uuid = uuid.uuid4()
    
    new_order = await Order.create(
        order_uuid=new_uuid,
        customer_name=order_data.customer_name,
        total_amount=Decimal(total),
        items=[item.dict() for item in order_data.items],
        status="PENDING"
    )
    
    event_payload = {
        "order_uuid": str(new_uuid),
        "customer_name": order_data.customer_name,
        "items": [item.dict() for item in order_data.items],
        "total": float(total)
    }
    publish_event("OrderCreated", event_payload)

    return new_order

@app.get("/analytics/dashboard")
async def get_analytics(current_user: str = Depends(get_current_user)):
    from tortoise.functions import Count, Sum
    total_orders = await Order.all().count()
    sales_result = await Order.all().annotate(sum=Sum("total_amount")).first()
    total_sales = sales_result.sum if sales_result else 0
    
    pending = await Order.filter(status="PENDING").count()
    confirmed = await Order.filter(status="CONFIRMED").count()
    
    return {
        "total_orders": total_orders,
        "total_sales": float(total_sales or 0),
        "by_status": {"PENDING": pending, "CONFIRMED": confirmed}
    }

register_tortoise(
    app,
    db_url=os.getenv("DATABASE_URL"),
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)