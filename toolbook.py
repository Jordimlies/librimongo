import os
import csv
import logging
from tkinter import Tk, Label, Button, filedialog, messagebox, Text, Scrollbar, RIGHT, Y, END, Frame, OptionMenu, StringVar
from pymongo import MongoClient
from flask import Flask
from sqlalchemy import inspect, text
from models.mariadb_models import db, Book
from models.mongodb_models import BookText
from config.config import get_config

# Configurar el logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("toolbook")

# Crear la aplicación Flask
def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    db.init_app(app)
    mongo_client = MongoClient(app.config['MONGO_URI'])
    app.mongo_client = mongo_client
    return app

# -------------------- Funciones de MariaDB --------------------

def get_mariadb_tables(app):
    """Obtener las tablas de MariaDB."""
    with app.app_context():
        inspector = inspect(db.engine)
        return inspector.get_table_names()

def inspect_mariadb_table(app, table_name, log_widget):
    """Inspeccionar una tabla específica de MariaDB."""
    with app.app_context():
        try:
            rows = db.session.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            if not rows:
                log_widget.insert(END, f"No data found in table {table_name}.\n", "error")
            else:
                log_widget.insert(END, f"Data from table {table_name}:\n", "header")
                for row in rows:
                    log_widget.insert(END, f"{row}\n", "data")
        except Exception as e:
            log_widget.insert(END, f"Error inspecting table {table_name}: {e}\n", "error")

def delete_all_mariadb(app, log_widget):
    """Eliminar todas las tablas de MariaDB."""
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            # Deshabilitar restricciones de claves foráneas
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                db.session.execute(text(f"DROP TABLE {table}"))
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))  # Volver a habilitar restricciones
            db.session.commit()
            log_widget.insert(END, "All MariaDB tables deleted successfully.\n", "success")
        except Exception as e:
            log_widget.insert(END, f"Error deleting MariaDB tables: {e}\n", "error")

def show_mariadb_table_content(app, table_name, log_widget):
    """Mostrar el contenido de una tabla específica de MariaDB."""
    with app.app_context():
        try:
            rows = db.session.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            if not rows:
                log_widget.insert(END, f"No data found in table {table_name}.\n", "error")
            else:
                # Mostrar encabezados
                headers = rows[0]._fields  # Usar _fields para obtener los nombres de las columnas
                log_widget.insert(END, f"Table: {table_name}\n", "header")
                log_widget.insert(END, f"{' | '.join(headers)}\n", "header")
                log_widget.insert(END, "-" * 50 + "\n")
                # Mostrar filas
                for row in rows:
                    log_widget.insert(END, f"{' | '.join(str(value) for value in row)}\n", "data")
        except Exception as e:
            log_widget.insert(END, f"Error showing table content: {e}\n", "error")

# -------------------- Funciones de MongoDB --------------------

def get_mongodb_collections(app):
    """Obtener las colecciones de MongoDB."""
    with app.app_context():
        mongo_client = app.mongo_client
        mongo_db = mongo_client[app.config['MONGO_DB_NAME']]
        return mongo_db.list_collection_names()

def inspect_mongodb_collection(app, collection_name, log_widget):
    """Inspeccionar una colección específica de MongoDB."""
    with app.app_context():
        try:
            mongo_client = app.mongo_client
            mongo_db = mongo_client[app.config['MONGO_DB_NAME']]
            documents = mongo_db[collection_name].find()
            log_widget.insert(END, f"Data from collection {collection_name}:\n", "header")
            for document in documents:
                log_widget.insert(END, f"{document}\n", "data")
        except Exception as e:
            log_widget.insert(END, f"Error inspecting collection {collection_name}: {e}\n", "error")

def delete_all_mongodb(app, log_widget):
    """Eliminar todas las colecciones de MongoDB."""
    with app.app_context():
        try:
            mongo_client = app.mongo_client
            mongo_db = mongo_client[app.config['MONGO_DB_NAME']]
            collections = mongo_db.list_collection_names()
            for collection in collections:
                mongo_db.drop_collection(collection)
            log_widget.insert(END, "All MongoDB collections deleted successfully.\n", "success")
        except Exception as e:
            log_widget.insert(END, f"Error deleting MongoDB collections: {e}\n", "error")

def show_mongodb_collection_content(app, collection_name, log_widget):
    """Mostrar el contenido de una colección específica de MongoDB."""
    with app.app_context():
        try:
            mongo_client = app.mongo_client
            mongo_db = mongo_client[app.config['MONGO_DB_NAME']]
            documents = mongo_db[collection_name].find()
            log_widget.insert(END, f"Collection: {collection_name}\n", "header")
            log_widget.insert(END, "-" * 50 + "\n")
            for document in documents:
                log_widget.insert(END, f"{document}\n", "data")
        except Exception as e:
            log_widget.insert(END, f"Error showing collection content: {e}\n", "error")

# -------------------- Funciones conjuntas --------------------

def delete_all_databases(app, mariadb_log_widget, mongodb_log_widget):
    """Eliminar todas las tablas y colecciones de ambas bases de datos."""
    delete_all_mariadb(app, mariadb_log_widget)
    delete_all_mongodb(app, mongodb_log_widget)

def import_books_and_covers(app, source_dir, covers_dest, mariadb_log_widget, mongodb_log_widget):
    """Importar libros y carátulas."""
    books_file = os.path.join(source_dir, 'books.txt')
    covers_source = os.path.join(source_dir, 'covers')

    if not os.path.exists(books_file):
        mariadb_log_widget.insert(END, f"Books file not found: {books_file}\n", "error")
        return

    with app.app_context():
        with open(books_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 7:
                    try:
                        # Convertir book_id a entero y luego a cadena
                        book_id = str(int(parts[0]))  # Asegurarse de que sea una cadena
                    except ValueError:
                        mariadb_log_widget.insert(END, f"Invalid book ID: {parts[0]}\n", "error")
                        continue  # Saltar esta línea si el ID no es válido

                    title, author, genres, publisher, year, cover_image = parts[1:7]
                    description = parts[7] if len(parts) > 7 else ""

                    # Crear registro en MariaDB
                    year_int = int(year) if year.isdigit() else None
                    book = Book(
                        isbn=book_id,
                        title=title,
                        author=author,
                        year=year_int,
                        genre=genres,
                        publisher=publisher,
                        description=description,
                        cover_image_path=f"covers/{cover_image}" if os.path.exists(os.path.join(covers_source, cover_image)) else None,
                        available_copies=1,
                        total_copies=1
                    )
                    db.session.add(book)

                    # Crear registro en MongoDB
                    BookText.create(book_id, description)

            db.session.commit()
            mariadb_log_widget.insert(END, "Books imported successfully.\n", "success")
            mongodb_log_widget.insert(END, "Book descriptions imported successfully.\n", "success")
            
# -------------------- Interfaz gráfica --------------------

def main_gui():
    app = create_app()

    def update_mariadb_tables():
        """Actualizar el menú desplegable de tablas de MariaDB."""
        tables = get_mariadb_tables(app)
        mariadb_table_var.set("")
        mariadb_table_menu["menu"].delete(0, "end")
        for table in tables:
            mariadb_table_menu["menu"].add_command(label=table, command=lambda value=table: mariadb_table_var.set(value))

    def update_mongodb_collections():
        """Actualizar el menú desplegable de colecciones de MongoDB."""
        collections = get_mongodb_collections(app)
        mongodb_collection_var.set("")
        mongodb_collection_menu["menu"].delete(0, "end")
        for collection in collections:
            mongodb_collection_menu["menu"].add_command(label=collection, command=lambda value=collection: mongodb_collection_var.set(value))

    def delete_all_action():
        """Eliminar todas las tablas y colecciones."""
        if messagebox.askyesno("Delete All", "Are you sure you want to delete all data from both databases?"):
            delete_all_databases(app, mariadb_log_text, mongodb_log_text)

    def import_action():
        """Importar libros y carátulas."""
        source_dir = filedialog.askdirectory(title="Select Source Directory")
        covers_dest = filedialog.askdirectory(title="Select Covers Destination")
        if source_dir and covers_dest:
            import_books_and_covers(app, source_dir, covers_dest, mariadb_log_text, mongodb_log_text)

    def show_mariadb_content_action():
        """Mostrar el contenido de la tabla seleccionada de MariaDB."""
        table_name = mariadb_table_var.get()
        if table_name:
            mariadb_log_text.delete(1.0, END)
            show_mariadb_table_content(app, table_name, mariadb_log_text)
        else:
            messagebox.showwarning("Select Table", "Please select a MariaDB table to show content.")

    def show_mongodb_content_action():
        """Mostrar el contenido de la colección seleccionada de MongoDB."""
        collection_name = mongodb_collection_var.get()
        if collection_name:
            mongodb_log_text.delete(1.0, END)
            show_mongodb_collection_content(app, collection_name, mongodb_log_text)
        else:
            messagebox.showwarning("Select Collection", "Please select a MongoDB collection to show content.")

    # Crear ventana principal
    root = Tk()
    root.title("ToolBook - Database Manager")

    # Contenedores principales
    left_frame = Frame(root)
    right_frame = Frame(root)
    left_frame.pack(side="left", padx=10, pady=10)
    right_frame.pack(side="right", padx=10, pady=10)

    # Botones de MariaDB
    Label(left_frame, text="MariaDB Actions", font=("Arial", 12)).pack()
    mariadb_table_var = StringVar()
    mariadb_table_menu = OptionMenu(left_frame, mariadb_table_var, "")
    mariadb_table_menu.pack(pady=5)
    Button(left_frame, text="Update Tables", command=update_mariadb_tables, width=20).pack(pady=5)
    Button(left_frame, text="Delete All Tables", command=lambda: delete_all_mariadb(app, mariadb_log_text), width=20).pack(pady=5)
    Button(left_frame, text="Show Table Content", command=show_mariadb_content_action, width=20).pack(pady=5)

    # Botones de MongoDB
    Label(right_frame, text="MongoDB Actions", font=("Arial", 12)).pack()
    mongodb_collection_var = StringVar()
    mongodb_collection_menu = OptionMenu(right_frame, mongodb_collection_var, "")
    mongodb_collection_menu.pack(pady=5)
    Button(right_frame, text="Update Collections", command=update_mongodb_collections, width=20).pack(pady=5)
    Button(right_frame, text="Delete All Collections", command=lambda: delete_all_mongodb(app, mongodb_log_text), width=20).pack(pady=5)
    Button(right_frame, text="Show Collection Content", command=show_mongodb_content_action, width=20).pack(pady=5)

    # Botones conjuntos
    Button(root, text="Delete All Data", command=delete_all_action, width=20).pack(pady=5)
    Button(root, text="Import Books and Covers", command=import_action, width=20).pack(pady=5)

    # Logs de MariaDB
    Label(left_frame, text="MariaDB Logs", font=("Arial", 12)).pack(pady=5)
    mariadb_log_text = Text(left_frame, wrap="word", height=20, width=70)
    mariadb_log_text.pack(pady=5)
    mariadb_scrollbar = Scrollbar(left_frame, command=mariadb_log_text.yview)
    mariadb_scrollbar.pack(side=RIGHT, fill=Y)
    mariadb_log_text.config(yscrollcommand=mariadb_scrollbar.set)

    # Logs de MongoDB
    Label(right_frame, text="MongoDB Logs", font=("Arial", 12)).pack(pady=5)
    mongodb_log_text = Text(right_frame, wrap="word", height=20, width=70)
    mongodb_log_text.pack(pady=5)
    mongodb_scrollbar = Scrollbar(right_frame, command=mongodb_log_text.yview)
    mongodb_scrollbar.pack(side=RIGHT, fill=Y)
    mongodb_log_text.config(yscrollcommand=mongodb_scrollbar.set)

    # Estilización de logs
    for log_text in [mariadb_log_text, mongodb_log_text]:
        log_text.tag_config("header", foreground="blue", font=("Arial", 10, "bold"))
        log_text.tag_config("data", foreground="white", font=("Arial", 10))
        log_text.tag_config("success", foreground="green", font=("Arial", 10, "italic"))
        log_text.tag_config("error", foreground="red", font=("Arial", 10, "italic"))

    root.mainloop()

if __name__ == "__main__":
    main_gui()