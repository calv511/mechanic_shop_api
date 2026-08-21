from datetime import datetime, timedelta, timezone
from jose import jwt
import jose
from dotenv import load_dotenv
import os
from functools import wraps
from flask import request, jsonify
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

def encode_token(customer_id):
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(days=0, hours=1), # Set expiration time
        'iat': datetime.now(timezone.utc), # Issues at
        'sub': str(customer_id), # Must be a string per the JWT spec
        'role': 'customer' # Marks this as a customer token, as opposed to a mechanic token
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def encode_mechanic_token(mechanic_id):
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(days=0, hours=1),
        'iat': datetime.now(timezone.utc),
        'sub': str(mechanic_id),
        'role': 'mechanic' # This is the field mechanic_token_required checks for
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            token = request.headers['Authorization'].split()[1]

            if not token:
                return jsonify({"message": "missing token"}), 400

            try:
                data = jwt.decode(token, SECRET_KEY, algorithms="HS256")
                customer_id = int(data['sub'])
            except jwt.ExpiredSignatureError:
                return jsonify({"message": "token expired"}), 400
            except jwt.JWTError:
                return jsonify({"message": "invalid token"}), 400

            return f(customer_id, *args, **kwargs)

        else:
            return jsonify({"message": "You must be logged in to access this"}), 400

    return decorated

def mechanic_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"message": "You must be logged in to access this"}), 400

        header_parts = auth_header.split()
        if len(header_parts) != 2:
            return jsonify({"message": "missing token"}), 400
        token = header_parts[1]

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms="HS256")
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "token expired"}), 400
        except jwt.JWTError:
            return jsonify({"message": "invalid token"}), 400

        # This is what separates a mechanic route from a customer route - a
        # customer's token decodes fine here, it just won't carry this claim
        if data.get('role') != 'mechanic':
            return jsonify({"message": "This action requires a mechanic account."}), 403

        mechanic_id = int(data['sub'])
        return f(mechanic_id, *args, **kwargs)

    return decorated