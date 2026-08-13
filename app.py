from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST")

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{db_pass}@localhost/{db_name}'

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class= Base)

db.init_app(app)

app.run()