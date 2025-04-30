# Librimongo

A Flask web application for managing a digital library, using MariaDB and MongoDB for data storage.

## Project Overview

Librimongo is a migration and enhancement of the original Libritxt 1.0 application, moving from file-based storage to a more robust database architecture using MariaDB and MongoDB. The application provides book management, user authentication, loan tracking, and book recommendations.

## Features

- User authentication and authorization
- Book catalog with search and filter functionality
- Book loan management
- Review and rating system
- Book recommendation algorithm
- Admin dashboard for system management
- Docker support for easy deployment

## Directory Structure

```
librimongo/
├── app.py                      # Main application entry point
├── config.py                   # Configuration settings
├── importador.py               # Script to import books from dades/ folder
├── docker_init.py              # Docker container setup script
├── requirements.txt            # Python dependencies
├── routes/                     # Route handlers
│   ├── __init__.py
│   ├── auth_routes.py          # Authentication routes
│   ├── book_routes.py          # Book-related routes
│   └── user_routes.py          # User-related routes
├── models/                     # Database models
│   ├── __init__.py
│   ├── mariadb_models.py       # MariaDB models (users, books, loans)
│   └── mongodb_models.py       # MongoDB models (reviews, loan history, book text)
├── services/                   # Business logic
│   ├── __init__.py
│   ├── auth_service.py         # Authentication services
│   ├── book_service.py         # Book-related services
│   ├── recommendation_service.py # Book recommendation algorithm
│   └── user_service.py         # User-related services
├── templates/                  # HTML templates
│   ├── base.html               # Base template
│   ├── index.html              # Home page
│   ├── book_detail.html        # Book detail page
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   └── ...                     # Other templates
├── static/                     # Static assets
│   ├── css/                    # CSS files
│   ├── js/                     # JavaScript files
│   └── images/                 # Image files
└── utils/                      # Utility functions
    ├── __init__.py
    ├── db_init.py              # Database initialization
    └── helpers.py              # Helper functions
```

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose (optional, for containerized setup)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/librimongo.git
   cd librimongo
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (create a `.env` file in the project root):
   ```
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   MARIADB_USER=librimongo
   MARIADB_PASSWORD=librimongo
   MARIADB_HOST=localhost
   MARIADB_PORT=3306
   MARIADB_DB=librimongo
   MONGO_URI=mongodb://localhost:27017/librimongo
   MONGO_DB_NAME=librimongo
   ```

### Database Setup

#### Option 1: Using Docker (Recommended)

1. Run the Docker initialization script:
   ```bash
   python docker_init.py --action start
   ```

   This will:
   - Create Docker containers for MariaDB and MongoDB
   - Configure networking between containers
   - Initialize databases with required users and permissions

2. Import data from Libritxt 1.0 (if available):
   ```bash
   python importador.py --source "/path/to/Libritxt 1.0/data"
   ```

#### Option 2: Manual Setup

1. Install and configure MariaDB and MongoDB on your system

2. Create databases and users:
   - For MariaDB:
     ```sql
     CREATE DATABASE librimongo;
     CREATE USER 'librimongo'@'localhost' IDENTIFIED BY 'librimongo';
     GRANT ALL PRIVILEGES ON librimongo.* TO 'librimongo'@'localhost';
     FLUSH PRIVILEGES;
     ```
   
   - For MongoDB:
     ```
     use librimongo
     db.createCollection('reviews')
     db.createCollection('loan_history')
     db.createCollection('book_texts')
     ```

3. Update the `.env` file with your database connection details

4. Import data from Libritxt 1.0 (if available):
   ```bash
   python importador.py --source "/path/to/Libritxt 1.0/data"
   ```

### Running the Application

1. Start the Flask development server:
   ```bash
   python app.py
   ```

2. Access the application in your web browser at `http://localhost:5000`

## Usage

### User Roles

- **Reader**: Can browse books, borrow books, and leave reviews
- **Admin**: Can manage books, users, and loans

### Default Users

- Admin: username `admin`, password `admin`
- Reader: username `user`, password `user`

### Main Features

- **Book Catalog**: Browse and search for books
- **Book Details**: View book information, reviews, and availability
- **User Profile**: Manage your account and view your loan history
- **Admin Dashboard**: Manage books, users, and loans (admin only)

## Data Import

The `importador.py` script allows you to import data from the original Libritxt 1.0 application:

```bash
python importador.py --source "/path/to/Libritxt 1.0/data" --covers-dest "static/covers"
```

Options:
- `--source`: Source directory containing Libritxt 1.0 data
- `--covers-dest`: Destination directory for book covers
- `--reset`: Reset databases before importing
- `--skip-books`: Skip importing books
- `--skip-users`: Skip importing users
- `--skip-loans`: Skip importing loans
- `--skip-reviews`: Skip importing reviews
- `--resume`: Resume from last imported item
- `--verbose`: Increase verbosity

## Docker Management

The `docker_init.py` script provides commands to manage Docker containers:

```bash
python docker_init.py --action [start|stop|restart|reset|status]
```

Options:
- `--action`: Action to perform (start, stop, restart, reset, status)
- `--mariadb-port`: Port for MariaDB container (default: 3306)
- `--mongodb-port`: Port for MongoDB container (default: 27017)
- `--data-dir`: Directory for Docker volume data (default: ./docker_data)
- `--verbose`: Increase verbosity

## Development

### Testing

Run tests with pytest:
```bash
pytest
```

### Code Formatting

Format code with Black:
```bash
black .
```

Check code style with Flake8:
```bash
flake8
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.# libreriadb
