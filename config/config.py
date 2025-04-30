import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Base configuration class."""
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_development_only')
    DEBUG = False
    TESTING = False
    
    # MariaDB configuration
    MARIADB_USER = os.environ.get('MARIADB_USER', 'librimongo')
    MARIADB_PASSWORD = os.environ.get('MARIADB_PASSWORD', 'librimongo')
    MARIADB_HOST = os.environ.get('MARIADB_HOST', 'localhost')
    MARIADB_PORT = os.environ.get('MARIADB_PORT', '3306')
    MARIADB_DB = os.environ.get('MARIADB_DB', 'librimongo')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MongoDB configuration
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/librimongo')
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'librimongo')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    MONGO_URI = 'mongodb://localhost:27017/librimongo_test'
    MONGO_DB_NAME = 'librimongo_test'


class ProductionConfig(Config):
    """Production configuration."""
    # In production, all values should come from environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    MONGO_URI = os.environ.get('MONGO_URI')
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME')


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Get configuration based on environment
def get_config():
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env)