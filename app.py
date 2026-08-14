from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, select
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError
from datetime import date
from dotenv import load_dotenv
import os
from typing import List

load_dotenv()

app = Flask(__name__)

class Base(DeclarativeBase):
    pass

db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{db_pass}@localhost/{db_name}'

db = SQLAlchemy(model_class=Base)
ma = Marshmallow()

db.init_app(app)
ma.init_app(app)

class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    email: Mapped[str] = mapped_column(db.String(360), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)

    services_tickets: Mapped[List['Service_Ticket']] = db.relationship(back_populates='customer')

# Junction
service_mechanics = db.Table(
    'service_mechanics',
    Base.metadata,
    db.Column('ticket_id', db.ForeignKey('service_tickets.id'), primary_key=True),
    db.Column('mechanic_id', db.ForeignKey('mechanics.id'), primary_key=True)
)

class Service_Ticket(Base):
    __tablename__ = 'service_tickets'
    id: Mapped[int] = mapped_column(primary_key=True)
    VIN: Mapped[str] = mapped_column(db.String(20))
    service_date: Mapped[date] = mapped_column(db.Date)
    service_desc: Mapped[str] = mapped_column(db.String(255))
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('customers.id'))

    customer: Mapped['Customer'] = db.relationship(back_populates='services_tickets')
    mechanics: Mapped[List['Mechanic']] = db.relationship(
        secondary=service_mechanics,
        back_populates='service_tickets'
    )


class Mechanic(Base):
    __tablename__ = 'mechanics'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255))
    email: Mapped[str] = mapped_column(db.String(255))
    phone: Mapped[str] = mapped_column(db.String(255))
    salary: Mapped[float] = mapped_column()
    service_tickets: Mapped[List['Service_Ticket']] = db.relationship(
        secondary=service_mechanics,
        back_populates='mechanics'
    )

class CustomerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Customer
        load_instance = True

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

@app.route("/customers", methods=['POST'])
def create_customer():
    try:
        customer_data = customer_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify(e.messages), 400

    existing_customer = db.session.execute(
        select(Customer).where(Customer.email == customer_data['email'])
    ).scalars().first()

    if existing_customer:
        return jsonify({"error": "Email already associated with an account."}), 400

    new_customer = Customer(**customer_data)
    db.session.add(new_customer)
    db.session.commit()
    return customer_schema.jsonify(new_customer), 201

# GET ALL CUSTOMERS
@app.route("/customers", method=['GET'])
def get_members():
    query = select(Customer)
    customers = db.session.execute(query).scalar().all()

    return customers_schema.jsonify(customers)

# GET SPECIFIC CUSTOMER
@app.route("/customers/<int:customer_id>", methods=['GET'])
def get_member(customer_id):
    customer = db.session.get(Customer, customer_id)

    if customer:
        return customer_schema.jsonify(customer), 200
    return jsonify({"error": "Customer not found."}), 404

app.run()