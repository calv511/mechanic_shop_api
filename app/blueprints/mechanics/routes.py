from .schemas import mechanic_schema, mechanics_schema, mechanic_login_schema
from flask import request, jsonify
from marshmallow import ValidationError
from sqlalchemy import select, func
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import Mechanic, service_mechanics, db
from app.extensions import limiter
from app.utils.util import encode_mechanic_token, mechanic_token_required
from . import mechanics_bp

# CREATE MECHANIC
@mechanics_bp.route("/", methods=['POST'])
def create_mechanic():
    try:
        mechanic_data = mechanic_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify(e.messages), 400

    existing_mechanic = db.session.execute(
        select(Mechanic).where(Mechanic.email == mechanic_data['email'])
    ).scalars().first()

    if existing_mechanic:
        return jsonify({"error": "Email already associated with an account."}), 400

    mechanic_data['password'] = generate_password_hash(mechanic_data['password'])

    new_mechanic = Mechanic(**mechanic_data)
    db.session.add(new_mechanic)
    db.session.commit()
    return mechanic_schema.jsonify(new_mechanic), 201

# MECHANIC LOGIN
@mechanics_bp.route("/login", methods=['POST'])
@limiter.limit("5 per minute") # Same brute-force protection as customer login
def mechanic_login():
    try:
        credentials = mechanic_login_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify(e.messages), 400

    query = select(Mechanic).where(Mechanic.email == credentials['email'])
    mechanic = db.session.execute(query).scalars().first()

    if mechanic and check_password_hash(mechanic.password, credentials['password']):
        token = encode_mechanic_token(mechanic.id)
        return jsonify({
            "status": "success",
            "message": "successfully logged in.",
            "token": token
        }), 200

    return jsonify({"message": "Invalid email or password"}), 401

# GET ALL MECHANICS
@mechanics_bp.route("/", methods=['GET'])
def get_mechanics():
    mechanics = db.session.execute(select(Mechanic)).scalars().all()
    return mechanics_schema.jsonify(mechanics), 200

# GET MECHANICS RANKED BY NUMBER OF TICKETS WORKED
@mechanics_bp.route("/most-tickets", methods=['GET'])
def get_mechanics_by_ticket_count():
    ticket_count = func.count(service_mechanics.c.ticket_id).label('ticket_count')

    query = (
        select(Mechanic, ticket_count)
        .outerjoin(service_mechanics, Mechanic.id == service_mechanics.c.mechanic_id)
        .group_by(Mechanic.id)
        .order_by(ticket_count.desc())
    )
    results = db.session.execute(query).all()

    ranked_mechanics = []
    for mechanic, count in results:
        mechanic_data = mechanic_schema.dump(mechanic)
        mechanic_data['ticket_count'] = count
        ranked_mechanics.append(mechanic_data)

    return jsonify(ranked_mechanics), 200

# UPDATE SPECIFIC MECHANIC (any logged-in mechanic may update mechanic records)
@mechanics_bp.route("/<int:mechanic_id>", methods=['PUT'])
@mechanic_token_required
def update_mechanic(current_mechanic_id, mechanic_id):
    mechanic = db.session.get(Mechanic, mechanic_id)

    if not mechanic:
        return jsonify({"error": "Mechanic not found."}), 404

    try:
        mechanic_data = mechanic_schema.load(request.get_json(), partial=True)
    except ValidationError as e:
        return jsonify(e.messages), 400

    for key, value in mechanic_data.items():
        if key == 'password':
            value = generate_password_hash(value)
        setattr(mechanic, key, value)

    db.session.commit()
    return mechanic_schema.jsonify(mechanic), 200

# DELETE SPECIFIC MECHANIC (any logged-in mechanic may remove a mechanic record)
@mechanics_bp.route("/<int:mechanic_id>", methods=['DELETE'])
@mechanic_token_required
def delete_mechanic(current_mechanic_id, mechanic_id):
    mechanic = db.session.get(Mechanic, mechanic_id)

    if not mechanic:
        return jsonify({"error": "Mechanic not found."}), 404

    db.session.delete(mechanic)
    db.session.commit()
    return jsonify({"message": f'Mechanic id: {mechanic_id}, successfully deleted.'}), 200
