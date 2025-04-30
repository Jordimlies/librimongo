from flask import Flask, render_template
from flask_login import LoginManager
from pymongo import MongoClient
from config.config import get_config
from models.mariadb_models import db, User
import os
from datetime import datetime

def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(get_config())
    
    # Initialize MariaDB with SQLAlchemy
    db.init_app(app)
    
    # Initialize MongoDB connection
    mongo_client = MongoClient(app.config['MONGO_URI'])
    app.mongo_client = mongo_client
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth_routes.login_route'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load a user from the database."""
        return User.query.get(int(user_id))
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Initialize database tables and collections
    with app.app_context():
        from utils.db_init import init_db
        init_db()
    
    # Add template filters
    @app.template_filter('now')
    def _now():
        """Return the current year."""
        from datetime import datetime
        return datetime.utcnow()
    
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}
    
    return app

def register_blueprints(app):
    """Register Flask blueprints."""
    # Import blueprints
    from routes.auth_routes import auth_bp
    from routes.book_routes import book_bp
    from routes.user_routes import user_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(user_bp)
    
    @app.route('/')
    def index():
        # Import here to avoid circular imports
        from services.book_service import get_all_books
        from services.recommendation_service import get_popular_books
        
        # Get some books for the homepage
        recent_books, _, _ = get_all_books(page=1, per_page=6, sort_by='created_at', sort_order='desc')
        popular_books = get_popular_books(limit=6)
        
        return render_template('index.html', recent_books=recent_books, popular_books=popular_books)

def register_error_handlers(app):
    """Register error handlers."""
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)