"""
Book service for LibriMongo application.
Handles book management, search, filtering, and lending operations.
"""

from datetime import datetime
from flask import current_app
from models.mariadb_models import Book, Loan, db
from models.mongodb_models import Review, BookText, LoanHistory
from utils.helpers import calculate_due_date, log_activity

def get_all_books(page=1, per_page=12, sort_by=None, sort_order='asc', filters=None):
    """
    Get all books with pagination, sorting, and filtering.
    
    Args:
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        sort_by (str): Field to sort by (title, author, year)
        sort_order (str): Sort order ('asc' or 'desc')
        filters (dict): Filters to apply (author, genre, language, etc.)
        
    Returns:
        tuple: (books, total_pages, total_items)
    """
    query = Book.query
    
    # Apply filters
    if filters:
        if 'title' in filters and filters['title']:
            query = query.filter(Book.title.ilike(f"%{filters['title']}%"))
        if 'author' in filters and filters['author']:
            query = query.filter(Book.author.ilike(f"%{filters['author']}%"))
        if 'genre' in filters and filters['genre']:
            query = query.filter(Book.genre == filters['genre'])
        if 'language' in filters and filters['language']:
            query = query.filter(Book.language == filters['language'])
        if 'year_from' in filters and filters['year_from']:
            query = query.filter(Book.year >= filters['year_from'])
        if 'year_to' in filters and filters['year_to']:
            query = query.filter(Book.year <= filters['year_to'])
        if 'available' in filters and filters['available']:
            query = query.filter(Book.available_copies > 0)
    
    # Apply sorting
    if sort_by == 'title':
        if sort_order == 'desc':
            query = query.order_by(Book.title.desc())
        else:
            query = query.order_by(Book.title)
    elif sort_by == 'author':
        if sort_order == 'desc':
            query = query.order_by(Book.author.desc())
        else:
            query = query.order_by(Book.author)
    elif sort_by == 'year':
        if sort_order == 'desc':
            query = query.order_by(Book.year.desc())
        else:
            query = query.order_by(Book.year)
    else:
        # Default sorting
        query = query.order_by(Book.title)
    
    # Execute query with pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return pagination.items, pagination.pages, pagination.total

def get_book_by_id(book_id):
    """
    Get a book by its ID.
    
    Args:
        book_id (int): The ID of the book
        
    Returns:
        Book: The book object, or None if not found
    """
    return Book.query.get(book_id)

def get_book_by_isbn(isbn):
    """
    Get a book by its ISBN.
    
    Args:
        isbn (str): The ISBN of the book
        
    Returns:
        Book: The book object, or None if not found
    """
    return Book.query.filter_by(isbn=isbn).first()

def search_books(query, page=1, per_page=12):
    """
    Search for books by title, author, or description.
    
    Args:
        query (str): The search query
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        
    Returns:
        tuple: (books, total_pages, total_items)
    """
    search_query = f"%{query}%"
    book_query = Book.query.filter(
        (Book.title.ilike(search_query)) |
        (Book.author.ilike(search_query)) |
        (Book.description.ilike(search_query))
    ).order_by(Book.title)
    
    pagination = book_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return pagination.items, pagination.pages, pagination.total

def get_book_content(book_id):
    """Retrieve the content of a book from MongoDB using its ID."""
    content = BookText.get_by_book(book_id)
    print(f"Book ID: {book_id}, Content: {content}")
    return content

def get_book_reviews(book_id, limit=None):
    """
    Get reviews for a book.
    
    Args:
        book_id (int): The ID of the book
        limit (int, optional): Maximum number of reviews to return
        
    Returns:
        list: The reviews for the book
    """
    return list(Review.get_by_book(book_id, limit=limit))

def get_average_rating(book_id):
    """
    Get the average rating for a book.
    
    Args:
        book_id (int): The ID of the book
        
    Returns:
        float: The average rating, or None if no ratings
    """
    return Review.get_average_rating(book_id)

def add_review(book_id, user_id, rating, text=None):
    """
    Add a review for a book.
    
    Args:
        book_id (int): The ID of the book
        user_id (int): The ID of the user
        rating (int): The rating (1-5)
        text (str, optional): The review text
        
    Returns:
        str: The ID of the new review
    """
    # Validate rating
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5")
    
    # Check if book exists
    book = get_book_by_id(book_id)
    if not book:
        raise ValueError("Book not found")
    
    # Add review
    review_id = Review.create(book_id, user_id, rating, text)
    log_activity('add_review', user_id=user_id, book_id=book_id, details={'rating': rating})
    
    return review_id

def update_review(review_id, user_id, rating=None, text=None):
    """
    Update a review.
    
    Args:
        review_id (str): The ID of the review
        user_id (int): The ID of the user
        rating (int, optional): The new rating
        text (str, optional): The new review text
        
    Returns:
        bool: Whether the update was successful
    """
    # Get the review
    review = Review.find_one({'_id': review_id, 'user_id': user_id})
    if not review:
        return False
    
    # Update fields
    update = {'$set': {}}
    if rating is not None:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        update['$set']['rating'] = rating
    
    if text is not None:
        update['$set']['text'] = text
    
    # Update the review
    result = Review.update_one({'_id': review_id, 'user_id': user_id}, update)
    log_activity('update_review', user_id=user_id, book_id=review['book_id'], details={'review_id': str(review_id)})
    
    return result.modified_count > 0

def delete_review(review_id, user_id):
    """
    Delete a review.
    
    Args:
        review_id (str): The ID of the review
        user_id (int): The ID of the user
        
    Returns:
        bool: Whether the deletion was successful
    """
    # Get the review
    review = Review.find_one({'_id': review_id, 'user_id': user_id})
    if not review:
        return False
    
    # Delete the review
    result = Review.delete_one({'_id': review_id, 'user_id': user_id})
    log_activity('delete_review', user_id=user_id, book_id=review['book_id'], details={'review_id': str(review_id)})
    
    return result.deleted_count > 0

def lend_book(book_id, user_id, days=14):
    """
    Lend a book to a user.
    
    Args:
        book_id (int): The ID of the book
        user_id (int): The ID of the user
        days (int, optional): The number of days to lend the book for
        
    Returns:
        tuple: (success, loan_or_error_message)
    """
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found"
    
    if book.available_copies <= 0:
        return False, "No copies available for lending"
    
    # Check if user already has this book
    existing_loan = Loan.query.filter_by(
        user_id=user_id,
        book_id=book_id,
        is_returned=False
    ).first()
    
    if existing_loan:
        return False, "You already have this book on loan"
    
    # Create loan
    due_date = calculate_due_date(days)
    loan = Loan(
        user_id=user_id,
        book_id=book_id,
        loan_date=datetime.utcnow(),
        due_date=due_date,
        is_returned=False
    )
    
    # Update book availability
    book.available_copies -= 1
    
    try:
        db.session.add(loan)
        db.session.commit()
        
        # Create loan history entry
        LoanHistory.create_from_loan(loan)
        
        log_activity('lend_book', user_id=user_id, book_id=book_id, details={'loan_id': loan.id})
        return True, loan
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error lending book: {str(e)}")
        return False, "Error lending book"

def return_book(loan_id, user_id):
    """
    Return a book.
    
    Args:
        loan_id (int): The ID of the loan
        user_id (int): The ID of the user
        
    Returns:
        tuple: (success, message)
    """
    # Check if loan exists and belongs to user
    loan = Loan.query.filter_by(id=loan_id, user_id=user_id, is_returned=False).first()
    if not loan:
        return False, "Loan not found or already returned"
    
    # Update loan
    loan.return_date = datetime.utcnow()
    loan.is_returned = True
    
    # Update book availability
    book = get_book_by_id(loan.book_id)
    if book:
        book.available_copies += 1
    
    try:
        db.session.commit()
        
        # Update loan history
        LoanHistory.update_one(
            {'loan_id': loan.id},
            {'$set': {'return_date': loan.return_date, 'is_returned': True}}
        )
        
        log_activity('return_book', user_id=user_id, book_id=loan.book_id, details={'loan_id': loan.id})
        return True, "Book returned successfully"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error returning book: {str(e)}")
        return False, "Error returning book"

def get_user_loans(user_id, include_returned=False, page=1, per_page=10):
    """
    Get loans for a user.
    
    Args:
        user_id (int): The ID of the user
        include_returned (bool): Whether to include returned loans
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        
    Returns:
        tuple: (loans, total_pages, total_items)
    """
    query = Loan.query.filter_by(user_id=user_id)
    
    if not include_returned:
        query = query.filter_by(is_returned=False)
    
    query = query.order_by(Loan.loan_date.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return pagination.items, pagination.pages, pagination.total

def get_book_loans(book_id, include_returned=False, page=1, per_page=10):
    """
    Get loans for a book.
    
    Args:
        book_id (int): The ID of the book
        include_returned (bool): Whether to include returned loans
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        
    Returns:
        tuple: (loans, total_pages, total_items)
    """
    query = Loan.query.filter_by(book_id=book_id)
    
    if not include_returned:
        query = query.filter_by(is_returned=False)
    
    query = query.order_by(Loan.loan_date.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return pagination.items, pagination.pages, pagination.total

def get_genres():
    """
    Get all unique book genres.
    
    Returns:
        list: List of unique genres
    """
    return [genre[0] for genre in db.session.query(Book.genre).distinct().all() if genre[0]]

def get_languages():
    """
    Get all unique book languages.
    
    Returns:
        list: List of unique languages
    """
    return [lang[0] for lang in db.session.query(Book.language).distinct().all() if lang[0]]

def create_book(title, author, year=None, isbn=None, language=None, genre=None, 
                publisher=None, description=None, cover_image_path=None, 
                available_copies=1, total_copies=1, content=None, content_format='text'):
    """
    Create a new book.
    
    Args:
        title (str): The title of the book
        author (str): The author of the book
        year (int, optional): The publication year
        isbn (str, optional): The ISBN
        language (str, optional): The language
        genre (str, optional): The genre
        publisher (str, optional): The publisher
        description (str, optional): The description
        cover_image_path (str, optional): Path to the cover image
        available_copies (int, optional): Number of available copies
        total_copies (int, optional): Total number of copies
        content (str, optional): The book content
        content_format (str, optional): The format of the content
        
    Returns:
        tuple: (success, book_or_error_message)
    """
    # Check if ISBN already exists
    if isbn and Book.query.filter_by(isbn=isbn).first():
        return False, "ISBN already exists"
    
    # Create book
    book = Book(
        title=title,
        author=author,
        year=year,
        isbn=isbn,
        language=language,
        genre=genre,
        publisher=publisher,
        description=description,
        cover_image_path=cover_image_path,
        available_copies=available_copies,
        total_copies=total_copies
    )
    
    try:
        db.session.add(book)
        db.session.commit()
        
        # Add content if provided
        if content:
            BookText.create(book.id, content, format=content_format)
        
        log_activity('create_book', book_id=book.id)
        return True, book
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating book: {str(e)}")
        return False, "Error creating book"

def update_book(book_id, title=None, author=None, year=None, isbn=None, language=None, 
                genre=None, publisher=None, description=None, cover_image_path=None, 
                available_copies=None, total_copies=None):
    """
    Update a book.
    
    Args:
        book_id (int): The ID of the book
        title (str, optional): The new title
        author (str, optional): The new author
        year (int, optional): The new publication year
        isbn (str, optional): The new ISBN
        language (str, optional): The new language
        genre (str, optional): The new genre
        publisher (str, optional): The new publisher
        description (str, optional): The new description
        cover_image_path (str, optional): New path to the cover image
        available_copies (int, optional): New number of available copies
        total_copies (int, optional): New total number of copies
        
    Returns:
        tuple: (success, book_or_error_message)
    """
    # Get book
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found"
    
    # Check if ISBN already exists
    if isbn and isbn != book.isbn and Book.query.filter_by(isbn=isbn).first():
        return False, "ISBN already exists"
    
    # Update fields
    if title is not None:
        book.title = title
    if author is not None:
        book.author = author
    if year is not None:
        book.year = year
    if isbn is not None:
        book.isbn = isbn
    if language is not None:
        book.language = language
    if genre is not None:
        book.genre = genre
    if publisher is not None:
        book.publisher = publisher
    if description is not None:
        book.description = description
    if cover_image_path is not None:
        book.cover_image_path = cover_image_path
    if available_copies is not None:
        book.available_copies = available_copies
    if total_copies is not None:
        book.total_copies = total_copies
    
    try:
        db.session.commit()
        log_activity('update_book', book_id=book.id)
        return True, book
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating book: {str(e)}")
        return False, "Error updating book"

def update_book_content(book_id, content, content_format='text'):
    """
    Update the content of a book.
    
    Args:
        book_id (int): The ID of the book
        content (str): The new content
        content_format (str, optional): The format of the content
        
    Returns:
        bool: Whether the update was successful
    """
    # Check if book exists
    book = get_book_by_id(book_id)
    if not book:
        return False
    
    # Check if content exists
    existing_content = BookText.get_by_book(book_id)
    
    if existing_content:
        # Update existing content
        result = BookText.update_one(
            {'book_id': book_id},
            {'$set': {'content': content, 'format': content_format}}
        )
        success = result.modified_count > 0
    else:
        # Create new content
        BookText.create(book_id, content, format=content_format)
        success = True
    
    if success:
        log_activity('update_book_content', book_id=book_id)
    
    return success

def delete_book(book_id):
    """
    Delete a book.
    
    Args:
        book_id (int): The ID of the book
        
    Returns:
        tuple: (success, message)
    """
    # Get book
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found"
    
    # Check if book has active loans
    active_loans = Loan.query.filter_by(book_id=book_id, is_returned=False).count()
    if active_loans > 0:
        return False, "Cannot delete book with active loans"
    
    try:
        # Delete book content
        BookText.delete_one({'book_id': book_id})
        
        # Delete book
        db.session.delete(book)
        db.session.commit()
        
        log_activity('delete_book', book_id=book_id)
        return True, "Book deleted successfully"
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting book: {str(e)}")
        return False, "Error deleting book"