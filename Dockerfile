# 1. Usamos una versión estable y ligera de Python
FROM python:3.10-slim

# Variables de entorno para optimizar Python en Docker
# Evita que Python escriba archivos .pyc innecesarios en el contenedor
ENV PYTHONDONTWRITEBYTECODE=1
# Fuerza a Python a enviar los logs directamente a la consola en tiempo real
ENV PYTHONUNBUFFERED=1

# Le decimos a Docker que trabaje en la carpeta /app
WORKDIR /app

# Crear un usuario del sistema seguro (No-Root) y darle permisos en /app
RUN useradd -m appuser && chown -R appuser /app

# Copiamos primero las dependencias para aprovechar la caché de capas de Docker
COPY requirements.txt .

# Instalamos todo sin guardar basura caché para que ocupe el mínimo espacio
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código de nuestra web (main.py, carpetas estáticas...)
COPY . .

# Cambiamos al usuario seguro para que Gunicorn no corra como Root
USER appuser

# Exponemos el puerto 5000 para que el servidor web sea accesible
EXPOSE 5000

# Arrancamos el servidor profesional Gunicorn apuntando a main.py
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "main:app"]