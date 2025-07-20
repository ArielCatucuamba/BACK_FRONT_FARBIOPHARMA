# Usa una imagen base de Python
FROM python:latest


# Copia los archivos de la aplicación al contenedor
COPY . .

# Instala las dependencias
RUN apt-get update && apt-get install -y gcc 
RUN pip install Flask==2.3.2
RUN pip install Flask-MySQLdb==1.0.1
RUN pip install bcrypt==4.0.1

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python", "app.py"]
