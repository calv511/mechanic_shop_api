from .schemas import inventory_schema, inventories_schema
from flask import request, jsonify
from marshmallow import ValidationError
from sqlalchemy import select
from app.models import Inventory, db
from app.utils.util import mechanic_token_required
from . import inventory_bp

# CREATE PART (mechanic-only: shop staff manage the catalog, not customers)
@inventory_bp.route("/", methods=['POST'])
@mechanic_token_required
def create_part(current_mechanic_id):
    try:
        part_data = inventory_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_part = Inventory(**part_data)
    db.session.add(new_part)
    db.session.commit()
    return inventory_schema.jsonify(new_part), 201

# GET ALL PARTS
@inventory_bp.route("/", methods=['GET'])
def get_parts():
    parts = db.session.execute(select(Inventory)).scalars().all()
    return inventories_schema.jsonify(parts), 200

# GET SPECIFIC PART
@inventory_bp.route("/<int:part_id>", methods=['GET'])
def get_part(part_id):
    part = db.session.get(Inventory, part_id)

    if not part:
        return jsonify({"error": "Part not found."}), 404

    return inventory_schema.jsonify(part), 200

# UPDATE SPECIFIC PART (mechanic-only)
@inventory_bp.route("/<int:part_id>", methods=['PUT'])
@mechanic_token_required
def update_part(current_mechanic_id, part_id):
    part = db.session.get(Inventory, part_id)

    if not part:
        return jsonify({"error": "Part not found."}), 404

    # partial=True so the client can send just the fields they want changed
    try:
        part_data = inventory_schema.load(request.get_json(), partial=True)
    except ValidationError as e:
        return jsonify(e.messages), 400

    for key, value in part_data.items():
        setattr(part, key, value)

    db.session.commit()
    return inventory_schema.jsonify(part), 200

# DELETE SPECIFIC PART (mechanic-only)
@inventory_bp.route("/<int:part_id>", methods=['DELETE'])
@mechanic_token_required
def delete_part(current_mechanic_id, part_id):
    part = db.session.get(Inventory, part_id)

    if not part:
        return jsonify({"error": "Part not found."}), 404

    db.session.delete(part)
    db.session.commit()
    return jsonify({"message": f'Part id: {part_id}, successfully deleted.'}), 200
