#!/usr/bin/env python3
"""
Importador.py - Data migration script for Librimongo

This script imports books data from a Libritxt 1.0 file-based storage
to the new MariaDB and MongoDB databases used by Librimongo.
"""

import os
import sys
import logging
import shutil
from datetime import datetime
from flask import Flask
from models.mariadb_models import db, Book
from models.mongodb_models import BookText
from config.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("import.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("importador")

def create_app():
    """Create a Flask app instance for database operations."""
    app = Flask(__name__)
    app.config.from_object(get_config())
    db.init_app(app)
    
    # Initialize MongoDB connection
    from pymongo import MongoClient
    mongo_client = MongoClient(app.config['MONGO_URI'])
    app.mongo_client = mongo_client
    
    return app

def import_books(app, source_dir, covers_dest, resume=False):
    """Import books from books.txt file and copy cover images."""
    books_file = os.path.join(source_dir, 'books.txt')
    covers_source = os.path.join(source_dir, 'covers')
    
    if not os.path.exists(books_file):
        logger.error(f"Books file not found: {books_file}")
        return False
    
    if not os.path.exists(covers_source):
        logger.warning(f"Covers directory not found: {covers_source}")
    
    logger.info(f"Importing books from {books_file}")
    
    with app.app_context():
        # Check if we should resume or start fresh
        if resume and Book.query.count() > 0:
            logger.info(f"Resuming book import from book ID {Book.query.order_by(Book.id.desc()).first().id}")
            imported_ids = {book.isbn for book in Book.query.all()}
        else:
            imported_ids = set()
        
        # Read books file and import books
        with open(books_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 7:
                    book_id, title, author, genres, publisher, year, cover_image = parts[:7]
                    description = parts[7] if len(parts) > 7 else ""
                    
                    # Skip if already imported
                    if book_id in imported_ids:
                        logger.debug(f"Book {book_id} already imported, skipping")
                        continue
                    
                    # Copy cover image if it exists
                    cover_path = None
                    source_cover = os.path.join(covers_source, cover_image)
                    if os.path.exists(source_cover):
                        dest_cover = os.path.join(covers_dest, cover_image)
                        shutil.copy2(source_cover, dest_cover)
                        cover_path = f"covers/{cover_image}"
                        logger.debug(f"Copied cover image: {cover_image}")
                    else:
                        logger.warning(f"Cover image not found: {source_cover}")
                    
                    # Create book record
                    try:
                        year_int = int(year) if year.isdigit() else None
                    except (ValueError, TypeError):
                        year_int = None
                    
                    book = Book(
                        isbn=book_id,
                        title=title,
                        author=author,
                        year=year_int,
                        genre=genres,
                        publisher=publisher,
                        description=description,
                        cover_image_path=cover_path,
                        available_copies=1,
                        total_copies=1
                    )
                    db.session.add(book)
                    
                    # Store book text in MongoDB
                    mongo_client = app.mongo_client
                    BookText.create(book_id, description)
                    
                    logger.info(f"Added book: {title} by {author}")
                    
                    # Commit periodically to avoid large transactions
                    if Book.query.count() % 50 == 0:
                        db.session.commit()
                        logger.info(f"Committed batch of books, total: {Book.query.count()}")
            
            # Final commit
            db.session.commit()
            logger.info(f"Imported {Book.query.count()} books successfully")
    
    return True

def main():
    """Main function to run the import process."""
    if len(sys.argv) < 3:
        logger.error("Please provide the source directory and covers destination.")
        sys.exit(1)

    source_dir = sys.argv[1]
    covers_dest = sys.argv[2]
    
    # Create Flask app
    app = create_app()
    
    # Import books
    success = import_books(app, source_dir, covers_dest)
    
    if success:
        logger.info("Import completed successfully")
    else:
        logger.error("Import failed")
        sys.exit(1)

if __name__ == "__main__":
    main()