from tortoise import fields, models

class Order(models.Model):
    id = fields.IntField(pk=True)
    # Correlation ID para trazabilidad
    order_uuid = fields.UUIDField(unique=True) 
    customer_name = fields.CharField(max_length=100)
    total_amount = fields.DecimalField(max_digits=10, decimal_places=2)
    status = fields.CharField(max_length=20, default="PENDING")
    created_at = fields.DatetimeField(auto_now_add=True)
    
    # Guardamos items como JSON
    items = fields.JSONField()

    class Meta:
        table = "orders"