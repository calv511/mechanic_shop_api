from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date
from typing import List


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    email: Mapped[str] = mapped_column(db.String(360), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(db.String(255), nullable=False)

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
    # Junction rows, not Inventory objects - each row carries its own quantity
    parts: Mapped[List['Service_Ticket_Inventory']] = db.relationship(
        back_populates='service_ticket',
        cascade='all, delete-orphan'
    )


class Mechanic(Base):
    __tablename__ = 'mechanics'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255))
    email: Mapped[str] = mapped_column(db.String(255), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(db.String(255))
    salary: Mapped[float] = mapped_column()
    password: Mapped[str] = mapped_column(db.String(255), nullable=False)
    service_tickets: Mapped[List['Service_Ticket']] = db.relationship(
        secondary=service_mechanics,
        back_populates='mechanics'
    )


class Inventory(Base):
    __tablename__ = 'inventory'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)

    # Junction rows linking this part to the tickets it was used on
    ticket_parts: Mapped[List['Service_Ticket_Inventory']] = db.relationship(
        back_populates='part',
        cascade='all, delete-orphan'
    )


# Junction model (association object) - a plain db.Table cannot hold extra
# columns, so quantity forces this to be a full model
class Service_Ticket_Inventory(Base):
    __tablename__ = 'service_ticket_inventory'
    ticket_id: Mapped[int] = mapped_column(db.ForeignKey('service_tickets.id'), primary_key=True)
    inventory_id: Mapped[int] = mapped_column(db.ForeignKey('inventory.id'), primary_key=True)
    quantity: Mapped[int] = mapped_column(default=1)

    service_ticket: Mapped['Service_Ticket'] = db.relationship(back_populates='parts')
    part: Mapped['Inventory'] = db.relationship(back_populates='ticket_parts')
