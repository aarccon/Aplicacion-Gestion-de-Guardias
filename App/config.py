import os   
from dotenv import load_dotenv
import pymysql

# Cargar variables de entorno. Si no están definidas, las carga desde el archivo .env
load_dotenv()

# Variables de entorno, por si no están definidas en .venv (se deben definir en el sistema operativo)
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
SECRET_KEY = os.getenv('SECRET_KEY')

# Conexión a MySQL con pymysql
def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor  # Devuelve resultados como diccionarios
    )