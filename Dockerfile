# Imagen base oficial y ligera de Python
FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc y habilitar logs sin búfer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente y configuraciones
COPY config/ ./config/
COPY src/ ./src/

# Exponer el puerto para Google Cloud Run (por defecto 8080)
EXPOSE 8080

# Comando de ejecución con Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
