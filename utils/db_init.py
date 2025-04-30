from flask import current_app
from pymongo import MongoClient, ASCENDING, TEXT
from sqlalchemy.exc import SQLAlchemyError
from models.mariadb_models import db, User, Book, Loan

def init_mariadb():
    """Initialize MariaDB database and create tables if they don't exist."""
    try:
        # Create all tables defined in the models
        db.create_all()
        current_app.logger.info("MariaDB tables created successfully")
        
        # Check if admin user exists, create if not
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@librimongo.com',
                first_name='Admin',
                last_name='User',
                is_admin=True
            )
            admin.set_password('admin')  # This should be changed in production
            db.session.add(admin)
            db.session.commit()
            current_app.logger.info("Admin user created successfully")
        
        return True
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error initializing MariaDB: {str(e)}")
        return False

def init_mongodb():
    """Initialize MongoDB database and create collections and indexes."""
    try:
        mongo_client = current_app.mongo_client
        db_name = current_app.config['MONGO_DB_NAME']
        db = mongo_client[db_name]
        
        # Create collections if they don't exist
        if 'reviews' not in db.list_collection_names():
            db.create_collection('reviews')
        if 'loan_history' not in db.list_collection_names():
            db.create_collection('loan_history')
        if 'book_texts' not in db.list_collection_names():
            db.create_collection('book_texts')
        
        # Create indexes for reviews collection
        reviews = db['reviews']
        reviews.create_index([('book_id', ASCENDING)])
        reviews.create_index([('user_id', ASCENDING)])
        reviews.create_index([('created_at', ASCENDING)])
        
        # Create indexes for loan_history collection
        loan_history = db['loan_history']
        loan_history.create_index([('loan_id', ASCENDING)])
        loan_history.create_index([('user_id', ASCENDING)])
        loan_history.create_index([('book_id', ASCENDING)])
        loan_history.create_index([('loan_date', ASCENDING)])
        
        # Create indexes for book_texts collection
        book_texts = db['book_texts']
        book_texts.create_index([('book_id', ASCENDING)], unique=True)
        book_texts.create_index([('content', TEXT)], default_language='english')
        
        current_app.logger.info("MongoDB collections and indexes created successfully")
        return True
    except Exception as e:
        current_app.logger.error(f"Error initializing MongoDB: {str(e)}")
        return False

def init_db():
    """Initialize both MariaDB and MongoDB databases."""
    mariadb_success = init_mariadb()
    mongodb_success = init_mongodb()
    
    if mariadb_success and mongodb_success:
        current_app.logger.info("Database initialization completed successfully")
        return True
    else:
        current_app.logger.error("Database initialization failed")
        return False