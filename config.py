from dotenv import load_dotenv
import os

load_dotenv()
db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")
db_host = os.getenv("DB_HOST")

class DevelopmentConfig:
    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://root:{db_pass}@localhost/{db_name}'
    DEBUG = True

class TestingConfig:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///testing.db'
    DEBUG = True
    TESTING = True
    # NullCache so a cached response from an earlier request can never be
    # served to a later one - SimpleCache made GET /customers/ return stale data
    CACHE_TYPE = 'NullCache'
    # The suite makes far more requests than the 20/hour default limit allows
    RATELIMIT_ENABLED = False

class ProductionConfig:
    pass