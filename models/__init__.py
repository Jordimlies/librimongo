"""
Models package for LibriMongo application.

This package contains database models for both MariaDB and MongoDB:
- MariaDB models: User, Book, Loan
- MongoDB models: Review, LoanHistory, BookText
"""

from models.mariadb_models import db, User, Book, Loan
from models.mongodb_models import Review, LoanHistory, BookText

__all__ = [
    'db',
    'User',
    'Book',
    'Loan',
    'Review',
    'LoanHistory',
    'BookText'
]