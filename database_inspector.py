import pymysql
from pymongo import MongoClient
import logging

# Configurar el logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("database_inspector")

# Configuració de connexió per a MariaDB
MARIADB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "librimongo",
    "password": "librimongo",
    "database": "librimongo"
}

# Configuració de connexió per a MongoDB
MONGODB_URI = "mongodb://localhost:27017/"
MONGODB_DB_NAME = "librimongo"

def inspect_mariadb():
    """Llistar les bases de dades, taules i contingut de MariaDB."""
    logger.info("Connecting to MariaDB...")
    try:
        connection = pymysql.connect(**MARIADB_CONFIG)
        cursor = connection.cursor()

        # Llistar les taules
        logger.info(f"Inspecting MariaDB database: {MARIADB_CONFIG['database']}")
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        if not tables:
            logger.warning("No tables found in MariaDB.")
        else:
            for table in tables:
                table_name = table[0]
                logger.info(f"Table: {table_name}")

                # Llistar el contingut de cada taula
                cursor.execute(f"SELECT * FROM {table_name};")
                rows = cursor.fetchall()
                if rows:
                    logger.info(f"Content of table {table_name}:")
                    for row in rows:
                        logger.info(row)
                else:
                    logger.info(f"Table {table_name} is empty.")

        cursor.close()
        connection.close()
    except Exception as e:
        logger.error(f"Error connecting to MariaDB: {e}")

def inspect_mongodb():
    """Llistar les bases de dades, col·leccions i contingut de MongoDB."""
    logger.info("Connecting to MongoDB...")
    try:
        client = MongoClient(MONGODB_URI)
        db = client[MONGODB_DB_NAME]

        # Llistar les col·leccions
        logger.info(f"Inspecting MongoDB database: {MONGODB_DB_NAME}")
        collections = db.list_collection_names()
        if not collections:
            logger.warning("No collections found in MongoDB.")
        else:
            for collection_name in collections:
                logger.info(f"Collection: {collection_name}")

                # Llistar el contingut de cada col·lecció
                collection = db[collection_name]
                documents = collection.find()
                logger.info(f"Content of collection {collection_name}:")
                for document in documents:
                    logger.info(document)

        client.close()
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")

def main():
    """Funció principal per inspeccionar les bases de dades."""
    logger.info("Starting database inspection...")
    inspect_mariadb()
    inspect_mongodb()
    logger.info("Database inspection completed.")

if __name__ == "__main__":
    main()