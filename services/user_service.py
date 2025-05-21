"""
Servei d'usuari per a l'aplicació LibriMongo.
Gestiona el perfil d'usuari, l'historial de lectura i les preferències.
"""

from flask import current_app
from models.mariadb_models import User, Loan, Book, db
from models.mongodb_models import Review, LoanHistory, UserPreferences
from services.recommendation_service import get_recommendations_for_user, track_user_interaction
from utils.helpers import log_activity
from datetime import datetime, timezone
from dateutil.parser import parse

def get_user_by_id(user_id):
    """
    Obté un usuari pel seu ID.
    
    Args:
        user_id (int): L'ID de l'usuari
        
    Returns:
        User: L'objecte usuari, o None si no es troba
    """
    return User.query.get(user_id)

def get_user_profile(user_id):
    """
    Obté la informació del perfil d'un usuari.
    
    Args:
        user_id (int): L'ID de l'usuari
        
    Returns:
        dict: La informació del perfil de l'usuari
    """
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    # Obté els préstecs actius de l'usuari
    active_loans = Loan.query.filter_by(user_id=user_id, is_returned=False).all()
    
    # Obté l'historial de lectura de l'usuari
    loan_history = list(LoanHistory.get_by_user(user_id))
    total_books_read = len({loan['book_id'] for loan in loan_history if loan.get('is_returned', False)})
    
    # Obté les ressenyes de l'usuari
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
    # Obtenir l'historial de préstecs
    loan_history = list(LoanHistory.find(
        {'user_id': user_id},
        sort=[('loan_date', -1)]
    ))
    
    # Filtrar els préstecs actius si és necessari
    if not include_active:
        loan_history = [loan for loan in loan_history if loan.get('is_returned', False)]
    
    clean_loan_history = []
    for loan in loan_history:
        loan_date = loan.get('loan_date')
        if not loan_date:
            continue  # Ignorar préstecs sense data
        
        # Convertir la cadena a datetime si és necessari
        if isinstance(loan_date, str):
            try:
                loan['loan_date'] = parse(loan_date)
            except Exception:
                continue  # Ignorar si no es pot parsejar
        
        clean_loan_history.append(loan)
    
    # Obtenir detalls del llibre per a cada préstec net
    history_items = []
    for loan in clean_loan_history:
        book = Book.query.get(loan['book_id'])
        if book:
            loan['id'] = str(loan['_id'])
            history_items.append({
                'loan': loan,
                'book': book
            })
    
    # Paginació manual
    total_items = len(history_items)
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    
    return history_items[start_idx:end_idx], total_pages, total_items

def get_user_reviews(user_id, page=1, per_page=10):
    """
    Obté les ressenyes escrites per un usuari.
    
    Args:
        user_id (int): L'ID de l'usuari
        page (int): Número de pàgina (començant per 1)
        per_page (int): Nombre d'elements per pàgina
        
    Returns:
        tuple: (reviews_with_books, total_pages, total_items)
    """
    # Obté ressenyes de MongoDB
    skip = (page - 1) * per_page
    reviews = list(Review.find(
        {'user_id': user_id},
        sort=[('created_at', -1)],
        skip=skip,
        limit=per_page
    ))
    
    # Obté el recompte total per a la paginació
    total_items = Review.get_collection().count_documents({'user_id': user_id})
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
    
    # Obté detalls del llibre per a cada ressenya
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
    Obté recomanacions de llibres personalitzades per a un usuari.
    
    Args:
        user_id (int): L'ID de l'usuari
        limit (int): Nombre màxim de recomanacions a retornar
        
    Returns:
        list: Llibres recomanats
    """
    return get_recommendations_for_user(user_id, limit=limit)

def track_book_view(user_id, book_id):
    """
    Registra quan un usuari visualitza un llibre.
    
    Args:
        user_id (int): L'ID de l'usuari
        book_id (int): L'ID del llibre
        
    Returns:
        bool: Si el registre ha estat exitós
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
    print(f"Préstecs actius per a l'usuari {user_id}: {active_loans} (tipus: {type(active_loans)})")  # Depuració
    return active_loans or []

def get_user_reading_preferences(user_id):
    """
    Obté les preferències de lectura d'un usuari.

    Args:
        user_id (int): L'ID de l'usuari

    Returns:
        dict: Preferències de lectura
    """
    preferences = UserPreferences.get_preferences(user_id)
    return {
        'preferred_genres': preferences.get('preferred_genres', []),
        'preferred_authors': preferences.get('preferred_authors', []),
        'reading_frequency': preferences.get('reading_frequency', 'New reader')
    }

def update_user_preferences(user_id, preferred_genres=None, preferred_authors=None, reading_frequency=None):
    """
    Actualitza les preferències de lectura d'un usuari.

    Args:
        user_id (int): L'ID de l'usuari
        preferred_genres (list, optional): Gèneres preferits
        preferred_authors (list, optional): Autors preferits
        reading_frequency (str, optional): Freqüència de lectura

    Returns:
        bool: Si l'actualització ha estat exitosa
    """
    try:
        UserPreferences.update_preferences(
            user_id=user_id,
            preferred_genres=preferred_genres,
            preferred_authors=preferred_authors,
            reading_frequency=reading_frequency
        )
        return True
    except Exception as e:
        current_app.logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
        return False

def get_overdue_loans(user_id):
    """
    Obté els préstecs vençuts d'un usuari.
    
    Args:
        user_id (int): L'ID de l'usuari
        
    Returns:
        list: Préstecs vençuts amb detalls del llibre
    """
    now = datetime.now(timezone.utc)
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
    Obté estadístiques sobre els hàbits de lectura d'un usuari.
    
    Args:
        user_id (int): L'ID de l'usuari
        
    Returns:
        dict: Estadístiques de l'usuari
    """
    # Obté l'historial de préstecs
    loan_history = list(LoanHistory.get_by_user(user_id))
    
    # Calcula les estadístiques
    total_books_read = len({loan['book_id'] for loan in loan_history if loan.get('action') == 'read'})
    
    # Calcula la puntuació mitjana donada
    reviews = list(Review.find({'user_id': user_id}))
    ratings = [review.get('rating', 0) for review in reviews if 'rating' in review]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Calcula llibres llegits per mes (últims 6 mesos)
    now = datetime.now(timezone.utc)
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