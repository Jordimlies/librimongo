import os
import sys
from flask import Flask
from pymongo import MongoClient
from sqlalchemy.exc import SQLAlchemyError
from models.mariadb_models import db, User, Book, Loan
from config.config import get_config

def test_mariadb_connection():
    """Test connection to MariaDB and model creation."""
    print("Testing MariaDB connection...")
    
    try:
        # Create a test user
        test_user = User(
            username='test_user',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        test_user.set_password('password123')
        
        # Add to session and commit
        db.session.add(test_user)
        db.session.commit()
        print(f"Created test user: {test_user.username} (ID: {test_user.id})")
        
        # Create a test book
        test_book = Book(
            title='Test Book',
            author='Test Author',
            year=2023,
            isbn='1234567890123',
            language='English',
            genre='Test',
            publisher='Test Publisher',
            description='This is a test book',
            available_copies=5,
            total_copies=5
        )
        
        # Add to session and commit
        db.session.add(test_book)
        db.session.commit()
        print(f"Created test book: {test_book.title} (ID: {test_book.id})")
        
        # Create a test loan
        from datetime import datetime, timedelta
        test_loan = Loan(
            user_id=test_user.id,
            book_id=test_book.id,
            loan_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=14)
        )
        
        # Add to session and commit
        db.session.add(test_loan)
        db.session.commit()
        print(f"Created test loan: {test_loan.id}")
        
        # Clean up
        db.session.delete(test_loan)
        db.session.delete(test_book)
        db.session.delete(test_user)
        db.session.commit()
        print("Test data cleaned up successfully")
        
        return True
    except SQLAlchemyError as e:
        print(f"MariaDB test failed: {str(e)}")
        return False

def test_mongodb_connection(app):
    """Test connection to MongoDB and collection operations."""
    print("Testing MongoDB connection...")
    
    try:
        mongo_client = app.mongo_client
        db_name = app.config['MONGO_DB_NAME']
        db = mongo_client[db_name]
        
        # Test reviews collection
        reviews = db['reviews']
        test_review = {
            'book_id': 1,
            'user_id': 1,
            'rating': 5,
            'text': 'This is a test review'
        }
        review_id = reviews.insert_one(test_review).inserted_id
        print(f"Created test review with ID: {review_id}")
        
        # Test book_texts collection
        book_texts = db['book_texts']
        test_book_text = {
            'book_id': 1,
            'content': 'This is test content for a book',
            'format': 'text'
        }
        book_text_id = book_texts.insert_one(test_book_text).inserted_id
        print(f"Created test book text with ID: {book_text_id}")
        
        # Test loan_history collection
        loan_history = db['loan_history']
        test_loan_history = {
            'loan_id': 1,
            'user_id': 1,
            'book_id': 1,
            'loan_date': datetime.utcnow(),
            'due_date': datetime.utcnow() + timedelta(days=14),
            'is_returned': False
        }
        loan_history_id = loan_history.insert_one(test_loan_history).inserted_id
        print(f"Created test loan history with ID: {loan_history_id}")
        
        # Clean up
        reviews.delete_one({'_id': review_id})
        book_texts.delete_one({'_id': book_text_id})
        loan_history.delete_one({'_id': loan_history_id})
        print("Test data cleaned up successfully")
        
        return True
    except Exception as e:
        print(f"MongoDB test failed: {str(e)}")
        return False

def main():
    """Main function to run the tests."""
    # Create a Flask app for testing
    app = Flask(__name__)
    app.config.from_object(get_config())
    
    # Initialize MariaDB with SQLAlchemy
    db.init_app(app)
    
    # Initialize MongoDB connection
    mongo_client = MongoClient(app.config['MONGO_URI'])
    app.mongo_client = mongo_client
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Test MariaDB connection
        mariadb_success = test_mariadb_connection()
        
        # Test MongoDB connection
        mongodb_success = test_mongodb_connection(app)
        
        if mariadb_success and mongodb_success:
            print("All database tests passed successfully!")
            return 0
        else:
            print("Some database tests failed.")
            return 1

if __name__ == '__main__':
    from datetime import datetime
    sys.exit(main())