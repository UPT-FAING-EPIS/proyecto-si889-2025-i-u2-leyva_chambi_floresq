import pyodbc

server = 'server-proyecto-patrones.database.windows.net'
database = 'DocMark'
username = 'sqladminuser'
password = 'Kxj0mchx@'
driver = 'ODBC Driver 17 for SQL Server'

conn_str = (
    f"DRIVER={{{driver}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

try:
    conn = pyodbc.connect(conn_str)
    print("✅ Conexión exitosa a Azure SQL Server.")
except Exception as e:
    print("❌ Error de conexión:", e)
