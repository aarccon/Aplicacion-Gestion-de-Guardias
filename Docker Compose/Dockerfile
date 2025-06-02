# Usa una imagen oficial de Python
FROM python:3.11-slim

# Crea el directorio de trabajo en el contenedor
WORKDIR /app

# Copia requirements.txt y lo instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el resto del proyecto
COPY . .

# Expone el puerto por el que corre Flask
EXPOSE 5000

# Comando para ejecutar la app
CMD ["python", "app.py"]