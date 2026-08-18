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
        'sub': customer_id 
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
                customer_id = data['sub']
            except jwt.ExpiredSignatureError as e:
                return jsonify({"message": "token expired"}), 400
            except jwt.InvalidTokenError:
                return jsonify({"message": "invalid token"}), 400

            return f(customer_id, *args, **kwargs)

        else:
            return jsonify({"message": "You must be logged in to accces this"}), 400

    return decorated