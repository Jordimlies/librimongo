from flask import Flask
from pymongo import MongoClient
from models.mariadb_models import db
from config.config import get_config

def reset_databases():
    """Reset both MariaDB and MongoDB databases."""
    app = Flask(__name__)
    app.config.from_object(get_config())
    
    # Initialize MariaDB
    db.init_app(app)
    
    # Initialize MongoDB
    mongo_client = MongoClient(app.config['MONGO_URI'])
    mongo_db = mongo_client[app.config['MONGO_DB_NAME']]
    
    with app.app_context():
        # Reset MariaDB
        print("Dropping all MariaDB tables...")
        db.drop_all()
        print("Creating all MariaDB tables...")
        db.create_all()
        
        # Reset MongoDB
        print("Dropping all MongoDB collections...")
        for collection_name in mongo_db.list_collection_names():
            mongo_db.drop_collection(collection_name)
        
        print("Databases reset successfully.")

if __name__ == "__main__":
    reset_databases()