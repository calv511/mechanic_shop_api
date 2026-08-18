from .schemas import service_ticket_schema, service_tickets_schema, edit_service_ticket_schema
from flask import request, jsonify
from marshmallow import ValidationError
from sqlalchemy import select
from app.models import Service_Ticket, Mechanic, Customer, Inventory, Service_Ticket_Inventory, db
from . import service_tickets_bp

# CREATE SERVICE TICKET
@service_tickets_bp.route("/", methods=['POST'])
def create_service_ticket():
    try:
        ticket_data = service_ticket_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify(e.messages), 400

    customer = db.session.get(Customer, ticket_data['customer_id'])

    if not customer:
        return jsonify({"error": "Customer not found."}), 404

    new_ticket = Service_Ticket(**ticket_data)
    db.session.add(new_ticket)
    db.session.commit()
    return service_ticket_schema.jsonify(new_ticket), 201

# GET ALL SERVICE TICKETS
@service_tickets_bp.route("/", methods=['GET'])
def get_service_tickets():
    tickets = db.session.execute(select(Service_Ticket)).scalars().all()
    return service_tickets_schema.jsonify(tickets), 200

# ASSIGN MECHANIC TO SERVICE TICKET
@service_tickets_bp.route("/<int:ticket_id>/assign-mechanic/<int:mechanic_id>", methods=['PUT'])
def assign_mechanic(ticket_id, mechanic_id):
    ticket = db.session.get(Service_Ticket, ticket_id)
    mechanic = db.session.get(Mechanic, mechanic_id)

    if not ticket:
        return jsonify({"error": "Service ticket not found."}), 404
    if not mechanic:
        return jsonify({"error": "Mechanic not found."}), 404

    if mechanic in ticket.mechanics:
        return jsonify({"error": "Mechanic already assigned to this service ticket."}), 400

    ticket.mechanics.append(mechanic)
    db.session.commit()
    return service_ticket_schema.jsonify(ticket), 200

# REMOVE MECHANIC FROM SERVICE TICKET
@service_tickets_bp.route("/<int:ticket_id>/remove-mechanic/<int:mechanic_id>", methods=['PUT'])
def remove_mechanic(ticket_id, mechanic_id):
    ticket = db.session.get(Service_Ticket, ticket_id)
    mechanic = db.session.get(Mechanic, mechanic_id)

    if not ticket:
        return jsonify({"error": "Service ticket not found."}), 404
    if not mechanic:
        return jsonify({"error": "Mechanic not found."}), 404

    if mechanic not in ticket.mechanics:
        return jsonify({"error": "Mechanic is not assigned to this service ticket."}), 400

    ticket.mechanics.remove(mechanic)
    db.session.commit()
    return service_ticket_schema.jsonify(ticket), 200

# ADD/REMOVE MECHANICS ON A SERVICE TICKET
@service_tickets_bp.route("/<int:ticket_id>/edit", methods=['PUT'])
def edit_service_ticket(ticket_id):
    try:
        edit_data = edit_service_ticket_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify(e.messages), 400

    service_ticket = db.session.get(Service_Ticket, ticket_id)

    if not service_ticket:
        return jsonify({"error": "Service ticket not found."}), 404

    for mechanic_id in edit_data['add_ids']:
        mechanic = db.session.get(Mechanic, mechanic_id)

        if mechanic and mechanic not in service_ticket.mechanics:
            service_ticket.mechanics.append(mechanic)

    for mechanic_id in edit_data['remove_ids']:
        mechanic = db.session.get(Mechanic, mechanic_id)

        if mechanic and mechanic in service_ticket.mechanics:
            service_ticket.mechanics.remove(mechanic)

    db.session.commit()
    return service_ticket_schema.jsonify(service_ticket), 200

# ADD A PART TO A SERVICE TICKET
@service_tickets_bp.route("/<int:ticket_id>/add-part/<int:part_id>", methods=['POST'])
def add_part_to_ticket(ticket_id, part_id):
    service_ticket = db.session.get(Service_Ticket, ticket_id)
    part = db.session.get(Inventory, part_id)

    if not service_ticket:
        return jsonify({"error": "Service ticket not found."}), 404
    if not part:
        return jsonify({"error": "Part not found."}), 404

    # Optional {"quantity": n} body; defaults to 1 if no body or key is sent
    body = request.get_json(silent=True) or {}
    quantity = body.get('quantity', 1)

    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({"error": "quantity must be a positive integer."}), 400

    # ticket_id + inventory_id is a composite primary key on the junction
    # table, so this part can only appear once per ticket - find that row
    existing_link = db.session.execute(
        select(Service_Ticket_Inventory).where(
            Service_Ticket_Inventory.ticket_id == ticket_id,
            Service_Ticket_Inventory.inventory_id == part_id
        )
    ).scalars().first()

    if existing_link:
        # Part is already on this ticket - add to the existing quantity
        # instead of inserting a duplicate row
        existing_link.quantity += quantity
    else:
        service_ticket.parts.append(Service_Ticket_Inventory(part=part, quantity=quantity))

    db.session.commit()
    return service_ticket_schema.jsonify(service_ticket), 200