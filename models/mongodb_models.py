from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from flask import current_app
import logging

# Configurar el logger
logger = logging.getLogger("mongodb_models")
logger.setLevel(logging.INFO)  # Cambia a DEBUG si necesitas más detalles

class MongoBase:
    """Base class for MongoDB models."""
    
    @classmethod
    def get_collection(cls):
        """Get the MongoDB collection for this model."""
        mongo_client = current_app.mongo_client
        db = mongo_client[current_app.config['MONGO_DB_NAME']]
        return db[cls.collection_name]
    
    @classmethod
    def find_one(cls, query):
        """Find a single document matching the query."""
        return cls.get_collection().find_one(query)
    
    @classmethod
    def find(cls, query=None, sort=None, limit=None, skip=None):
        """Find documents matching the query."""
        query = query or {}
        cursor = cls.get_collection().find(query)
        
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
            
        return cursor
    
    @classmethod
    def insert_one(cls, document):
        """Insert a document into the collection."""
        if '_id' not in document:
            document['created_at'] = datetime.utcnow()
            document['updated_at'] = datetime.utcnow()
        result = cls.get_collection().insert_one(document)
        return result.inserted_id
    
    @classmethod
    def update_one(cls, query, update):
        """Update a document in the collection."""
        update['$set'] = update.get('$set', {})
        update['$set']['updated_at'] = datetime.utcnow()
        return cls.get_collection().update_one(query, update)
    
    @classmethod
    def delete_one(cls, query):
        """Delete a document from the collection."""
        return cls.get_collection().delete_one(query)


class Review(MongoBase):
    """Model for book reviews."""
    collection_name = 'reviews'
    
    @classmethod
    def create(cls, book_id, user_id, rating, text=None):
        """Create a new review."""
        review = {
            'book_id': book_id,
            'user_id': user_id,
            'rating': rating,
            'text': text,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        return cls.insert_one(review)
    
    @classmethod
    def get_by_book(cls, book_id, limit=None):
        """Get reviews for a specific book."""
        return cls.find({'book_id': book_id}, sort=[('created_at', -1)], limit=limit)
    
    @classmethod
    def get_by_user(cls, user_id, limit=None):
        """Get reviews by a specific user."""
        return cls.find({'user_id': user_id}, sort=[('created_at', -1)], limit=limit)
    
    @classmethod
    def get_average_rating(cls, book_id):
        """Get the average rating for a book."""
        pipeline = [
            {'$match': {'book_id': book_id}},
            {'$group': {'_id': '$book_id', 'avg_rating': {'$avg': '$rating'}}}
        ]
        result = list(cls.get_collection().aggregate(pipeline))
        if result:
            return result[0]['avg_rating']
        return None


class LoanHistory(MongoBase):
    """Model for tracking detailed loan history."""
    collection_name = 'loan_history'
    
    @classmethod
    def create_from_loan(cls, loan):
        """Create a loan history entry from a loan object."""
        history = {
            'loan_id': loan.id,
            'user_id': loan.user_id,
            'book_id': loan.book_id,
            'loan_date': loan.loan_date,
            'due_date': loan.due_date,
            'return_date': loan.return_date,
            'is_returned': loan.is_returned,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        return cls.insert_one(history)
    
    @classmethod
    def get_by_user(cls, user_id, limit=None):
        """Get loan history for a specific user."""
        return cls.find({'user_id': user_id}, sort=[('loan_date', -1)], limit=limit)
    
    @classmethod
    def get_by_book(cls, book_id, limit=None):
        """Get loan history for a specific book."""
        return cls.find({'book_id': book_id}, sort=[('loan_date', -1)], limit=limit)


class BookText(MongoBase):
    """Model for storing book text content."""
    collection_name = 'book_texts'
    
    @classmethod
    def create(cls, book_id, content, format='text'):
        """Create a new book text entry."""
        # Verificar si el documento ya existe
        existing_document = cls.get_by_book(book_id)
        if existing_document:
            logger.warning(f"Book text with book_id {book_id} already exists, skipping insertion")
            return existing_document  # Retorna el documento existente en lugar de insertar uno nuevo
        
        # Crear un nuevo documento
        book_text = {
            'book_id': book_id,
            'content': content,
            'format': format,  # text, html, markdown, etc.
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        return cls.insert_one(book_text)
    
    @classmethod
    def get_by_book(cls, book_id):
        """Get text content for a specific book."""
        return cls.find_one({'book_id': book_id})
    
    @classmethod
    def search_text(cls, query, limit=10):
        """Search for books containing specific text."""
        # This requires a text index on the content field
        return cls.find(
            {'$text': {'$search': query}},
            sort=[('score', {'$meta': 'textScore'})],
            limit=limit
        )