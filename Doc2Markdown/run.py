# CONFIGURACION LOCAL
import uvicorn
from app.app import app

if _name_ == "_main_":
    uvicorn.run(
        "app.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
        #ssl_keyfile="./key.pem",
        #ssl_certfile="./cert.pem"
    )