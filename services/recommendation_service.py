"""
Recommendation service for LibriMongo application.
Provides personalized book recommendations based on user preferences and reading history.
"""

from flask import current_app
from models.mariadb_models import Book, Loan, User, db
from models.mongodb_models import Review, LoanHistory
from sqlalchemy import func, desc
import numpy as np
from collections import Counter
from utils.helpers import log_activity

def get_user_genre_preferences(user_id):
    """
    Calculate a user's genre preferences based on their reading history and reviews.
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        dict: Genre preferences with scores
    """
    genre_scores = Counter()
    
    # Get books the user has borrowed
    loan_history = list(LoanHistory.get_by_user(user_id))
    book_ids = [loan['book_id'] for loan in loan_history]
    
    if book_ids:
        # Get genres of borrowed books
        borrowed_books = Book.query.filter(Book.id.in_(book_ids)).all()
        for book in borrowed_books:
            if book.genre:
                genre_scores[book.genre] += 1
    
    # Get books the user has reviewed positively (rating >= 4)
    user_reviews = list(Review.find({'user_id': user_id}))
    positive_review_book_ids = [review['book_id'] for review in user_reviews if review.get('rating', 0) >= 4]
    
    if positive_review_book_ids:
        # Get genres of positively reviewed books
        reviewed_books = Book.query.filter(Book.id.in_(positive_review_book_ids)).all()
        for book in reviewed_books:
            if book.genre:
                genre_scores[book.genre] += 2  # Higher weight for positive reviews
    
    return dict(genre_scores)

def get_similar_users(user_id, min_similarity=0.1, max_users=10):
    """
    Find users with similar reading preferences.
    
    Args:
        user_id (int): The ID of the user
        min_similarity (float): Minimum similarity score (0-1)
        max_users (int): Maximum number of similar users to return
        
    Returns:
        list: Similar users with similarity scores
    """
    # Get target user's genre preferences
    target_preferences = get_user_genre_preferences(user_id)
    
    if not target_preferences:
        return []
    
    # Get all users
    users = User.query.filter(User.id != user_id).all()
    similar_users = []
    
    for user in users:
        # Get user's genre preferences
        user_preferences = get_user_genre_preferences(user.id)
        
        if not user_preferences:
            continue
        
        # Calculate similarity score using cosine similarity
        similarity = calculate_similarity(target_preferences, user_preferences)
        
        if similarity >= min_similarity:
            similar_users.append({
                'user_id': user.id,
                'similarity': similarity
            })
    
    # Sort by similarity (descending) and limit
    similar_users.sort(key=lambda x: x['similarity'], reverse=True)
    return similar_users[:max_users]

def calculate_similarity(prefs1, prefs2):
    """
    Calculate similarity between two preference dictionaries using cosine similarity.
    
    Args:
        prefs1 (dict): First preference dictionary
        prefs2 (dict): Second preference dictionary
        
    Returns:
        float: Similarity score (0-1)
    """
    # Get all keys
    all_keys = set(prefs1.keys()) | set(prefs2.keys())
    
    # Create vectors
    vec1 = np.array([prefs1.get(key, 0) for key in all_keys])
    vec2 = np.array([prefs2.get(key, 0) for key in all_keys])
    
    # Calculate cosine similarity
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    return dot_product / (norm1 * norm2)

def get_book_similarity(book_id1, book_id2):
    """
    Calculate similarity between two books based on genre, author, and user interactions.
    
    Args:
        book_id1 (int): ID of the first book
        book_id2 (int): ID of the second book
        
    Returns:
        float: Similarity score (0-1)
    """
    book1 = Book.query.get(book_id1)
    book2 = Book.query.get(book_id2)
    
    if not book1 or not book2:
        return 0
    
    similarity = 0
    
    # Genre similarity (0.4 weight)
    if book1.genre and book2.genre and book1.genre == book2.genre:
        similarity += 0.4
    
    # Author similarity (0.3 weight)
    if book1.author and book2.author and book1.author == book2.author:
        similarity += 0.3
    
    # User interaction similarity (0.3 weight)
    # Find users who have interacted with both books
    users_book1 = set(loan['user_id'] for loan in LoanHistory.get_by_book(book_id1))
    users_book2 = set(loan['user_id'] for loan in LoanHistory.get_by_book(book_id2))
    
    common_users = users_book1.intersection(users_book2)
    
    # Calculate interaction similarity based on common users
    if users_book1 and users_book2:
        interaction_similarity = len(common_users) / (len(users_book1) + len(users_book2) - len(common_users))
        similarity += 0.3 * interaction_similarity
    
    return similarity

def get_similar_books(book_id, min_similarity=0.3, max_books=10):
    """
    Find books similar to a given book.
    
    Args:
        book_id (int): The ID of the book
        min_similarity (float): Minimum similarity score (0-1)
        max_books (int): Maximum number of similar books to return
        
    Returns:
        list: Similar books with similarity scores
    """
    book = Book.query.get(book_id)
    if not book:
        return []
    
    # Get all other books
    other_books = Book.query.filter(Book.id != book_id).all()
    similar_books = []
    
    for other_book in other_books:
        similarity = get_book_similarity(book_id, other_book.id)
        
        if similarity >= min_similarity:
            similar_books.append({
                'book': other_book,
                'similarity': similarity
            })
    
    # Sort by similarity (descending) and limit
    similar_books.sort(key=lambda x: x['similarity'], reverse=True)
    return similar_books[:max_books]

def get_popular_books(limit=10, days=30):
    """
    Get popular books based on loan frequency and ratings.
    
    Args:
        limit (int): Maximum number of books to return
        days (int): Number of days to consider for recent popularity
        
    Returns:
        list: Popular books
    """
    # Get books with most loans
    popular_by_loans = db.session.query(
        Book, func.count(Loan.id).label('loan_count')
    ).join(Loan).group_by(Book.id).order_by(desc('loan_count')).limit(limit).all()
    
    # Get books with highest ratings
    books_with_ratings = []
    for book in Book.query.all():
        avg_rating = Review.get_average_rating(book.id)
        if avg_rating:
            books_with_ratings.append((book, avg_rating))
    
    # Sort by rating (descending) and limit
    popular_by_ratings = sorted(books_with_ratings, key=lambda x: x[1], reverse=True)[:limit]
    
    # Combine and deduplicate
    popular_books = []
    seen_ids = set()
    
    # Add books popular by loans
    for book, _ in popular_by_loans:
        if book.id not in seen_ids:
            popular_books.append(book)
            seen_ids.add(book.id)
    
    # Add books popular by ratings
    for book, _ in popular_by_ratings:
        if book.id not in seen_ids and len(popular_books) < limit:
            popular_books.append(book)
            seen_ids.add(book.id)
    
    return popular_books[:limit]

def track_user_interaction(user_id, book_id, interaction_type, details=None):
    """
    Track a user's interaction with a book for recommendation purposes.
    
    Args:
        user_id (int): The ID of the user
        book_id (int): The ID of the book
        interaction_type (str): Type of interaction (view, loan, return, review)
        details (dict, optional): Additional details about the interaction
        
    Returns:
        bool: Whether the tracking was successful
    """
    try:
        log_activity(f'book_{interaction_type}', user_id=user_id, book_id=book_id, details=details)
        return True
    except Exception as e:
        current_app.logger.error(f"Error tracking user interaction: {str(e)}")
        return False

def get_recommendations_for_user(user_id, limit=10, exclude_read=True):
    """
    Get personalized book recommendations for a user.
    
    Args:
        user_id (int): The ID of the user
        limit (int): Maximum number of recommendations to return
        exclude_read (bool): Whether to exclude books the user has already read
        
    Returns:
        list: Recommended books
    """
    recommendations = []
    
    # Get user's genre preferences
    user_preferences = get_user_genre_preferences(user_id)
    
    # Get books the user has already read
    read_book_ids = set()
    if exclude_read:
        loan_history = list(LoanHistory.get_by_user(user_id))
        read_book_ids = {loan['book_id'] for loan in loan_history}
    
    # Strategy 1: Recommend based on genre preferences
    if user_preferences:
        # Get top genres
        top_genres = [genre for genre, _ in Counter(user_preferences).most_common(3)]
        
        for genre in top_genres:
            # Get books in this genre that the user hasn't read
            genre_books = Book.query.filter(
                Book.genre == genre,
                ~Book.id.in_(read_book_ids) if read_book_ids else True
            ).order_by(func.random()).limit(5).all()
            
            for book in genre_books:
                if book not in recommendations:
                    recommendations.append(book)
    
    # Strategy 2: Recommend based on similar users
    similar_users = get_similar_users(user_id)
    
    for similar_user in similar_users:
        # Get books that similar users have rated highly
        similar_user_reviews = list(Review.find({
            'user_id': similar_user['user_id'],
            'rating': {'$gte': 4}
        }))
        
        for review in similar_user_reviews:
            book = Book.query.get(review['book_id'])
            if book and book.id not in read_book_ids and book not in recommendations:
                recommendations.append(book)
    
    # Strategy 3: Add some popular books if we don't have enough recommendations
    if len(recommendations) < limit:
        popular_books = get_popular_books(limit=limit)
        
        for book in popular_books:
            if book.id not in read_book_ids and book not in recommendations:
                recommendations.append(book)
    
    # Limit the number of recommendations
    return recommendations[:limit]

def get_recommendations_by_book(book_id, limit=5):
    """
    Get book recommendations based on a specific book.
    
    Args:
        book_id (int): The ID of the book
        limit (int): Maximum number of recommendations to return
        
    Returns:
        list: Recommended books
    """
    similar_books = get_similar_books(book_id)
    return [item['book'] for item in similar_books[:limit]]