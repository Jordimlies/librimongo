#!/usr/bin/env python3
"""
Docker initialization script for Librimongo

This script sets up Docker containers for MariaDB and MongoDB,
configures networking, and initializes the databases.
"""

import os
import sys
import argparse
import logging
import subprocess
import time
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("docker_init.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("docker_init")

# Default configuration
DEFAULT_CONFIG = {
    'mariadb': {
        'image': 'mariadb:10.11',
        'container_name': 'librimongo-mariadb',
        'port': 3306,
        'root_password': 'rootpassword',
        'database': 'librimongo',
        'user': 'librimongo',
        'password': 'librimongo',
        'volume': './mariadb_data'
    },
    'mongodb': {
        'image': 'mongo:6.0',
        'container_name': 'librimongo-mongodb',
        'port': 27017,
        'database': 'librimongo',
        'volume': './mongodb_data'
    },
    'network': {
        'name': 'librimongo-network'
    }
}

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Set up Docker containers for Librimongo')
    parser.add_argument('--action', choices=['start', 'stop', 'restart', 'reset', 'status'], 
                        default='start', help='Action to perform')
    parser.add_argument('--mariadb-port', type=int, default=DEFAULT_CONFIG['mariadb']['port'],
                        help='Port for MariaDB container')
    parser.add_argument('--mongodb-port', type=int, default=DEFAULT_CONFIG['mongodb']['port'],
                        help='Port for MongoDB container')
    parser.add_argument('--mariadb-password', default=DEFAULT_CONFIG['mariadb']['root_password'],
                        help='Root password for MariaDB')
    parser.add_argument('--mariadb-user', default=DEFAULT_CONFIG['mariadb']['user'],
                        help='User for MariaDB')
    parser.add_argument('--mariadb-user-password', default=DEFAULT_CONFIG['mariadb']['password'],
                        help='User password for MariaDB')
    parser.add_argument('--mariadb-database', default=DEFAULT_CONFIG['mariadb']['database'],
                        help='Database name for MariaDB')
    parser.add_argument('--mongodb-database', default=DEFAULT_CONFIG['mongodb']['database'],
                        help='Database name for MongoDB')
    parser.add_argument('--data-dir', default='./docker_data',
                        help='Directory for Docker volume data')
    parser.add_argument('--no-compose', action='store_true',
                        help='Do not use Docker Compose, use Docker CLI directly')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increase verbosity (can be used multiple times)')
    
    return parser.parse_args()

def run_command(command, check=True, shell=False):
    """Run a shell command and return the result."""
    logger.debug(f"Running command: {command}")
    try:
        if shell:
            result = subprocess.run(command, shell=True, check=check, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True)
        else:
            result = subprocess.run(command, check=check, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        if check:
            raise
        return e

def check_docker_installed():
    """Check if Docker is installed and running."""
    try:
        result = run_command(['docker', 'info'], check=False)
        if result.returncode != 0:
            logger.error("Docker is not running or not installed")
            logger.error(f"Error: {result.stderr}")
            return False
        
        # Check for Docker Compose
        compose_result = run_command(['docker', 'compose', 'version'], check=False)
        if compose_result.returncode != 0:
            logger.warning("Docker Compose is not installed or not in PATH")
            logger.warning("Will use Docker CLI directly")
            return True, False
        
        return True, True
    except FileNotFoundError:
        logger.error("Docker is not installed or not in PATH")
        return False, False

def create_docker_network(network_name):
    """Create a Docker network if it doesn't exist."""
    # Check if network exists
    result = run_command(['docker', 'network', 'ls', '--filter', f'name={network_name}', '--format', '{{.Name}}'])
    if network_name in result.stdout:
        logger.info(f"Docker network {network_name} already exists")
        return True
    
    # Create network
    result = run_command(['docker', 'network', 'create', network_name])
    logger.info(f"Created Docker network: {network_name}")
    return True

def create_docker_compose_file(config, data_dir):
    """Create a Docker Compose file based on the configuration."""
    # Ensure data directories exist
    mariadb_data_dir = os.path.join(data_dir, 'mariadb')
    mongodb_data_dir = os.path.join(data_dir, 'mongodb')
    os.makedirs(mariadb_data_dir, exist_ok=True)
    os.makedirs(mongodb_data_dir, exist_ok=True)
    
    # Create Docker Compose configuration
    compose_config = {
        'version': '3',
        'services': {
            'mariadb': {
                'image': config['mariadb']['image'],
                'container_name': config['mariadb']['container_name'],
                'restart': 'unless-stopped',
                'environment': {
                    'MYSQL_ROOT_PASSWORD': config['mariadb']['root_password'],
                    'MYSQL_DATABASE': config['mariadb']['database'],
                    'MYSQL_USER': config['mariadb']['user'],
                    'MYSQL_PASSWORD': config['mariadb']['password']
                },
                'ports': [
                    f"{config['mariadb']['port']}:3306"
                ],
                'volumes': [
                    f"{mariadb_data_dir}:/var/lib/mysql"
                ],
                'networks': [
                    config['network']['name']
                ],
                'healthcheck': {
                    'test': ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", f"-p{config['mariadb']['root_password']}"],
                    'interval': '10s',
                    'timeout': '5s',
                    'retries': 5
                }
            },
            'mongodb': {
                'image': config['mongodb']['image'],
                'container_name': config['mongodb']['container_name'],
                'restart': 'unless-stopped',
                'ports': [
                    f"{config['mongodb']['port']}:27017"
                ],
                'volumes': [
                    f"{mongodb_data_dir}:/data/db"
                ],
                'networks': [
                    config['network']['name']
                ],
                'command': 'mongod --bind_ip_all',
                'healthcheck': {
                    'test': ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"],
                    'interval': '10s',
                    'timeout': '5s',
                    'retries': 5
                }
            }
        },
        'networks': {
            config['network']['name']: {
                'driver': 'bridge'
            }
        }
    }
    
    # Write Docker Compose file
    with open('docker-compose.yml', 'w') as f:
        yaml.dump(compose_config, f, default_flow_style=False)
    
    logger.info("Created Docker Compose file: docker-compose.yml")
    return True

def start_containers_with_compose():
    """Start containers using Docker Compose."""
    result = run_command(['docker', 'compose', 'up', '-d'])
    if result.returncode == 0:
        logger.info("Started containers with Docker Compose")
        return True
    else:
        logger.error("Failed to start containers with Docker Compose")
        return False

def stop_containers_with_compose():
    """Stop containers using Docker Compose."""
    result = run_command(['docker', 'compose', 'down'])
    if result.returncode == 0:
        logger.info("Stopped containers with Docker Compose")
        return True
    else:
        logger.error("Failed to stop containers with Docker Compose")
        return False

def start_containers_with_cli(config, data_dir):
    """Start containers using Docker CLI."""
    # Ensure data directories exist
    mariadb_data_dir = os.path.join(data_dir, 'mariadb')
    mongodb_data_dir = os.path.join(data_dir, 'mongodb')
    os.makedirs(mariadb_data_dir, exist_ok=True)
    os.makedirs(mongodb_data_dir, exist_ok=True)
    
    # Create network
    create_docker_network(config['network']['name'])
    
    # Start MariaDB container
    mariadb_cmd = [
        'docker', 'run', '-d',
        '--name', config['mariadb']['container_name'],
        '--network', config['network']['name'],
        '-p', f"{config['mariadb']['port']}:3306",
        '-v', f"{mariadb_data_dir}:/var/lib/mysql",
        '-e', f"MYSQL_ROOT_PASSWORD={config['mariadb']['root_password']}",
        '-e', f"MYSQL_DATABASE={config['mariadb']['database']}",
        '-e', f"MYSQL_USER={config['mariadb']['user']}",
        '-e', f"MYSQL_PASSWORD={config['mariadb']['password']}",
        '--restart', 'unless-stopped',
        config['mariadb']['image']
    ]
    
    # Start MongoDB container
    mongodb_cmd = [
        'docker', 'run', '-d',
        '--name', config['mongodb']['container_name'],
        '--network', config['network']['name'],
        '-p', f"{config['mongodb']['port']}:27017",
        '-v', f"{mongodb_data_dir}:/data/db",
        '--restart', 'unless-stopped',
        config['mongodb']['image'],
        'mongod', '--bind_ip_all'
    ]
    
    # Run commands
    try:
        # Check if containers already exist
        mariadb_exists = run_command(['docker', 'ps', '-a', '--filter', f"name={config['mariadb']['container_name']}", '--format', '{{.Names}}'])
        mongodb_exists = run_command(['docker', 'ps', '-a', '--filter', f"name={config['mongodb']['container_name']}", '--format', '{{.Names}}'])
        
        # Remove existing containers if they exist
        if config['mariadb']['container_name'] in mariadb_exists.stdout:
            run_command(['docker', 'rm', '-f', config['mariadb']['container_name']])
        
        if config['mongodb']['container_name'] in mongodb_exists.stdout:
            run_command(['docker', 'rm', '-f', config['mongodb']['container_name']])
        
        # Start containers
        mariadb_result = run_command(mariadb_cmd)
        mongodb_result = run_command(mongodb_cmd)
        
        logger.info(f"Started MariaDB container: {mariadb_result.stdout.strip()}")
        logger.info(f"Started MongoDB container: {mongodb_result.stdout.strip()}")
        
        return True
    except Exception as e:
        logger.error(f"Error starting containers: {e}")
        return False

def stop_containers_with_cli(config):
    """Stop containers using Docker CLI."""
    try:
        # Stop and remove MariaDB container
        run_command(['docker', 'stop', config['mariadb']['container_name']], check=False)
        run_command(['docker', 'rm', config['mariadb']['container_name']], check=False)
        
        # Stop and remove MongoDB container
        run_command(['docker', 'stop', config['mongodb']['container_name']], check=False)
        run_command(['docker', 'rm', config['mongodb']['container_name']], check=False)
        
        logger.info("Stopped and removed containers")
        return True
    except Exception as e:
        logger.error(f"Error stopping containers: {e}")
        return False

def wait_for_mariadb(config, timeout=60):
    """Wait for MariaDB to be ready."""
    logger.info(f"Waiting for MariaDB to be ready (timeout: {timeout}s)...")
    
    cmd = [
        'docker', 'exec', config['mariadb']['container_name'],
        'mysqladmin', 'ping', '-h', 'localhost',
        '-u', 'root', f"-p{config['mariadb']['root_password']}"
    ]
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = run_command(cmd, check=False)
        if result.returncode == 0:
            logger.info("MariaDB is ready")
            return True
        time.sleep(2)
    
    logger.error(f"MariaDB not ready after {timeout} seconds")
    return False

def wait_for_mongodb(config, timeout=60):
    """Wait for MongoDB to be ready."""
    logger.info(f"Waiting for MongoDB to be ready (timeout: {timeout}s)...")
    
    cmd = [
        'docker', 'exec', config['mongodb']['container_name'],
        'mongosh', '--eval', "db.adminCommand('ping')"
    ]
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = run_command(cmd, check=False)
        if result.returncode == 0:
            logger.info("MongoDB is ready")
            return True
        time.sleep(2)
    
    logger.error(f"MongoDB not ready after {timeout} seconds")
    return False

def initialize_mariadb(config):
    """Initialize MariaDB with required users and permissions."""
    logger.info("Initializing MariaDB...")
    
    # Create SQL script
    sql_script = f"""
    CREATE DATABASE IF NOT EXISTS {config['mariadb']['database']};
    CREATE USER IF NOT EXISTS '{config['mariadb']['user']}'@'%' IDENTIFIED BY '{config['mariadb']['password']}';
    GRANT ALL PRIVILEGES ON {config['mariadb']['database']}.* TO '{config['mariadb']['user']}'@'%';
    FLUSH PRIVILEGES;
    """
    
    # Write SQL script to a temporary file
    with open('init_mariadb.sql', 'w') as f:
        f.write(sql_script)
    
    # Copy SQL script to container
    run_command(['docker', 'cp', 'init_mariadb.sql', f"{config['mariadb']['container_name']}:/tmp/init_mariadb.sql"])
    
    # Execute SQL script
    cmd = [
        'docker', 'exec', config['mariadb']['container_name'],
        'mysql', '-u', 'root', f"-p{config['mariadb']['root_password']}",
        '-e', 'source /tmp/init_mariadb.sql'
    ]
    result = run_command(cmd)
    
    # Remove temporary file
    os.remove('init_mariadb.sql')
    run_command(['docker', 'exec', config['mariadb']['container_name'], 'rm', '/tmp/init_mariadb.sql'])
    
    logger.info("MariaDB initialized successfully")
    return True

def initialize_mongodb(config):
    """Initialize MongoDB with required users and permissions."""
    logger.info("Initializing MongoDB...")
    
    # Create MongoDB script
    js_script = f"""
    use {config['mongodb']['database']};
    db.createCollection('reviews');
    db.createCollection('loan_history');
    db.createCollection('book_texts');
    
    // Create indexes
    db.reviews.createIndex({{ book_id: 1 }});
    db.reviews.createIndex({{ user_id: 1 }});
    db.reviews.createIndex({{ created_at: 1 }});
    
    db.loan_history.createIndex({{ loan_id: 1 }});
    db.loan_history.createIndex({{ user_id: 1 }});
    db.loan_history.createIndex({{ book_id: 1 }});
    db.loan_history.createIndex({{ loan_date: 1 }});
    
    db.book_texts.createIndex({{ book_id: 1 }}, {{ unique: true }});
    db.book_texts.createIndex({{ content: "text" }}, {{ default_language: "english" }});
    """
    
    # Write JS script to a temporary file
    with open('init_mongodb.js', 'w') as f:
        f.write(js_script)
    
    # Copy JS script to container
    run_command(['docker', 'cp', 'init_mongodb.js', f"{config['mongodb']['container_name']}:/tmp/init_mongodb.js"])
    
    # Execute JS script
    cmd = [
        'docker', 'exec', config['mongodb']['container_name'],
        'mongosh', '--file', '/tmp/init_mongodb.js'
    ]
    result = run_command(cmd)
    
    # Remove temporary file
    os.remove('init_mongodb.js')
    run_command(['docker', 'exec', config['mongodb']['container_name'], 'rm', '/tmp/init_mongodb.js'])
    
    logger.info("MongoDB initialized successfully")
    return True

def show_connection_info(config):
    """Show connection information for the databases."""
    print("\n=== Database Connection Information ===")
    print(f"MariaDB:")
    print(f"  Host: localhost")
    print(f"  Port: {config['mariadb']['port']}")
    print(f"  Database: {config['mariadb']['database']}")
    print(f"  User: {config['mariadb']['user']}")
    print(f"  Password: {config['mariadb']['password']}")
    print(f"  Connection string: mysql+pymysql://{config['mariadb']['user']}:{config['mariadb']['password']}@localhost:{config['mariadb']['port']}/{config['mariadb']['database']}")
    print(f"\nMongoDB:")
    print(f"  Host: localhost")
    print(f"  Port: {config['mongodb']['port']}")
    print(f"  Database: {config['mongodb']['database']}")
    print(f"  Connection string: mongodb://localhost:{config['mongodb']['port']}/{config['mongodb']['database']}")
    print("\nEnvironment variables for .env file:")
    print(f"MARIADB_USER={config['mariadb']['user']}")
    print(f"MARIADB_PASSWORD={config['mariadb']['password']}")
    print(f"MARIADB_HOST=localhost")
    print(f"MARIADB_PORT={config['mariadb']['port']}")
    print(f"MARIADB_DB={config['mariadb']['database']}")
    print(f"MONGO_URI=mongodb://localhost:{config['mongodb']['port']}/{config['mongodb']['database']}")
    print(f"MONGO_DB_NAME={config['mongodb']['database']}")
    print("\nTo connect to the containers:")
    print(f"  MariaDB: docker exec -it {config['mariadb']['container_name']} mysql -u {config['mariadb']['user']} -p{config['mariadb']['password']} {config['mariadb']['database']}")
    print(f"  MongoDB: docker exec -it {config['mongodb']['container_name']} mongosh {config['mongodb']['database']}")

def check_container_status(config):
    """Check the status of the containers."""
    print("\n=== Container Status ===")
    
    # Check MariaDB container
    mariadb_status = run_command(['docker', 'ps', '-a', '--filter', f"name={config['mariadb']['container_name']}", '--format', '{{.Status}}'], check=False)
    if mariadb_status.returncode == 0 and mariadb_status.stdout.strip():
        print(f"MariaDB: {mariadb_status.stdout.strip()}")
    else:
        print(f"MariaDB: Not found")
    
    # Check MongoDB container
    mongodb_status = run_command(['docker', 'ps', '-a', '--filter', f"name={config['mongodb']['container_name']}", '--format', '{{.Status}}'], check=False)
    if mongodb_status.returncode == 0 and mongodb_status.stdout.strip():
        print(f"MongoDB: {mongodb_status.stdout.strip()}")
    else:
        print(f"MongoDB: Not found")

def main():
    """Main function to run the Docker initialization process."""
    args = parse_arguments()
    
    # Set logging level based on verbosity
    if args.verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif args.verbose >= 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
    
    # Check if Docker is installed and running
    docker_installed, compose_available = check_docker_installed()
    if not docker_installed:
        logger.error("Docker is not installed or not running")
        return 1
    
    # Use Docker CLI if Docker Compose is not available or --no-compose is specified
    use_compose = compose_available and not args.no_compose
    
    # Update configuration with command line arguments
    config = DEFAULT_CONFIG.copy()
    config['mariadb']['port'] = args.mariadb_port
    config['mongodb']['port'] = args.mongodb_port
    config['mariadb']['root_password'] = args.mariadb_password
    config['mariadb']['user'] = args.mariadb_user
    config['mariadb']['password'] = args.mariadb_user_password
    config['mariadb']['database'] = args.mariadb_database
    config['mongodb']['database'] = args.mongodb_database
    
    # Create data directory
    data_dir = os.path.abspath(args.data_dir)
    os.makedirs(data_dir, exist_ok=True)
    
    # Perform the requested action
    if args.action == 'status':
        check_container_status(config)
        return 0
    
    elif args.action == 'start':
        if use_compose:
            create_docker_compose_file(config, data_dir)
            if not start_containers_with_compose():
                return 1
        else:
            if not start_containers_with_cli(config, data_dir):
                return 1
        
        # Wait for databases to be ready
        if not wait_for_mariadb(config):
            logger.error("MariaDB is not ready, initialization skipped")
        else:
            initialize_mariadb(config)
        
        if not wait_for_mongodb(config):
            logger.error("MongoDB is not ready, initialization skipped")
        else:
            initialize_mongodb(config)
        
        show_connection_info(config)
    
    elif args.action == 'stop':
        if use_compose:
            if not stop_containers_with_compose():
                return 1
        else:
            if not stop_containers_with_cli(config):
                return 1
    
    elif args.action == 'restart':
        if use_compose:
            stop_containers_with_compose()
            if not start_containers_with_compose():
                return 1
        else:
            stop_containers_with_cli(config)
            if not start_containers_with_cli(config, data_dir):
                return 1
        
        # Wait for databases to be ready
        wait_for_mariadb(config)
        wait_for_mongodb(config)
        
        show_connection_info(config)
    
    elif args.action == 'reset':
        if use_compose:
            stop_containers_with_compose()
            
            # Remove volume directories
            import shutil
            mariadb_data_dir = os.path.join(data_dir, 'mariadb')
            mongodb_data_dir = os.path.join(data_dir, 'mongodb')
            if os.path.exists(mariadb_data_dir):
                shutil.rmtree(mariadb_data_dir)
            if os.path.exists(mongodb_data_dir):
                shutil.rmtree(mongodb_data_dir)
            
            create_docker_compose_file(config, data_dir)
            if not start_containers_with_compose():
                return 1
        else:
            stop_containers_with_cli(config)
            
            # Remove volume directories
            import shutil
            mariadb_data_dir = os.path.join(data_dir, 'mariadb')
            mongodb_data_dir = os.path.join(data_dir, 'mongodb')
            if os.path.exists(mariadb_data_dir):
                shutil.rmtree(mariadb_data_dir)
            if os.path.exists(mongodb_data_dir):
                shutil.rmtree(mongodb_data_dir)
            
            if not start_containers_with_cli(config, data_dir):
                return 1
        
        # Wait for databases to be ready
        if not wait_for_mariadb(config):
            logger.error("MariaDB is not ready, initialization skipped")
        else:
            initialize_mariadb(config)
        
        if not wait_for_mongodb(config):
            logger.error("MongoDB is not ready, initialization skipped")
        else:
            initialize_mongodb(config)
        
        show_connection_info(config)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())