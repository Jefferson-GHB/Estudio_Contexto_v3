FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Exponer puerto de Streamlit
EXPOSE 7860

# Comando de inicio
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
