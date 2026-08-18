from app.extensions import ma
from app.models import Inventory

class InventorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Inventory
        dump_only = ("id",)

inventory_schema = InventorySchema()
inventories_schema = InventorySchema(many=True)
