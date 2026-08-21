from .schemas import customer_schema, customers_schema, login_schema
from flask import request, jsonify
from marshmallow import ValidationError
from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import Customer, Service_Ticket, db
from . import customers_bp
from app.extensions import cache, limiter
from app.utils.util import encode_token, token_required
from app.blueprints.service_tickets.schemas import service_tickets_schema

@customers_bp.route("/login", methods=['POST'])
@limiter.limit("5 per minute") # Stricter than the app default - slows down password-guessing
def login():
    # load() raises ValidationError, not KeyError, when a field is missing
    try:
        credentials = login_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify(e.messages), 400

    query = select(Customer).where(Customer.email == credentials['email'])
    customer = db.session.execute(query).scalars().first()

    if customer and check_password_hash(customer.password, credentials['password']):
        token = encode_token(customer.id)

        response = {
            "status": "success",
            "message": "successfully logged in.",
            "token": token
        }

        return jsonify(response), 200

    return jsonify({'message': "Invalid email or password"}), 401

@customers_bp.route("/", methods=['POST'])
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

    customer_data['password'] = generate_password_hash(customer_data['password'])

    new_customer = Customer(**customer_data)
    db.session.add(new_customer)
    db.session.commit()
    return customer_schema.jsonify(new_customer), 201

# GET ALL CUSTOMERS (PAGINATED)
@customers_bp.route("/", methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def get_customers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    pagination = db.paginate(
        select(Customer),
        page=page,
        per_page=per_page,
        max_per_page=100,
        error_out=False
    )

    return jsonify({
        "customers": customers_schema.dump(pagination.items),
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "total_customers": pagination.total
    }), 200

# GET SPECIFIC CUSTOMER
@customers_bp.route("/<int:customer_id>", methods=['GET'])
def get_customer(customer_id):
    customer = db.session.get(Customer, customer_id)

    if customer:
        return customer_schema.jsonify(customer), 200
    return jsonify({"error": "Customer not found."}), 404

# GET THIS CUSTOMER'S SERVICE TICKETS
@customers_bp.route("/my-tickets", methods=["GET"])
@token_required
def my_tickets(customer_id):
    tickets = db.session.execute(
        select(Service_Ticket).where(Service_Ticket.customer_id == customer_id)
    ).scalars().all()

    return service_tickets_schema.jsonify(tickets), 200

# UPDATE SPECIFIC USER
@customers_bp.route("/", methods=["PUT"])
@token_required
def update_customer(customer_id):
    customer = db.session.get(Customer, customer_id)

    if not customer:
        return jsonify({"error": "Customer not found."}), 404

    try:
        customer_data = customer_schema.load(request.get_json(), partial=True)
    except ValidationError as e:
        return jsonify(e.messages), 400

    for key, value in customer_data.items():
        if key == 'password':
            value = generate_password_hash(value)
        setattr(customer, key, value)

    db.session.commit()
    return customer_schema.jsonify(customer), 200

# DELETE SPECIFIC CUSTOMER
@customers_bp.route("/", methods=["DELETE"])
@token_required
def delete_customer(customer_id):
    customer = db.session.get(Customer, customer_id)

    if not customer:
        return jsonify({"error": "Customer not found."}), 404

    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": f'Customer id: {customer_id}, successfully deleted.'}), 200
