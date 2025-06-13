import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Cargar variables de entorno al inicio
load_dotenv()

class Config:
    # Configuración de GitHub
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_URI = "http://127.0.0.1:8000/github/callback"  # Cambiado a puerto 8000 para FastAPI
    
    # Configuración de Azure SQL
    SQL_SERVER = os.getenv('SQL_SERVER', 'server-proyecto-patrones-u2.database.windows.net')
    SQL_DATABASE = os.getenv('SQL_DATABASE', 'DocMark')
    SQL_USERNAME = os.getenv('SQL_USERNAME', 'sqladminuser')
    SQL_PASSWORD = os.getenv('SQL_PASSWORD', 'Danilo123456@')
    SQL_DRIVER = os.getenv('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')
    
    # Cadena de conexión - Formato corregido
    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pyodbc://{SQL_USERNAME}:{quote_plus(SQL_PASSWORD)}@"
        f"{SQL_SERVER}/{SQL_DATABASE}?"
        f"driver={quote_plus('ODBC Driver 17 for SQL Server')}&"
        "encrypt=yes&"
        "trustservercertificate=no&"
        "connection_timeout=30"
    )
    
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///docmark.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de la aplicación
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../uploads')
    ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf', 'html', 'txt'}
    
    # Configuración de Markdown
    MARKDOWN_EXTENSIONS = ['extra', 'codehilite', 'tables', 'toc']
    ACCESS_TOKEN_EXPIRE_MINUTES = 30 
    SECRET_KEY = os.getenv('SECRET_KEY', 'mWJkMUtLpXO~>Qlhu|iLj~=%C,T/?fsZ')
    
    @staticmethod
    def init_app(app):
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)