FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias del sistema + git-lfs para descargar la BD
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio data y descargar DuckDB desde GitHub LFS
RUN mkdir -p /app/data && \
    git clone --depth 1 https://github.com/Jefferson-GHB/Estudio_Contexto_v3.git /tmp/ec_repo && \
    cd /tmp/ec_repo && git lfs pull --include="data/repositorio.duckdb" && \
    cp /tmp/ec_repo/data/repositorio.duckdb /app/data/repositorio.duckdb && \
    rm -rf /tmp/ec_repo

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo de la aplicacion
COPY . .

# Exponer puerto de Streamlit
EXPOSE 7860

# Comando de inicio
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
