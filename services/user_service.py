"""
User service for LibriMongo application.
Handles user profile management, reading history, and preferences.
"""

from flask import current_app
from models.mariadb_models import User, Loan, Book, db
from models.mongodb_models import Review, LoanHistory
from services.recommendation_service import get_recommendations_for_user, track_user_interaction
from utils.helpers import log_activity
from datetime import datetime

def get_user_by_id(user_id):
    """
    Get a user by their ID.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        User: The user object, or None if not found
    """
    return User.query.get(user_id)

def get_user_profile(user_id):
    """
    Get a user's profile information.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        dict: The user's profile information
    """
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    # Get user's active loans
    active_loans = Loan.query.filter_by(user_id=user_id, is_returned=False).all()
    
    # Get user's reading history
    loan_history = list(LoanHistory.get_by_user(user_id))
    total_books_read = len({loan['book_id'] for loan in loan_history if loan.get('is_returned', False)})
    
    # Get user's reviews
    reviews = list(Review.find({'user_id': user_id}))
    
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_admin': user.is_admin,
        'created_at': user.created_at,
        'active_loans': active_loans,
        'total_books_read': total_books_read,
        'total_reviews': len(reviews)
    }

def get_user_reading_history(user_id, page=1, per_page=10, include_active=True):
    """
    Get a user's reading history.
    
    Args:
        user_id (int): The ID of the user
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        include_active (bool): Whether to include active loans
        
    Returns:
        tuple: (history_items, total_pages, total_items)
    """
    # Get loan history from MongoDB
    loan_history = list(LoanHistory.find(
        {'user_id': user_id},
        sort=[('loan_date', -1)]
    ))
    
    # Filter out active loans if needed
    if not include_active:
        loan_history = [loan for loan in loan_history if loan.get('is_returned', False)]
    
    # Get book details for each loan
    history_items = []
    for loan in loan_history:
        book = Book.query.get(loan['book_id'])
        if book:
            history_items.append({
                'loan': loan,
                'book': book
            })
    
    # Manual pagination
    total_items = len(history_items)
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    
    return history_items[start_idx:end_idx], total_pages, total_items

def get_user_reviews(user_id, page=1, per_page=10):
    """
    Get reviews written by a user.
    
    Args:
        user_id (int): The ID of the user
        page (int): Page number (1-indexed)
        per_page (int): Number of items per page
        
    Returns:
        tuple: (reviews_with_books, total_pages, total_items)
    """
    # Get reviews from MongoDB
    skip = (page - 1) * per_page
    reviews = list(Review.find(
        {'user_id': user_id},
        sort=[('created_at', -1)],
        skip=skip,
        limit=per_page
    ))
    
    # Get total count for pagination
    total_items = Review.get_collection().count_documents({'user_id': user_id})
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    # Get book details for each review
    reviews_with_books = []
    for review in reviews:
        book = Book.query.get(review['book_id'])
        if book:
            reviews_with_books.append({
                'review': review,
                'book': book
            })
    
    return reviews_with_books, total_pages, total_items

def get_user_recommendations(user_id, limit=10):
    """
    Get personalized book recommendations for a user.
    
    Args:
        user_id (int): The ID of the user
        limit (int): Maximum number of recommendations to return
        
    Returns:
        list: Recommended books
    """
    return get_recommendations_for_user(user_id, limit=limit)

def track_book_view(user_id, book_id):
    """
    Track when a user views a book.
    
    Args:
        user_id (int): The ID of the user
        book_id (int): The ID of the book
        
    Returns:
        bool: Whether the tracking was successful
    """
    return track_user_interaction(user_id, book_id, 'view')

def get_user_active_loans(user_id):
    loans = Loan.query.filter_by(user_id=user_id, is_returned=False).all()
    active_loans = []
    for loan in loans:
        book = Book.query.get(loan.book_id)
        if book:
            active_loans.append({
                'loan': loan,
                'book': book,
                'is_overdue': loan.is_overdue
            })

    return active_loans

def get_user_reading_preferences(user_id):
    """
    Get a user's reading preferences based on their history.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        dict: Reading preferences
    """
    # Get books the user has read
    loan_history = list(LoanHistory.get_by_user(user_id))
    book_ids = [loan['book_id'] for loan in loan_history]
    
    if not book_ids:
        return {
            'favorite_genres': [],
            'favorite_authors': [],
            'reading_frequency': 'New user'
        }
    
    # Get books
    books = Book.query.filter(Book.id.in_(book_ids)).all()
    
    # Calculate favorite genres
    genres = [book.genre for book in books if book.genre]
    genre_counts = {}
    for genre in genres:
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    favorite_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    favorite_genres = [genre for genre, count in favorite_genres]
    
    # Calculate favorite authors
    authors = [book.author for book in books if book.author]
    author_counts = {}
    for author in authors:
        author_counts[author] = author_counts.get(author, 0) + 1
    
    favorite_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    favorite_authors = [author for author, count in favorite_authors]
    
    # Calculate reading frequency
    if len(loan_history) >= 20:
        reading_frequency = 'Avid reader'
    elif len(loan_history) >= 10:
        reading_frequency = 'Regular reader'
    elif len(loan_history) >= 5:
        reading_frequency = 'Occasional reader'
    else:
        reading_frequency = 'New reader'
    
    return {
        'favorite_genres': favorite_genres,
        'favorite_authors': favorite_authors,
        'reading_frequency': reading_frequency
    }

def update_user_preferences(user_id, preferred_genres=None, preferred_authors=None):
    """
    Update a user's reading preferences.
    
    Args:
        user_id (int): The ID of the user
        preferred_genres (list, optional): Preferred genres
        preferred_authors (list, optional): Preferred authors
        
    Returns:
        bool: Whether the update was successful
    """
    # This would typically store preferences in a user_preferences collection in MongoDB
    # For now, we'll just log the activity
    details = {}
    if preferred_genres is not None:
        details['preferred_genres'] = preferred_genres
    if preferred_authors is not None:
        details['preferred_authors'] = preferred_authors
    
    log_activity('update_preferences', user_id=user_id, details=details)
    return True

def get_overdue_loans(user_id):
    """
    Get a user's overdue loans.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        list: Overdue loans with book details
    """
    now = datetime.utcnow()
    loans = Loan.query.filter(
        Loan.user_id == user_id,
        Loan.is_returned == False,
        Loan.due_date < now
    ).all()
    
    overdue_loans = []
    for loan in loans:
        book = Book.query.get(loan.book_id)
        if book:
            overdue_loans.append({
                'loan': loan,
                'book': book,
                'days_overdue': (now - loan.due_date).days
            })
    
    return overdue_loans

def get_user_statistics(user_id):
    """
    Get statistics about a user's reading habits.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        dict: User statistics
    """
    # Get loan history
    loan_history = list(LoanHistory.get_by_user(user_id))
    
    # Calculate statistics
    total_books_read = len({loan['book_id'] for loan in loan_history if loan.get('is_returned', False)})
    
    # Calculate average rating given
    reviews = list(Review.find({'user_id': user_id}))
    ratings = [review.get('rating', 0) for review in reviews if 'rating' in review]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Calculate books read per month (last 6 months)
    now = datetime.utcnow()
    months = {}
    for i in range(6):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        months[(year, month)] = 0
    
    for loan in loan_history:
        if 'loan_date' in loan:
            loan_date = loan['loan_date']
            if (loan_date.year, loan_date.month) in months:
                months[(loan_date.year, loan_date.month)] += 1
    
    monthly_reads = [{'year': year, 'month': month, 'count': count} 
                    for (year, month), count in months.items()]
    
    return {
        'total_books_read': total_books_read,
        'total_reviews': len(reviews),
        'average_rating': avg_rating,
        'monthly_reads': monthly_reads
    }