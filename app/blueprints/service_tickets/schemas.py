from app.extensions import ma
from app.models import Service_Ticket
from app.blueprints.mechanics.schemas import MechanicSchema

class ServiceTicketSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Service_Ticket
        include_fk = True
        dump_only = ("id",)

    mechanics = ma.Nested(MechanicSchema, many=True, dump_only=True)

service_ticket_schema = ServiceTicketSchema()
service_tickets_schema = ServiceTicketSchema(many=True)
