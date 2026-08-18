from datetime import datetime, timedelta, timezone
from jose import jwt
import jose
from dotenv import load_dotenv
import os

load_dotenv

SECRET_KEY = os.getenv("SECRET_KEY")

def encode_token(user_id):
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(days=0, hours=1), # Set expiration time
        'iat': datetime.now(timezone.utc), # Issues at
        'sub': user_id 
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token