# Usa la imagen completa de Python. Debian sirve sus repositorios por HTTPS
# para evitar respuestas intermedias/proxy que invaliden los metadatos apt.
FROM python:latest

# Copia los archivos de la aplicación al contenedor
COPY . .

# Instala el compilador que requiere mysqlclient y limpia los índices apt.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Framework web y conector de MySQL
RUN python -m pip install --no-cache-dir Flask==2.3.2 Flask-MySQLdb==1.0.1 openpyxl==3.1.5

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python", "app.py"]
