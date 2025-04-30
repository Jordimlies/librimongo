# Librimongo

Una aplicación web Flask para gestionar una biblioteca digital, utilizando MariaDB y MongoDB para el almacenamiento de datos.

## Resumen del Proyecto

Librimongo es una migración y mejora de la aplicación original Libritxt 1.0, pasando de un almacenamiento basado en archivos a una arquitectura de base de datos más robusta utilizando MariaDB y MongoDB. La aplicación ofrece gestión de libros, autenticación de usuarios, seguimiento de préstamos y recomendaciones de libros.

## Características

- Autenticación y autorización de usuarios
- Catálogo de libros con funcionalidad de búsqueda y filtrado
- Gestión de préstamos de libros
- Sistema de reseñas y valoraciones
- Algoritmo de recomendación de libros
- Panel de administración para gestión del sistema
- Soporte para Docker para un despliegue sencillo

## Estructura del Directorio

```
librimongo/
├── app.py                      # Punto de entrada principal de la aplicación
├── config.py                   # Configuraciones
├── importador.py               # Script para importar libros desde la carpeta dades/
├── docker_init.py              # Script de configuración de contenedores Docker
├── requirements.txt            # Dependencias de Python
├── routes/                     # Manejadores de rutas
│   ├── __init__.py
│   ├── auth_routes.py          # Rutas de autenticación
│   ├── book_routes.py          # Rutas relacionadas con libros
│   └── user_routes.py          # Rutas relacionadas con usuarios
├── models/                     # Modelos de base de datos
│   ├── __init__.py
│   ├── mariadb_models.py       # Modelos MariaDB (usuarios, libros, préstamos)
│   └── mongodb_models.py       # Modelos MongoDB (reseñas, historial de préstamos, texto de libros)
├── services/                   # Lógica de negocio
│   ├── __init__.py
│   ├── auth_service.py         # Servicios de autenticación
│   ├── book_service.py         # Servicios relacionados con libros
│   ├── recommendation_service.py # Algoritmo de recomendación de libros
│   └── user_service.py         # Servicios relacionados con usuarios
├── templates/                  # Plantillas HTML
│   ├── base.html               # Plantilla base
│   ├── index.html              # Página principal
│   ├── book_detail.html        # Página de detalle de libro
│   ├── login.html              # Página de inicio de sesión
│   ├── register.html           # Página de registro
│   └── ...                     # Otras plantillas
├── static/                     # Recursos estáticos
│   ├── css/                    # Archivos CSS
│   ├── js/                     # Archivos JavaScript
│   └── images/                 # Archivos de imágenes
└── utils/                      # Funciones utilitarias
    ├── __init__.py
    ├── db_init.py              # Inicialización de bases de datos
    └── helpers.py              # Funciones auxiliares
```

## Instrucciones de Instalación

### Requisitos Previos

- Python 3.9 o superior (3.12.9)
- Docker y Docker Compose (opcional, para configuración en contenedores)
- Git

### Instalación

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/yourusername/librimongo.git
   cd librimongo
   ```

2. Crear y activar un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno (crear un archivo `.env` en la raíz del proyecto):
   ```
   FLASK_ENV=development
   SECRET_KEY=tu_clave_secreta
   MARIADB_USER=librimongo
   MARIADB_PASSWORD=librimongo
   MARIADB_HOST=localhost
   MARIADB_PORT=3306
   MARIADB_DB=librimongo
   MONGO_URI=mongodb://localhost:27017/librimongo
   MONGO_DB_NAME=librimongo
   ```

### Configuración de Bases de Datos

#### Opción 1: Usando Docker (Recomendado)

1. Ejecutar el script de inicialización Docker:
   ```bash
   python docker_init.py --action start
   ```

   Esto:
   - Creará contenedores Docker para MariaDB y MongoDB
   - Configurará la red entre contenedores
   - Inicializará las bases de datos con usuarios y permisos necesarios

2. Importar datos desde Libritxt 1.0 (si están disponibles):
   ```bash
   python importador.py --source "/ruta/a/Libritxt 1.0/data"
   ```

#### Opción 2: Configuración Manual

1. Instalar y configurar MariaDB y MongoDB en tu sistema

2. Crear bases de datos y usuarios:
   - Para MariaDB:
     ```sql
     CREATE DATABASE librimongo;
     CREATE USER 'librimongo'@'localhost' IDENTIFIED BY 'librimongo';
     GRANT ALL PRIVILEGES ON librimongo.* TO 'librimongo'@'localhost';
     FLUSH PRIVILEGES;
     ```
   
   - Para MongoDB:
     ```
     use librimongo
     db.createCollection('reviews')
     db.createCollection('loan_history')
     db.createCollection('book_texts')
     ```

3. Actualizar el archivo `.env` con los detalles de conexión a las bases de datos

4. Importar datos desde Libritxt 1.0 (si están disponibles):
   ```bash
   python importador.py --source "/ruta/a/Libritxt 1.0/data"
   ```

### Ejecución de la Aplicación

1. Iniciar el servidor de desarrollo Flask:
   ```bash
   python app.py
   ```

2. Acceder a la aplicación en el navegador web en `http://localhost:5000`

## Uso

### Roles de Usuario

- **Lector**: Puede navegar por los libros, tomar libros prestados y dejar reseñas
- **Administrador**: Puede gestionar libros, usuarios y préstamos

### Usuarios Predeterminados

- Administrador: usuario `admin`, contraseña `admin`
- Lector: usuario `user`, contraseña `user`

### Funcionalidades Principales

- **Catálogo de Libros**: Navegar y buscar libros
- **Detalles del Libro**: Ver información del libro, reseñas y disponibilidad
- **Perfil de Usuario**: Gestionar cuenta y ver historial de préstamos
- **Panel de Administración**: Gestionar libros, usuarios y préstamos (solo admin)

## Importación de Datos

El script `importador.py` permite importar datos desde la aplicación original Libritxt 1.0:

```bash
python importador.py --source "/ruta/a/Libritxt 1.0/data" --covers-dest "static/covers"
```

Opciones:
- `--source`: Directorio fuente que contiene los datos de Libritxt 1.0
- `--covers-dest`: Directorio destino para las portadas de libros
- `--reset`: Reiniciar las bases de datos antes de importar
- `--skip-books`: Omitir la importación de libros
- `--skip-users`: Omitir la importación de usuarios
- `--skip-loans`: Omitir la importación de préstamos
- `--skip-reviews`: Omitir la importación de reseñas
- `--resume`: Reanudar desde el último ítem importado
- `--verbose`: Incrementar la verbosidad

## Gestión con Docker

El script `docker_init.py` proporciona comandos para gestionar los contenedores Docker:

```bash
python docker_init.py --action [start|stop|restart|reset|status]
```

Opciones:
- `--action`: Acción a realizar (start, stop, restart, reset, status)
- `--mariadb-port`: Puerto para el contenedor MariaDB (por defecto: 3306)
- `--mongodb-port`: Puerto para el contenedor MongoDB (por defecto: 27017)
- `--data-dir`: Directorio para datos de volúmenes Docker (por defecto: ./docker_data)
- `--verbose`: Incrementar la verbosidad

## Desarrollo

### Pruebas

Ejecutar pruebas con pytest:
```bash
pytest
```

### Formateo de Código

Formatear código con Black:
```bash
black .
```

Verificar estilo con Flake8:
```bash
flake8
```

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.