from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

# --- Schemas para Autenticación ---
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginData(BaseModel):
    username: str
    password: str

# --- Schemas para Pedidos ---
class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price: float

class OrderCreate(BaseModel):
    customer_name: str
    items: List[OrderItem]

class OrderResponse(BaseModel):
    order_uuid: UUID
    customer_name: str
    status: str
    total_amount: float
    created_at: datetime
    
    class Config:
        from_attributes = True