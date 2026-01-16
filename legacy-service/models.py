from tortoise import fields, models

class Order(models.Model):
    id = fields.IntField(pk=True)
    # Correlation ID para trazabilidad (requisito 5.4 del PDF)
    order_uuid = fields.UUIDField(unique=True) 
    customer_name = fields.CharField(max_length=100)
    total_amount = fields.DecimalField(max_digits=10, decimal_places=2)
    status = fields.CharField(max_length=20, default="PENDING")
    created_at = fields.DatetimeField(auto_now_add=True)
    
    # Guardamos los items como JSON simple para no complicar el MVP con tablas relacionales extra
    items = fields.JSONField()

    class Meta:
        table = "orders"