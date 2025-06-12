FROM python:3.11-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de dependencias
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código fuente al contenedor
COPY . .

# Expone el puerto 8000 para FastAPI/Uvicorn
EXPOSE 8000

# Comando por defecto para ejecutar la app (ajusta si tu entrypoint es otro)
CMD ["python", "run.py"]