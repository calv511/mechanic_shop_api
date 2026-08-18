from app.extensions import ma
from app.models import Mechanic

class MechanicSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Mechanic
        dump_only = ("id",)
        load_only = ("password",) # accepted on input, never included in a response

mechanic_schema = MechanicSchema()
mechanics_schema = MechanicSchema(many=True)
# Login only needs email + password - exclude everything else, same approach as customers' login_schema
mechanic_login_schema = MechanicSchema(exclude=['name', 'phone', 'salary'])
