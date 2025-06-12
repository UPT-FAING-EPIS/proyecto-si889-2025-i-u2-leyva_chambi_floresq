# CONFIGURACION DE PRODUCCION ACTUALIZADA 
import uvicorn
from app.app import app

if __name__ == "__main__":
    uvicorn.run(
        "app.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )

# CONFIGURACION LOCAL ACTUALIZADA 
# import uvicorn
# from app.app import app

# if __name__ == "__main__":
#    uvicorn.run(
#        "app.app:app",
#        host="127.0.0.1",
#        port=8000,
#        reload=True
#        #ssl_keyfile="./key.pem",
#        #ssl_certfile="./cert.pem"
#    )