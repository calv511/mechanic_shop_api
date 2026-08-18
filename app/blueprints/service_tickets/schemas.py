from marshmallow import fields
from app.extensions import ma
from app.models import Service_Ticket
from app.blueprints.mechanics.schemas import MechanicSchema

class ServiceTicketSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Service_Ticket
        include_fk = True
        dump_only = ("id",)

    mechanics = ma.Nested(MechanicSchema, many=True, dump_only=True)

class Edit_Service_Tickets_Schema(ma.Schema):
    add_ids = fields.List(fields.Int(), load_default=[])
    remove_ids = fields.List(fields.Int(), load_default=[])

    class Meta:
        fields = ("add_ids", "remove_ids")

service_ticket_schema = ServiceTicketSchema()
service_tickets_schema = ServiceTicketSchema(many=True)
edit_service_ticket_schema = Edit_Service_Tickets_Schema()