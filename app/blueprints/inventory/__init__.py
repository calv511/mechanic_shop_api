from flask import Blueprint

inventory_bp = Blueprint("inventory_bp", __name__)

# Imported last so the routes can attach to the blueprint above
from . import routes
