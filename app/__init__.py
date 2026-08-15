from flask import Flask
from .extensions import ma
from .models import db

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(f'config.{config_name}')

    # Initialize extensions
    ma.init_app(app)
    db.init_app(app)

    # Register Blueprints

    return app